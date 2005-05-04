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
SchoolTool timetabling views.

$Id$
"""

import datetime
import itertools

from zope.interface import Interface
from zope.schema import TextLine, Date
from zope.app.publisher.browser import BrowserView
from zope.app.form.browser.add import AddView
from zope.app.form.utility import getWidgetsData
from zope.app.form.interfaces import WidgetsError

from schoolbell.app.browser.app import ContainerView
from schoolbell.calendar.utils import next_month, week_start
from schoolbell.app.browser.cal import month_names, short_day_of_week_names
from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ITermService
from schooltool.timetable import TermCalendar


class TermServiceView(ContainerView):
    """Term service view."""

    __used_for__ = ITermService

    index_title = _("Terms")
    add_title = _("Add a new term")
    add_url = "new.html"


class ITermAddForm(Interface):

    title = TextLine(
        title=_("Title"))

    start_date = Date(
        title=_("Start date"))

    end_date = Date(
        title=_("End date"))


class TermAddView(AddView):
    """Adding view for terms."""

    __used_for__ = ITermService

    title = _("New term")
    schema = ITermAddForm

    def _buildTerm(self):
        """Build a TermCalendar object from form values.

        Returns None if the form doesn't contain enough information.
        """
        try:
            data = getWidgetsData(self, self.schema,
                                names=['start_date', 'end_date'])
        except WidgetsError:
            return None
        try:
            term = TermCalendar(data['start_date'], data['end_date'])
        except ValueError:
            return None # date range invalid
        # TODO: extract schooldays/holidays from request
        return term

    def calendar(self):
        """Prepare the calendar for display.

        Returns None if the form doesn't contain enough information.  Otherwise
        returns a list of month dicts (see `month`).
        """
        term = self._buildTerm()
        if not term:
            return None
        calendar = []
        date = term.first
        counter = itertools.count(1)
        while date <= term.last:
            start_of_next_month = next_month(date)
            end_of_this_month = start_of_next_month - datetime.date.resolution
            maxdate = min(term.last, end_of_this_month)
            calendar.append(self.month(date, maxdate, counter))
            date = start_of_next_month
        return calendar

    def month(mindate, maxdate, counter):
        """Prepare one month for display.

        Returns a dict with these keys:

            title   -- month title ("January 2005")
            weeks   -- a list of week dicts in this month (see `week`)

        """
        first_day_of_week = 0 # Monday  TODO: get from IPersonPreferences
        assert (mindate.year, mindate.month) == (maxdate.year, maxdate.month)
        month_title = _('%(month)s %(year)s') % {
                          'month': month_names[mindate.month],
                          'year': mindate.year}
        weeks = []
        date = week_start(mindate, first_day_of_week)
        while date <= maxdate:
            weeks.append(TermAddView.week(date, mindate, maxdate, counter))
            date += datetime.timedelta(days=7)
        return {'title': month_title,
                'weeks': weeks}

    month = staticmethod(month)

    def week(start_of_week, mindate, maxdate, counter):
        """Prepare one week for display.

        Returns a dict with these keys:

            title   -- week title ("Week 42")
            days    -- a list of exactly seven dicts

        Each day dict has the following keys

            date    -- date as a string (YYYY-MM-DD)
            number  -- day of month
                       (None when date is outside [mindate, maxdate])

        """
        # start_of_week will be a Sunday or a Monday.  If it is a Sunday,
        # we want to take the ISO week number of the following Monday.  If
        # it is a Monday, we won't break anything by taking the week number
        # of the following Tuesday.
        week_no = (start_of_week + datetime.date.resolution).isocalendar()[1]
        week_title = _('Week %d') % week_no
        date = start_of_week
        days = []
        for day in range(7):
            if mindate <= date <= maxdate:
                index = counter.next()
                # TODO: extract checked from self.term
                checked = False
                css_class = checked and 'holiday' or 'schoolday'
                days.append({'number': date.day, 'class': css_class,
                             'date': date.strftime('%Y-%m-%d'),
                             'index': index, 'checked': checked,
                             'onclick': 'javascript:toggle(%d)' % index})
            else:
                days.append({'number': None, 'class': None, 'index': None,
                             'onclick': None, 'checked': None, 'date': None})
            date += datetime.date.resolution
        return {'title': week_title,
                'days': days}

    week = staticmethod(week)

