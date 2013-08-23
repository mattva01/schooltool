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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Resource Booking caledar and events
"""
from zope.interface import implements
from zope.component import queryAdapter
from zope.location.location import Location, locate
from zope.publisher.interfaces import NotFound
from zope.session.interfaces import ISession

from schooltool.calendar.simple import ImmutableCalendar
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.resource.interfaces import IBookingCalendarEvent
from schooltool.resource.interfaces import IBookingTimetableEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPerson
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.calendar import ImmutableScheduleCalendar
from schooltool.traverser.traverser import TraverserPlugin


class BookingCalendarEvent(SimpleCalendarEvent):
    implements(IBookingCalendarEvent)


class BookingTimetableEvent(SimpleCalendarEvent):
    implements(IBookingTimetableEvent)


def createBookingCalendar(calendar, calendars, event_factory=BookingCalendarEvent):
    events = []
    for event in calendar:
        resources = []
        for resource_calendar in calendars:
            evts = list(resource_calendar.expand(event.dtstart,
                                                 event.dtstart + event.duration))
            if not list(evts):
                resources.append(resource_calendar.__parent__)

        if resources:
            event = event_factory(event.dtstart, event.duration,
                                  event.title,
                                  description=event.description,
                                  unique_id=event.unique_id)
            event.resources = resources
            event.__parent__ = None
            events.append(event)

    return ImmutableCalendar(events)


def getSelectedResourceCalendars(request):
    rc = ISchoolToolApplication(None)['resources']
    session = ISession(request)['schooltool.resource']
    resource_calendars = [ISchoolToolCalendar(rc[resource_id])
                          for resource_id in session['bookingSelection']]
    return resource_calendars


class ResourceBookingCalendar(ImmutableCalendar, Location):
    implements(IBookingCalendar)

    def __init__(self, context):
        self.context = context
        self.__parent__ = self.context
        self.__name__ = 'booking'
        self.title = "Booking Calendar"

    def expand(self, start, end):
        app = ISchoolToolApplication(None)

        school_timetables = ITimetableContainer(app, None)

        if school_timetables is None or school_timetables.default is None:
            return []

        calendar = ImmutableScheduleCalendar(school_timetables.default)
        events = []
        events.extend(calendar.expand(start, end))

        timetable_calendar = ImmutableCalendar(events)

        resource_calendars = getSelectedResourceCalendars(self.request)
        booking_calendar = createBookingCalendar(timetable_calendar,
                                                 resource_calendars,
                                                 event_factory=BookingTimetableEvent)
        return booking_calendar.expand(start, end)

    def __iter__(self):
        return iter([])


class ResourceBookingTraverserPlugin(TraverserPlugin):
    """Traverse to an adapter by name."""

    def traverse(self, name):
        bookingCalendar = queryAdapter(self.context, IBookingCalendar, name='')
        if bookingCalendar is None:
            raise NotFound(self.context, name, self.request)
        bookingCalendar.request = self.request
        return bookingCalendar


class ResourceBookingCalendarProvider(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """
        person_calendar = ISchoolToolCalendar(IPerson(self.request.principal))
        resource_calendars = getSelectedResourceCalendars(self.request)
        booking_calendar = createBookingCalendar(person_calendar,
                                                 resource_calendars)
        yield (booking_calendar, '#9db8d2', '#7590ae')
        yield (self.context, '#bfdaf4', '#99b2ce')
