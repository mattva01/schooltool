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
Calendar overlay views for the SchoolBell application.

$Id$
"""

from sets import Set

from zope.interface import Interface, implements
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.api import getPath
from zope.app.traversing.browser.absoluteurl import absoluteURL
from zope.security.proxy import removeSecurityProxy

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import ISchoolBellCalendar, IPerson
from schoolbell.app.app import getSchoolBellApplication


class ICalendarOverlayView(Interface):
    """A view for the calendar overlay portlet."""

    def __nonzero__():
        """Check whether the calendar overlay box should be displayed."""

    def items():
        """Return items to be shown in the calendar overlay.

        Does not include "my calendar".

        Each item is a dict with the following keys:

            'title' - title of the calendar

            'calendar' - the calendar object

            'color1', 'color2' - colors assigned to this calendar

            'id' - identifier for form controls

            'checked' - was this item checked for display (either "checked" or
            None)?

        """


class CalendarOverlayView(BrowserView):
    """@@calendar_overlay view

    This view provides information for the calendar overlay portlet rendered
    in the calendar_page macro.  It also handles form submissions for that
    portlet.

    Note that page templates should be careful to use nocall: when they only
    want to access attributes or check whether the overlay needs to be shown.
    If nocall: is omitted, the form processing code will get called.
    """

    __used_for__ = ISchoolBellCalendar

    implements(ICalendarOverlayView)

    def __nonzero__(self):
        """Check whether the calendar overlay portlet needs to be rendered.

        The portlet is only shown when an authenticated user is looking
        at his/her calendar.

        Anonymous user:

            >>> from zope.publisher.browser import TestRequest
            >>> from schoolbell.app.app import Person
            >>> request = TestRequest()
            >>> person = Person()
            >>> context = person.calendar
            >>> view = CalendarOverlayView(context, request)
            >>> bool(view)
            False

        Person that we're looking at

            >>> from schoolbell.app.security import Principal
            >>> request.setPrincipal(Principal('id', 'title', person))
            >>> bool(view)
            True

        A different person:

            >>> request.setPrincipal(Principal('id', 'title', Person()))
            >>> bool(view)
            False

        """
        logged_in = IPerson(self.request.principal, None)
        calendar_owner = removeSecurityProxy(self.context.__parent__)
        return logged_in is calendar_owner

    def items(self):
        """Return items to be shown in the calendar overlay.

        This is a short wrapper around Person's overlaid_calendars property.

            >>> from schoolbell.relationship.tests import setUp, tearDown
            >>> from zope.app.testing.setup import setUpTraversal
            >>> setUp()
            >>> setUpTraversal()

            >>> from zope.app.traversing.interfaces import IContainmentRoot
            >>> from zope.interface import directlyProvides
            >>> from schoolbell.app.app import SchoolBellApplication
            >>> app = SchoolBellApplication()
            >>> directlyProvides(app, IContainmentRoot)

            >>> from schoolbell.app.app import Person, Group
            >>> from schoolbell.app.security import Principal
            >>> person = Person('p1')
            >>> app['persons']['p1'] = person

            >>> from zope.publisher.browser import TestRequest
            >>> request = TestRequest()
            >>> request.setPrincipal(Principal('', '', person))
            >>> context = person.calendar
            >>> view = CalendarOverlayView(context, request)
            >>> view.items()
            []

            >>> group1 = Group(title="Group 1")
            >>> group2 = Group(title="Group 2")
            >>> app['groups']['g1'] = group1
            >>> app['groups']['g2'] = group2
            >>> person.overlaid_calendars.add(group2.calendar)
            >>> person.overlaid_calendars.add(group1.calendar, show=False)

            >>> from zope.testing.doctestunit import pprint
            >>> pprint(view.items())    # doctest: +ELLIPSIS
            [{'calendar': <schoolbell.app.cal.Calendar object at ...>,
              'checked': '',
              'color1': '#eed680',
              'color2': '#d1940c',
              'id': u'/groups/g1',
              'title': 'Group 1'},
             {'calendar': <schoolbell.app.cal.Calendar object at ...>,
              'checked': 'checked',
              'color1': '#e0b6af',
              'color2': '#c1665a',
              'id': u'/groups/g2',
              'title': 'Group 2'}]

            >>> tearDown()

        """
        person = IPerson(self.request.principal)
        items = [(item.calendar.__parent__.title,
                  {'title': item.calendar.__parent__.title,
                   'id': getPath(item.calendar.__parent__),
                   'calendar': item.calendar,
                   'checked': item.show and "checked" or '',
                   'color1': item.color1,
                   'color2': item.color2})
                 for item in person.overlaid_calendars]
        items.sort()
        return [i[-1] for i in items]

    def __call__(self):
        """Process form submission."""
        if 'MORE' in self.request:
            # TODO: unit test
            person = IPerson(self.request.principal)
            url = absoluteURL(person)
            self.request.response.redirect(url + '/calendar_selection.html')
        raise NotImplementedError("TODO")


class CalendarSelectionView(BrowserView):
    """A view for calendar selection.

    The context of this view is always the currently authenticated user
    (otherwise we cannot check permissions).
    """

    __used_for__ = IPerson  # TODO: make this a view on ISchoolBellApplication

    error = None
    message = None

    def persons(self):
        """List all persons."""
        user = IPerson(self.request.principal, None)
        if user is None:
            return []
        app = getSchoolBellApplication()
        # TODO: only show calendars that we can access
        return [{'id': p.__name__,
                 'title': p.title,
                 'selected': p.calendar in user.overlaid_calendars,
                 'person': p}
                for p in app['persons'].values()
                if p is not user]
    persons = property(persons)

    def update(self):
        """Process forms."""
        if 'CANCEL' in self.request:
            nexturl = self.request.form.get('nexturl')
            if nexturl:
                self.request.response.redirect(nexturl)
            return
        user = IPerson(self.request.principal, None)
        if user is None:
            return
        if 'UPDATE_SUBMIT' in self.request:
            selected = Set(self.request.form.get('people', []))
            for person in self.persons:
                if person['id'] in selected and not person['selected']:
                    user.overlaid_calendars.add(person['person'].calendar)
                elif person['id'] not in selected and person['selected']:
                    user.overlaid_calendars.remove(person['person'].calendar)
            self.message = _('Saved changes.')
            nexturl = self.request.form.get('nexturl')
            if nexturl:
                self.request.response.redirect(nexturl)

