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

from datetime import date, datetime, timedelta
import urllib

from zope.interface import implements
from zope.component import queryView, adapts
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.browser.absoluteurl import absoluteURL
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schoolbell import SchoolBellMessageID as _
from schoolbell.calendar.interfaces import ICalendar, ICalendarEvent
from schoolbell.calendar.simple import SimpleCalendarEvent
from schoolbell.calendar.utils import week_start, prev_month, next_month
from schoolbell.calendar.utils import parse_date
from schoolbell.app.interfaces import ICalendarOwner


class CalendarOwnerTraverser(object):
    """A traverser that allows to traverse to a calendar owner's calendar."""

    adapts(ICalendarOwner)
    implements(IBrowserPublisher)

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


class CalendarDay(object):
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
    month_names = {
        1: _("January"), 2: _("February"), 3: _("March"),
        4: _("April"), 5: _("May"), 6: _("June"),
        7: _("July"), 8: _("August"), 9: _("September"),
        10: _("October"), 11: _("November"), 12: _("December")}

    day_of_week_names = {
        0: _("Monday"), 1: _("Tuesday"), 2: _("Wednesday"), 3: _("Thursday"),
        4: _("Friday"), 5: _("Saturday"), 6: _("Sunday")}

    short_day_of_week_names = {
        0: _("Mon"), 1: _("Tue"), 2: _("Wed"), 3: _("Thu"),
        4: _("Fri"), 5: _("Sat"), 6: _("Sun"),
    }

    # Which day is considered to be the first day of the week (0 = Monday,
    # 6 = Sunday).  Currently hardcoded.
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
        if len(title) < 17:
             return title
        else:
             return title[:15] + '...'

    def update(self):
        if 'date' not in self.request:
            self.cursor = date.today()
        else:
            # It would be nice not to b0rk when the date is invalid but fall
            # back to the current date, as if the date had not been specified.
            self.cursor = parse_date(self.request['date'])

    def getWeek(self, dt):
        """Return the week that contains the day dt.

        Returns a list of CalendarDay objects.
        """
        start = week_start(dt, self.first_day_of_week)
        end = start + timedelta(7)
        return self.getDays(start, end)

    def getMonth(self, dt):
        """Return a nested list of days in the month that contains dt.

        Returns a list of lists of date objects.  Days in neighbouring
        months are included if they fall into a week that contains days in
        the current month.
        """
        weeks = []
        start_of_next_month = next_month(dt)
        start_of_week = week_start(dt.replace(day=1), self.first_day_of_week)
        while start_of_week < start_of_next_month:
            start_of_next_week = start_of_week + timedelta(7)
            weeks.append(self.getDays(start_of_week, start_of_next_week))
            start_of_week = start_of_next_week
        return weeks

    def getYear(self, dt):
        """Return the current year.

        This returns a list of quarters, each quarter is a list of months,
        each month is a list of weeks, and each week is a list of CalendarDays.
        """
        quarters = []
        for q in range(4):
            quarter = [self.getMonth(date(dt.year, month + (q * 3), 1))
                       for month in range(1, 4)]
            quarters.append(quarter)
        return quarters

    def _eventView(self, event):
        return CalendarEventView(event, self.request, calendar=self.context)

    def eventClass(self, event):
        return self._eventView(event).cssClass()

    def renderEvent(self, event, date):
        return self._eventView(event).full(self.request, date)

    def eventShort(self, event):
        return self._eventView(event).short(self.request)

    def eventHidden(self, event):
        return False # TODO We don't have hidden events yet.

    def eventColors(self, event):
        return ('#9db8d2', '#7590ae') # XXX TODO

    def getDays(self, start, end):
        """Get a list of CalendarDay objects for a selected period of time.

        `start` and `end` (date objects) are bounds (half-open) for the result.

        Events spanning more than one day get included in all days they
        overlap.
        """
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

    def prevMonth(self):
        """Return the first day of the previous month."""
        return prev_month(self.cursor)

    def nextMonth(self):
        """Return the first day of the next month."""
        return next_month(self.cursor)

    def prevDay(self):
        return self.cursor - timedelta(1)

    def nextDay(self):
        return self.cursor + timedelta(1)


class WeeklyCalendarView(CalendarViewBase):
    """A view that shows one week of the calendar."""

    __used_for__ = ICalendar

    def title(self):
        month_name = unicode(self.month_names[self.cursor.month])
        args = {'month': month_name,
                'year': self.cursor.year,
                'week': self.cursor.isocalendar()[1]}
        return _('%(month)s, %(year)s (week %(week)s)') % args

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
    """Monthly calendar view."""

    def title(self):
        month_name = unicode(self.month_names[self.cursor.month])
        args = {'month': month_name, 'year': self.cursor.year}
        return _('%(month)s, %(year)s') % args

    def dayOfWeek(self, date):
        return unicode(self.day_of_week_names[date.weekday()])

    def weekTitle(self, date):
        return _('Week %d') % date.isocalendar()[1]

    def getCurrentMonth(self):
        """Return the current month as a nested list of CalendarDays."""
        return self.getMonth(self.cursor)


class YearlyCalendarView(CalendarViewBase):
    """Yearly calendar view."""

    def monthTitle(self, date):
        return unicode(self.month_names[date.month])

    def shortDayOfWeek(self, date):
        return unicode(self.short_day_of_week_names[date.weekday()])

    def prevYear(self):
        """Return the first day of the next year."""
        return date(self.cursor.year - 1, 1, 1)

    def nextYear(self):
        """Return the first day of the previous year."""
        return date(self.cursor.year + 1, 1, 1)

    def renderRow(self, week, month):
        """Do some HTML rendering in Python for performance.

        This gains us 0.4 seconds out of 0.6 on my machine.
        Here is the original piece of ZPT:

         <td class="cal_yearly_day" tal:repeat="day week">
          <a tal:condition="python:day.date.month == month[1][0].date.month"
             tal:content="day/date/day"
             tal:attributes="href python:view.calURL('daily', day.date);
                             class python:(len(day.events) > 0
                                           and 'cal_yearly_day_busy'
                                           or  'cal_yearly_day')"/>
         </td>
        """
        result = []

        for day in week:
            result.append('<td class="cal_yearly_day">')
            if day.date.month == month:
                if len(day.events):
                    cssClass = 'cal_yearly_day_busy'
                else:
                    cssClass = 'cal_yearly_day'
                # Let us hope that URLs will not contain < > & or "
                # This is somewhat related to
                #   http://issues.schooltool.org/issue96
                result.append('<a href="%s" class="%s">%s</a>' %
                              (self.calURL('daily', day.date), cssClass,
                               day.date.day))
            result.append('</td>')
        return "\n".join(result)


class CalendarEventView(object):
    """Renders the inside of the event box in various calendar views."""

    __used_for__ = ICalendarEvent

    template = ViewPageTemplateFile('templates/cal_event.pt')

    def __init__(self, event, request, calendar=None):
        """Create a view for event.

        Since ordinary calendar events do not know which calendar they come
        from, we have to explicitly provide the access control list (acl)
        that governs access to this calendar.
        """
        self.context = event
        self.request = request
        self.calendar = calendar
        self.date = None

    def canEdit(self):
        """Can the current user edit this calendar event?"""
        return True # TODO: implement this when we have security.

    def canView(self):
        """Can the current user view this calendar event?"""
        return True # TODO: implement this when we have security.

    def isHidden(self):
        """Should the event be hidden from the current user?"""
        return False # TODO

    def cssClass(self):
        """Choose a CSS class for the event."""
        return 'event' # TODO: for now we do not have any other CSS classes.

    def getPeriod(self):
        """Returns the title of the timetable period this event coincides with.

        Returns None if there is no such period.
        """
        return None # XXX Does not apply to SchoolBell.

    def duration(self):
        """Format the time span of the event."""
        dtstart = self.context.dtstart
        dtend = dtstart + self.context.duration
        if dtstart.date() == dtend.date():
            span =  "%s&ndash;%s" % (dtstart.strftime('%H:%M'),
                                     dtend.strftime('%H:%M'))
        else:
            span = "%s&ndash;%s" % (dtstart.strftime('%Y-%m-%d %H:%M'),
                                    dtend.strftime('%Y-%m-%d %H:%M'))

        period = self.getPeriod()
        if period:
            return "Period %s (%s)" % (period, span)
        else:
            return span

    def full(self, request, date):
        """Full representation of the event for daily/weekly views."""
        try:
            self.request = request
            self.date = date
            return self.template(request)
        finally:
            self.request = None
            self.date = None

    def short(self, request):
        """Short representation of the event for the monthly view."""
        self.request = request
        ev = self.context
        end = ev.dtstart + ev.duration
        if self.canView():
            title = ev.title
        else:
            title = _("Busy")
        if ev.dtstart.date() == end.date():
            period = self.getPeriod()
            if period:
                duration = _("Period %s") % period
            else:
                duration =  "%s&ndash;%s" % (ev.dtstart.strftime('%H:%M'),
                                             end.strftime('%H:%M'))
        else:
            duration =  "%s&ndash;%s" % (ev.dtstart.strftime('%b&nbsp;%d'),
                                         end.strftime('%b&nbsp;%d'))
        return "%s (%s)" % (title, duration)

    def editLink(self):
        """Return the link for editing this event."""
        return 'edit_event.html?' + self._params()

    def deleteLink(self):
        """Return the link for deleting this event."""
        return 'delete_event.html?' + self._params()

    def _params(self):
        """Prepare query arguments for editLink and deleteLink."""
        event_id = self.context.unique_id
        date = self.date.strftime('%Y-%m-%d')
        return 'date=%s&event_id=%s' % (date, urllib.quote(event_id))

    def privacy(self):
        return _("Public") # TODO used to also have busy-block and hidden.

