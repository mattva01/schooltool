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

from schooltool.browser import View, Template, absoluteURL
from schooltool.browser.auth import TeacherAccess, PrivateAccess
from schooltool.cal import CalendarEvent, Period
from schooltool.common import to_unicode, parse_datetime
from schooltool.component import traverse, getPath
from schooltool.interfaces import IResource, ICalendar
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
            arg = 'start_date'
            year, month, day = map(int, start_date_str.split('-'))
            date(year, month, day) # validation
            arg = 'start_time'
            hours, seconds = map(int, start_time_str.split(':'))
            time(hours, seconds)   # validation

            start = datetime(year, month, day, hours, seconds)

            arg = 'duration'
            duration = timedelta(minutes=int(duration_str))
        except (ValueError, TypeError):
            self.error = _("%r argument incorrect") % arg
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

    Oppositely from Calendar.byDate(), events that span several days are
    included in the first one only.
    """
    # XXX I'm not sure whether we should repeat events spanning several days.

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

    def getDays(self, start, end):
        """Get a list of CalendarDay objects for a selected period of time.

        `start` and `end` (date objects) are bounds (half-open) for the result.
        """
        # XXX Multiple-day events (see the XXX above)
        events = {}
        dt = start
        while dt < end:
            events[dt] = []
            dt += timedelta(days=1)

        for event in self.context:
            event_start = event.dtstart.date()
            if start <= event_start < end:
                events[event_start].append(event)
        days = []
        for day in events.keys():
            events[day].sort()
            days.append(CalendarDay(day, events[day]))
        days.sort()
        return days

    def getWeek(self, dt):
        """Return the week that contains the day dt.

        Returns a list of CalendarDay objects."""
        # XXX Hardcoded Monday-based weeks.
        start = dt - timedelta(dt.weekday())
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

    starthour = 0
    endhour = 23

    def prev(self):
        return self.cursor - timedelta(1)

    def next(self):
        return self.cursor + timedelta(1)

    def dayEvents(self, date):
        """Return events for a day sorted by start time.

        Events spanning several days and overlapping with this day
        are included.
        """
        events = list(self.context.byDate(date))
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

    def getHours(self):
        """Return an iterator over columns of the table"""
        nr_cols = self.getColumns()
        events = self.dayEvents(self.cursor)
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
        end = datetime.combine(self.cursor, time(self.endhour))

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

    Switches daily, weekly, monthly calendar presentations.
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
        raise KeyError(name)

    def render(self, request):
        return str(request.redirect(
            absoluteURL(request, self.context) + '/daily.html'))
