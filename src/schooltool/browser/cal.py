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
        return absoluteURL(self.request, self.context.__parent__,
                          'calendar_%s.html?date=%s' % (cal_type, cursor))

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
            if event_start >= start and event_start < end:
                events[event_start].append(event)

        days = []
        for day in events.keys():
            events[day].sort()
            days.append(CalendarDay(day, events[day]))
        days.sort()
        return days


class WeeklyCalendarView(CalendarViewBase):

    template = Template("www/cal_weekly.pt")

    def prevWeek(self):
        """Return the day a week before."""
        return self.cursor - timedelta(7)

    def nextWeek(self):
        """Return the day a week after."""
        return self.cursor + timedelta(7)

    def getWeek(self):
        """Return the current week as a list of CalendarDay objects."""
        # For now, we're Monday based
        start = self.cursor - timedelta(self.cursor.weekday())
        end = start + timedelta(6)
        return self.getDays(start, end)


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

    def getMonth(self):
        """Return a nested list of days in a month.

        Returns a list of lists of date objects.  Days in neighbouring
        months are included if they fall into a week that contains days in
        the current month.
        """
        # XXX Monday-based weeks.
        cursor = self.cursor
        prev_lastday = (date(cursor.year, cursor.month, 1) - timedelta(days=1))
        weekday = prev_lastday.weekday()
        if weekday != 6:
            start = prev_lastday - timedelta(days=weekday)
        else:
            start = date(cursor.year, cursor.month, 1)
        weeks = []

        last = start
        while last.month in [start.month, cursor.month]:
            end = last + timedelta(days=7)
            week = self.getDays(last, end)
            weeks.append(week)
            last = end
        return weeks
