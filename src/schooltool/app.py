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
SchoolTool application

$Id$

"""

from persistent import Persistent

import zope.interface
from zope.app import zapi
from zope.app.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.app.container import btree, contained
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.app.security.interfaces import IUnauthenticatedGroup
from zope.app.site.servicecontainer import SiteManagerContainer

from schoolbell.relationship import RelationshipProperty
from schoolbell.relationship.relationship import BoundRelationshipProperty
from schoolbell.app import app as sb
from schoolbell.app.cal import Calendar
from schoolbell.app.group.group import Group
from schoolbell.app.membership import URIMembership, URIGroup, URIMember
from schoolbell.app.overlay import choose_color, DEFAULT_COLORS
from schoolbell.app.overlay import OverlaidCalendarsProperty
from schoolbell.app.overlay import BoundOverlaidCalendarsProperty
from schoolbell.app.overlay import CalendarOverlayInfo
from schoolbell.app.group.interfaces import IGroup
from schoolbell.app.person.interfaces import IPerson
from schoolbell.app.person.person import Person as SBPerson
from schoolbell.app.resource.interfaces import IResource

from schooltool import SchoolToolMessageID as _
from schooltool import interfaces, relationships

###############################################################################
# Import objects here, since they will eventually move here as well.

from schoolbell.app.app import SchoolBellApplication as SchoolToolApplication
from schoolbell.app.app import getApplicationPreferences
from schoolbell.app.app import \
     getSchoolBellApplication as getSchoolToolApplication

###############################################################################


def addManagerGroupToApplication(event):
    event.object['groups']['manager'] = Group(u'Manager', u'Manager Group.')


class OverlaidCalendarsAndTTProperty(object):
    """Property for `overlaid_calendars` in SchoolTool.

    Stores the list of overlaid calendars in relationships.

    Example:

        >>> class SomeClass(object): # must be a new-style class
        ...     calendars = OverlaidCalendarsAndTTProperty()

        >>> someinstance = SomeClass()
        >>> someinstance.calendars
        <schooltool.app.BoundOverlaidCalendarsAndTTProperty object at 0x...>

    """

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return BoundOverlaidCalendarsAndTTProperty(instance)


class BoundOverlaidCalendarsAndTTProperty(BoundOverlaidCalendarsProperty):
    """Bound property for `overlaid_calendars` in SchoolTool.

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schoolbell.relationship.tests import SomeObject
        >>> from schoolbell.relationship import getRelatedObjects
        >>> setUp()

    Given a relatable object, and a relatable calendar

        >>> a = SomeObject('a')
        >>> cal = SomeObject('cal')

    we can create a BoundOverlaidCalendarsProperty

        >>> overlaid_calendars = BoundOverlaidCalendarsAndTTProperty(a)

    The `add` method establishes a URICalendarSubscriber relationship

        >>> overlaid_calendars.add(cal, show=False, show_timetables=False,
        ...                        color1="red", color2="green")

        >>> from schoolbell.app.overlay import URICalendarProvider
        >>> from schoolbell.app.overlay import URICalendarSubscriber
        >>> getRelatedObjects(a, URICalendarProvider)
        [cal]
        >>> getRelatedObjects(cal, URICalendarSubscriber)
        [a]

    You can extract these when iterating

        >>> for item in overlaid_calendars:
        ...     print item.calendar, item.show, item.show_timetables
        ...     print item.color1, item.color2
        cal False False
        red green

    We're done.

        >>> tearDown()

    """

    def add(self, calendar, show=True, show_timetables=True,
            color1=None, color2=None):
        if not color1 or not color2:
            used_colors = [(item.color1, item.color2) for item in self]
            color1, color2 = choose_color(DEFAULT_COLORS, used_colors)
        info = CalendarAndTTOverlayInfo(calendar, show, show_timetables,
                                        color1, color2)
        info.__parent__ = self.this
        BoundRelationshipProperty.add(self, calendar, info)


class CalendarAndTTOverlayInfo(CalendarOverlayInfo):
    """Tests for CalendarAndTTOverlayInfo.

    CalendarAndTTOverlayInfo is much like the ordinary CalendarOverlayInfo
    object, with one difference: it has an extra attribute `show_timetables`.

        >>> calendar = object()
        >>> item = CalendarAndTTOverlayInfo(calendar, True, False,
        ...                                 'red', 'yellow')

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(interfaces.ICalendarAndTTOverlayInfo, item)
        True

        >>> item.show
        True
        >>> item.show_timetables
        False

    The `show_timetables` attribute is changeable:

        >>> item.show_timetables = True

    """

    zope.interface.implements(interfaces.ICalendarAndTTOverlayInfo)

    def __init__(self, calendar, show, show_timetables, color1, color2):
        self._calendar = calendar
        self.show = show
        self.show_timetables = show_timetables
        self.color1 = color1
        self.color2 = color2


class Person(SBPerson):

    overlaid_calendars = OverlaidCalendarsAndTTProperty()


class CourseContainer(btree.BTreeContainer):
    """Container of Courses."""

    zope.interface.implements(interfaces.ICourseContainer,
                              IAttributeAnnotatable)


def addCourseContainerToApplication(event):
    event.object['courses'] = CourseContainer()


class Course(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ICourseContained,
                              interfaces.IHaveNotes,
                              IAttributeAnnotatable)

    sections = RelationshipProperty(relationships.URICourseSections,
                                    relationships.URICourse,
                                    relationships.URISectionOfCourse)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


class Section(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ISectionContained,
                              interfaces.IHaveNotes, IAttributeAnnotatable)

    def __init__(self, title="Section", description=None, schedule=None,
                 courses=None, location=None):
        self.title = title
        self.description = description
        self.calendar = Calendar(self)
        self.location = location


    def _getLabel(self):
        instructors = " ".join([i.title for i in self.instructors])
        courses = " ".join([c.title for c in self.courses])
        msg = _('${instructors} -- ${courses}')
        msg.mapping = {'instructors': instructors, 'courses': courses}
        return msg

    label = property(_getLabel)

    def _getSize(self):
        size = 0
        for member in self.members:
            if IPerson.providedBy(member):
                size = size + 1
            if IGroup.providedBy(member):
                size = size + len(member.members)

        return size

    size = property(_getSize)

    _location = None

    def _setLocation(self, location):
        if location is not None:
            if (not IResource.providedBy(location) or not location.isLocation):
                raise TypeError("Locations must be location resources.")
        self._location = location

    location = property(lambda self: self._location, _setLocation)

    instructors = RelationshipProperty(relationships.URIInstruction,
                                       relationships.URISection,
                                       relationships.URIInstructor)

    courses = RelationshipProperty(relationships.URICourseSections,
                                   relationships.URISectionOfCourse,
                                   relationships.URICourse)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)


class SectionContainer(btree.BTreeContainer):
    """Container of Sections."""

    zope.interface.implements(interfaces.ISectionContainer,
                              IAttributeAnnotatable)


def addSectionContainerToApplication(event):
    event.object['sections'] = SectionContainer()


class ApplicationPreferences(sb.ApplicationPreferences):
    """Object for storing any application-wide preferences we have."""

    title = 'SchoolTool'


def applicationCalendarPermissionsSubscriber(event):
    """Set the default permissions for schooltool.

    By default view and viewCalendar are granted for unauthenticated users to
    the top level application so that everyone can see the front page and the
    the sitewide calendar without logging in.

    Because permissions are applied recursively, we must restrict access
    explicitly to the areas of the site that should not be public.

    By default we restrict:
        school/persons
        school/groups
        school/resources
        school/sections
        school/courses

    """
    if not IObjectAddedEvent.providedBy(event):
        # TODO: Do we need to do this in python if the subscriber is set in
        # zcml?
        return

    if interfaces.ISchoolToolApplication.providedBy(event.object):
        unauthenticated = zapi.queryUtility(IUnauthenticatedGroup)

        app_perms = IPrincipalPermissionManager(event.object)
        app_perms.grantPermissionToPrincipal('schoolbell.view',
                                          unauthenticated.id)
        app_perms.grantPermissionToPrincipal('schoolbell.viewCalendar',
                                          unauthenticated.id)

        for container in ['persons', 'groups', 'resources', 'sections',
                          'courses']:
            container_perms = IPrincipalPermissionManager(event.object[container])
            container_perms.denyPermissionToPrincipal('schoolbell.view',
                                              unauthenticated.id)
            container_perms.denyPermissionToPrincipal('schoolbell.viewCalendar',
                                              unauthenticated.id)
