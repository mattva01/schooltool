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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolBell calendar views.

$Id$
"""

from datetime import datetime, date, timedelta

from zope.interface import implements
from zope.component import queryView
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.browser.absoluteurl import absoluteURL

from schoolbell import SchoolBellMessageID as _
from schoolbell.calendar.interfaces import ICalendar
from schoolbell.calendar.simple import SimpleCalendarEvent
from schoolbell.calendar.utils import week_start
from schoolbell.app.interfaces import ICalendarOwner


class CalendarOwnerTraverser(object):

    implements(IBrowserPublisher)

    __used_for__ = ICalendarOwner

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == 'calendar':
            return self.context.calendar

        view = queryView(self.context, name, request)
        if view is not None:
            return view

        raise NotFound(self.context, name, request)

    def browserDefault(self, request):
        return self.context, ('index.html', )


class CalendarDay:
    # XXX Not tested.
    """A single day in a calendar.

    Attributes:
       'date'   -- date of the day (a datetime.date instance)
       'events' -- list of events that took place that day, sorted by start
                   time (in ascending order).

    """

    def __init__(self, date, events=None):
        self.date = date
        if events is None:
            self.events = []
        else:
            self.events = events

    def __cmp__(self, other):
        return cmp(self.date, other.date)


class PlainCalendarView(BrowserView):
    """A calendar view purely for testing purposes."""

    __used_for__ = ICalendar

    num_events = 5
    evt_range = 60*24*14 # two weeks

    def iterEvents(self):
        events = list(self.context)
        events.sort()
        return events

    def update(self):
        if 'GENERATE' in self.request:
            import random
            for i in range(self.num_events):
                delta = random.randint(-self.evt_range, self.evt_range)
                dtstart = datetime.now() + timedelta(minutes=delta)
                length = timedelta(minutes=random.randint(1, 60*12))
                title = 'Event %d' % random.randint(1, 999)
                event = SimpleCalendarEvent(dtstart, length, title)
                self.context.addEvent(event)


class CalendarViewBase(BrowserView):
    """A base class for the calendar views.

    This class provides functionality that is useful to several calendar views.
    """

    __used_for__ = ICalendar

    # XXX I'd rather these constants would go somewhere in schoolbell.calendar.
    day_of_week_names = {
        0: _("Monday"), 1: _("Tuesday"), 2: _("Wednesday"), 3: _("Thursday"),
        4: _("Friday"), 5: _("Saturday"), 6: _("Sunday")}

    month_names = {
        1: _("January"), 2: _("February"), 3: _("March"),
        4: _("April"), 5: _("May"), 6: _("June"),
        7: _("July"), 8: _("August"), 9: _("September"),
        10: _("October"), 11: _("November"), 12: _("December")}

    # Which day is considered to be the first day of the week (0 = Monday,
    # 6 = Sunday).  Currently hardcoded.  A similar value is also hardcoded
    # in schooltool.browser.timetable.
    first_day_of_week = 0

    def dayTitle(self, day):
        day_of_week = unicode(self.day_of_week_names[day.weekday()])
        return _('%s, %s') % (day_of_week, day.strftime('%Y-%m-%d'))

    __url = None

    def calURL(self, cal_type, cursor=None):
        if cursor is None:
            cursor = self.cursor
        if self.__url is None:
            self.__url = absoluteURL(self.context, self.request)
        return  '%s/%s.html?date=%s' % (self.__url, cal_type, cursor)

    def ellipsizeTitle(self, title):
        """For labels with limited space replace the tail with '...'."""
        # XXX Not tested.
        if len(title) < 17:
             return title
        else:
             return title[:15] + '...'

    def update(self):
        # XXX Not tested, TODO: parse_date
        #if 'date' not in self.request.args:
        self.cursor = date.today()
        ##else:
        ##    self.cursor = parse_date(self.request.args['date'][0])

    def getWeek(self, dt):
        """Return the week that contains the day dt.

        Returns a list of CalendarDay objects.
        """
        # XXX Not tested
        start = week_start(dt, self.first_day_of_week)
        end = start + timedelta(7)
        return self.getDays(start, end)

    def eventHidden(self, event):
        return False # XXX TODO

    def eventColors(self, event):
        return ('#9db8d2', '#7590ae') # XXX TODO

    def getDays(self, start, end):
        """Get a list of CalendarDay objects for a selected period of time.

        `start` and `end` (date objects) are bounds (half-open) for the result.

        Events spanning more than one day get included in all days they
        overlap.
        """
        # XXX Not tested
        events = {}
        day = start
        while day < end:
            events[day] = []
            day += timedelta(1)

        for event in self.iterEvents(start, end):
            if self.eventHidden(event):
                continue
            #  day1  day2  day3  day4  day5
            # |.....|.....|.....|.....|.....|
            # |     |  [-- event --)  |     |
            # |     |  ^  |     |  ^  |     |
            # |     |  `dtstart |  `dtend   |
            #        ^^^^^       ^^^^^
            #      first_day   last_day
            #
            # dtstart and dtend are datetime.datetime instances and point to
            # time instants.  first_day and last_day are datetime.date
            # instances and point to whole days.  Also note that [dtstart,
            # dtend) is a half-open interval, therefore
            #   last_day == dtend.date() - 1 day   when dtend.time() is 00:00
            #                                      and duration > 0
            #               dtend.date()           otherwise
            dtend = event.dtstart + event.duration
            first_day = event.dtstart.date()
            last_day = max(first_day, (dtend - dtend.resolution).date())
            # Loop through the intersection of two day ranges:
            #    [start, end) intersect [first_day, last_day]
            # Note that the first interval is half-open, but the second one is
            # closed.  Since we're dealing with whole days,
            #    [first_day, last_day] == [first_day, last_day + 1 day)
            day = max(start, first_day)
            limit = min(end, last_day + timedelta(1))
            while day < limit:
                events[day].append(event)
                day += timedelta(1)

        days = []
        day = start
        while day < end:
            events[day].sort()
            days.append(CalendarDay(day, events[day]))
            day += timedelta(1)
        return days

    def iterEvents(self, first, last):
        return self.context.expand(first, last)


class WeeklyCalendarView(CalendarViewBase):
    """A view that shows one week of the calendar."""

    __used_for__ = ICalendar

    def title(self):
        # XXX Not tested.
        month_name = unicode(self.month_names[self.cursor.month])
        args = {'month': month_name,
                'year': self.cursor.year,
                'week': self.cursor.isocalendar()[1]}
        return _('%(month)s, %(year)s (week %(week)s)') % args

    def prevWeek(self):
        """Return the day a week before."""
        # XXX Not tested.
        return self.cursor - timedelta(7)

    def nextWeek(self):
        """Return the day a week after."""
        # XXX Not tested.
        return self.cursor + timedelta(7)

    def getCurrentWeek(self):
        """Return the current week as a list of CalendarDay objects."""
        # XXX Not tested.
        return self.getWeek(self.cursor)
