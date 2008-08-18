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
from zope.interface import implements
from zope.session.interfaces import ISession
from zope.location.location import locate

from schooltool.common import getRequestFromInteraction
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.resource.interfaces import IBookingCalendarEvent
from schooltool.resource.interfaces import IBookingTimetableEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.interfaces import IPerson
from schooltool.term.interfaces import ITermContainer
from schooltool.timetable import TimetableActivity
from schooltool.traverser.traverser import NameTraverserPlugin


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


class ResourceBookingCalendar(ImmutableCalendar):
    implements(IBookingCalendar)

    def __init__(self, context):
        self.context = context
        self.__parent__ = self.context
        self.__name__ = 'booking'
        self.title = "Booking Calendar"

    def createFullTimetable(self, school_timetable, term):
        """Create a timetable with an activity for every possible period"""
        timetable = school_timetable.createTimetable(term)

        # must be set so event ids would get generated properly, as
        # the ids use the absolutePath.
        locate(timetable, self, 'booking-timetable')

        for day_id, day in timetable.items():
            for period_id in day.keys():
                act = TimetableActivity(title=period_id, owner=None)
                day.add(period_id, act, send_events=False)

        return timetable

    def expand(self, start, end):
        app = ISchoolToolApplication(None)
        terms = ITermContainer(app)
        school_timetables = app['ttschemas']

        events = []
        for term in terms.values():
            # date component of these timestamps are in the right
            # timezone already.
            if (term.first > end.date()) or (term.last < start.date()):
                # skip non overlapping terms
                continue

            timetable = self.createFullTimetable(school_timetables.getDefault(),
                                                 term)
            calendar = timetable.model.createCalendar(term, timetable,
                                                      start.date(),
                                                      end.date())
            events.extend(calendar.expand(start, end))

        timetable_calendar = ImmutableCalendar(events)

        resource_calendars = getSelectedResourceCalendars(self.request)
        booking_calendar = createBookingCalendar(timetable_calendar,
                                                 resource_calendars,
                                                 event_factory=BookingTimetableEvent)
        return booking_calendar.expand(start, end)

    def __iter__(self):
        return iter([])


class ResourceBookingTraverserPlugin(NameTraverserPlugin):
    """Traverse to an adapter by name."""

    traversalName = 'booking'

    def _traverse(self, request, name):
        from zope.component import queryAdapter
        bookingCalendar = queryAdapter(self.context, IBookingCalendar, name='')
        if bookingCalendar is None:
            from zope.publisher.interfaces import NotFound
            raise NotFound(self.context, name, request)

        bookingCalendar.request = request
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
