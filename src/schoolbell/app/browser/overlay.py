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

import urllib
from sets import Set

from zope.app.publisher.browser import BrowserView
from zope.app.traversing.api import getPath
from zope.app.traversing.browser.absoluteurl import absoluteURL
from zope.app.location.interfaces import ILocation
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canAccess

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import ISchoolBellCalendar, IPerson
from schoolbell.app.app import getSchoolBellApplication


class CalendarOverlayView(BrowserView):
    """View for the calendar overlay portlet.

    This view can be used with any context, but it gets rendered to an empty
    string unless context is the calendar of the authenticated user.

    Note that this view contains a self-posting form and handles submits that
    contain 'OVERLAY_APPLY' or 'OVERLAY_MORE' in the request.
    """

    def show_overlay(self):
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
            >>> view.show_overlay()
            False

        Person that we're looking at

            >>> from schoolbell.app.security import Principal
            >>> request.setPrincipal(Principal('id', 'title', person))
            >>> view.show_overlay()
            True

        A different person:

            >>> request.setPrincipal(Principal('id', 'title', Person()))
            >>> view.show_overlay()
            False

        """
        if not ILocation.providedBy(self.context):
            return False
        logged_in = IPerson(self.request.principal, None)
        calendar_owner = removeSecurityProxy(self.context.__parent__)
        return logged_in is calendar_owner

    def items(self):
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
        person = IPerson(self.request.principal)
        items = [(item.calendar.title,
                  {'title': item.calendar.title,
                   'id': getPath(item.calendar.__parent__),
                   'calendar': item.calendar,
                   'checked': item.show and "checked" or '',
                   'color1': item.color1,
                   'color2': item.color2})
                 for item in person.overlaid_calendars]
        items.sort()
        return [i[-1] for i in items]

    def update(self):
        """Process form submission."""
        if 'OVERLAY_MORE' in self.request:
            person = IPerson(self.request.principal)
            url = absoluteURL(person, self.request)
            url += '/calendar_selection.html'
            url += '?nexturl=%s' % urllib.quote(str(self.request.URL))
            self.request.response.redirect(url)
        if 'OVERLAY_APPLY' in self.request:
            person = IPerson(self.request.principal)
            selected = Set(self.request.get('overlay', []))
            for item in person.overlaid_calendars:
                item.show = getPath(item.calendar.__parent__) in selected


class CalendarSelectionView(BrowserView):
    """A view for calendar selection.

    This view can be used with any context, but always operates on the
    currently authenticated user's list of overlaid calendars.
    """

    error = None
    message = None

    def getCalendars(self, container):
        """List all calendars from a given container."""
        user = IPerson(self.request.principal, None)
        if user is None:
            return []
        app = getSchoolBellApplication()
        return [{'id': o.__name__,
                 'title': o.title,
                 'selected': o.calendar in user.overlaid_calendars,
                 'calendar': o.calendar}
                for o in app[container].values()
                if o is not user and canAccess(o.calendar, '__iter__')]

    persons = property(lambda self: self.getCalendars('persons'))
    groups = property(lambda self: self.getCalendars('groups'))
    resources = property(lambda self: self.getCalendars('resources'))

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
            for container in 'persons', 'groups', 'resources':
                selected = Set(self.request.form.get(container, []))
                for item in self.getCalendars(container):
                    if item['id'] in selected and not item['selected']:
                        user.overlaid_calendars.add(item['calendar'])
                    elif item['id'] not in selected and item['selected']:
                        user.overlaid_calendars.remove(item['calendar'])
            self.message = _('Saved changes.')
            nexturl = self.request.form.get('nexturl')
            if nexturl:
                self.request.response.redirect(nexturl)

