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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool application views.
"""

import urllib
import calendar
from datetime import datetime, date, time, timedelta

import transaction
from pytz import utc
from zope.cachedescriptors.property import Lazy
from zope.component import getUtility
from zope.component import queryMultiAdapter, getMultiAdapter
from zope.component import adapts, adapter
from zope.component import subscribers
from zope.event import notify
from zope.interface import implements, implementer, Interface
from zope.i18n import translate
from zope.security.interfaces import ForbiddenAttribute, Unauthorized
from zope.security.proxy import removeSecurityProxy
from zope.proxy import sameProxiedObjects
from zope.security.checker import canAccess, canWrite
from zope.security import checkPermission
from zope.schema import Date, TextLine, Choice, Int, Bool, List, Text
from zope.schema.interfaces import RequiredMissing, ConstraintNotSatisfied
from zope.lifecycleevent import ObjectModifiedEvent
from zope.app.form.browser.add import AddView
from zope.app.form.browser.editview import EditView
from zope.app.form.utility import setUpWidgets
from zope.app.form.interfaces import ConversionError
from zope.app.form.interfaces import IWidgetInputError, IInputWidget
from zope.app.form.interfaces import WidgetInputError, WidgetsError
from zope.app.form.utility import getWidgetsData
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.api import getParent
from zope.filerepresentation.interfaces import IWriteFile, IReadFile
from zope.session.interfaces import ISession
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.html.field import HtmlFragment
from zope.component import queryAdapter
from zope.viewlet.interfaces import IViewletManager

from zc.table.column import GetterColumn
from zc.table import table

from schooltool.common import SchoolToolMessage as _

from schooltool.table.table import CheckboxColumn
from schooltool.table.interfaces import IFilterWidget
from schooltool.app.cal import CalendarEvent
from schooltool.app.browser import ViewPreferences, same
from schooltool.app import pdf
from schooltool.app.browser.interfaces import ICalendarProvider
from schooltool.app.browser.interfaces import IEventForDisplay
from schooltool.app.browser.interfaces import IHaveEventLegend
from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.table.batch import IterableBatch
from schooltool.table.table import label_cell_formatter_factory
from schooltool.calendar.interfaces import ICalendar
from schooltool.calendar.interfaces import IEditCalendar
from schooltool.calendar.recurrent import DailyRecurrenceRule
from schooltool.calendar.recurrent import YearlyRecurrenceRule
from schooltool.calendar.recurrent import MonthlyRecurrenceRule
from schooltool.calendar.recurrent import WeeklyRecurrenceRule
from schooltool.calendar.interfaces import IDailyRecurrenceRule
from schooltool.calendar.interfaces import IYearlyRecurrenceRule
from schooltool.calendar.interfaces import IMonthlyRecurrenceRule
from schooltool.calendar.interfaces import IWeeklyRecurrenceRule
from schooltool.calendar.utils import parse_date, parse_datetimetz
from schooltool.calendar.utils import parse_time
from schooltool.calendar.utils import week_start, prev_month, next_month
from schooltool.common import DateRange
from schooltool.app.utils import vocabulary
from schooltool.person.interfaces import IPerson
from schooltool.term.interfaces import IDateManager
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.app.browser.interfaces import ICalendarMenuViewlet
from schooltool.resource.interfaces import IBaseResource
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.resource.interfaces import IResourceTypeInformation

#
# Calendar names
#

# TODO: use zope.i18n.locales to get this data from CLDR

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
    12: _("December")}

day_of_week_names = {
    0: _("Monday"),
    1: _("Tuesday"),
    2: _("Wednesday"),
    3: _("Thursday"),
    4: _("Friday"),
    5: _("Saturday"),
    6: _("Sunday")}

weekday_names = [
    (0, _("Mon")),
    (1, _("Tue")),
    (2, _("Wed")),
    (3, _("Thu")),
    (4, _("Fri")),
    (5, _("Sat")),
    (6, _("Sun"))]

short_day_of_week_names = dict(weekday_names)


#
# Calendar displaying backend
#

@adapter(IEventForDisplay, IBrowserRequest, IEditCalendar)
@implementer(Interface)
def getCalendarEventDeleteLink(event, request, calendar):
    if not checkPermission("schooltool.edit", event.source_calendar):
        return None
    url = '%s/delete.html?event_id=%s&date=%s' % (
        absoluteURL(calendar, request),
        event.unique_id,
        event.dtstarttz.strftime('%Y-%m-%d'))
    back_url = urllib.quote(event.parent_view_link)
    if back_url:
        url = '%s&back_url=%s' % (url, back_url)
    return url


class EventForDisplay(object):
    """A decorated calendar event."""

    implements(IEventForDisplay)

    cssClass = 'event'  # at the moment no other classes are used

    def __init__(self, event, request, color1, color2, source_calendar,
                 timezone, parent_view_link=''):
        self.request = request
        self.source_calendar = source_calendar
        self.parent_view_link = parent_view_link
        if canAccess(source_calendar, '__iter__'):
            # Due to limitations in the default Zope 3 security
            # policy, a calendar event inherits permissions from the
            # calendar of its __parent__.  However if there's an event
            # that books a resource, and the authenticated user has
            # schooltool.view access for the resource's calendar, she
            # should be able to view this event when it comes from the
            # resource's calendar.  For this reason we have to remove
            # the security proxy and check the permission manually.
            event = removeSecurityProxy(event)
        self.context = event
        self.dtend = event.dtstart + event.duration
        self.color1 = color1
        self.color2 = color2
        self.shortTitle = self.title
        if len(self.title) > 16:
            self.shortTitle = self.title[:15] + '...'
        self.dtstarttz = event.dtstart.astimezone(timezone)
        self.dtendtz = self.dtend.astimezone(timezone)

    def __cmp__(self, other):
        return cmp(self.context.dtstart, other.context.dtstart)

    def __getattr__(self, name):
        return getattr(self.context, name)

    @property
    def title(self):
        return self.context.title

    def getBooker(self):
        """Return the booker."""
        event = ISchoolToolCalendarEvent(self.context, None)
        if event:
            return event.owner

    def getBookedResources(self):
        """Return the list of booked resources."""
        booker = ISchoolToolCalendarEvent(self.context, None)
        if booker:
            return booker.resources
        else:
            return ()

    def viewLink(self):
        """Return the URL where you can view this event.

        Returns None if the event is not viewable (e.g. it is a timetable
        event).
        """
        if self.context.__parent__ is None:
            return None

        if IEditCalendar.providedBy(self.source_calendar):
            # display the link of the source calendar (the event is a
            # booking event)
            return '%s/%s' % (absoluteURL(self.source_calendar, self.request),
                              urllib.quote(self.__name__))

        # if event is comming from an immutable (readonly) calendar,
        # display the absolute url of the event itself
        return absoluteURL(self.context, self.request)


    def editLink(self):
        """Return the URL where you can edit this event.

        Returns None if the event is not editable (e.g. it is a timetable
        event).
        """
        if self.context.__parent__ is None:
            return None

        url = '%s/edit.html?date=%s' % (
            absoluteURL(self.context, self.request),
            self.dtstarttz.strftime('%Y-%m-%d'))

        back_url = urllib.quote(self.parent_view_link)
        if back_url:
            url = '%s&back_url=%s&cancel_url=%s' % (url, back_url, back_url)
        return url

    def deleteLink(self):
        """Return the URL where you can delete this event.

        Returns None if the event is not deletable (e.g. it is a timetable
        event).
        """
        if self.context.__parent__ is None:
            return None

        link = queryMultiAdapter(
            (self, self.request, self.source_calendar), Interface,
            name="delete_link")
        return link

    def linkAllowed(self):
        """Return the URL where you can view/edit this event.

        Returns the URL where can you edit this event if the user can
        edit it, otherwise returns the URL where you can view this event.
        """

        try:
            if self.context.__parent__ is not None and \
               (canWrite(self.context, 'title') or \
               hasattr(self.context, 'original') and \
               canWrite(self.context.original, 'title')):
                return self.editLink()
            else:
                return self.viewLink()
        except ForbiddenAttribute:
        # this exception is raised when the event does not allow
        # us to even check if the title is editable
            return self.viewLink()

    def bookingLink(self):
        """Return the URL where you can book resources for this event.

        Returns None if you can't do that.
        """
        if self.context.__parent__ is None:
            return None
        return '%s/booking.html?date=%s' % (
                        absoluteURL(self.context, self.request),
                        self.dtstarttz.strftime('%Y-%m-%d'))

    def renderShort(self):
        """Short representation of the event for the monthly view."""
        if self.dtstarttz.date() == self.dtendtz.date():
            fmt = '%H:%M'
        else:
            fmt = '%b&nbsp;%d'
        return "%s (%s&ndash;%s)" % (self.shortTitle,
                                     self.dtstarttz.strftime(fmt),
                                     self.dtendtz.strftime(fmt))


class CalendarDay(object):
    """A single day in a calendar.

    Attributes:
       'date'   -- date of the day (a datetime.date instance)
       'title'  -- day title, including weekday and date.
       'events' -- list of events that took place that day, sorted by start
                   time (in ascending order).
    """

    css_class = ''

    def __init__(self, date, events=None, is_today=None):
        if events is None:
            events = []
        self.date = date
        self.events = events
        if is_today is None:
            self.is_today = bool(self.date == getUtility(IDateManager).today)
        else:
            self.is_today = is_today
        if self.is_today:
            self.css_class = (self.css_class + ' cal-day-today').strip()

    def __cmp__(self, other):
        return cmp(self.date, other.date)

    def today(self):
        return self.is_today and 'today' or ''


#
# Calendar display views
#

class CalendarViewBase(BrowserView):
    """A base class for the calendar views.

    This class provides functionality that is useful to several calendar views.
    """

    __used_for__ = ISchoolToolCalendar

    # Which day is considered to be the first day of the week (0 = Monday,
    # 6 = Sunday).  Based on authenticated user preference, defaults to Monday

    cursor = None
    cursor_range = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

        # XXX Clean this up (use self.preferences in this and subclasses)
        prefs = ViewPreferences(request)
        self.today = getUtility(IDateManager).today
        self.first_day_of_week = prefs.first_day_of_week
        self.time_fmt = prefs.timeformat
        self.dateformat = prefs.dateformat
        self.timezone = prefs.timezone

        self._days_cache = None

    def eventAddLink(self, hour):
        item = self.context.__parent__
        if IBaseResource.providedBy(item):
            rc = ISchoolToolApplication(None)['resources']
            booking_calendar = IBookingCalendar(rc)
            url = absoluteURL(booking_calendar, self.request)
            url = "%s/book_one_resource.html?resource_id=%s" % (url, item.__name__)
            url = "%s&start_date=%s&start_time=%s&duration=%s&title=%s" % (
                url, self.cursor, hour['time'], hour['duration']*60,
                translate(_("Unnamed Event"), context=self.request))
        else:
            url = "%s/add.html?field.start_date=%s&field.start_time=%s&field.duration=%s"
            url = url % (absoluteURL(self.context, self.request),
                         self.cursor, hour['time'], hour['duration'])
        return url

    def pdfURL(self):
        if not pdf.enabled:
            return None
        else:
            assert self.cal_type != 'yearly'
            url = self.calURL(self.cal_type, cursor=self.cursor)
            return url + '.pdf'

    def dayTitle(self, day):
        formatter = getMultiAdapter((day, self.request), name='fullDate')
        return formatter()

    __url = None

    def calURL(self, cal_type, cursor=None):
        """Construct a URL to a calendar at cursor."""
        if cursor is None:
            session = ISession(self.request)['calendar']
            dt = session.get('last_visited_day')
            if dt and self.inCurrentPeriod(dt):
                cursor = dt
            else:
                cursor = self.cursor

        if self.__url is None:
            self.__url = absoluteURL(self.context, self.request)

        if cal_type == 'daily':
            dt = cursor.isoformat()
        elif cal_type == 'weekly':
            dt = '%04d-w%02d' % cursor.isocalendar()[:2]
        elif cal_type == 'monthly':
            dt = cursor.strftime('%Y-%m')
        elif cal_type == 'yearly':
            dt = str(cursor.year)
        else:
            raise ValueError(cal_type)

        return '%s/%s' % (self.__url, dt)

    def _initDaysCache(self):
        """Initialize the _days_cache attribute.

        When ``update`` figures out which time period will be displayed to the
        user, it calls ``_initDaysCache`` to give the view a chance to
        precompute the calendar events for the time interval.

        The base implementation designates three months around self.cursor as
        the time interval for caching.
        """
        # The calendar portlet will always want three months around self.cursor
        start_of_prev_month = prev_month(self.cursor)
        first = week_start(start_of_prev_month, self.first_day_of_week)
        end_of_next_month = next_month(next_month(self.cursor)) - timedelta(1)
        last = week_start(end_of_next_month,
                          self.first_day_of_week) + timedelta(7)
        self._days_cache = DaysCache(self._getDays, first, last)

    def update(self):
        """Figure out which date we're supposed to be showing.

        Can extract date from the request or the session.  Defaults on today.
        """
        session = ISession(self.request)['calendar']
        dt = session.get('last_visited_day')
        visited_on = session.get('visited_on')

        if 'date' not in self.request:
            if (visited_on and
                visited_on != self.today):
                # Special case: only restore last visited calendar days
                #               that user looked at today
                dt = None
            self.cursor = dt or self.today
        else:
            # TODO: It would be nice not to b0rk when the date is invalid but
            # fall back to the current date, as if the date had not been
            # specified.
            self.cursor = parse_date(self.request['date'])

        if not (dt and self.inCurrentPeriod(dt)):
            session['last_visited_day'] = self.cursor
            if not visited_on or visited_on != self.today:
                session['visited_on'] = self.today

        self._initDaysCache()

    def inCurrentPeriod(self, dt):
        """Return True if dt is in the period currently being shown."""
        raise NotImplementedError("override in subclasses")

    def pigeonhole(self, intervals, days):
        """Sort CalendarDay objects into date intervals.

        Can be used to sort a list of CalendarDay objects into weeks,
        months, quarters etc.

        `intervals` is a list of date pairs that define half-open time
        intervals (the start date is inclusive, and the end date is
        exclusive).  Intervals can overlap.

        Returns a list of CalendarDay object lists -- one list for
        each interval.
        """
        results = []
        for start, end in intervals:
            results.append([day for day in days if start <= day.date < end])
        return results

    def getWeek(self, dt):
        """Return the week that contains the day dt.

        Returns a list of CalendarDay objects.
        """
        start = week_start(dt, self.first_day_of_week)
        end = start + timedelta(7)
        return self.getDays(start, end)

    def getMonth(self, dt, days=None):
        """Return a nested list of days in the month that contains dt.

        Returns a list of lists of date objects.  Days in neighbouring
        months are included if they fall into a week that contains days in
        the current month.
        """
        start_of_next_month = next_month(dt)
        start_of_week = week_start(dt.replace(day=1), self.first_day_of_week)
        start_of_display_month = start_of_week

        week_intervals = []
        while start_of_week < start_of_next_month:
            start_of_next_week = start_of_week + timedelta(7)
            week_intervals.append((start_of_week, start_of_next_week))
            start_of_week = start_of_next_week

        end_of_display_month = start_of_week
        if not days:
            days = self.getDays(start_of_display_month, end_of_display_month)
        # Make sure the cache contains all the days we're interested in
        assert days[0].date <= start_of_display_month, 'not enough days'
        assert days[-1].date >= end_of_display_month - timedelta(1), 'not enough days'
        weeks = self.pigeonhole(week_intervals, days)
        return weeks

    def getYear(self, dt):
        """Return the current year.

        This returns a list of quarters, each quarter is a list of months,
        each month is a list of weeks, and each week is a list of CalendarDays.
        """
        first_day_of_year = date(dt.year, 1, 1)
        year_start_day_padded_weeks = week_start(first_day_of_year,
                                                 self.first_day_of_week)
        last_day_of_year = date(dt.year, 12, 31)
        year_end_day_padded_weeks = week_start(last_day_of_year,
                                               self.first_day_of_week) + timedelta(7)

        day_cache = self.getDays(year_start_day_padded_weeks,
                                 year_end_day_padded_weeks)

        quarters = []
        for q in range(4):
            quarter = [self.getMonth(date(dt.year, month + (q * 3), 1),
                                     day_cache)
                       for month in range(1, 4)]
            quarters.append(quarter)
        return quarters

    _day_events = None # cache

    def dayEvents(self, date):
        """Return events for a day sorted by start time.

        Events spanning several days and overlapping with this day
        are included.
        """
        if self._day_events is None:
            self._day_events = {}

        if date in self._day_events:
            day = self._day_events[date]
        else:
            day = self.getDays(date, date + timedelta(1))[0]
            self._day_events[date] = day
        return day.events

    _calendars = None # cache

    def getCalendars(self):
        providers = subscribers((self.context, self.request), ICalendarProvider)

        if self._calendars is None:
            result = []
            for provider in providers:
                result += provider.getCalendars()
            self._calendars = result
        return self._calendars

    def getEvents(self, start_dt, end_dt):
        """Get a list of EventForDisplay objects for a selected time interval.

        `start_dt` and `end_dt` (datetime objects) are bounds (half-open) for
        the result.
        """
        view_link = absoluteURL(self.context, self.request)
        for calendar, color1, color2 in self.getCalendars():
            for event in calendar.expand(start_dt, end_dt):
                if (same(event.__parent__, self.context) and
                    calendar is not self.context):
                    # Skip resource booking events (coming from
                    # overlaid calendars) if they were booked by the
                    # person whose calendar we are viewing.
                    # removeSecurityProxy(event.__parent__) and
                    # removeSecurityProxy(self.context) are needed so we
                    # could compare them.
                    continue
                yield EventForDisplay(event, self.request, color1, color2,
                                      calendar, self.timezone,
                                      parent_view_link=view_link)

    def collapseEvents(self, events):
        """Collapse events that come from multiple calendars."""
        events = sorted(events, key=lambda e:e.unique_id)
        by_uid = {}
        for event in events:
            uid = (event.context.unique_id, event.context.dtstart)
            if uid in by_uid:
                known = by_uid[uid]
                if (sameProxiedObjects(known.source_calendar,
                                       known.context.__parent__) or
                    not sameProxiedObjects(event.source_calendar,
                                           event.context.__parent__)):
                    continue
            by_uid[uid] = event
        return by_uid.values()

    def getDays(self, start, end):
        """Get a list of CalendarDay objects for a selected period of time.

        Uses the _days_cache.

        `start` and `end` (date objects) are bounds (half-open) for the result.

        Events spanning more than one day get included in all days they
        overlap.
        """
        if self._days_cache is None:
            return self._getDays(start, end)
        else:
            return self._days_cache.getDays(start, end)

    def _getDays(self, start, end):
        """Get a list of CalendarDay objects for a selected period of time.

        No caching.

        `start` and `end` (date objects) are bounds (half-open) for the result.

        Events spanning more than one day get included in all days they
        overlap.
        """
        events = {}
        day = start
        while day < end:
            events[day] = []
            day += timedelta(1)

        # We have date objects, but ICalendar.expand needs datetime objects
        start_dt = self.timezone.localize(datetime.combine(start, time()))
        end_dt = self.timezone.localize(datetime.combine(end, time()))
        for event in self.collapseEvents(self.getEvents(start_dt, end_dt)):
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
            dtend = event.dtend
            if event.allday:
                # XXX: I do dislike that allday events happen in different
                #      timezone (UTC) than local events (view prefs).
                first_day = event.dtstart.date()
                last_day = max(first_day, (dtend - dtend.resolution).date())
            else:
                first_day = event.dtstart.astimezone(self.timezone).date()
                last_day = max(first_day, (dtend.astimezone(self.timezone) -
                                           dtend.resolution).date())
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
        today = self.today
        while day < end:
            events[day].sort()
            days.append(CalendarDay(day, events[day], is_today=bool(today==day)))
            day += timedelta(1)
        return days

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

    def getJumpToYears(self):
        """Return jump targets for five years centered on the current year."""
        this_year = self.today.year
        return [{'selected': year == this_year,
                 'label': year,
                 'href': self.calURL('yearly', date(year, 1, 1))}
                for year in range(this_year - 2, this_year + 3)]

    def getJumpToMonths(self):
        """Return a list of months for the drop down in the jump portlet."""
        year = self.cursor.year
        return [{'label': v,
                 'href': self.calURL('monthly', date(year, k, 1))}
                for k, v in month_names.items()]

    def monthTitle(self, date):
        return month_names[date.month]

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
                                           or  'cal_yearly_day')
                                        + (day.today() and ' today' or '')"/>
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
                if day.today():
                    cssClass += ' today'
                cssClass = ('%s %s' % (cssClass, day.css_class)).strip()
                # Let us hope that URLs will not contain < > & or "
                # This is somewhat related to
                #   http://issues.schooltool.org/issue96
                result.append('<a href="%s" class="%s">%s</a>' %
                              (self.calURL('daily', day.date), cssClass,
                               day.date.day))
            result.append('</td>')
        return "\n".join(result)

    def canAddEvents(self):
        """Return True if current viewer can add events to this calendar."""
        return canAccess(self.context, "addEvent")

    def canRemoveEvents(self):
        """Return True if current viewer can remove events to this calendar."""
        return canAccess(self.context, "removeEvent")


class DaysCache(object):
    """A cache of calendar days.

    Since the expansion of recurrent calendar events, and the pigeonholing of
    calendar events into days is an expensive task, it is better to compute
    the calendar days of a single larger period of time, and then refer
    to subsets of the result.

    DaysCache provides an object that is able to do so.  The goal here is that
    any view will need perform the expensive computation only once or twice.
    """

    def __init__(self, expensive_getDays, cache_first, cache_last):
        """Create a cache.

        ``expensive_getDays`` is a function that takes a half-open date range
        and returns a list of CalendarDay objects.

        ``cache_first`` and ``cache_last`` provide the initial approximation
        of the date range that will be needed in the future.  You may later
        extend the cache interval by calling ``extend``.
        """
        self.expensive_getDays = expensive_getDays
        self.cache_first = cache_first
        self.cache_last = cache_last
        self._cache = None

    def extend(self, first, last):
        """Extend the cache.

        You should call ``extend`` before any calls to ``getDays``, and not
        after.
        """
        self.cache_first = min(self.cache_first, first)
        self.cache_last = max(self.cache_last, last)

    def getDays(self, first, last):
        """Return a list of calendar days from ``first`` to ``last``.

        If the interval from ``first`` to ``last`` falls into the cached
        range, and the cache is already computed, this operation becomes
        fast.

        If the interval is not in cache, delegates to the expensive_getDays
        computation.
        """
        assert first <= last, 'invalid date range: %s..%s' % (first, last)
        if first >= self.cache_first and last <= self.cache_last:
            if self._cache is None:
                self._cache = self.expensive_getDays(self.cache_first,
                                                     self.cache_last)
            first_idx = (first - self.cache_first).days
            last_idx = (last - self.cache_first).days
            return self._cache[first_idx:last_idx]
        else:
            return self.expensive_getDays(first, last)


class WeeklyCalendarView(CalendarViewBase):
    """A view that shows one week of the calendar."""
    implements(IHaveEventLegend)

    __used_for__ = ISchoolToolCalendar

    cal_type = 'weekly'

    next_title = _("Next week")
    current_title = _("Current week")
    prev_title = _("Previous week")

    go_to_next_title = _("Go to next week")
    go_to_current_title = _("Go to current week")
    go_to_prev_title = _("Go to previous week")

    non_timetable_template = ViewPageTemplateFile("templates/cal_weekly.pt")
    timetable_template = ViewPageTemplateFile("templates/cal_weekly_timetable.pt")

    def __call__(self):
        app = ISchoolToolApplication(None)
        # XXX ttshemas were removed from app in evolve28.
        #     timetable_template can be killed now (maybe?).
        #     All related code should go to land of no return.
        if 'ttschemas' in app and app['ttschemas'].default_id is not None:
            return self.timetable_template()
        return self.non_timetable_template()

    def inCurrentPeriod(self, dt):
        # XXX wrong if week starts on Sunday.
        return dt.isocalendar()[:2] == self.cursor.isocalendar()[:2]

    @property
    def cursor_range(self):
        cursor = self.cursor
        if cursor is None:
            return None
        first = date(cursor.year, cursor.month, cursor.day)
        while first.isoweekday() > 1:
            first -= timedelta(days=1)
        last = first + timedelta(weeks=1) - timedelta(days=1)
        cursor_range = DateRange(first, last)
        return cursor_range

    def title(self):
        month_name_msgid = month_names[self.cursor.month]
        month_name = translate(month_name_msgid, context=self.request)
        msg = _('${month}, ${year} (week ${week})',
                mapping = {'month': month_name,
                           'year': self.cursor.year,
                           'week': self.cursor.isocalendar()[1]})
        return msg

    def prev(self):
        """Return the link for the previous week."""
        return self.calURL('weekly', self.cursor - timedelta(weeks=1))

    def current(self):
        """Return the link for the current week."""
        return self.calURL('weekly', self.today)

    def next(self):
        """Return the link for the next week."""
        return self.calURL('weekly', self.cursor + timedelta(weeks=1))

    def getCurrentWeek(self):
        """Return the current week as a list of CalendarDay objects."""
        return self.getWeek(self.cursor)

    def cloneEvent(self, event):
        """Returns a copy of an event so that it can be inserted into a list."""
        new_event = EventForDisplay(CalendarEvent(event.dtstart,
                                    event.duration,
                                    event.title),
                                    self.request, event.color1,
                                    event.color2, event.source_calendar,
                                    event.dtendtz.tzinfo)
        new_event.linkAllowed = event.linkAllowed
        new_event.allday = event.allday
        return new_event

    def getCurrentWeekEvents(self, eventCheck):
        week = self.getWeek(self.cursor)
        week_by_rows = []
        start_times = []

        for day in week:
            for event in day.events:
                if (eventCheck(event, day) and not
                   (event.dtstart.hour, event.dtstart.minute) in start_times):
                    start_times.append((event.dtstart.hour,
                                        event.dtstart.minute))
                    week_by_rows.append([])

        start_times.sort()
        for day in week:
            events_in_day = []
            for index in range(0, len(start_times)):
                block = []
                for event in day.events:
                    if (eventCheck(event, day) and
                       (event.dtstart.hour, event.dtstart.minute) ==
                        start_times[index] and
                        event.dtstart.day == day.date.day):
                        block.append(event)

                if block == []:
                    block = [None]

                events_in_day.append(block)

            row_num = 0
            for event in events_in_day:
                week_by_rows[row_num].append(event)
                row_num += 1

        self.formatCurrentWeekEvents(week_by_rows)
        return week_by_rows

    def formatCurrentWeekEvents(self, week_by_rows):
        """Formats a list of rows of events by deleting blank rows and extending
           rows to fill the entire week."""
        row_num = 0
        while row_num < len(week_by_rows):
            non_empty_row = False
            while (len(week_by_rows[row_num]) > 0
                  and len(week_by_rows[row_num]) < len(day_of_week_names)):
                week_by_rows[row_num].append([])

            for block in week_by_rows[row_num]:
                for event in block:
                    if event is not None:
                        non_empty_row = True
                        break

            if non_empty_row:
                row_num += 1
            else:
                del week_by_rows[row_num]

    def getCurrentWeekNonTimetableEvents(self):
        """Return the current week's events in formatted lists."""
        eventCheck = lambda e, day: e is not None
        return self.getCurrentWeekEvents(eventCheck)

    def getCurrentWeekTimetableEvents(self):
        """Return the current week's timetable events in formatted lists."""
        week = self.getWeek(self.cursor)
        week_by_rows = []
        view = getMultiAdapter((self.context, self.request),
                                name='daily_calendar_rows')

        empty_begin_days = 0
        for day in week:
            periods = view.getPeriods(day.date)
            events_in_day = []
            start_times = []

            if periods == [] and week_by_rows == []:
                empty_begin_days += 1

            for period, tstart, duration in periods:
                if not tstart in start_times:
                    start_times.append(tstart)
                    week_by_rows.append([])
                if not tstart + duration in start_times:
                    start_times.append(tstart + duration)
                    week_by_rows.append([])

            for index in range(0, len(start_times)-1):
                block = []
                for event in day.events:
                    if ((((start_times[index] < event.dtstart + event.duration
                           and start_times[index] > event.dtstart) or
                          (event.dtstart < start_times[index+1] and
                           event.dtstart > start_times[index])) or
                           event.dtstart == start_times[index]) and
                           not event.allday):
                        block.append(event)
                if block == []:
                    block = [None]

                events_in_day.append(block)

            row_num = 0
            for event in events_in_day:
                week_by_rows[row_num].append(event)
                row_num += 1

        self.formatCurrentWeekEvents(week_by_rows)

        if empty_begin_days > 0:
           old_week_by_rows = week_by_rows
           new_week_by_rows = []
           for week_by_row in old_week_by_rows:
               new_week_by_row = []
               for i in range(0,empty_begin_days):
                   new_week_by_row.append([None])
               j = 0
               while j < len(week_by_row)-empty_begin_days:
                   new_week_by_row.append(week_by_row[j])
                   j += 1
               new_week_by_rows.append(new_week_by_row)
           week_by_rows = new_week_by_rows
        return week_by_rows

    def getCurrentWeekAllDayEvents(self):
        """Return the current week's all day events in formatted lists."""
        eventCheck = lambda e, day: e is not None and e.allday
        return self.getCurrentWeekEvents(eventCheck)

    def getCurrentWeekEventsBeforeTimetable(self):
        """Return the current week's events that start before the timetable
           events in formatted lists."""
        view = getMultiAdapter((self.context, self.request),
                                    name='daily_calendar_rows')
        eventCheck = lambda e, day: (e is not None and not e.allday and
                                    (view.getPeriods(day.date) == [] or
                                     e.dtstart < view.getPeriods(day.date)[0][1]))
        return self.getCurrentWeekEvents(eventCheck)

    def getCurrentWeekEventsAfterTimetable(self):
        """Return the current week's events that start after the timetable
           events in formatted lists."""
        view = getMultiAdapter((self.context, self.request),
                                    name='daily_calendar_rows')
        eventCheck = lambda e, day: (view.getPeriods(day.date) != [] and
                                     e is not None and not e.allday and
                                     e.dtstart + e.duration >
                                     view.getPeriods(day.date)[-1][1] +
                                     view.getPeriods(day.date)[-1][2])
        return self.getCurrentWeekEvents(eventCheck)


class AtomCalendarView(WeeklyCalendarView):
    """View the upcoming week's events in Atom formatted xml."""

    def __call__(self):
        return super(WeeklyCalendarView, self).__call__()

    def getCurrentWeek(self):
        """Return the current week as a list of CalendarDay objects."""
        return self.getWeek(self.today)

    def w3cdtf_datetime(self, dt):
        # XXX: shouldn't assume the datetime is in UTC
        assert dt.tzname() == 'UTC'
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def w3cdtf_datetime_now(self):
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


class MonthlyCalendarView(CalendarViewBase):
    """Monthly calendar view."""
    implements(IHaveEventLegend)

    __used_for__ = ISchoolToolCalendar

    cal_type = 'monthly'

    next_title = _("Next month")
    current_title = _("Current month")
    prev_title = _("Previous month")

    go_to_next_title = _("Go to next month")
    go_to_current_title = _("Go to current month")
    go_to_prev_title = _("Go to previous month")

    def inCurrentPeriod(self, dt):
        return (dt.year, dt.month) == (self.cursor.year, self.cursor.month)

    @property
    def cursor_range(self):
        cursor = self.cursor
        if cursor is None:
            return None
        first = date(cursor.year, cursor.month, 1)
        if first.month == 12:
            last = date(first.year+1, 1, 1)
        else:
            last = date(first.year, first.month+1, 1)
        last -= timedelta(days=1)
        cursor_range = DateRange(first, last)
        return cursor_range

    def title(self):
        month_name_msgid = month_names[self.cursor.month]
        month_name = translate(month_name_msgid, context=self.request)
        msg = _('${month}, ${year}',
                mapping={'month': month_name, 'year': self.cursor.year})
        return msg

    def prev(self):
        """Return the link for the previous month."""
        return self.calURL('monthly', self.prevMonth())

    def current(self):
        """Return the link for the current month."""
        # XXX shouldn't use date.today; it depends on the server's timezone
        # which may not match user expectations
        return self.calURL('monthly', self.today)

    def next(self):
        """Return the link for the next month."""
        return self.calURL('monthly', self.nextMonth())

    def dayOfWeek(self, date):
        return day_of_week_names[date.weekday()]

    def weekTitle(self, date):
        msg = _('Week ${week_no}',
                mapping={'week_no': date.isocalendar()[1]})
        return msg

    def getCurrentMonth(self):
        """Return the current month as a nested list of CalendarDays."""
        return self.getMonth(self.cursor)


class YearlyCalendarView(CalendarViewBase):
    """Yearly calendar view."""

    __used_for__ = ISchoolToolCalendar

    cal_type = 'yearly'

    next_title = _("Next year")
    current_title = _("Current year")
    prev_title = _("Previous year")

    go_to_next_title = _("Go to next year")
    go_to_current_title = _("Go to current year")
    go_to_prev_title = _("Go to previous year")

    def pdfURL(self):
        return None

    def inCurrentPeriod(self, dt):
        return dt.year == self.cursor.year

    @property
    def cursor_range(self):
        cursor = self.cursor
        if cursor is None:
            return None
        first = date(cursor.year, 1, 1)
        last = date(cursor.year+1, 1, 1)
        last -= timedelta(days=1)
        cursor_range = DateRange(first, last)
        return cursor_range

    def title(self):
        return unicode(self.cursor.year)

    def prev(self):
        """Return the link for the previous year."""
        return self.calURL('yearly', date(self.cursor.year - 1, 1, 1))

    def current(self):
        """Return the link for the current year."""
        # XXX shouldn't use date.today; it depends on the server's timezone
        # which may not match user expectations
        return self.calURL('yearly', self.today)

    def next(self):
        """Return the link for the next year."""
        return self.calURL('yearly', date(self.cursor.year + 1, 1, 1))

    def shortDayOfWeek(self, date):
        return short_day_of_week_names[date.weekday()]

    def _initDaysCache(self):
        """Initialize the _days_cache attribute.

        When ``update`` figures out which time period will be displayed to the
        user, it calls ``_initDaysCache`` to give the view a chance to
        precompute the calendar events for the time interval.

        This implementation designates the year of self.cursor as the time
        interval for caching.
        """
        CalendarViewBase._initDaysCache(self)
        first_day_of_year = self.cursor.replace(month=1, day=1)
        first = week_start(first_day_of_year, self.first_day_of_week)
        last_day_of_year = self.cursor.replace(month=12, day=31)
        last = week_start(last_day_of_year,
                          self.first_day_of_week) + timedelta(7)
        self._days_cache.extend(first, last)


class DailyCalendarView(CalendarViewBase):
    """Daily calendar view.

    The events are presented as boxes on a 'sheet' with rows
    representing hours.

    The challenge here is to present the events as a table, so that
    the overlapping events are displayed side by side, and the size of
    the boxes illustrate the duration of the events.
    """
    implements(IHaveEventLegend)

    __used_for__ = ISchoolToolCalendar

    cal_type = 'daily'

    starthour = 8
    endhour = 19

    next_title = _("The next day")
    current_title = _("Today")
    prev_title = _("The previous day")

    go_to_next_title = _("Go to the next day")
    go_to_current_title = _("Go to today")
    go_to_prev_title = _("Go to the previous day")

    def inCurrentPeriod(self, dt):
        return dt == self.cursor

    @property
    def cursor_range(self):
        cursor = self.cursor
        if cursor is None:
            return None
        return DateRange(cursor, cursor)

    def title(self):
        return self.dayTitle(self.cursor)

    def prev(self):
        """Return the link for the next day."""
        return self.calURL('daily', self.cursor - timedelta(1))

    def current(self):
        """Return the link for today."""
        # XXX shouldn't use date.today; it depends on the server's timezone
        # which may not match user expectations
        return self.calURL('daily', self.today)

    def next(self):
        """Return the link for the previous day."""
        return self.calURL('daily', self.cursor + timedelta(1))

    def getColumns(self):
        """Return the maximum number of events that are overlapping.

        Extends the event so that start and end times fall on hour
        boundaries before calculating overlaps.
        """
        width = [0] * 24
        daystart = datetime.combine(self.cursor, time(tzinfo=utc))
        events = self.dayEvents(self.cursor)
        for event in events:
            t = daystart
            dtend = daystart + timedelta(1)
            for title, start, duration in self.calendarRows(events):
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

    def _setRange(self, events, periods):
        """Set the starthour and endhour attributes according to events and
        periods.

        The range of the hours to display is the union of the range
        8:00-18:00 and time spans of all the events in the events
        list and all the periods as well.
        """
        time_blocks = ([(event.dtstart, event.duration) for event in events] +
            [(dtstart, duration) for id, dtstart, duration in periods])
        for dtstart, duration in time_blocks:
            start = self.timezone.localize(datetime.combine(self.cursor,
                                            time(self.starthour)))
            end = self.timezone.localize(datetime.combine(self.cursor,
                   time()) + timedelta(hours=self.endhour)) # endhour may be 24
            if dtstart < start:
                newstart = max(self.timezone.localize(
                                        datetime.combine(self.cursor, time())),
                                        dtstart.astimezone(self.timezone))
                self.starthour = newstart.hour

            if dtstart + duration > end and \
                dtstart.astimezone(self.timezone).day <= self.cursor.day:
                newend = min(self.timezone.localize(
                                        datetime.combine(self.cursor,
                                                        time())) + timedelta(1),
                            dtstart.astimezone(self.timezone) +
                                        duration + timedelta(0, 3599))
                self.endhour = newend.hour
                if self.endhour == 0:
                    self.endhour = 24

    __cursor = None
    __calendar_rows = None

    def calendarRows(self, events):
        """Iterate over (title, start, duration) of time slots that make up
        the daily calendar.

        Returns a list, caches the answer for subsequent calls.
        """
        view = getMultiAdapter((self.context, self.request),
                                    name='daily_calendar_rows')
        return view.calendarRows(self.cursor, self.starthour, self.endhour,
                                 events)

    def _getCurrentTime(self):
        """Returns current time localized to UTC timezone."""
        return utc.localize(datetime.utcnow())

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
        all_events = self.dayEvents(self.cursor)
        # Filter allday events
        simple_events = [event for event in all_events
                         if not event.allday]
        # use daily_calendar_rows view to get the periods
        view = getMultiAdapter((self.context, self.request),
                                    name='daily_calendar_rows')
        if 'getPeriods' in dir(view):
            periods = view.getPeriods(self.cursor)
        else:
            periods = []
        # set this view's start and end hours from the events and periods
        self._setRange(simple_events, periods)
        slots = Slots()
        top = 0
        for title, start, duration in self.calendarRows(simple_events):
            end = start + duration
            hour = start.hour

            # Remove the events that have already ended
            for i in range(nr_cols):
                ev = slots.get(i, None)
                if ev is not None and ev.dtstart + ev.duration <= start:
                    del slots[i]

            # Add events that start during (or before) this hour
            while (simple_events and simple_events[0].dtstart < end):
                event = simple_events.pop(0)
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

            height = duration.seconds / 900.0
            if height < 1.5:
                # Do not display the time of the start of the period when there
                # is too little space as that looks rather ugly.
                title = ''

            active = start <= self._getCurrentTime() < end

            yield {'title': title,
                   'full_title': translate(_("Add new event starting at "
                                             "${title}",
                                             mapping={"title": title})),
                   'cols': tuple(cols),
                   'time': start.strftime("%H:%M"),
                   'active': active,
                   'top': top,
                   'height': height,
                   # We can trust no period will be longer than a day
                   'duration': duration.seconds // 60}

            top += height

    def snapToGrid(self, dt):
        """Calculate the position of a datetime on the display grid.

        The daily view uses a grid where a unit (currently 'em', but that
        can be changed in the page template) corresponds to 15 minutes, and
        0 represents self.starthour.

        Clips dt so that it is never outside today's box.
        """
        base = self.timezone.localize(datetime.combine(self.cursor, time()))
        display_start = base + timedelta(hours=self.starthour)
        display_end = base + timedelta(hours=self.endhour)
        clipped_dt = max(display_start, min(dt, display_end))
        td = clipped_dt - display_start
        offset_in_minutes = td.seconds / 60 + td.days * 24 * 60
        return offset_in_minutes / 15.

    def eventTop(self, event):
        """Calculate the position of the top of the event block in the display.

        See `snapToGrid`.
        """
        return self.snapToGrid(event.dtstart.astimezone(self.timezone))

    def eventHeight(self, event, minheight=3):
        """Calculate the height of the event block in the display.

        Rounds the height up to a minimum of minheight.

        See `snapToGrid`.
        """
        dtend = event.dtstart + event.duration
        return max(minheight,
                   self.snapToGrid(dtend) - self.snapToGrid(event.dtstart))

    def getAllDayEvents(self):
        """Get a list of EventForDisplay objects for the all-day events at the
        cursors current position.
        """
        for event in self.dayEvents(self.cursor):
            if event.allday:
                yield event


class DailyCalendarRowsView(BrowserView):
    """Daily calendar rows view for SchoolTool.

    This view differs from the original view in SchoolTool in that it can
    also show day periods instead of hour numbers.
    """
    __used_for__ = ISchoolToolCalendar

    def getPersonTimezone(self):
        """Return the prefered timezone of the user."""
        return ViewPreferences(self.request).timezone

    def calendarRows(self, cursor, starthour, endhour, events):
        """Iterate over (title, start, duration) of time slots that make up
        the daily calendar.

        Returns a generator.
        """
        tz = self.getPersonTimezone()
        daystart = tz.localize(datetime.combine(cursor, time()))
        rows = [daystart + timedelta(hours=hour)
                for hour in range(starthour, endhour+1)]

        calendar_rows = []

        starts, row_ends = rows[0], rows[1:]
        starts = starts.astimezone(tz)
        for end in row_ends:
            duration = end - starts
            calendar_rows.append(
                (self.rowTitle(starts, duration), starts, duration))
            starts = end
        return calendar_rows

    def rowTitle(self, starts, duration):
        """Return the row title as HH:MM or H:MM am/pm."""
        prefs = ViewPreferences(self.request)
        return starts.strftime(prefs.timeformat)


class CalendarListSubscriber(object):
    """A subscriber that can tell which calendars should be displayed.

    This subscriber includes composite timetable calendars, overlaid
    calendars and the calendar you are looking at.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """
        # personal calendar
        yield (self.context, '#9db8d2', '#7590ae')

        parent = getParent(self.context)

        user = IPerson(self.request.principal, None)
        if user is None:
            return # unauthenticated user

        unproxied_context = removeSecurityProxy(self.context)
        unproxied_calendar = removeSecurityProxy(ISchoolToolCalendar(user))
        if unproxied_context is not unproxied_calendar:
            return # user looking at the calendar of some other person

        for item in user.overlaid_calendars:
            if canAccess(item.calendar, '__iter__'):
                # overlaid calendars
                if item.show:
                    yield (item.calendar, item.color1, item.color2)


#
# Calendar modification views
#


class EventDeleteView(BrowserView):
    """A view for deleting events."""

    __used_for__ = ISchoolToolCalendar

    recevent_template = ViewPageTemplateFile("templates/recevent_delete.pt")
    simple_event_template = ViewPageTemplateFile("templates/simple_event_delete.pt")

    def __call__(self):
        event_id = self.request['event_id']
        date = parse_date(self.request['date'])
        self.event = self._findEvent(event_id)

        if self.event is None:
            # The event was not found.
            return self._redirectBack()

        if self.event.recurrence is None or self.event.__parent__ != self.context:
            return self._deleteSimpleEvent(self.event)
        else:
            # The event is recurrent, we might need to show a form.
            return self._deleteRepeatingEvent(self.event, date)

    def _findEvent(self, event_id):
        """Find an event that has the id event_id.

        First the event is searched for in the current calendar and then,
        overlaid calendars if any.

        If no event with the given id is found, None is returned.
        """
        try:
            return self.context.find(event_id)
        except KeyError:
            pass

    def _redirectBack(self):
        """Redirect to the current calendar's daily view."""
        self.request.response.redirect(
            self.request.get('back_url', '').encode('utf-8') or
            absoluteURL(self.context, self.request))

    def _deleteRepeatingEvent(self, event, date):
        """Delete a repeating event."""
        if 'CANCEL' in self.request:
            pass # Fall through and redirect back to the calendar.
        elif 'ALL' in self.request:
            self.context.removeEvent(removeSecurityProxy(event))
        elif 'FUTURE' in self.request:
            self._modifyRecurrenceRule(event, until=(date - timedelta(1)),
                                       count=None)
        elif 'CURRENT' in self.request:
            exceptions = event.recurrence.exceptions + (date, )
            self._modifyRecurrenceRule(event, exceptions=exceptions)
        else:
            return self.recevent_template()

        # We did our job, redirect back to the calendar view.
        return self._redirectBack()

    def _deleteSimpleEvent(self, event):
        """Delete a simple event."""
        if 'CANCEL' in self.request:
            pass # Fall through and redirect back to the calendar.
        elif 'DELETE' in self.request:
            self.context.removeEvent(removeSecurityProxy(event))
        else:
            return self.simple_event_template()

        # We did our job, redirect back to the calendar view.
        return self._redirectBack()

    def _modifyRecurrenceRule(self, event, **kwargs):
        """Modify the recurrence rule of an event.

        If the event does not have any recurrences afterwards, it is removed
        from the parent calendar
        """
        rrule = event.recurrence
        new_rrule = rrule.replace(**kwargs)
        # This view requires the modifyEvent permission.
        event.recurrence = removeSecurityProxy(new_rrule)
        if not event.hasOccurrences():
            ICalendar(event).removeEvent(removeSecurityProxy(event))


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


class CalendarEventView(BrowserView):
    """View for single events."""

    # XXX what are these used for?
    color1 = '#9db8d2'
    color2 = '#7590ae'

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.preferences = ViewPreferences(request)

        self.dtstart = context.dtstart.astimezone(self.preferences.timezone)
        self.dtend = self.dtstart + context.duration
        self.start = self.dtstart.strftime(self.preferences.timeformat)
        self.end = self.dtend.strftime(self.preferences.timeformat)

        dayformat = '%A, ' + self.preferences.dateformat
        self.day = unicode(self.dtstart.strftime(dayformat))

        self.display = EventForDisplay(context, self.request,
                                       self.color1, self.color2,
                                       context.__parent__,
                                       timezone=self.preferences.timezone)


class ICalendarEventAddForm(Interface):
    """Schema for event adding form."""

    title = TextLine(
        title=_("Title"),
        required=False)
    allday = Bool(
        title=_("All day"),
        required=False)
    start_date = Date(
        title=_("Date"),
        required=False)
    start_time = TextLine(
        title=_("Time"),
        description=_("Start time in 24h format"),
        required=False)

    duration = Int(
        title=_("Duration"),
        required=False,
        default=60)

    duration_type = Choice(
        title=_("Duration Type"),
        required=False,
        default="minutes",
        vocabulary=vocabulary([("minutes", _("Minutes")),
                               ("hours", _("Hours")),
                               ("days", _("Days"))]))

    location = TextLine(
        title=_("Location"),
        required=False)

    description = HtmlFragment(
        title=_("Description"),
        required=False)

    # Recurrence
    recurrence = Bool(
        title=_("Recurring"),
        required=False)

    recurrence_type = Choice(
        title=_("Recurs every"),
        required=True,
        default="daily",
        vocabulary=vocabulary([("daily", _("Day")),
                               ("weekly", _("Week")),
                               ("monthly", _("Month")),
                               ("yearly", _("Year"))]))

    interval = Int(
        title=_("Repeat every"),
        required=False,
        default=1)

    range = Choice(
        title=_("Range"),
        required=False,
        default="forever",
        vocabulary=vocabulary([("count", _("Count")),
                               ("until", _("Until")),
                               ("forever", _("forever"))]))

    count = Int(
        title=_("Number of events"),
        required=False)

    until = Date(
        title=_("Repeat until"),
        required=False)

    weekdays = List(
        title=_("Weekdays"),
        required=False,
        value_type=Choice(
            title=_("Weekday"),
            vocabulary=vocabulary(weekday_names)))

    monthly = Choice(
        title=_("Monthly"),
        default="monthday",
        required=False,
        vocabulary=vocabulary([("monthday", "md"),
                               ("weekday", "wd"),
                               ("lastweekday", "lwd")]))

    exceptions = Text(
        title=_("Exception dates"),
        required=False)


class CalendarEventViewMixin(object):
    """A mixin that holds the code common to CalendarEventAdd and Edit Views."""

    timezone = utc

    def _setError(self, name, error=RequiredMissing()):
        """Set an error on a widget."""
        # XXX Touching widget._error is bad, see
        #     http://dev.zope.org/Zope3/AccessToWidgetErrors
        # The call to setRenderedValue is necessary because
        # otherwise _getFormValue will call getInputValue and
        # overwrite _error while rendering.
        widget = getattr(self, name + '_widget')
        widget.setRenderedValue(widget._getFormValue())
        if not IWidgetInputError.providedBy(error):
            error = WidgetInputError(name, widget.label, error)
        widget._error = error

    def _requireField(self, name, errors):
        """If widget has no input, WidgetInputError is set.

        Also adds the exception to the `errors` list.
        """
        widget = getattr(self, name + '_widget')
        field = widget.context
        try:
            if widget.getInputValue() == field.missing_value:
                self._setError(name)
                errors.append(widget._error)
        except WidgetInputError, e:
            # getInputValue might raise an exception on invalid input
            errors.append(e)

    def weekdayChecked(self, weekday):
        """Return True if the given weekday should be checked.

        The weekday of start_date is always checked, others can be selected by
        the user.

        Used to format checkboxes for weekly recurrences.
        """
        return (int(weekday) in self.weekdays_widget._getFormValue() or
                self.weekdayDisabled(weekday))

    def weekdayDisabled(self, weekday):
        """Return True if the given weekday should be disabled.

        The weekday of start_date is always disabled, all others are always
        enabled.

        Used to format checkboxes for weekly recurrences.
        """
        day = self.getStartDate()
        return bool(day and day.weekday() == int(weekday))

    def getMonthDay(self):
        """Return the day number in a month, according to start_date.

        Used by the page template to format monthly recurrence rules.
        """
        evdate = self.getStartDate()
        if evdate is None:
            return '??'
        else:
            return str(evdate.day)

    def getWeekDay(self):
        """Return the week and weekday in a month, according to start_date.

        The output looks like '4th Tuesday'

        Used by the page template to format monthly recurrence rules.
        """
        evdate = self.getStartDate()
        if evdate is None:
            return _("same weekday")

        weekday = evdate.weekday()
        index = (evdate.day + 6) // 7

        indexes = {1: _('1st'), 2: _('2nd'), 3: _('3rd'), 4: _('4th'),
                   5: _('5th')}
        day_of_week = day_of_week_names[weekday]
        return "%s %s" % (indexes[index], day_of_week)

    def getLastWeekDay(self):
        """Return the week and weekday in a month, counting from the end.

        The output looks like 'Last Friday'

        Used by the page template to format monthly recurrence rules.
        """
        evdate = self.getStartDate()

        if evdate is None:
            return _("last weekday")

        lastday = calendar.monthrange(evdate.year, evdate.month)[1]

        if lastday - evdate.day >= 7:
            return None
        else:
            weekday = evdate.weekday()
            day_of_week_msgid = day_of_week_names[weekday]
            day_of_week = translate(day_of_week_msgid, context=self.request)
            msg = _("Last ${weekday}", mapping={'weekday': day_of_week})
            return msg

    def getStartDate(self):
        """Return the value of the widget if a start_date is set."""
        try:
            return self.start_date_widget.getInputValue()
        except (WidgetInputError, ConversionError):
            return None

    def updateForm(self):
        # Just refresh the form.  It is necessary because some labels for
        # monthly recurrence rules depend on the event start date.
        self.update_status = ''
        try:
            data = getWidgetsData(self, self.schema, names=self.fieldNames)
            kw = {}
            for name in self._keyword_arguments:
                if name in data:
                    kw[str(name)] = data[name]
            self.processRequest(kw)
        except WidgetsError, errors:
            self.errors = errors
            self.update_status = _("An error occurred.")
            return self.update_status
        # AddView.update() sets self.update_status and returns it.  Weird,
        # but let's copy that behavior.
        return self.update_status

    def processRequest(self, kwargs):
        """Put information from the widgets into a dict.

        This method performs additional validation, because Zope 3 forms aren't
        powerful enough.  If any errors are encountered, a WidgetsError is
        raised.
        """
        errors = []
        self._requireField("title", errors)
        self._requireField("start_date", errors)

        # What we require depends on weather or not we have an allday event
        allday = kwargs.pop('allday', None)
        if not allday:
            self._requireField("start_time", errors)

        self._requireField("duration", errors)

        # Remove fields not needed for makeRecurrenceRule from kwargs
        title = kwargs.pop('title', None)
        start_date = kwargs.pop('start_date', None)
        start_time = kwargs.pop('start_time', None)
        if start_time:
            try:
                start_time = parse_time(start_time)
            except ValueError:
                self._setError("start_time",
                               ConversionError(_("Invalid time")))
                errors.append(self.start_time_widget._error)
        duration = kwargs.pop('duration', None)
        duration_type = kwargs.pop('duration_type', 'minutes')
        location = kwargs.pop('location', None)
        description = kwargs.pop('description', None)
        recurrence = kwargs.pop('recurrence', None)

        if recurrence:
            self._requireField("interval", errors)
            self._requireField("recurrence_type", errors)
            self._requireField("range", errors)

            range = kwargs.get('range')
            if range == "count":
                self._requireField("count", errors)
            elif range == "until":
                self._requireField("until", errors)
                if start_date and kwargs.get('until'):
                    if kwargs['until'] < start_date:
                        self._setError("until", ConstraintNotSatisfied(
                                    _("End date is earlier than start date")))
                        errors.append(self.until_widget._error)

        exceptions = kwargs.pop("exceptions", None)
        if exceptions:
            try:
                kwargs["exceptions"] = datesParser(exceptions)
            except ValueError:
                self._setError("exceptions", ConversionError(
                 _("Invalid date.  Please specify YYYY-MM-DD, one per line.")))
                errors.append(self.exceptions_widget._error)

        if errors:
            raise WidgetsError(errors)

        # Some fake data for allday events, based on what iCalendar seems to
        # expect
        if allday is True:
            # iCalendar has no spec for describing all-day events, but it seems
            # to be the de facto standard to give them a 1d duration.
            # XXX ignas: ical has allday events, they are different
            # from normal events, because they have a date as their
            # dtstart not a datetime
            duration_type = "days"
            # XXX: I do dislike that allday events happen in different
            #      timezone (UTC) than local events (view prefs).
            start_time = time(0, 0, tzinfo=utc)
            start = datetime.combine(start_date, start_time)
        else:
            start = datetime.combine(start_date, start_time)
            start = self.timezone.localize(start).astimezone(utc)

        dargs = {duration_type : duration}
        duration = timedelta(**dargs)

        # Shift the weekdays to the correct timezone
        if 'weekdays' in kwargs and kwargs['weekdays']:
            kwargs['weekdays'] = tuple(convertWeekdaysList(start,
                                                           self.timezone,
                                                           start.tzinfo,
                                                           kwargs['weekdays']))


        rrule = recurrence and makeRecurrenceRule(**kwargs) or None
        return {'location': location,
                'description': description,
                'title': title,
                'allday': allday,
                'start': start,
                'duration': duration,
                'rrule': rrule}

    @Lazy
    def resources(self):
        result = []
        if not checkPermission('schooltool.view', self.context):
            return result

        for resource in self.context.resources:
            insecure_resource = removeSecurityProxy(resource)
            if checkPermission('schooltool.view', resource):
                url = absoluteURL(insecure_resource, self.request)
            else:
                url = ''
            result.append({
                'title': insecure_resource.title,
                'type': insecure_resource.type,
                'url': url,
                })

        return result


class CalendarEventAddView(CalendarEventViewMixin, AddView):
    """A view for adding an event."""

    __used_for__ = ISchoolToolCalendar
    schema = ICalendarEventAddForm

    title = _("Add event")
    submit_button_title = _("Add")

    show_book_checkbox = True
    show_book_link = False
    _event_uid = None

    error = None

    def __init__(self, context, request):

        prefs = ViewPreferences(request)
        self.timezone = prefs.timezone

        if "field.start_date" not in request:
            # XXX shouldn't use date.today; it depends on the server's timezone
            # which may not match user expectations
            today = getUtility(IDateManager).today.strftime("%Y-%m-%d")
            request.form["field.start_date"] = today
        super(AddView, self).__init__(context, request)

    def create(self, **kwargs):
        """Create an event."""
        data = self.processRequest(kwargs)
        event = self._factory(data['start'], data['duration'], data['title'],
                              recurrence=data['rrule'],
                              location=data['location'],
                              allday=data['allday'],
                              description=data['description'])
        return event

    def add(self, event):
        """Add the event to a calendar."""
        self.context.addEvent(event)
        uid = event.unique_id
        self._event_name = event.__name__
        session_data = ISession(self.request)['schooltool.calendar']
        session_data.setdefault('added_event_uids', set()).add(uid)
        return event

    def update(self):
        """Process the form."""
        if 'UPDATE' in self.request:
            return self.updateForm()
        elif 'CANCEL' in self.request:
            self.update_status = ''
            self.request.response.redirect(self.nextURL())
            return self.update_status
        else:
            return AddView.update(self)

    def nextURL(self):
        """Return the URL to be displayed after the add operation."""
        if "field.book" in self.request:
            url = absoluteURL(self.context, self.request)
            return '%s/%s/booking.html' % (url, self._event_name)
        else:
            return absoluteURL(self.context, self.request)


class ICalendarEventEditForm(ICalendarEventAddForm):
    pass


class CalendarEventEditView(CalendarEventViewMixin, EditView):
    """A view for editing an event."""

    error = None
    show_book_checkbox = False
    show_book_link = True

    title = _("Edit event")
    submit_button_title = _("Update")

    def __init__(self, context, request):
        prefs = ViewPreferences(request)
        self.timezone = prefs.timezone
        EditView.__init__(self, context, request)

    def keyword_arguments(self):
        """Wraps fieldNames under another name.

        AddView and EditView API does not match so some wrapping is needed.
        """
        return self.fieldNames

    _keyword_arguments = property(keyword_arguments, None)

    def _setUpWidgets(self):
        setUpWidgets(self, self.schema, IInputWidget, names=self.fieldNames,
                     initial=self._getInitialData(self.context))

    def _getInitialData(self, context):
        """Extract initial widgets data from context."""

        initial = {}
        initial["title"] = context.title
        initial["allday"] = context.allday
        initial["start_date"] = context.dtstart.date()
        initial["start_time"] = context.dtstart.astimezone(self.timezone).strftime("%H:%M")
        duration = context.duration.seconds / 60 + context.duration.days * 1440
        initial["duration_type"] = (duration % 60 and "minutes" or
                                    duration % (24 * 60) and "hours" or
                                    "days")
        initial["duration"] = (initial["duration_type"] == "minutes" and duration or
                               initial["duration_type"] == "hours" and duration / 60 or
                               initial["duration_type"] == "days" and duration / 60 / 24)
        initial["location"] = context.location
        initial["description"] = context.description
        recurrence = context.recurrence
        initial["recurrence"] = recurrence is not None
        if recurrence:
            initial["interval"] = recurrence.interval
            recurrence_type = (
                IDailyRecurrenceRule.providedBy(recurrence) and "daily" or
                IWeeklyRecurrenceRule.providedBy(recurrence) and "weekly" or
                IMonthlyRecurrenceRule.providedBy(recurrence) and "monthly" or
                IYearlyRecurrenceRule.providedBy(recurrence) and "yearly")

            initial["recurrence_type"] = recurrence_type
            if recurrence.until:
                initial["until"] = recurrence.until
                initial["range"] = "until"
            elif recurrence.count:
                initial["count"] = recurrence.count
                initial["range"] = "count"
            else:
                initial["range"] = "forever"

            if recurrence.exceptions:
                exceptions = map(str, recurrence.exceptions)
                initial["exceptions"] = "\n".join(exceptions)

            if recurrence_type == "weekly":
                if recurrence.weekdays:
                    # Convert weekdays to the correct TZ
                    initial["weekdays"] = convertWeekdaysList(
                        self.context.dtstart,
                        self.context.dtstart.tzinfo,
                        self.timezone,
                        recurrence.weekdays)

            if recurrence_type == "monthly":
                if recurrence.monthly:
                    initial["monthly"] = recurrence.monthly

        return initial

    def getStartDate(self):
        if "field.start_date" in self.request:
            return CalendarEventViewMixin.getStartDate(self)
        else:
            return self.context.dtstart.astimezone(self.timezone).date()

    def applyChanges(self):
        data = getWidgetsData(self, self.schema, names=self.fieldNames)
        kw = {}
        for name in self._keyword_arguments:
            if name in data:
                kw[str(name)] = data[name]

        widget_data = self.processRequest(kw)

        parsed_date = parse_datetimetz(widget_data['start'].isoformat())
        self.context.dtstart = parsed_date
        self.context.recurrence = widget_data['rrule']
        for attrname in ['allday', 'duration', 'title',
                         'location', 'description']:
            setattr(self.context, attrname, widget_data[attrname])
        return True

    def update(self):
        if self.update_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.update_status

        status = ''

        start_date = self.context.dtstart.strftime("%Y-%m-%d")

        if "UPDATE" in self.request:
            return self.updateForm()
        elif 'CANCEL' in self.request:
            self.update_status = ''
            self.request.response.redirect(self.nextURL())
            return self.update_status
        elif "UPDATE_SUBMIT" in self.request:
            # Replicating EditView functionality
            changed = False
            try:
                changed = self.applyChanges()
                if changed:
                    notify(ObjectModifiedEvent(self.context))
            except WidgetsError, errors:
                self.errors = errors
                status = _("An error occurred.")
                transaction.abort()
            else:
                if changed:
                    formatter = self.request.locale.dates.getFormatter(
                        'dateTime', 'medium')
                    status = _("Updated on ${date_time}",
                               mapping = {'date_time': formatter.format(
                                   datetime.utcnow())})
                self.request.response.redirect(self.nextURL())

        self.update_status = status
        return status

    def nextURL(self):
        """Return the URL to be displayed after the add operation."""
        if "field.book" in self.request:
            result = absoluteURL(self.context, self.request) + '/booking.html'
        elif 'CANCEL' in self.request and self.request.get('cancel_url'):
            result = self.request.get('cancel_url')
        else:
            result = (self.request.get('back_url') or
                      absoluteURL(self.context.__parent__, self.request))
        return result.encode('utf-8')


class EventForBookingDisplay(object):
    """Event wrapper for display in booking view.

    This is a wrapper around an ICalendarEvent object.  It adds view-specific
    attributes:

        dtend -- timestamp when the event ends
        shortTitle -- title truncated to ~15 characters

    """

    def __init__(self, event):
        # The event came from resource calendar, so its parent might
        # be a calendar we don't have permission to view.
        self.context = removeSecurityProxy(event)
        self.dtstart = self.context.dtstart
        self.dtend = self.context.dtstart + self.context.duration
        self.title = self.context.title
        if len(self.title) > 16:
            # Title needs truncation.
            self.shortTitle = self.title[:15] + '...'
        else:
            self.shortTitle = self.title
        self.unique_id = self.context.unique_id


class CalendarEventBookingView(CalendarEventView):
    """A view for booking resources."""

    errors = ()
    update_status = None

    template = ViewPageTemplateFile("templates/event_booking.pt")

    def __init__(self, context, request):
        CalendarEventView.__init__(self, context, request)

        format = '%s - %s' % (self.preferences.dateformat,
                              self.preferences.timeformat)
        self.start = u'' + self.dtstart.strftime(format)
        self.end = u'' + self.dtend.strftime(format)

    def __call__(self):
        self.checkPermission()
        return self.template()

    def checkPermission(self):
        if canAccess(self.context, 'bookResource'):
            return
        # If the authenticated user has the addEvent permission and has
        # come here directly from the event adding form, let him book.
        # (Fixes issue 486.)
        if self.justAddedThisEvent():
            return
        raise Unauthorized("user not allowed to book")

    def hasBookedItems(self):
        return bool(self.context.resources)

    def bookingStatus(self, item, formatter):
        conflicts = list(self.getConflictingEvents(item))
        status = {}
        for conflict in conflicts:
            if conflict.context.__parent__ and conflict.context.__parent__.__parent__:
                absoluteURL(self.context, self.request)
                owner = conflict.context.__parent__.__parent__
                url = absoluteURL(owner, self.request)
            else:
                owner = conflict.context.activity.owner
                url = owner.absolute_url()
            owner_url = "%s/calendar" % url
            owner_name = owner.title
            status[owner_name] = owner_url
        return status

    def columns(self):

        def statusFormatter(value, item, formatter):
            url = []
            if value:
                for eventOwner, ownerCalendar in value.items():
                    url.append('<a href="%s">%s</a>' % (ownerCalendar, eventOwner))
                return ", ".join(url)
            else:
                return 'Free'
        return [GetterColumn(name='title',
                             title=_("Title"),
                             getter=lambda i, f: i.title,
                             subsort=True),
                GetterColumn(name='type',
                             title=_("Type"),
                             getter=lambda i, f: IResourceTypeInformation(i).title,
                             subsort=True),
                GetterColumn(title=_("Booked by others"),
                             cell_formatter=statusFormatter,
                             getter=self.bookingStatus
                             )]

    def getBookedItems(self):
        return removeSecurityProxy(self.context.resources)

    def updateBatch(self, lst):
        extra_url = ""
        if self.filter_widget:
            extra_url = self.filter_widget.extra_url()
        self.batch = IterableBatch(lst, self.request, sort_by='title', extra_url=extra_url)

    def renderBookedTable(self):
        prefix = "remove_item"
        columns = [CheckboxColumn(prefix=prefix, name='remove', title=u'')]
        available_columns = self.columns()
        available_columns[0].cell_formatter = label_cell_formatter_factory(prefix)
        columns.extend(available_columns)
        formatter = table.FormFullFormatter(
            self.context, self.request, self.getBookedItems(),
            columns=columns,
            sort_on=self.sortOn(),
            prefix="booked")
        formatter.cssClasses['table'] = 'data'
        return formatter()

    def renderAvailableTable(self):
        prefix = "add_item"
        columns = [CheckboxColumn(prefix=prefix, name='add', title=u'',
                                  isDisabled=self.getConflictingEvents)]
        available_columns = self.columns()
        available_columns[0].cell_formatter = label_cell_formatter_factory(prefix)
        columns.extend(available_columns)
        formatter = table.FormFullFormatter(
            self.context, self.request, self.filter(self.availableResources),
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self.sortOn(),
            prefix="available")
        formatter.cssClasses['table'] = 'data'
        return formatter()

    def sortOn(self):
        return (("title", False),)

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['resources']

    def getAvailableItems(self):
        container = self.getAvailableItemsContainer()
        bookedItems = set(self.getBookedItems())
        allItems = set(self.availableResources)
        return list(allItems - bookedItems)

    def filter(self, list):
        return self.filter_widget.filter(list)


    def justAddedThisEvent(self):
        session_data = ISession(self.request)['schooltool.calendar']
        added_event_ids = session_data.get('added_event_uids', [])
        return self.context.unique_id in added_event_ids

    def clearJustAddedStatus(self):
        """Remove the context uid from the list of added events."""
        session_data = ISession(self.request)['schooltool.calendar']
        added_event_ids = session_data.get('added_event_uids', [])
        uid = self.context.unique_id
        if uid in added_event_ids:
            added_event_ids.remove(uid)

    def update(self):
        """Book/unbook resources according to the request."""
        start_date = self.context.dtstart.strftime("%Y-%m-%d")
        self.filter_widget = queryMultiAdapter((self.getAvailableItemsContainer(),
                                                self.request),
                                                IFilterWidget)

        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())

        elif "BOOK" in self.request: # and not self.update_status:
            self.update_status = ''
            sb = ISchoolToolApplication(None)
            for res_id, resource in sb["resources"].items():
                if 'add_item.%s' % res_id in self.request:
                    booked = self.hasBooked(resource)
                    if not booked:
                        event = removeSecurityProxy(self.context)
                        event.bookResource(resource)
            self.clearJustAddedStatus()

        elif "UNBOOK" in self.request:
            self.update_status = ''
            sb = ISchoolToolApplication(None)
            for res_id, resource in sb["resources"].items():
                if 'remove_item.%s' % res_id in self.request:
                    booked = self.hasBooked(resource)
                    if booked:
                        # Always allow unbooking, even if permission to
                        # book that specific resource was revoked.
                        self.context.unbookResource(resource)
        self.updateBatch(self.filter(self.availableResources))
        return self.update_status

    @property
    def availableResources(self):
        """Gives us a list of all bookable resources."""
        sb = ISchoolToolApplication(None)
        calendar_owner = removeSecurityProxy(self.context.__parent__.__parent__)
        def isBookable(resource):
            if resource is calendar_owner:
                # A calendar event in a resource's calendar shouldn't book
                # that resource, it would be silly.
                return False
            if self.canBook(resource) and not self.hasBooked(resource):
                return True
            return False
        return filter(isBookable, sb['resources'].values())

    def canBook(self, resource):
        """Can the user book this resource?"""
        return canAccess(ISchoolToolCalendar(resource), "addEvent")

    def hasBooked(self, resource):
        """Checks whether a resource is booked by this event."""
        return resource in self.context.resources

    def nextURL(self):
        """Return the URL to be displayed after the add operation."""
        return absoluteURL(self.context.__parent__, self.request)

    def getConflictingEvents(self, resource):
        """Return a list of events that would conflict when booking a resource."""
        calendar = ISchoolToolCalendar(resource)
        if not canAccess(calendar, "expand"):
            return []

        events = list(calendar.expand(self.context.dtstart,
                                      self.context.dtstart + self.context.duration))

        return [EventForBookingDisplay(event)
                for event in events
                if event != self.context]


def makeRecurrenceRule(interval=None, until=None,
                       count=None, range=None,
                       exceptions=None, recurrence_type=None,
                       weekdays=None, monthly=None):
    """Return a recurrence rule according to the arguments."""
    if interval is None:
        interval = 1

    if range != 'until':
        until = None
    if range != 'count':
        count = None

    if exceptions is None:
        exceptions = ()

    kwargs = {'interval': interval, 'count': count,
              'until': until, 'exceptions': exceptions}

    if recurrence_type == 'daily':
        return DailyRecurrenceRule(**kwargs)
    elif recurrence_type == 'weekly':
        weekdays = weekdays or ()
        return WeeklyRecurrenceRule(weekdays=tuple(weekdays), **kwargs)
    elif recurrence_type == 'monthly':
        monthly = monthly or "monthday"
        return MonthlyRecurrenceRule(monthly=monthly, **kwargs)
    elif recurrence_type == 'yearly':
        return YearlyRecurrenceRule(**kwargs)
    else:
        raise NotImplementedError()


def convertWeekdaysList(dt, fromtz, totz, weekdays):
    """Convert the weekday list from one timezone to the other.

    The days can shift by one day in either direction or stay,
    depending on the timezones and the time of the event.

    The arguments are as follows:

       dt       -- the tz-aware start of the event
       fromtz   -- the timezone the weekdays list is in
       totz     -- the timezone the weekdays list is converted to
       weekdays -- a list of values in range(7), 0 is Monday.

    """
    delta_td = dt.astimezone(totz).date() - dt.astimezone(fromtz).date()
    delta = delta_td.days
    return [(wd + delta) % 7 for wd in weekdays]


def datesParser(raw_dates):
    r"""Parse dates on separate lines into a tuple of date objects.

    Incorrect lines are ignored.

    >>> datesParser('2004-05-17\n\n\n2004-01-29')
    (datetime.date(2004, 5, 17), datetime.date(2004, 1, 29))

    >>> datesParser('2004-05-17\n123\n\nNone\n2004-01-29')
    Traceback (most recent call last):
    ...
    ValueError: Invalid date: '123'

    """
    results = []
    for dstr in raw_dates.splitlines():
        if dstr:
            d = parse_date(dstr)
            if isinstance(d, date):
                results.append(d)
    return tuple(results)


def enableVfbView(ical_view):
    """XXX wanna docstring!"""
    return IReadFile(ical_view.context)


def enableICalendarUpload(ical_view):
    """An adapter that enables HTTP PUT for calendars.

    When the user performs an HTTP PUT request on /path/to/calendar.ics,
    Zope 3 traverses to a view named 'calendar.ics' (which is most likely
    a schooltool.calendar.browser.Calendar ICalendarView).  Then Zope 3 finds an
    IHTTPrequest view named 'PUT'.  There is a standard one, that adapts
    its context (which happens to be the view named 'calendar.ics' in this
    case) to IWriteFile, and calls `write` on it.

    So, to hook up iCalendar uploads, the simplest way is to register an
    adapter for CalendarICalendarView that provides IWriteFile.

        >>> from zope.component import provideAdapter
        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()

    We have a calendar that provides IEditCalendar.

        >>> from schooltool.app.cal import Calendar
        >>> calendar = Calendar(None)

    We have a fake "real adapter" for IEditCalendar

        >>> class RealAdapter:
        ...     implements(IWriteFile)
        ...     def __init__(self, context):
        ...         pass
        ...     def write(self, data):
        ...         print 'real adapter got %r' % data
        >>> provideAdapter(RealAdapter, (IEditCalendar,), IWriteFile)

    We have a fake view on that calendar

        >>> from zope.publisher.browser import BrowserView
        >>> from zope.publisher.browser import TestRequest
        >>> view = BrowserView(calendar, TestRequest())

    And now we can hook things up together

        >>> adapter = enableICalendarUpload(view)
        >>> adapter.write('iCalendar data')
        real adapter got 'iCalendar data'

        >>> setup.placelessTearDown()

    """
    return IWriteFile(ical_view.context)


class CalendarActionMenuViewlet(object):
    implements(ICalendarMenuViewlet)


class CalendarMenuViewletCrowd(Crowd):
    adapts(ICalendarMenuViewlet)

    def contains(self, principal):
        """Returns true if you have the permission to see the calendar."""
        crowd = queryAdapter(ISchoolToolCalendar(self.context.context),
                             ICrowd,
                             name="schooltool.view")
        return crowd.contains(principal)


class ICalendarPortletViewletManager(IViewletManager):
    """ Interface for the Calendar Portlet Viewlet Manager """
