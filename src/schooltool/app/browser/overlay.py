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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Calendar overlay views for the SchoolTool application.
"""

import urllib

from zope.browserpage import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.interface import implements, Interface
from zope.publisher.browser import BrowserView
from zope.traversing.api import getPath
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.location.interfaces import ILocation
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canAccess
from zope.viewlet.viewlet import ViewletBase
from zc.table.column import GetterColumn

from schooltool.common import SchoolToolMessage as _
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.app import EditRelationships
from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.browser.app import RelationshipRemoveTableMixin
from schooltool.resource.interfaces import IResourceTypeInformation
from schooltool.person.interfaces import IPerson
from schooltool import table
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.table.table import FilterWidget


class CalendarOverlayBase(object):
    """View for the calendar overlay portlet.

    This view can be used with any context, but it gets rendered to an empty
    string unless context is the calendar of the authenticated user.

    Note that this view contains a self-posting form and handles submits that
    contain 'OVERLAY_APPLY' or 'OVERLAY_MORE' in the request.
    """

    def show_overlay(self):
        """Check whether the calendar overlay portlet needs to be rendered.

            >>> from zope.app.testing import setup
            >>> setup.placelessSetUp()
            >>> setup.setUpAnnotations()

            >>> from schooltool.testing import setup as sbsetup
            >>> sbsetup.setUpCalendaring()

        The portlet is only shown when an authenticated user is looking
        at his/her calendar.

        Anonymous user:

            >>> from zope.publisher.browser import TestRequest
            >>> from schooltool.person.person import Person
            >>> request = TestRequest()
            >>> person = Person()
            >>> context = ISchoolToolCalendar(person)
            >>> view = CalendarOverlayView(context, request, None, None)
            >>> view.show_overlay()
            False

        Person that we're looking at

            >>> from schooltool.app.security import Principal
            >>> request.setPrincipal(Principal('id', 'title', person))
            >>> view.show_overlay()
            True

        A different person:

            >>> request.setPrincipal(Principal('id', 'title', Person()))
            >>> view.show_overlay()
            False

       Cleanup:

            >>> setup.placelessTearDown()

        """
        if not ILocation.providedBy(self.context):
            return False
        logged_in = removeSecurityProxy(IPerson(self.request.principal, None))
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
        items = [((item.calendar.title, getPath(item.calendar.__parent__)),
                  {'title': item.calendar.title,
                   'id': getPath(item.calendar.__parent__),
                   'calendar': item.calendar,
                   'checked': item.show and "checked" or '',
                   'color1': item.color1,
                   'color2': item.color2})
                 for item in person.overlaid_calendars
                 if canAccess(item.calendar, '__iter__')]
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
            selected = set(self.request.get('overlay', []))
            for item in person.overlaid_calendars:
                item.show = getPath(item.calendar.__parent__) in selected
            url = str(self.request.URL)
            self.request.response.redirect(url)


class CalendarOverlayView(CalendarOverlayBase, ViewletBase):
    pass


class CalendarSelectionView(BrowserView):
    """A view for calendar selection.

    This view can be used with any context, but always operates on the
    currently authenticated user's list of overlaid calendars.
    """

    error = None
    message = None

    def getCalendars(self, container):
        """List all calendars from a given container."""
        user = removeSecurityProxy(IPerson(self.request.principal, None))
        if user is None:
            return []
        app = ISchoolToolApplication(None)

        result = []
        for obj in app[container].values():
            calendar = ISchoolToolCalendar(obj)
            if obj is not user and canAccess(calendar, '__iter__'):
                result.append(
                    {'id': obj.__name__,
                     'title': obj.title,
                     'selected': calendar in user.overlaid_calendars,
                     'calendar': calendar})
        return sorted(result, key=lambda item: (item['title'], item['id']))

    def getApplicationCalendar(self):
        """Return the application calendar.

        Returns None if the user lacks sufficient permissions.
        """
        user = IPerson(self.request.principal, None)
        if user:
            app = ISchoolToolApplication(None)
            calendar = ISchoolToolCalendar(app)
            if canAccess(calendar, '__iter__'):
                return {'title': app.title,
                        'selected': calendar in user.overlaid_calendars,
                        'calendar': calendar}
        return {}

    application = property(getApplicationCalendar)
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
            self._updateSelection(user)
            self.message = _('Saved changes.')
            nexturl = self.request.form.get('nexturl')
            if nexturl:
                self.request.response.redirect(nexturl)

    def _updateSelection(self, user):
        """Apply calendar selection changes  for `user`."""
        for container in ['resources']:
            selected = set(self.request.form.get(container, []))
            for item in self.getCalendars(container):
                if item['id'] in selected and not item['selected']:
                    user.overlaid_calendars.add(item['calendar'])
                elif item['id'] not in selected and item['selected']:
                    user.overlaid_calendars.remove(item['calendar'])
        appcal = self.getApplicationCalendar().get('calendar')
        if appcal is not None:
            if ('application' in self.request and
                    appcal not in user.overlaid_calendars):
                user.overlaid_calendars.add(appcal)
            elif ('application' not in self.request and
                    appcal in user.overlaid_calendars):
                user.overlaid_calendars.remove(appcal)


class IOverlayCalendarsContainer(Interface):
    pass


class OverlayCalendarsInfo(object):
    __name__ = None
    def __init__(self, calendar, title, cal_type):
        self.calendar = calendar
        self.title = title
        self.cal_type = cal_type

class OverlayCalendarsContainer(dict):
    implements(IOverlayCalendarsContainer)

    def __init__(self):
        self.by_calendar = {}

    def __setitem__(self, key, info):
        dict.__setitem__(self, key, info)
        info.__name__ = key
        self.by_calendar[info.calendar] = info


class OverlayCalendarsFormatter(SchoolToolTableFormatter):

    def columns(self):
        title = GetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        type = GetterColumn(
            name='type',
            title=_(u"Type"),
            getter=lambda i, f: i.cal_type,
            subsort=True)
        return [title, type]


class OverlayCalendarsFilterWidget(FilterWidget):
    template = ViewPageTemplateFile('templates/f_overlay_filter_widget.pt')


class OverlayCalendarTable(table.ajax.Table):

    def columns(self):
        title = GetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        type = GetterColumn(
            name='type',
            title=_(u"Type"),
            getter=lambda i, f: i.cal_type,
            subsort=True)
        return [title, type]


class CalendarAddRelationshipTable(RelationshipAddTableMixin,
                                   OverlayCalendarTable):
    pass


class CalendarRemoveRelationshipTable(RelationshipRemoveTableMixin,
                                      OverlayCalendarTable):
    pass


class FlourishCalendarSelectionView(EditRelationships):

    current_title = _('Selected calendars')
    available_title = _('Available calendars')

    @Lazy
    def user(self):
        return IPerson(self.request.principal, None)

    def getCollection(self):
        if self.user is None:
            return []
        return self.user.overlaid_calendars

    def getResourceCalendars(self):
        if self.user is None:
            return []
        app = ISchoolToolApplication(None)
        result = []
        for obj in app['resources'].values():
            calendar = ISchoolToolCalendar(obj)
            if canAccess(calendar, '__iter__'):
                result.append(calendar)
        return result

    def getApplicationCalendar(self):
        if self.user is None:
            return None
        app = ISchoolToolApplication(None)
        calendar = ISchoolToolCalendar(app)
        if not canAccess(calendar, '__iter__'):
            return None
        return calendar

    @Lazy
    def overlay_container(self):
        container = OverlayCalendarsContainer()
        cal = self.getApplicationCalendar()
        if cal is not None:
            key = 'app.school'
            container[key] = OverlayCalendarsInfo(
                removeSecurityProxy(cal),
                cal.__parent__.title, _('School Calendar'))
        for cal in self.getResourceCalendars():
            resource = cal.__parent__
            key = 'resource.%s' % resource.__name__
            res_info = IResourceTypeInformation(resource)
            container[key] = OverlayCalendarsInfo(
                removeSecurityProxy(cal),
                resource.title, res_info.title)
        return container

    def getAvailableItemsContainer(self):
        return self.overlay_container

    def add(self, item):
        super(FlourishCalendarSelectionView, self).add(item.calendar)

    def remove(self, item):
        super(FlourishCalendarSelectionView, self).remove(item.calendar)

    def getAvailableItems(self):
        available = self.getAvailableItemsContainer()
        selected = set([removeSecurityProxy(p.calendar)
                        for p in self.getCollection()])
        return [info
                for cal, info in available.by_calendar.items()
                if cal not in selected]

    def getSelectedItems(self):
        available = self.getAvailableItemsContainer()
        selected = set([removeSecurityProxy(p.calendar)
                        for p in self.getCollection()])
        return [available.by_calendar[calendar]
                for calendar in selected
                if calendar in available.by_calendar]

    def nextURL(self):
        url = self.request.get('nexturl')
        if url is None:
            cal = ISchoolToolCalendar(self.context)
            url = absoluteURL(cal, self.request)
        return url
