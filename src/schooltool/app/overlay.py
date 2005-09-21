#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Calendar overlays.

This module defines relationships used to store calendar subscriptions.

    >>> from zope.app.testing import setup
    >>> setup.placelessSetUp()
    >>> setup.setUpAnnotations()

    >>> from schooltool.testing import setup as sbsetup
    >>> sbsetup.setupCalendaring()

    >>> from schooltool.relationship.tests import setUpRelationships
    >>> setUpRelationships()

We will need some sample persons and groups for the demonstration

    >>> from schooltool.group.group import Group
    >>> from schooltool.person.person import Person
    >>> john = Person(title="John")
    >>> smith = Person(title="Smith")
    >>> developers = Group(title="Developers")
    >>> admins = Group(title="Admins")

Let's say John wants to see the calendars of Smith and the Developers group
overlaid on his own calendar

    >>> john.overlaid_calendars.add(ISchoolToolCalendar(smith))
    >>> john.overlaid_calendars.add(ISchoolToolCalendar(developers))

He also wants the Admins group calendar to be displayed in the overlaid
calendars portlet, but hidden by default:

    >>> john.overlaid_calendars.add(ISchoolToolCalendar(admins), show=False)

Iterating over `overlaid_calendars` returns ICalendarOverlayInfo objects

    >>> for item in john.overlaid_calendars:
    ...     checked = item.show and "+" or " "
    ...     title = item.calendar.__parent__.title
    ...     print "[%s] %-10s (%s, %s)" % (checked, title,
    ...                                    item.color1, item.color2)
    [+] Smith      (#e0b6af, #c1665a)
    [+] Developers (#eed680, #d1940c)
    [ ] Admins     (#c5d2c8, #83a67f)

However, 'in' checks for the presence of a calendar

    >>> ISchoolToolCalendar(smith) in john.overlaid_calendars
    True
    >>> ISchoolToolCalendar(Person(title="Newcomer")) in john.overlaid_calendars
    False

Clean up

    >>> setup.placelessTearDown()

"""

import sys
from persistent import Persistent
from zope.proxy import getProxiedObject
from zope.interface import Interface, implements
from zope.schema import Object, TextLine, Bool
from zope.security.proxy import removeSecurityProxy
from zope.app.container.interfaces import IObjectRemovedEvent

from schooltool.relationship import URIObject
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.relationship import BoundRelationshipProperty
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IHaveCalendar
from schooltool.relationship.relationship import unrelateAll


URICalendarSubscription = URIObject(
                "http://schooltool.org/ns/calendar_subscription",
                "Calendar subscription",
                "The calendar subscription relationship.")

URICalendarProvider = URIObject(
                "http://schooltool.org/ns/calendar_subscription/provider",
                "Calendar provider",
                "A role of an object providing a calendar.")

URICalendarSubscriber = URIObject(
                "http://schooltool.org/ns/calendar_subscription/subscriber",
                "Calendar subscriber",
                "A role of an object that subscribes to a calendar.")


DEFAULT_COLORS = (
        ('#e0b6af', '#c1665a'), # Red Highlight, Red Medium
        ('#eed680', '#d1940c'), # Accent Yellow, Accent Yellow Dark
        ('#c5d2c8', '#83a67f'), # Green Highlight, Green Medium
        ('#efe0cd', '#e0c39e'), # Face Skin Highlight, Face Skin Medium
        ('#ada7c8', '#887fa3'), # Purple Highlight, Purple Medium
        ('#eae8e3', '#bab5ab'), # Basic 3D Highlight, Basic 3D Medium
        ('#e0c39e', '#b39169'), # Face Skin Medium, Face Skin Dark
        ('#c1665a', '#884631'), # Red Medium, Red Dark
        ('#b39169', '#826647'), # Face Skin Dark, Face Skin Shadow
        ('#83a67f', '#5d7555'), # Green Medium, Green Dark
    )


class ICalendarOverlayInfo(Interface):
    """Information about an overlaid calendar."""

    calendar = Object(
            title=u"Calendar",
            schema=ISchoolToolCalendar,
            description=u"""
            Calendar.
            """)

    color1 = TextLine(
            title=u"Color 1",
            description=u"""
            Color for this calendar.

            This is a string that is acceptable as a CSS color, e.g. '#ccffee'.
            """)

    color2 = TextLine(
            title=u"Color 2",
            description=u"""
            Color for this calendar.

            This is a string that is acceptable as a CSS color, e.g. '#ccffee'.
            """)

    show = Bool(
            title=u"Show",
            description=u"""
            An option that controls whether events from this calendar are shown
            in the calendar views (show=True), or if they are only listed in
            the portlet (show=False).
            """)


class IOverlaidCalendarsProperty(Interface):
    """A property for maintaining a list of overlaid calendars."""

    def __nonzero__():
        """Are there any overlaid calendars?"""

    def __len__():
        """Return the number of overlaid calendars."""

    def __contains__(calendar):
        """Check whether `calendar` is in the list."""

    def __iter__():
        """Iterate over all overlaid calendars.

        Returns ICalendarOverlayInfo objects.  Iteration order is unspecified.
        """

    def add(calendar, show=True, color1=None, color2=None):
        """Add `calendar` to the list.

        If `color1` or `color2` is not specified, a pair of colours are chosen
        from a list of standard colors.  The color chooser tries to minimize
        color conflicts with other overlaid calendars.
        """

    def remove(calendar):
        """Remove `calendar` from the list."""


class OverlaidCalendarsProperty(object):
    """Property for `overlaid_calendars`.

    Stores the list of overlaid calendars in relationships.

    Example:

        >>> class SomeClass(object): # must be a new-style class
        ...     calendars = OverlaidCalendarsProperty()

        >>> from zope.interface.verify import verifyObject
        >>> someinstance = SomeClass()
        >>> verifyObject(IOverlaidCalendarsProperty, someinstance.calendars)
        True

    """

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return BoundOverlaidCalendarsProperty(instance)


class BoundOverlaidCalendarsProperty(BoundRelationshipProperty):
    """Bound property for `overlaid_calendars`

    Stores the list of overlaid calendars in relationships.

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.relationship.tests import SomeObject
        >>> from schooltool.relationship import getRelatedObjects
        >>> setUp()

    Given a relatable object, and a relatable calendar

        >>> a = SomeObject('a')
        >>> cal = SomeObject('cal')

    we can create a BoundOverlaidCalendarsProperty

        >>> overlaid_calendars = BoundOverlaidCalendarsProperty(a)

    The `add` method establishes a URICalendarSubscriber relationship

        >>> overlaid_calendars.add(cal)
        >>> getRelatedObjects(a, URICalendarProvider)
        [cal]
        >>> getRelatedObjects(cal, URICalendarSubscriber)
        [a]

    `__nonzero__` and `__len__` do the obvious things

        >>> bool(overlaid_calendars)
        True
        >>> len(overlaid_calendars)
        1

    The `remove` method breaks it

        >>> overlaid_calendars.remove(cal)
        >>> len(overlaid_calendars)
        0
        >>> bool(overlaid_calendars)
        False
        >>> getRelatedObjects(a, URICalendarProvider)
        []
        >>> getRelatedObjects(cal, URICalendarSubscriber)
        []

    You can specify extra arguments for `add`

        >>> overlaid_calendars.add(cal, show=False,
        ...                        color1="red", color2="green")

    You can extract these when iterating

        >>> for item in overlaid_calendars:
        ...     print item.calendar, item.show, item.color1, item.color2
        cal False red green

    We're done.

        >>> tearDown()

    """

    implements(IOverlaidCalendarsProperty)

    def __init__(self, this):
        BoundRelationshipProperty.__init__(self, this, URICalendarSubscription,
                                           URICalendarSubscriber,
                                           URICalendarProvider)
        # for the local grants to work
        self.__parent__ = this

    def add(self, calendar, show=True, color1=None, color2=None):
        if not color1 or not color2:
            used_colors = [(item.color1, item.color2) for item in self]
            color1, color2 = choose_color(DEFAULT_COLORS, used_colors)
        info = CalendarOverlayInfo(calendar, show, color1, color2)
        info.__parent__ = self.this
        BoundRelationshipProperty.add(self, calendar, info)

    def __contains__(self, calendar):
        for item in self:
            if item.calendar is calendar:
                return True
        return False

    def __iter__(self):
        for link in IRelationshipLinks(self.this):
            if link.role == self.other_role and link.rel_type == self.rel_type:
                yield link.extra_info


class CalendarOverlayInfo(Persistent):
    """Information about an overlaid calendar.

        >>> from zope.interface.verify import verifyObject
        >>> calendar = object()
        >>> item = CalendarOverlayInfo(calendar, True, 'red', 'yellow')
        >>> verifyObject(ICalendarOverlayInfo, item)
        True

    The calendar attribute must be read-only, because a CalendarOverlayInfo is
    stored as an attribute on a specific relationship with a specific calendar
    object.

        >>> item.calendar = object()
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

    `show`, `color1` and `color2` attributes are changeable

        >>> item.show = True
        >>> item.color1 = 'blue'
        >>> item.color2 = 'black'

    """

    implements(ICalendarOverlayInfo)

    calendar = property(lambda self: self._calendar)

    def __init__(self, calendar, show, color1, color2):
        self._calendar = calendar
        self.show = show
        self.color1 = color1
        self.color2 = color2


def choose_color(colors, used_colors):
    """Choose a color, avoiding colors that have been used already.

        >>> colors = ('red', 'green', 'blue')

    choose_color picks the first unused color.

        >>> choose_color(colors, [])
        'red'
        >>> choose_color(colors, ['red'])
        'green'
        >>> choose_color(colors, ['green', 'red'])
        'blue'

    If all colors have been used, choose_color picks the one that
    has been used the least number of times, and if there are several
    such colors, picks the first of them.

        >>> choose_color(colors, ['green', 'red', 'blue'])
        'red'
        >>> choose_color(colors, ['green', 'red', 'blue', 'red'])
        'green'

    You can also use choose_color for color pairs

        >>> pairs = [('red', 'green'), ('red', 'yellow'), ('blue', 'green')]
        >>> choose_color(pairs, [('red', 'green')])
        ('red', 'yellow')

    """
    if not colors:
        raise ValueError("no colors to choose from")
    used_count = {}
    for c in used_colors:
        used_count[c] = used_count.get(c, 0) + 1
    min_count = sys.maxint
    for c in colors:
        count = used_count.get(c, 0)
        if count == 0:
            return c
        if count < min_count:
            best_color = c
            min_count = count
    return best_color


def unrelateCelandarOnDeletion(event):
    """When you delete an object, relationships of it's calendar should be removed

        >>> from zope.app.testing import setup
        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.testing.setup import setupCalendaring

        >>> setUp()
        >>> setupCalendaring()

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schooltool.app.overlay import unrelateCelandarOnDeletion
        >>> zope.event.subscribers.append(unrelateCelandarOnDeletion)


    We will need some object that implements IHaveCalendar for that:

        >>> from zope.app.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> from schooltool.person.person import Person
        >>> container = BTreeContainer()
        >>> container['jonas'] = jonas = Person(username="Jonas")
        >>> container['petras'] = petras =  Person(username="Petras")

    Let's add calendar of Petras to the list of overlaid calendars:

        >>> jonas.overlaid_calendars.add(ISchoolToolCalendar(petras))
        >>> list(jonas.overlaid_calendars)
        [<schooltool.app.overlay.CalendarOverlayInfo object at ...>]

    If we delete Petras - Jonas should have no calendars in his overlay list:

        >>> del container['petras']
        >>> list(jonas.overlaid_calendars)
        []

    Restore old subscribers:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """
    if not IObjectRemovedEvent.providedBy(event):
        return
    # event.object may be a ContainedProxy
    obj = getProxiedObject(event.object)
    if not IHaveCalendar.providedBy(obj):
        return
    calendar = ISchoolToolCalendar(obj)
    linkset = IRelationshipLinks(calendar, None)
    if linkset is not None:
        unrelateAll(calendar)
