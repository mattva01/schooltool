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

from datetime import datetime, date, time, timedelta
import urllib

from zope.interface import implements
from zope.component import queryView, adapts
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.browser.absoluteurl import absoluteURL
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.cal import CalendarEvent
from schoolbell.calendar.interfaces import ICalendar, ICalendarEvent
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


class CalendarTraverser(object):
    """A traverser that allows to traverse to a calendar owner's calendar."""

    adapts(ICalendarOwner)
    implements(IBrowserPublisher)

    queryView = queryView

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def browserDefault(self, request):
        return self.context, ('daily.html', )

    def publishTraverse(self, request, name):
        view_name = self.getViewByDate(request, name)
        if view_name:
            return self.queryView(self.context, view_name, request)

        view = queryView(self.context, name, request)
        if view is not None:
            return view

        raise NotFound(self.context, name, request)

    def getViewByDate(self, request, name):
        parts = name.split('-')

        if len(parts) == 2 and parts[1].startswith('w'): # a week was given
            try:
                year = int(parts[0])
                week = int(parts[1][1:])
            except ValueError:
                return
            request.form['date'] = self.getWeek(year, week).isoformat()
            return 'weekly.html'

        # a year, month or day might have been given
        try:
            parts = [int(part) for part in parts]
        except ValueError:
            return
        if not parts:
            return
        parts = tuple(parts)

        if len(parts) == 1:
            request.form['date'] = "%d-01-01" % parts
            return 'yearly.html'
        elif len(parts) == 2:
            request.form['date'] = "%d-%02d-01" % parts
            return 'monthly.html'
        elif len(parts) == 3:
            request.form['date'] = "%d-%02d-%02d" % parts
            return 'daily.html'

    def getWeek(self, year, week):
        """Get the start of a week by week number.

        The function does not return the first day of the week, but that
        is good enough for our views.

            >>> traverser = CalendarTraverser(None, None)
            >>> traverser.getWeek(2002, 11)
            datetime.date(2002, 3, 15)
            >>> traverser.getWeek(2005, 1)
            datetime.date(2005, 1, 4)
            >>> traverser.getWeek(2005, 52)
            datetime.date(2005, 12, 27)

        """
        return date(year, 1, 4) + timedelta(weeks=(week-1))


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
                event = CalendarEvent(dtstart, length, title)
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

    def dayEvents(self, date):
        """Return events for a day sorted by start time.

        Events spanning several days and overlapping with this day
        are included.
        """
        day = self.getDays(date, date + timedelta(1))[0]
        return day.events

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
        # XXX A an evil temporary hack follows.  Currently expand() as provided
        #     in Calendar() (and CalendarMixin) compares dates with datetimes.
        #     Because the comparison is not inclusive, in this case things
        #     break horribly (date(2004, 1, 2) is not less than
        #     datetime(2004, 1, 2, 3, 4).  We probably want to fix expand().
        first = datetime(first.year, first.month, first.day)
        last = datetime(last.year, last.month, last.day)
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

    next_title = _("Next week")
    current_title = _("Current week")
    prev_title = _("Previous week")

    def title(self):
        month_name = unicode(self.month_names[self.cursor.month])
        args = {'month': month_name,
                'year': self.cursor.year,
                'week': self.cursor.isocalendar()[1]}
        return _('%(month)s, %(year)s (week %(week)s)') % args

    def prev(self):
        """Return the link for the previous week."""
        return self.calURL('weekly', self.cursor - timedelta(weeks=1))

    def next(self):
        """Return the link for the next week."""
        return self.calURL('weekly', self.cursor + timedelta(weeks=1))

    def getCurrentWeek(self):
        """Return the current week as a list of CalendarDay objects."""
        return self.getWeek(self.cursor)


class MonthlyCalendarView(CalendarViewBase):
    """Monthly calendar view."""

    next_title = _("Next month")
    current_title = _("Current month")
    prev_title = _("Previous month")

    def title(self):
        month_name = unicode(self.month_names[self.cursor.month])
        args = {'month': month_name, 'year': self.cursor.year}
        return _('%(month)s, %(year)s') % args

    def prev(self):
        """Return the link for the previous month."""
        return self.calURL('monthly', self.prevMonth())

    def next(self):
        """Return the link for the next month."""
        return self.calURL('monthly', self.nextMonth())

    def dayOfWeek(self, date):
        return unicode(self.day_of_week_names[date.weekday()])

    def weekTitle(self, date):
        return _('Week %d') % date.isocalendar()[1]

    def getCurrentMonth(self):
        """Return the current month as a nested list of CalendarDays."""
        return self.getMonth(self.cursor)


class YearlyCalendarView(CalendarViewBase):
    """Yearly calendar view."""

    next_title = _("Next year")
    current_title = _("Current year")
    prev_title = _("Previous year")

    def title(self):
        return self.cursor.strftime('%Y')

    def prev(self):
        """Return the link for the previous year."""
        return self.calURL('yearly', date(self.cursor.year - 1, 1, 1))

    def next(self):
        """Return the link for the next year."""
        return self.calURL('yearly', date(self.cursor.year + 1, 1, 1))

    def monthTitle(self, date):
        return unicode(self.month_names[date.month])

    def shortDayOfWeek(self, date):
        return unicode(self.short_day_of_week_names[date.weekday()])

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


class DailyCalendarView(CalendarViewBase):
    """Daily calendar view.

    The events are presented as boxes on a 'sheet' with rows
    representing hours.

    The challenge here is to present the events as a table, so that
    the overlapping events are displayed side by side, and the size of
    the boxes illustrate the duration of the events.
    """

    __used_for__ = ICalendar

    starthour = 8
    endhour = 19

    next_title = _("The next day")
    current_title = _("Today")
    prev_title = _("The previous day")

    def title(self):
        return self.dayTitle(self.cursor)

    def prev(self):
        """Return the link for the next day."""
        return self.calURL('daily', self.cursor - timedelta(1))

    def next(self):
        """Return the link for the previous day."""
        return self.calURL('daily', self.cursor + timedelta(1))

    def getColumns(self):
        """Return the maximum number of events that are overlapping.

        Extends the event so that start and end times fall on hour
        boundaries before calculating overlaps.
        """
        width = [0] * 24
        daystart = datetime.combine(self.cursor, time())
        for event in self.dayEvents(self.cursor):
            t = daystart
            dtend = daystart + timedelta(1)
            for title, start, duration in self.calendarRows():
                if start <= event.dtstart < start + duration:
                    t = start
                if start < event.dtstart + event.duration <= start + duration:
                    dtend = start + duration
            while True:
                width[t.hour] += 1
                t += timedelta(hours=1)
                if t >= dtend:
                    break
        return max(width) or 1

    def _setRange(self, events):
        """Set the starthour and endhour attributes according to events.

        The range of the hours to display is the union of the range
        8:00-18:00 and time spans of all the events in the events
        list.
        """
        for event in events:
            start = datetime.combine(self.cursor, time(self.starthour))
            end = (datetime.combine(self.cursor, time()) +
                   timedelta(hours=self.endhour)) # endhour may be 24
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

    def calendarRows(self):
        """Iterate over (title, start, duration) of time slots that make up
        the daily calendar.
        """
        # XXX not tested
        today = datetime.combine(self.cursor, time())
        row_ends = [today + timedelta(hours=hour + 1)
                    for hour in range(self.starthour, self.endhour)]

        start = today + timedelta(hours=self.starthour)
        for end in row_ends:
            duration = end - start
            yield ('%d:%02d' % (start.hour, start.minute), start, duration)
            start = end

    def getHours(self):
        """Return an iterator over the rows of the table.

        Every row is a dict with the following keys:

            'time' -- row label (e.g. 8:00)
            'cols' -- sequence of cell values for this row

        A cell value can be one of the following:
            None  -- if there is no event in this cell
            event -- if an event starts in this cell
            ''    -- if an event started above this cell

        """
        nr_cols = self.getColumns()
        events = self.dayEvents(self.cursor)
        self._setRange(events)
        slots = Slots()
        for title, start, duration in self.calendarRows():
            end = start + duration
            hour = start.hour

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

            yield {'title': title, 'cols': tuple(cols),
                   'time': start.strftime("%H:%M"),
                   # We can trust no period will be longer than a day
                   'duration': duration.seconds // 60}

    def rowspan(self, event):
        """Calculate how many calendar rows the event will take today."""
        count = 0
        for title, start, duration in self.calendarRows():
            if (start < event.dtstart + event.duration and
                event.dtstart < start + duration):
                count += 1
        return count

    def snapToGrid(self, dt):
        """Snap a datetime to the nearest position in the grid.

        Returns the grid line index where 0 corresponds to the top of
        the display box (self.starthour), and each subsequent line represents
        a 15 minute increment.

        Clips dt so that it is never outside today's box.
        """
        base = datetime.combine(self.cursor, time())
        display_start = base + timedelta(hours=self.starthour)
        display_end = base + timedelta(hours=self.endhour)
        clipped_dt = max(display_start, min(dt, display_end))
        td = clipped_dt - display_start
        offset_in_minutes = td.seconds / 60 + td.days * 24 * 60
        return (offset_in_minutes + 7) / 15 # round to nearest quarter

    def eventTop(self, event):
        """Calculate the position of the top of the event block in the display.

        Each hour is made up of 4 units ('em' currently). If an event starts at
        10:15, and the day starts at 8:00 we get a top value of:

          (2 * 4) + (15 / 15) = 9

        """
        return self.snapToGrid(event.dtstart)

    def eventHeight(self, event):
        """Calculate the height of the event block in the display.

        Each hour is made up of 4 units ('em' currently).  Need to round 1 -
        14 minute intervals up to 1 display unit.
        """
        dtend = event.dtstart + event.duration
        return max(1, self.snapToGrid(dtend) - self.snapToGrid(event.dtstart))

    def update(self):
        # Create self.cursor
        CalendarViewBase.update(self)

        # Initialize self.starthour and self.endhour
        events = self.dayEvents(self.cursor)
        self._setRange(events)

        # The number of hours displayed in the day view
        self.visiblehours = self.endhour - self.starthour


class Slots(dict):
    """A dict with automatic key selection.

    The add method automatically selects the lowest unused numeric key
    (starting from 0).

    Example:

      >>> s = Slots()
      >>> s.add("first")
      >>> s
      {0: 'first'}

      >>> s.add("second")
      >>> s
      {0: 'first', 1: 'second'}

    The keys can be reused:

      >>> del s[0]
      >>> s.add("third")
      >>> s
      {0: 'third', 1: 'second'}

    """

    def add(self, obj):
        i = 0
        while i in self:
            i += 1
        self[i] = obj

