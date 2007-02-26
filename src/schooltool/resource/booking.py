#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Resource Booking caledar and events

$Id$
"""
from datetime import datetime, timedelta
from pytz import utc

from zope.interface import implements

from schooltool.calendar.simple import ImmutableCalendar
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.traverser.traverser import AdapterTraverserPlugin
from schooltool.resource.interfaces import IBookingCalendarEvent


class BookingCalendarEvent(SimpleCalendarEvent):
    implements(IBookingCalendarEvent)


class ResourceBookingCalendar(ImmutableCalendar):
    implements(IBookingCalendar)

    def __init__(self, context):
        self.context = context
        self.__parent__ = self.context
        self.__name__ = 'booking'
        self.title = "Booking Calendar"

        # XXX A test event for functional testing
        dt = utc.localize(datetime(2007, 2, 26))
        event = BookingCalendarEvent(dt, timedelta(minutes=45),
                                     "Camera", unique_id="fooo")
        event.__parent__ = None
        self._events = (event, )


ResourceBookingTraverserPlugin = AdapterTraverserPlugin(
    'booking', IBookingCalendar)


class ResourceBookingCalendarProvider(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """
        # XXX or maybe collect all the booking calendars and return
        # them?
        yield (self.context, '#9db8d2', '#7590ae')
