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
from zope.app.session.interfaces import ISession

from schooltool.calendar.simple import ImmutableCalendar
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.traverser.traverser import AdapterTraverserPlugin
from schooltool.resource.interfaces import IBookingCalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPerson


class BookingCalendarEvent(SimpleCalendarEvent):
    implements(IBookingCalendarEvent)


class ResourceBookingCalendar(ImmutableCalendar):
    implements(IBookingCalendar)

    def __init__(self, context):
        self.context = context
        self.__parent__ = self.context
        self.__name__ = 'booking'
        self.title = "Booking Calendar"

    def __iter__(self):
        return iter([])


ResourceBookingTraverserPlugin = AdapterTraverserPlugin(
    'booking', IBookingCalendar)


class ResourceBookingCalendarProvider(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getBookingCalendar(self, calendar, *calendars):
        events = []
        for event in calendar:
            resources = []
            for resource_calendar in calendars:
                evts = list(resource_calendar.expand(event.dtstart,
                                                     event.dtstart + event.duration))
                if not list(evts):
                    resources.append(resource_calendar.__parent__)

            if resources:
                event = BookingCalendarEvent(event.dtstart,
                                             event.duration,
                                             event.title,
                                             description=event.description,
                                             unique_id=event.unique_id)
                event.resources = resources
                event.__parent__ = None
                events.append(event)

        return ImmutableCalendar(events)

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """
        session = ISession(self.request)['schooltool.resource']

        rc = ISchoolToolApplication(None)['resources']
        resource_calendars = [ISchoolToolCalendar(rc[resource_id])
                              for resource_id in session['bookingSelection']]
        person_calendar = ISchoolToolCalendar(IPerson(self.request.principal))
        booking_calendar = self.getBookingCalendar(person_calendar,
                                                   *resource_calendars)

        yield (booking_calendar, '#9db8d2', '#7590ae')
        yield (self.context, '#aec9e3', '#88a1bd')
