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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool calendar views.
"""
import base64
import datetime

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapts, queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound

import schooltool.skin.flourish.page
from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.app.browser.cal import CalendarViewBase
from schooltool.app.browser.cal import month_names
from schooltool.calendar.interfaces import ICalendar
from schooltool.calendar.utils import weeknum_bounds, prev_month, next_month
from schooltool.common.inlinept import InheritTemplate
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


class FlourishDailyCalendarView(FlourishCalendarView,
                                DailyCalendarView):
    update = DailyCalendarView.update

    @property
    def subtitle(self):
        return DailyCalendarView.title(self)


class FlourishWeeklyCalendarView(FlourishCalendarView,
                                 WeeklyCalendarView):
    update = WeeklyCalendarView.update

    @property
    def subtitle(self):
        return WeeklyCalendarView.title(self)


class FlourishMonthlyCalendarView(FlourishCalendarView,
                                  MonthlyCalendarView):
    update = MonthlyCalendarView.update

    @property
    def subtitle(self):
        return MonthlyCalendarView.title(self)


class FlourishYearlyCalendarView(FlourishCalendarView,
                                 YearlyCalendarView):
    update = YearlyCalendarView.update

    @property
    def subtitle(self):
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

    @Lazy
    def events(self):
        cursor = self.cursor
        all_events = self.view.dayEvents(cursor)
        timezone = self.view.timezone
        get_time = lambda t: t.astimezone(timezone).strftime('%H:%M')
        result = [{'event': e, 'time': get_time(e.dtstart)}
                  for e in all_events
                  if e.dtstart.date() == cursor]
        return result

    def render(self, *args, **kw):
        if not self.events:
            return ''
        return flourish.page.Refine.render(self, *args, **kw)


class CalendarTertiaryNavigation(flourish.page.Content):
    template = ViewPageTemplateFile('templates/calendar_tertiary_nav.pt')

    mode_types = (
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
        )

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
