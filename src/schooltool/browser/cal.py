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

import urllib
from datetime import datetime, date, time, timedelta

from schooltool.browser import View, Template, absoluteURL, absolutePath
from schooltool.browser.auth import TeacherAccess, PublicAccess
from schooltool.browser.auth import ACLViewAccess, ACLModifyAccess
from schooltool.browser.auth import ACLAddAccess
from schooltool.browser.acl import ACLView
from schooltool.cal import CalendarEvent, Period
from schooltool.common import to_unicode, parse_datetime, parse_date
from schooltool.component import traverse, getPath, getRelatedObjects, traverse
from schooltool.interfaces import IResource, ICalendar, ICalendarEvent
from schooltool.interfaces import IContainmentRoot
from schooltool.translation import ugettext as _
from schooltool.uris import URIMember

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


class CalendarViewBase(View):

    __used_for__ = ICalendar

    authorization = ACLViewAccess

    # Which day is considered to be the first day of the week (0 = Monday,
    # 6 = Sunday).  Currently hardcoded.  A similair value is also hardcoded
    # in schooltool.browser.timetable
    first_day_of_week = 0

    __url = None

    def renderEvent(self, event):
        view = CalendarEventView(event)
        # Using render here has two downsides:
        #  - the Content-Type header is overwritten
        #  - we do needless conversion from Unicode to UTF-8 and back
        return to_unicode(view.render(self.request))

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
        if self.__url is None:
            self.__url = absoluteURL(self.request, self.context)
        return  '%s/%s.html?date=%s' % (self.__url, cal_type, cursor)

    def iterEvents(self):
        """Iterate over the events of the calendars displayed

        This is a hook for subclasses that have to iterate over
        several calendars.
        """
        return iter(self.context)

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

        for event in self.iterEvents():
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


class DailyCalendarView(CalendarViewBase):
    """Daily calendar view.

    The events are presented as boxes on a 'sheet' with rows
    representing hours.

    The challenge here is to present the events as a table, so that
    the overlapping events are displayed side by side, and the size of
    the boxes illustrates the duration of the events.
    """

    __used_for__ = ICalendar

    authorization = ACLViewAccess

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
        day = self.getDays(date, date + timedelta(1))[0]
        return day.events

    def getColumns(self):
        """Return the maximum number of events that are overlapping.

        Extends the event so that start and end times fall on hour
        boundaries before calculating overlaps.
        """
        width = [0] * 24
        daystart = datetime.combine(self.cursor, time())
        for event in self.dayEvents(self.cursor):
            t = max(event.dtstart.replace(minute=0), daystart)
            dtend = min(event.dtstart + event.duration,
                        daystart + timedelta(1))
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
        """Calculate how many hours the event will take today."""
        start = datetime.combine(self.cursor, time(self.starthour))
        end = (datetime.combine(self.cursor, time()) +
               timedelta(hours=self.endhour)) # endhour may be 24

        event_start = max(start, event.dtstart)
        event_end = min(end, event.dtstart + event.duration)

        duration = event_end - event_start
        seconds = duration.days * 24 * 3600 + duration.seconds
        return (seconds + 3600 - 1) // 3600 # round up


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


class WeeklyCalendarView(CalendarViewBase):
    """Weekly calendar view."""

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
    """Monthly calendar view."""

    template = Template("www/cal_monthly.pt")

    def prevMonth(self):
        """Return the first day of the previous month."""
        return prev_month(self.cursor)

    def nextMonth(self):
        """Return the first day of the next month."""
        return next_month(self.cursor)

    def getCurrentMonth(self):
        """Return the current month as a nested list of CalendarDays."""
        return self.getMonth(self.cursor)


class YearlyCalendarView(CalendarViewBase):
    """Yearly calendar view."""

    template = Template('www/cal_yearly.pt')

    def prevYear(self):
        """Return the first day of the next year."""
        return date(self.cursor.year - 1, 1, 1)

    def nextYear(self):
        """Return the first day of the previous year."""
        return date(self.cursor.year + 1, 1, 1)

    __url = None

    def calURL(self, cal_type, cursor=None):
        if cursor is None:
            cursor = self.cursor
        if self.__url is None:
            self.__url = absolutePath(self.request, self.context)
        return  '%s/%s.html?date=%s' % (self.__url, cal_type, cursor)

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


class CalendarView(View):
    """The main calendar view.

    Switches daily, weekly, monthly, yearly calendar presentations.
    """

    authorization = ACLViewAccess

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
        elif name == 'acl.html':
            return ACLView(self.context.acl)
        raise KeyError(name)

    def do_GET(self, request):
        url = absoluteURL(request, self.context, 'daily.html')
        return self.redirect(url, request)


class EventViewBase(View):
    """A base class for event adding and editing views."""

    __used_for__ = ICalendar

    authorization = ACLModifyAccess

    template = Template('www/event.pt')
    page_title = None # overridden by subclasses

    error = u""
    title = u""
    start_date = u""
    start_time = u""
    location = u""
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
        if 'location' in request.args:
            self.location = to_unicode(request.args['location'][0])
        if 'location_other' in request.args:
            self.location_other = to_unicode(request.args['location_other'][0])

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

        if self.location != 'custom_location':
            location = self.location
        else:
            location = self.location_other

        self.process(start, duration, self.title, location)

        suffix = 'daily.html?date=%s' % start.date()
        url = absoluteURL(request, self.context, suffix)
        return self.redirect(url, request)

    def process(self, dtstart, duration, title, location):
        raise NotImplementedError("override this method in subclasses")

    def getLocations(self):
        """Get a list of titles for possible locations."""
        obj = self.context
        while not IContainmentRoot.providedBy(obj):
            obj = obj.__parent__
        location_group = obj['groups']['locations']

        locations = []
        for location in getRelatedObjects(location_group, URIMember):
            locations.append(location.title)
        locations.sort()
        return locations


class EventAddView(EventViewBase):
    """A view for adding events."""

    page_title = _("Add event")

    authorization = ACLAddAccess

    def process(self, dtstart, duration, title, location):
        ev = CalendarEvent(dtstart, duration, title,
                           self.context.__parent__, self.context.__parent__,
                           location=location)
        self.context.addEvent(ev)


class EventEditView(EventViewBase):
    """A view for editing events."""

    page_title = _("Edit event")

    def update(self):
        self.event_id = to_unicode(self.request.args['event_id'][0])
        for event in self.context:
            if event.unique_id == self.event_id:
                self.event = event
                break
        else:
            raise ValueError("Invalid event_id") # XXX Unfriendly? and not i18nized!
            # TODO: Create a traversal view for events
            # and refactor the event edit view to take the event as context

        self.title = self.event.title
        self.start_date = str(self.event.dtstart.date())
        self.start_time = str(self.event.dtstart.strftime("%H:%M"))
        self.duration = str(self.event.duration.seconds / 60)
        self.location = self.event.location
        EventViewBase.update(self)

    def process(self, dtstart, duration, title, location):
        uid = self.event.unique_id
        self.context.removeEvent(self.event)
        ev = CalendarEvent(dtstart, duration, title,
                           self.context.__parent__, self.context.__parent__,
                           location=location, unique_id=uid)
        self.context.addEvent(ev)


class EventDeleteView(View):
    """A view for deleting events."""

    __used_for__ = ICalendar

    authorization = ACLModifyAccess

    def do_GET(self, request):
        event_id = to_unicode(request.args['event_id'][0])
        for event in self.context:
            if event.unique_id == event_id:
                suffix = 'daily.html?date=%s' % event.dtstart.date()
                self.context.removeEvent(event)
                url = absoluteURL(request, self.context, suffix)
                return self.redirect(url, request)
        else:
            raise ValueError("Invalid event_id") # XXX Unfriendly? And not i18nized!


def EventSourceDecorator(e, source):
    """A decorator for an ICalendarEvent that provides a 'source' attribute.

    Here we rely on the fact that CalendarEvents are immutable, that is, we
    can substitute an event instance with a (decorated) copy and not worry
    about editing views making modifications to copies.
    """
    result = CalendarEvent(e.dtstart, e.duration, e.title, e.context,
                           e.owner, location=e.location, unique_id=e.unique_id)
    result.source = source
    return result


class CalendarComboMixin(View):
    """Mixin for views over the combined calendar of a person.

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
        elif name == 'acl.html':
            return ACLView(self.context.acl)
        raise KeyError(name)


class CalendarEventView(View):
    """Renders the inside of the event box in various calendar views."""

    __used_for__ = ICalendarEvent

    authorization = PublicAccess

    template = Template("www/cal_event.pt")

    def duration(self):
        """Format the time span of the event."""
        dtstart = self.context.dtstart
        dtend = dtstart + self.context.duration
        if dtstart.date() == dtend.date():
            return "%s&ndash;%s" % (dtstart.strftime('%H:%M'),
                                    dtend.strftime('%H:%M'))
        else:
            return "%s&ndash;%s" % (dtstart.strftime('%Y-%m-%d %H:%M'),
                                    dtend.strftime('%Y-%m-%d %H:%M'))

    def cssClass(self):
        """Choose a CSS class for the event."""
        if getattr(self.context, 'source', None) == 'timetable-calendar':
            return 'ro_event'
        else:
            return 'event'

    def short(self):
        """Short representation of the event for the monthly view."""
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

    def uniqueId(self):
        """Format the event ID for inclusion in a URL."""
        return urllib.quote(self.context.unique_id)


#
# Calendaring functions
# (Perhaps move them to schooltool.common?)
#

def prev_month(date):
    """Calculate the first day of the previous month for a given date.

       >>> prev_month(date(2004, 8, 1))
       datetime.date(2004, 7, 1)
       >>> prev_month(date(2004, 8, 31))
       datetime.date(2004, 7, 1)
       >>> prev_month(date(2004, 12, 15))
       datetime.date(2004, 11, 1)
       >>> prev_month(date(2005, 1, 28))
       datetime.date(2004, 12, 1)

    """
    return (date.replace(day=1) - timedelta(1)).replace(day=1)


def next_month(date):
    """Calculate the first day of the next month for a given date.

       >>> next_month(date(2004, 8, 1))
       datetime.date(2004, 9, 1)
       >>> next_month(date(2004, 8, 31))
       datetime.date(2004, 9, 1)
       >>> next_month(date(2004, 12, 15))
       datetime.date(2005, 1, 1)
       >>> next_month(date(2004, 2, 28))
       datetime.date(2004, 3, 1)
       >>> next_month(date(2004, 2, 29))
       datetime.date(2004, 3, 1)
       >>> next_month(date(2005, 2, 28))
       datetime.date(2005, 3, 1)

    """
    return (date.replace(day=28) + timedelta(7)).replace(day=1)


def week_start(date, first_day_of_week=0):
    """Calculate the first day of the week for a given date.

    Assuming that week starts on Mondays:

       >>> week_start(date(2004, 8, 19))
       datetime.date(2004, 8, 16)
       >>> week_start(date(2004, 8, 15))
       datetime.date(2004, 8, 9)
       >>> week_start(date(2004, 8, 14))
       datetime.date(2004, 8, 9)
       >>> week_start(date(2004, 8, 21))
       datetime.date(2004, 8, 16)
       >>> week_start(date(2004, 8, 22))
       datetime.date(2004, 8, 16)
       >>> week_start(date(2004, 8, 23))
       datetime.date(2004, 8, 23)

    Assuming that week starts on Sundays:

       >>> import calendar
       >>> week_start(date(2004, 8, 19), calendar.SUNDAY)
       datetime.date(2004, 8, 15)
       >>> week_start(date(2004, 8, 15), calendar.SUNDAY)
       datetime.date(2004, 8, 15)
       >>> week_start(date(2004, 8, 14), calendar.SUNDAY)
       datetime.date(2004, 8, 8)
       >>> week_start(date(2004, 8, 21), calendar.SUNDAY)
       datetime.date(2004, 8, 15)
       >>> week_start(date(2004, 8, 22), calendar.SUNDAY)
       datetime.date(2004, 8, 22)
       >>> week_start(date(2004, 8, 23), calendar.SUNDAY)
       datetime.date(2004, 8, 22)

    """
    assert 0 <= first_day_of_week < 7
    delta = date.weekday() - first_day_of_week
    if delta < 0:
        delta += 7
    return date - timedelta(delta)

