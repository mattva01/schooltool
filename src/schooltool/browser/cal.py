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
from schooltool.browser import AppObjectBreadcrumbsMixin
from schooltool.browser.auth import TeacherAccess, PublicAccess
from schooltool.browser.auth import ACLViewAccess, ACLModifyAccess
from schooltool.browser.auth import ACLAddAccess
from schooltool.browser.acl import ACLView
from schooltool.cal import CalendarEvent, Period
from schooltool.common import to_unicode, parse_date
from schooltool.component import traverse, getPath, getRelatedObjects, traverse
from schooltool.interfaces import IResource, ICalendar, ICalendarEvent
from schooltool.interfaces import ITimetableCalendarEvent
from schooltool.timetable import TimetableException
from schooltool.translation import ugettext as _
from schooltool.uris import URIMember
from schooltool.browser.widgets import TextWidget, SelectionWidget
from schooltool.browser.widgets import dateParser, timeParser, intParser
from schooltool.browser.widgets import timeFormatter

__metaclass__ = type


class BookingView(View, AppObjectBreadcrumbsMixin):

    __used_for__ = IResource

    authorization = TeacherAccess

    template = Template('www/booking.pt')

    error = u""

    booked = False

    def __init__(self, context):
        View.__init__(self, context)
        everyone = self.listAllPersons()
        self.owner_widget = SelectionWidget('owner', _('Owner'), everyone,
                                            parser=self.parse_owner,
                                            formatter=self.format_owner)
        self.date_widget = TextWidget('start_date', _('Date'),
                                      parser=dateParser)
        self.time_widget = TextWidget('start_time', _('Time'),
                                      parser=timeParser,
                                      formatter=timeFormatter)
        self.duration_widget = TextWidget('duration', _('Duration'),
                                          unit=_('min.'),
                                          parser=intParser,
                                          validator=durationValidator,
                                          value=30)

    def listAllPersons(self):
        person_container = traverse(self.context, '/persons')
        persons = [(person.title, person)
                   for person in person_container.itervalues()]
        persons.sort()
        return [(person, title) for title, person in persons]

    def parse_owner(self, raw_value):
        if not raw_value:
            return None
        persons = traverse(self.context, '/persons')
        try:
            return persons[raw_value]
        except KeyError:
            raise ValueError(_("This user does not exist."))

    def format_owner(self, value):
        if value is None:
            return None
        return value.__name__

    def do_GET(self, request):
        self.update()
        return View.do_GET(self, request)

    def update(self):
        request = self.request
        self.owner_widget.update(request)
        self.date_widget.update(request)
        self.time_widget.update(request)
        self.duration_widget.update(request)

        if 'CONFIRM_BOOK' not in request.args:
            # just set the initial values
            self.owner_widget.setValue(request.authenticated_user)
            return

        assert 'CONFIRM_BOOK' in request.args

        if self.isManager():
            self.owner_widget.require()
        self.date_widget.require()
        self.time_widget.require()
        self.duration_widget.require()
        errors = (self.owner_widget.error or self.date_widget.error or
                  self.time_widget.error or self.duration_widget.error)
        if errors:
            return

        start = datetime.combine(self.date_widget.value,
                                 self.time_widget.value)
        duration = timedelta(minutes=self.duration_widget.value)
        force = 'conflicts' in request.args
        if self.isManager():
            owner = self.owner_widget.value
        else:
            owner = request.authenticated_user
        self.booked = self.book(owner, start, duration, force=force)

    def book(self, owner, start, duration, force=False):
        if not force:
            p = Period(start, duration)
            for e in self.context.calendar:
                if p.overlaps(Period(e.dtstart, e.duration)):
                    self.error = _("The resource is busy"
                                   " at the specified time.")
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


class CalendarBreadcrumbsMixin(AppObjectBreadcrumbsMixin):

    def breadcrumbs(self):
        owner = self.context.__parent__
        breadcrumbs = AppObjectBreadcrumbsMixin.breadcrumbs(self,
                                                            context=owner)
        breadcrumbs.append((_('Calendar'),
                            absoluteURL(self.request, owner, 'calendar')))
        return breadcrumbs


class CalendarViewBase(View, CalendarBreadcrumbsMixin):

    __used_for__ = ICalendar

    authorization = ACLViewAccess

    # Which day is considered to be the first day of the week (0 = Monday,
    # 6 = Sunday).  Currently hardcoded.  A similar value is also hardcoded
    # in schooltool.browser.timetable.
    first_day_of_week = 0

    month_names = {
        1: _("January"),
        2: _("February"),
        3: _("March"),
        4: _("April"),
        5: _("May"),
        6: _("June"),
        7: _("July"),
        8: _("August"),
        9: _("September"),
        10: _("October"),
        11: _("November"),
        12: _("December"),
    }

    day_of_week_names = {
        0: _("Monday"),
        1: _("Tuesday"),
        2: _("Wednesday"),
        3: _("Thursday"),
        4: _("Friday"),
        5: _("Saturday"),
        6: _("Sunday"),
    }

    short_day_of_week_names = {
        0: _("Mon"),
        1: _("Tue"),
        2: _("Wed"),
        3: _("Thu"),
        4: _("Fri"),
        5: _("Sat"),
        6: _("Sun"),
    }

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

    def title(self):
        return _('%(month)s, %(year)s (week %(week)s)') % {
                                'month': self.month_names[self.cursor.month],
                                'year': self.cursor.year,
                                'week': self.cursor.isocalendar()[1],
                            }

    def dayTitle(self, day):
        return _('%(day_of_week)s, %(year)s-%(month)s-%(day)s') % {
                    'year': day.year,
                    'month': day.month,
                    'day': day.day,
                    'day_of_week': self.day_of_week_names[day.weekday()]}

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

    def title(self):
        return _('%(month)s, %(year)s') % {
                                'month': self.month_names[self.cursor.month],
                                'year': self.cursor.year,
                            }

    def dayOfWeek(self, date):
        return self.day_of_week_names[date.weekday()]

    def weekTitle(self, date):
        return _('Week %d') % date.isocalendar()[1]

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

    def monthTitle(self, date):
        return self.month_names[date.month]

    def dayOfWeek(self, date):
        return self.short_day_of_week_names[date.weekday()]

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


class EventViewBase(View, CalendarBreadcrumbsMixin):
    """A base class for event adding and editing views."""

    __used_for__ = ICalendar

    authorization = ACLModifyAccess

    template = Template('www/event.pt')
    page_title = None # overridden by subclasses

    def __init__(self, context):
        View.__init__(self, context)
        self.title_widget = TextWidget('title', _('Title'))
        self.date_widget = TextWidget('start_date', _('Date'),
                                      parser=dateParser)
        self.time_widget = TextWidget('start_time', _('Time'),
                                      parser=timeParser,
                                      formatter=timeFormatter)
        self.duration_widget = TextWidget('duration', _('Duration'),
                                          unit=_('min.'),
                                          parser=intParser,
                                          validator=durationValidator,
                                          value=30)
        self.locations = self.getLocations()
        choices = [(l, l) for l in self.locations] + [('', _('Other'))]
        self.location_widget = SelectionWidget('location', _('Location'),
                                               choices, value='')
        self.other_location_widget = TextWidget('location_other',
                                                _('Specify other location'))
        self.error = None

    def update(self):
        """Parse arguments in request and put them into view attributes."""
        request = self.request
        self.title_widget.update(request)
        self.date_widget.update(request)
        self.time_widget.update(request)
        self.duration_widget.update(request)
        self.location_widget.update(request)
        self.other_location_widget.update(request)

    def do_GET(self, request):
        self.update()
        return View.do_GET(self, request)

    def do_POST(self, request):
        self.update()
        if self.title_widget.value == "":
            # Force a "field is required" error if value is ""
            self.title_widget.setRawValue(None)
        self.title_widget.require()
        self.date_widget.require()
        self.time_widget.require()
        self.duration_widget.require()

        errors = (self.title_widget.error or self.date_widget.error or
                  self.time_widget.error or self.duration_widget.error or
                  self.location_widget.error or
                  self.other_location_widget.error)
        if errors:
            return View.do_GET(self, request)

        start = datetime.combine(self.date_widget.value,
                                 self.time_widget.value)
        duration = timedelta(minutes=self.duration_widget.value)

        location = (self.location_widget.value or
                    self.other_location_widget.value or None)

        self.process(start, duration, self.title_widget.value, location)

        suffix = 'daily.html?date=%s' % start.date()
        url = absoluteURL(request, self.context, suffix)
        return self.redirect(url, request)

    def process(self, dtstart, duration, title, location):
        raise NotImplementedError("override this method in subclasses")

    def getLocations(self):
        """Get a list of titles for possible locations."""
        location_group = traverse(self.context, '/groups/locations')
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
        try:
            self.event_id = to_unicode(self.request.args['event_id'][0])
            self.event = self.context.find(self.event_id)
        except (KeyError, UnicodeError):
            # Pehaps it would be better to create a traversal view for events
            # and refactor the event edit view to take the event as context,
            # then we would be able to simply display a standard 404 page.
            self.error = _("This event does not exist.")
            return

        self.title_widget.setValue(self.event.title)
        self.date_widget.setValue(self.event.dtstart.date())
        self.time_widget.setValue(self.event.dtstart.time())
        self.duration_widget.setValue(self.event.duration.seconds // 60)
        if self.event.location in self.locations:
            self.location_widget.setValue(self.event.location)
            self.other_location_widget.setValue('')
        else:
            self.location_widget.setValue('')
            self.other_location_widget.setValue(self.event.location)
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

    template = Template('www/ttevent_delete.pt')

    authorization = ACLModifyAccess

    event = None  # The event to be removed.  Set before rendering the template.

    def do_GET(self, request):
        event = None
        event_id = to_unicode(request.args['event_id'][0])

        try:
            # look for an ordinary calendar event
            event = self.context.find(event_id)
        except KeyError:
            # the event could be a timetable event
            appobject = self.context.__parent__
            try:
                event = appobject.makeCalendar().find(event_id)
            except KeyError:
                pass
            else:
                # found a timetable event
                if 'CONFIRM' in request.args:
                    self._removeTTEvent(event)
                else:
                    self.event = event
                    return View.do_GET(self, request)
        else:
            # found an ordinary event; remove it from the calendar
            self.context.removeEvent(event)

        if event is not None:
            suffix = 'daily.html?date=%s' % event.dtstart.date()
        else:
            suffix = 'daily.html'

        url = absoluteURL(request, self.context, suffix)
        return self.redirect(url, request)

    def _removeTTEvent(self, event):
        exception = TimetableException(event.dtstart.date(),
                                       event.period_id,
                                       event.activity, None)
        tt = event.activity.timetable
        tt.exceptions.append(exception)


class CalendarComboMixin(View):
    """Mixin for views over the combined calendar of a person.

    The calendar events are decorated with a 'source' attribute, which
    is a name of the calendar the event is from.
    """

    def iterEvents(self):
        """Iterate over the events of the calendars displayed"""

        for event in self.context:
            yield event
        for event in self.context.__parent__.makeCalendar():
            yield event


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
        if ITimetableCalendarEvent.providedBy(self.context):
            return 'ro_event' # TODO: rename
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


def durationValidator(value):
    """Check if duration is acceptable.

      >>> durationValidator(None)
      >>> durationValidator(42)
      >>> durationValidator(0)
      >>> durationValidator(-1)
      Traceback (most recent call last):
        ...
      ValueError: Duration cannot be negative.

    """
    if value is None:
        return
    if value < 0:
        raise ValueError(_("Duration cannot be negative."))


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


