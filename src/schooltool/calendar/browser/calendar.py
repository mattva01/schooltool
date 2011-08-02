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

from zope.component import adapts, queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound

import schooltool.skin.flourish.page
from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.calendar.interfaces import ICalendar
from schooltool.calendar.utils import weeknum_bounds
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


class FlourishDailyCalendarView(flourish.page.WideContainerPage,
                                DailyCalendarView):
    update = DailyCalendarView.update


class FlourishWeeklyCalendarView(flourish.page.WideContainerPage,
                                 WeeklyCalendarView):
    update = WeeklyCalendarView.update


class FlourishMonthlyCalendarView(flourish.page.WideContainerPage,
                                  MonthlyCalendarView):
    update = MonthlyCalendarView.update


class FlourishYearlyCalendarView(flourish.page.WideContainerPage,
                                 YearlyCalendarView):
    update = YearlyCalendarView.update
