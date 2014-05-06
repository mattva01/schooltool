#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
SchoolTool calendar views.
"""
import base64
import datetime

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapts, queryMultiAdapter
from zope.i18n import translate
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound
from zope.traversing.api import getParent

from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.app.browser.cal import month_names
from schooltool.app.browser.cal import short_day_of_week_names
from schooltool.app.browser.cal import day_of_week_names
from schooltool.calendar.interfaces import ICalendar
from schooltool.calendar.utils import weeknum_bounds, prev_month, next_month
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


class CalendarTraverser(object):
    """A smart calendar traverser that can handle dates in the URL."""

    adapts(ICalendar)
    implements(IBrowserPublisher)

    queryMultiAdapter = staticmethod(queryMultiAdapter)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def browserDefault(self, request):
        return self.context, ('daily.html', )

    def publishTraverse(self, request, name):
        view_name = self.getHTMLViewByDate(request, name)
        if not view_name:
            view_name = self.getPDFViewByDate(request, name)
        if view_name:
            return self.queryMultiAdapter((self.context, request),
                                          name=view_name)

        view = queryMultiAdapter((self.context, request), name=name)
        if view is not None:
            return view

        try:
            event_id = base64.decodestring(name).decode("utf-8")
        except:
            raise NotFound(self.context, name, request)

        try:
            return self.context.find(event_id)
        except KeyError:
            raise NotFound(self.context, event_id, request)

    def getHTMLViewByDate(self, request, name):
        """Get HTML view name from URL component."""
        return self.getViewByDate(request, name, 'html')

    def getPDFViewByDate(self, request, name):
        """Get PDF view name from URL component."""
        if not name.endswith('.pdf'):
            return None
        name = name[:-4] # strip off the .pdf
        view_name = self.getViewByDate(request, name, 'pdf')
        if view_name == 'yearly.pdf':
            return None # the yearly PDF view is not available
        else:
            return view_name

    def getViewByDate(self, request, name, suffix):
        """Get view name from URL component."""
        parts = name.split('-')

        if len(parts) == 2 and parts[1].startswith('w'): # a week was given
            try:
                year = int(parts[0])
                week = int(parts[1][1:])
            except ValueError:
                return
            request.form['date'] = self.getWeek(year, week).isoformat()
            return 'weekly.%s' % suffix

        # a year, month or day might have been given
        try:
            parts = [int(part) for part in parts]
        except ValueError:
            return
        if not parts:
            return
        parts = tuple(parts)

        if not (1900 < parts[0] < 2100):
            return

        if len(parts) == 1:
            request.form['date'] = "%d-01-01" % parts
            return 'yearly.%s' % suffix
        elif len(parts) == 2:
            request.form['date'] = "%d-%02d-01" % parts
            return 'monthly.%s' % suffix
        elif len(parts) == 3:
            request.form['date'] = "%d-%02d-%02d" % parts
            return 'daily.%s' % suffix

    def getWeek(self, year, week):
        """Get the start of a week by week number.

        The Monday of the given week is returned as a datetime.date.

            >>> traverser = CalendarTraverser(None, None)
            >>> traverser.getWeek(2002, 11)
            datetime.date(2002, 3, 11)
            >>> traverser.getWeek(2005, 1)
            datetime.date(2005, 1, 3)
            >>> traverser.getWeek(2005, 52)
            datetime.date(2005, 12, 26)

        """
        return weeknum_bounds(year, week)[0]


class FlourishCalendarView(flourish.page.WideContainerPage):
    pass


def year_week(date):
    """Return year and week for given date."""
    return date.isocalendar()[:-1]


class FlourishDailyCalendarView(FlourishCalendarView,
                                DailyCalendarView):
    update = DailyCalendarView.update
    current_title = _("Today")

    @property
    def subtitle(self):
        if self.cursor == self.today:
            return _("Today")
        if self.cursor == self.today + datetime.timedelta(days=1):
            return _("Tomorrow")
        if self.cursor == self.today - datetime.timedelta(days=1):
            return _("Yesterday")
        if (year_week(self.cursor) == year_week(self.today) and
            self.cursor > self.today):
            return day_of_week_names[self.cursor.weekday()]
        return None

    @property
    def date_title(self):
        return DailyCalendarView.title(self)


class FlourishWeeklyCalendarView(FlourishCalendarView,
                                 WeeklyCalendarView):
    update = WeeklyCalendarView.update
    current_title = _("Today")

    @property
    def subtitle(self):
        cursor_yw = year_week(self.cursor)
        if cursor_yw == year_week(self.today):
            return _("This Week")
        if cursor_yw == year_week(self.today - datetime.timedelta(weeks=1)):
            return _("Last Week")
        if cursor_yw == year_week(self.today + datetime.timedelta(weeks=1)):
            return _("Next Week")
        return None

    @property
    def date_title(self):
        return WeeklyCalendarView.title(self)

    def getCurrentWeek(self):
        result = []
        for n, day in enumerate(WeeklyCalendarView.getCurrentWeek(self)):
            day.css_class = ' '.join(filter(None,
               ['day-title', day.css_class, 'first' if n==0 else '']))
            result.append(day)
        return result


class FlourishMonthlyCalendarView(FlourishCalendarView,
                                  MonthlyCalendarView):
    update = MonthlyCalendarView.update
    current_title = _("Today")

    @property
    def subtitle(self):
        return month_names[self.cursor.month]

    @property
    def date_title(self):
        return MonthlyCalendarView.title(self)


class FlourishYearlyCalendarView(FlourishCalendarView,
                                 YearlyCalendarView):
    update = YearlyCalendarView.update
    current_title = _("Today")

    def subtitle(self):
        return unicode(self.cursor.year)

    @property
    def date_title(self):
        return YearlyCalendarView.title(self)


class CalendarJumpTo(flourish.page.Refine):

    title = _('Jump To')
    body_template = ViewPageTemplateFile('templates/calendar_jump_to.pt')

    def getJumpToYears(self):
        """Return jump targets for five years centered on the current year."""
        this_year = self.view.today.year
        return [{'selected': year == this_year,
                 'label': year,
                 'href': self.view.calURL('yearly',
                                          datetime.date(year, 1, 1))}
                for year in range(this_year - 2, this_year + 3)]

    def getJumpToMonths(self):
        """Return a list of months for the drop down in the jump portlet."""
        year = self.view.cursor.year
        return [{'label': v,
                 'href': self.view.calURL('monthly',
                                          datetime.date(year, k, 1))}
                for k, v in month_names.items()]


class CalendarMonthViewlet(flourish.page.Refine):

    body_template = ViewPageTemplateFile('templates/calendar_month_viewlet.pt')

    @property
    def cursor(self):
        return self.view.cursor

    @property
    def month_title(self):
        return month_names[self.cursor.month]

    @property
    def cal_url(self):
        return self.view.calURL('monthly', self.cursor)

    @property
    def rows(self):
        result = []
        cursor = self.cursor
        month = self.view.getMonth(cursor)
        for week in month:
            result.append(self.view.renderRow(week, cursor.month))
        return result

    def weekdays(self):
        result = []
        cursor = self.cursor
        month = self.view.getMonth(cursor)
        week = month[0]
        for day in week:
            name = short_day_of_week_names[day.date.weekday()]
            result.append(translate(name, context=self.request)[:1])
        return result


class CalendarPrevMonthViewlet(CalendarMonthViewlet):

    @Lazy
    def cursor(self):
        return prev_month(self.view.cursor)


class CalendarNextMonthViewlet(CalendarMonthViewlet):

    @Lazy
    def cursor(self):
        return next_month(self.view.cursor)


class CalendarTomorrowEvents(flourish.page.Refine):

    body_template = ViewPageTemplateFile('templates/calendar_tomorrow_events.pt')

    title = _("Tomorrow's Events")

    @property
    def cursor(self):
        today = self.view.today
        tomorrow = today + today.resolution
        return tomorrow

    def get_start_time(self, event, timezone):
        if event.allday:
            # We could make it clearer that this is an all day event
            return ""
        else:
            return event.dtstart.astimezone(timezone).strftime('%H:%M')

    @Lazy
    def events(self):
        cursor = self.cursor
        all_events = self.view.dayEvents(cursor)
        timezone = self.view.timezone
        result = [{'event': e, 'time': self.get_start_time(e, timezone)}
                  for e in all_events
                  if e.dtstart.date() == cursor]
        return result

    def render(self, *args, **kw):
        if not self.events:
            return ''
        return flourish.page.Refine.render(self, *args, **kw)


class CalendarTertiaryNavigation(flourish.page.Content,
                                 flourish.page.TertiaryNavigationManager):
    template = ViewPageTemplateFile('templates/calendar_tertiary_nav.pt')

    mode_types = (
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
        )

    @property
    def nav_today_class(self):
        is_today = self.view.inCurrentPeriod(self.view.today)
        cls = 'calendar-nav'
        if is_today:
            cls += ' active'
        return cls

    @property
    def modes(self):
        result = []
        for mode, title in self.mode_types:
            cls = "calendar-type"
            if mode == self.view.cal_type:
                cls += " active"
            result.append({
                    'title': title,
                    'url': self.view.calURL(mode),
                    'class': cls,
                    })
        return result


class CalendarAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for adding links in calendar views."""


class AddEventLink(flourish.page.LinkViewlet):
    @property
    def url(self):
        return "add.html?field.start_date=%s" % self.view.cursor.isoformat()


def getParentTitleContent(context, request, view):
    parent = getParent(context)
    if parent is None:
        return None
    providers = queryMultiAdapter(
        (parent, request, view),
        flourish.interfaces.IContentProviders)
    if providers is None:
        return None
    content = providers.get("title")
    return content
