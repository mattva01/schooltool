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

from schooltool.browser import View, Template
from schooltool.browser.auth import TeacherAccess, PrivateAccess
from schooltool.cal import CalendarEvent, Period
from schooltool.common import to_unicode, parse_datetime
from schooltool.component import traverse, getPath
from schooltool.interfaces import IResource, ICalendar
from schooltool.translation import ugettext as _
from schooltool.common import parse_date

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


class WeeklyCalendarView(View):

    __used_for__ = ICalendar

    authorization = PrivateAccess

    template = Template("www/cal_weekly.pt")

    def update(self):
        if 'date' not in self.request.args:
            self.cursor = date.today()
        else:
            self.cursor = parse_date(self.request.args['date'][0])

        self.prev = self.cursor - timedelta(7)
        self.next = self.cursor + timedelta(7)

    def getDays(self):
        # For now, we're Monday based
        start = self.cursor - timedelta(self.cursor.weekday())
        return [start + timedelta(i) for i in range(7)]

    def dayEvents(self, date):
        """Return events for a day sorted by start time."""
        # XXX If an event spans several days, it will be shown multiple times.
        daycal = self.context.byDate(date)
        events = [(e.dtstart, e) for e in daycal]
        events.sort()
        return [e for start, e in events]


class MonthlyCalendarView(View):

    __used_for__ = ICalendar

    authorization = PrivateAccess

    template = Template("www/cal_monthly.pt")

    def update(self):
        if 'date' not in self.request.args:
            cursor = date.today()
        else:
            cursor = parse_date(self.request.args['date'][0])
        self.cursor = cursor

        prev_lastday = (date(cursor.year, cursor.month, 1) - timedelta(days=1))
        self.prev = date(prev_lastday.year, prev_lastday.month, 1)

        next_someday = (date(cursor.year, cursor.month, 28) + timedelta(7))
        self.next = date(next_someday.year, next_someday.month, 1)

    def getWeeks(self):
        """Return a nested list of days in a month.

        Returns a list of lists of date objects.  Days in neighbouring
        months are included if they fall into a week that contains days in
        the current month.
        """
        # XXX Monday-based weeks.
        prev_lastday = (date(self.cursor.year, self.cursor.month, 1)
                        - timedelta(days=1))
        weekday = prev_lastday.weekday()
        if weekday != 6:
            start = prev_lastday - timedelta(days=weekday)
        else:
            start = date(self.cursor.year, self.cursor.month, 1)
        weeks = []

        last = start
        while last.month in [start.month, self.cursor.month]:
            week = [last + timedelta(days=i) for i in range(7)]
            weeks.append(week)
            last = last + timedelta(days=7)
        return weeks

