#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Browser views for calendaring.

$Id$
"""

from datetime import datetime, date, time, timedelta
from sets import Set
from zope.interface import implements
from schooltool.browser import View, Template, absoluteURL
from schooltool.browser.auth import TeacherAccess, PrivateAccess, PublicAccess
from schooltool.cal import Calendar, CalendarEvent, Period
from schooltool.common import to_unicode, parse_datetime
from schooltool.component import traverse, getPath
from schooltool.interfaces import IResource, ICalendar, ICalendarEvent
from schooltool.translation import ugettext as _
from schooltool.common import parse_date


__metaclass__ = type


class BookingView(View):

    __used_for__ = IResource

    authorization = TeacherAccess

    template = Template('www/booking.pt')

    error = u""

    owner_name = u""
    start_date = u""
    start_time = u""
    duration = u""

    booked = False

    def update(self):
        request = self.request
        if 'CONFIRM_BOOK' not in request.args:
            if 'start' in request.args:
                start = to_unicode(request.args['start'][0])
                parts = start.split(' ')
                self.start_date = parts[0]
                self.start_time = ":".join(parts[1].split(':')[:2])
            if 'mins' in request.args:
                self.duration = to_unicode(request.args['mins'][0])
            self.owner_name = request.authenticated_user.__name__
            return

        force = 'conflicts' in request.args

        start_date_str = to_unicode(request.args['start_date'][0])
        start_time_str = to_unicode(request.args['start_time'][0])
        duration_str = to_unicode(request.args['duration'][0])

        self.start_date = start_date_str
        self.start_time = start_time_str
        self.duration = duration_str

        if 'owner' in request.args:
            if not self.isManager():
                self.error = _("Only managers can set the owner")
                return
            persons = traverse(self.context, '/persons')
            self.owner_name = to_unicode(request.args['owner'][0])
            try:
                owner = persons[self.owner_name]
            except KeyError:
                self.error = _("Invalid owner: %s") % self.owner_name
                return
        else:
            owner = request.authenticated_user
            self.owner_name = owner.__name__

        try:
            start = parse_datetime('%s %s:00' % (start_date_str,
                                                 start_time_str))
        except ValueError:
            self.error = _("Invalid date/time")
            return

        try:
            duration = timedelta(minutes=int(duration_str))
        except ValueError:
            self.error = _("Invalid duration")
            return

        self.booked = self.book(owner, start, duration, force=force)

    def book(self, owner, start, duration, force=False):
        if not force:
            p = Period(start, duration)
            for e in self.context.calendar:
                if p.overlaps(Period(e.dtstart, e.duration)):
                    self.error = _("The resource is busy at specified time")
                    return False

        title = _('%s booked by %s') % (self.context.title, owner.title)
        ev = CalendarEvent(start, duration, title, owner, self.context)
        self.context.calendar.addEvent(ev)
        owner.calendar.addEvent(ev)
        self.request.appLog(_("%s (%s) booked by %s (%s) at %s for %s") %
                            (getPath(self.context), self.context.title,
                             getPath(owner), owner.title, start, duration))
        return True


class CalendarDay:
    """A single day in a calendar.

    The attribute `date` is the day as a date() object,
    `events` is list of events that took place that day, sorted by start time.

    """

    def __init__(self, date, events=None):
        self.date = date
        if events is None:
            self.events = []
        else:
            self.events = events

    def __cmp__(self, other):
        return cmp(self.date, other.date)


class CalendarViewBase(View):

    __used_for__ = ICalendar

    authorization = PrivateAccess

    first_day_of_week = 0

    def renderEvent(self, event):
        view = CalendarEventView(event)
        return view.render(self.request)

    def eventClass(self, event):
        view = CalendarEventView(event)
        return view.cssClass()

    def eventShort(self, event):
        view = CalendarEventView(event)
        return view.short()

    def update(self):
        if 'date' not in self.request.args:
            self.cursor = date.today()
        else:
            self.cursor = parse_date(self.request.args['date'][0])

    def calURL(self, cal_type, cursor=None):
        if cursor is None:
            cursor = self.cursor
        return absoluteURL(self.request, self.context,
                          '%s.html?date=%s' % (cal_type, cursor))

    def iterEvents(self):
        """Iterate over the events of the calendars displayed

        This is a hook for subclasses that have to iterate over
        several calendars.
        """
        return iter(self.context)

    def getDays(self, start, end):
        """Get a list of CalendarDay objects for a selected period of time.

        `start` and `end` (date objects) are bounds (half-open) for the result.

        Events spanning more than one day get included in all days they overlap.
        """
        events = {}
        dt = start
        while dt < end:
            events[dt] = []
            dt += timedelta(days=1)

        for event in self.iterEvents():
            event_day = event.dtstart.date()
            event_start_date = event.dtstart.date()
            event_end_date = (event.dtstart + event.duration).date()
            while (event_start_date <= event_day <= event_end_date
                   and start <= event_day < end):
                events[event_day].append(event)
                event_day += event_day.resolution

        days = []
        for day in events.keys():
            events[day].sort()
            days.append(CalendarDay(day, events[day]))
        days.sort()
        return days

    def getWeek(self, dt):
        """Return the week that contains the day dt.

        Returns a list of CalendarDay objects."""
        delta = dt.weekday() - self.first_day_of_week
        if delta < 0:
            delta += 7
        start = dt - timedelta(delta)
        end = start + timedelta(7)
        return self.getDays(start, end)

    def getMonth(self, dt):
        """Return a nested list of days in the month that contains dt.

        Returns a list of lists of date objects.  Days in neighbouring
        months are included if they fall into a week that contains days in
        the current month.
        """
        day = (date(dt.year, dt.month, 1))
        prev_month = (dt.month == 1 and 12) or dt.month - 1

        weeks = []
        while True:
            week = self.getWeek(day)
            if week[0].date.month not in (dt.month, prev_month):
                break
            weeks.append(week)
            day += timedelta(days=7)
        return weeks

    def getYear(self, dt):
        """Return the current year.

        This returns a list of quarters, each quarter is a list of months,
        each month is a list of weeks, and each week is a list of CalendarDays.
        Ouch!
        """
        # XXX This is probably going to be *really* slow :((

        # alga 2004-08-16:  I ran benchmarks by measuring time.clock()
        # in request.render.
        # On a populated calendar (/person/000001/calendar in 2003)
        # with a warm cache this gets rendered in 1.5..2.0 seconds.
        #
        # The manager's calendar (empty) gets rendered in 1.4..1.8 seconds.
        #
        # Measuring execution time of this function results in times
        # in order of 0.1 second, that is most time is spent loops in
        # the page template.
        quarters = []
        for q in range(4):
            quarter = [self.getMonth(date(dt.year, month + (q * 3), 1))
                       for month in range(1, 4)]
            quarters.append(quarter)
        return quarters


class DailyCalendarView(CalendarViewBase):
    """Daily calendar view.

    The events are presented as boxes on a 'sheet' with rows
    representing hours.

    The challenge here is to present the events as a table, so that
    the overlapping events are displayed side by side, and the size of
    the boxes illustrates the duration of the events.
    """

    __used_for__ = ICalendar

    authorization = PrivateAccess

    template = Template("www/cal_daily.pt")

    starthour = 8
    endhour = 19

    def prev(self):
        return self.cursor - timedelta(1)

    def next(self):
        return self.cursor + timedelta(1)

    def dayEvents(self, date):
        """Return events for a day sorted by start time.

        Events spanning several days and overlapping with this day
        are included.
        """

        # The following will be enough when getDays will include
        # events spanning several days into all CalendarDays.
        #
        #day = self.getDays(date, date + timedelta(1))[0]
        #return day.events

        cal = Calendar()
        cal.update(self.iterEvents())
        events = list(cal.byDate(date))
        events.sort()
        return events

    def getColumns(self):
        """Return the maximum number of events overlapping"""
        spanning = Set()
        overlap = 1
        for event in self.dayEvents(self.cursor):
            for oldevent in spanning.copy():
                if oldevent.dtstart + oldevent.duration <= event.dtstart:
                    spanning.remove(oldevent)
            spanning.add(event)
            if len(spanning) > overlap:
                overlap = len(spanning)
        return overlap

    def _setRange(self, events):
        """Sets the starthour and endhour attributes according to the events

        The range of the hours to display is the union of the range
        8:00-18:00 and time spans of all the events in the events
        list.
        """
        for event in events:
            start = (datetime.combine(self.cursor, time()) +
                     timedelta(hours=self.starthour))
            end = (datetime.combine(self.cursor, time()) +
                   timedelta(hours=self.endhour))
            if event.dtstart < start:
                newstart = max(datetime.combine(self.cursor, time()),
                               event.dtstart)
                self.starthour = newstart.hour

            if event.dtstart + event.duration > end:
                newend = min(
                    datetime.combine(self.cursor, time()) + timedelta(1),
                    event.dtstart + event.duration + timedelta(0, 3599))
                self.endhour = newend.hour
                if self.endhour == 0:
                    self.endhour = 24

    def getHours(self):
        """Return an iterator over columns of the table"""
        nr_cols = self.getColumns()
        events = self.dayEvents(self.cursor)
        self._setRange(events)
        slots = Slots()
        for hour in range(self.starthour, self.endhour):
            start = datetime.combine(self.cursor, time(hour, 0))
            end = start + timedelta(hours=1)

            # Remove the events that have already ended
            for i in range(nr_cols):
                ev = slots.get(i, None)
                if ev is not None and ev.dtstart + ev.duration <= start:
                    del slots[i]

            # Add events that start during (or before) this hour
            while (events and events[0].dtstart < end):
                event = events.pop(0)
                slots.add(event)
            cols = []

            # Format the row
            for i in range(nr_cols):
                ev = slots.get(i, None)
                if (ev is not None
                    and ev.dtstart < start
                    and hour != self.starthour):
                    # The event started before this hour (except first row)
                    cols.append('')
                else:
                    # Either None, or new event
                    cols.append(ev)

            yield {'time': "%d:00" % hour, 'cols': tuple(cols)}

    def rowspan(self, event):
        """Calculate how many hours the event will take today"""
        start = datetime.combine(self.cursor, time(self.starthour))
        end = (datetime.combine(self.cursor, time()) +
               timedelta(hours=self.endhour))

        eventstart = event.dtstart
        eventend = event.dtstart + event.duration

        if event.dtstart < start:
            eventstart = start
        if end < event.dtstart + event.duration:
            eventend = end

        duration = eventend - eventstart
        seconds = duration.days * 24 * 3600 + duration.seconds
        return (seconds - 1)/3600 + 1


class Slots(dict):
    """A dict with integer indices which assigns the lowest unused index

    Add the first value:

    >>> s = Slots()
    >>> s.add("first")
    >>> s
    {0: 'first'}

    Add second value, it gets the index 1.

    >>> s.add("second")
    >>> s
    {0: 'first', 1: 'second'}

    Remove first, add third.  It should get the index 0.

    >>> del s[0]
    >>> s.add("third")
    >>> s
    {0: 'third', 1: 'second'}
    """

    def add(self, obj):
        i = 0
        while True:
            if i in self:
                i += 1
                continue
            else:
                self[i] = obj
                break


class WeeklyCalendarView(CalendarViewBase):

    template = Template("www/cal_weekly.pt")

    def prevWeek(self):
        """Return the day a week before."""
        return self.cursor - timedelta(7)

    def nextWeek(self):
        """Return the day a week after."""
        return self.cursor + timedelta(7)

    def getCurrentWeek(self):
        """Return the current week as a list of CalendarDay objects."""
        return self.getWeek(self.cursor)


class MonthlyCalendarView(CalendarViewBase):

    template = Template("www/cal_monthly.pt")

    def prevMonth(self):
        """Return the first day of the previous month."""
        prev_lastday = (date(self.cursor.year, self.cursor.month, 1)
                        - timedelta(days=1))
        return date(prev_lastday.year, prev_lastday.month, 1)

    def nextMonth(self):
        """Return the first day of the next month."""
        next_someday = (date(self.cursor.year, self.cursor.month, 28)
                        + timedelta(7))
        return date(next_someday.year, next_someday.month, 1)

    def getCurrentMonth(self):
        """Return the current month as a nested list of CalendarDays."""
        return self.getMonth(self.cursor)


class YearlyCalendarView(CalendarViewBase):

    template = Template('www/cal_yearly.pt')

    def prevYear(self):
        """Return the first day of the next year."""
        return date(self.cursor.year - 1, 1, 1)

    def nextYear(self):
        """Return the first day of the previous year."""
        return date(self.cursor.year + 1, 1, 1)


class CalendarView(View):
    """The main calendar view.

    Switches daily, weekly, monthly, yearly calendar presentations.
    """

    authorization = PrivateAccess

    def _traverse(self, name, request):
        if name == 'weekly.html':
            return WeeklyCalendarView(self.context)
        elif name == 'daily.html':
            return DailyCalendarView(self.context)
        elif name == 'monthly.html':
            return MonthlyCalendarView(self.context)
        elif name == 'yearly.html':
            return YearlyCalendarView(self.context)
        elif name == 'add_event.html':
            return EventAddView(self.context)
        elif name == 'edit_event.html':
            return EventEditView(self.context)
        elif name == 'delete_event.html':
            return EventDeleteView(self.context)
        raise KeyError(name)

    def render(self, request):
        return str(request.redirect(
            absoluteURL(request, self.context) + '/daily.html'))


class EventViewBase(View):
    """A base class for event adding and editing views."""

    __used_for__ = ICalendar

    authorization = PrivateAccess

    template = Template('www/event_add.pt')

    error = u""
    title = u""
    start_date = u""
    start_time = u""
    duration = u"30" # default

    def update(self):
        """Parse arguments in request and put them into view attributes."""
        request = self.request

        if 'title' in request.args:
            self.title = to_unicode(request.args['title'][0])
        if 'start_date' in request.args and 'start_time' in request.args:
            self.start_date = to_unicode(request.args['start_date'][0])
            self.start_time = to_unicode(request.args['start_time'][0])
        if 'duration' in request.args:
            self.duration = to_unicode(request.args['duration'][0])

    def do_POST(self, request):
        self.update()

        if not self.title:
            self.error = _("Missing title")
            return self.do_GET(request)

        try:
            start = parse_datetime('%s %s:00' % (self.start_date,
                                                 self.start_time))
        except ValueError:
            self.error = _("Invalid date/time")
            return self.do_GET(request)

        try:
            duration = int(self.duration)
        except ValueError:
            self.error = _("Invalid duration")
            return self.do_GET(request)

        duration = timedelta(minutes=duration)

        self.process(start, duration, self.title)

        suffix = 'daily.html?date=%s' % start.date()
        url = absoluteURL(request, self.context, suffix)
        return self.redirect(url, request)

    def process(self, dtstart, duration, title):
        raise NotImplementedError()


class EventAddView(EventViewBase):
    """A view for adding events."""

    def process(self, dtstart, duration, title):
        ev = CalendarEvent(dtstart, duration, title,
                           self.context.__parent__, self.context.__parent__)
        self.context.addEvent(ev)


class EventEditView(EventViewBase):
    """A view for editing events."""

    def update(self):
        self.event_id = to_unicode(self.request.args['event_id'][0])
        for event in self.context:
            if event.unique_id == self.event_id:
                self.event = event
                break
        else:
            raise ValueError("Invalid event_id") # XXX Unfriendly?

        self.title = self.event.title
        self.start_date = str(self.event.dtstart.date())
        self.start_time = str(self.event.dtstart.strftime("%H:%M"))
        self.duration = str(self.event.duration.seconds / 60)
        EventViewBase.update(self)

    def process(self, dtstart, duration, title):
        self.context.removeEvent(self.event)
        ev = CalendarEvent(dtstart, duration, title,
                           self.context.__parent__, self.context.__parent__)
        self.context.addEvent(ev)


class EventDeleteView(View):
    """A view for deleting events."""

    __used_for__ = ICalendar

    authorization = PrivateAccess

    def do_GET(self, request):
        event_id = to_unicode(request.args['event_id'][0])
        for event in self.context:
            if event.unique_id == event_id:
                suffix = 'daily.html?date=%s' % event.dtstart.date()
                self.context.removeEvent(event)
                url = absoluteURL(request, self.context, suffix)
                return self.redirect(url, request)
        else:
            raise ValueError("Invalid event_id") # XXX Unfriendly?


def EventSourceDecorator(e, source):
    """A decorator for an ICalendarEvent that provides a 'source' attribute

    Here we rely on the fact that CalendarEvents are immutable.
    """
    result = CalendarEvent(e.dtstart, e.duration, e.title, e.context, e.owner)
    result.source = source
    return result


class CalendarComboMixin(View):
    """Mixin for views over all calendars of a person.

    The calendar events are decorated with a 'source' attribute, which
    is a name of the calendar the event is from.
    """

    def iterEvents(self):
        """Iterate over the events of the calendars displayed"""

        for event in self.context:
            decorated = EventSourceDecorator(event, 'calendar')
            yield decorated

        for event in self.context.__parent__.makeCalendar():
            decorated = EventSourceDecorator(event, 'timetable-calendar')
            yield decorated


class ComboDailyCalendarView(CalendarComboMixin, DailyCalendarView):
    pass


class ComboWeeklyCalendarView(CalendarComboMixin, WeeklyCalendarView):
    pass


class ComboMonthlyCalendarView(CalendarComboMixin, MonthlyCalendarView):
    pass


class ComboCalendarView(CalendarView):
    """A view combining several calendars.

    This view will display events from both a private and timetable
    calendars of an application object.
    """

    def _traverse(self, name, request):
        if name == 'weekly.html':
            return ComboWeeklyCalendarView(self.context)
        elif name == 'daily.html':
            return ComboDailyCalendarView(self.context)
        elif name == 'monthly.html':
            return ComboMonthlyCalendarView(self.context)
        elif name == 'yearly.html':
            return YearlyCalendarView(self.context)
        elif name == 'add_event.html':
            return EventAddView(self.context)
        elif name == 'edit_event.html':
            return EventEditView(self.context)
        elif name == 'delete_event.html':
            return EventDeleteView(self.context)
        raise KeyError(name)


class CalendarEventView(View):
    """Renders the inside of the event box in various calendar views"""

    __used_for__ = ICalendarEvent

    authorization = PublicAccess

    template = Template("www/cal_event.pt")

    def duration(self):
        ev = self.context
        if ev.dtstart.date() == (ev.dtstart + ev.duration).date():
            return "%s&ndash;%s" % (ev.dtstart.strftime('%H:%M'),
                              (ev.dtstart + ev.duration).strftime('%H:%M'))
        else:
            return "%s&ndash;%s" % (
                ev.dtstart.strftime('%Y-%m-%d %H:%M'),
                (ev.dtstart + ev.duration).strftime('%Y-%m-%d %H:%M'))

    def cssClass(self):
        if getattr(self.context, 'source', None) == 'timetable-calendar':
            return 'ro_event'
        else:
            return 'event'

    def short(self):
        """Short representation of the event for the monthly view"""
        ev = self.context
        end = ev.dtstart + ev.duration
        if ev.dtstart.date() == end.date():
            return "%s (%s&ndash;%s)" % (ev.title,
                                         ev.dtstart.strftime('%H:%M'),
                                         end.strftime('%H:%M'))
        else:
            return "%s (%s&ndash;%s)" % (ev.title,
                                         ev.dtstart.strftime('%b&nbsp;%d'),
                                         end.strftime('%b&nbsp;%d'))
