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
SchoolTool skin.
"""

from zope.interface import Interface
from zope.interface import implements
from zope.schema import Object
from zope.viewlet.interfaces import IViewletManager
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.browser.interfaces import IEventForDisplay
from schooltool.skin.skin import OrderedViewletManager
from schooltool.resource.interfaces import IBookingCalendarEvent


class ICalendarEventViewletManager(IViewletManager):
    """Provides a viewlet hook for daily calendar events."""


class ICalendarEventContext(Interface):
    """Schema for attributes required by CalendarEventViewletManager."""

    event = Object(IEventForDisplay)


class CalendarEventBookingViewlet(object):
    """
    This is the view class for the booking viewlet on the CalendarEventView
    """

    def bookingUrl(self, resource_id):
        url = absoluteURL(self.context, self.request)
        url = "%s/book_one_resource.html?resource_id=%s" % (url, resource_id)
        event = self.manager.event.context
        if IBookingCalendarEvent.providedBy(event):
            url = "%s&event_id=%s" % (url, event.unique_id)
        else:
            url = "%s&start_date=%s&start_time=%s&duration=%s&title=%s" % (
                url, event.dtstart.date(), event.dtstart.time(),
                event.duration.seconds, event.title)

        return url

    def listResources(self):
        return [{'id': resource.__name__, 'title': resource.title}
                for resource in self.manager.event.context.resources]


class CalendarEventViewletManager(OrderedViewletManager):
    """Viewlet manager for displaying of additional event information."""

    implements(ICalendarEventContext)
