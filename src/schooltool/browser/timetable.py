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
from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.app.form.browser.add import AddView
from zope.app.form.utility import getWidgetsData
from zope.app.form.interfaces import WidgetsError
from zope.app.container.interfaces import INameChooser

from schoolbell.calendar.utils import parse_date
from schoolbell.calendar.utils import next_month, week_start
from schoolbell.app.browser.app import ContainerView
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

    # Since this view is registered via <browser:page>, and not via
    # <browser:addform>, we need to set up some attributes for AddView.
    schema = ITermAddForm
    _arguments = ()
    _keyword_arguments = ()
    _set_before_add = ()
    _set_after_add = ()

    def update(self):
        """Process the form."""
        self.term = self._buildTerm()
        return AddView.update(self)

    def create(self):
        """Create the object to be added.

        We already have it, actually -- unless there was an error in the form.
        """
        if self.term is None:
            raise WidgetsError([])
        return self.term

    def add(self, content):
        """Add the object to the term service."""
        chooser = INameChooser(self.context)
        name = chooser.chooseName(None, content)
        self.context[name] = content

    def nextURL(self):
        """Return the location to visit once the term's been added."""
        return zapi.absoluteURL(self.context, self.request)

    def _buildTerm(self):
        """Build a TermCalendar object from form values.

        Returns None if the form doesn't contain enough information.
        """
        try:
            data = getWidgetsData(self, self.schema,
                                  names=['title', 'start_date', 'end_date'])
        except WidgetsError:
            return None
        try:
            term = TermCalendar(data['title'], data['start_date'],
                                data['end_date'])
        except ValueError:
            return None # date range invalid
        term.addWeekdays(0, 1, 2, 3, 4, 5, 6)
        holidays = self.request.form.get('holiday', [])
        if not isinstance(holidays, list):
            holidays = [holidays]
        for holiday in holidays:
            try:
                term.remove(parse_date(holiday))
            except ValueError:
                pass # ignore ill-formed or out-of-range dates
        toggle = [n for n in range(7) if ('TOGGLE_%d' % n) in self.request]
        if toggle:
            term.toggleWeekdays(*toggle)
        return term

    def calendar(self):
        """Prepare the calendar for display.

        Returns None if the form doesn't contain enough information.  Otherwise
        returns a list of month dicts (see `month`).
        """
        term = self.term
        if not term:
            return None
        calendar = []
        date = term.first
        counter = itertools.count(1)
        while date <= term.last:
            start_of_next_month = next_month(date)
            end_of_this_month = start_of_next_month - datetime.date.resolution
            maxdate = min(term.last, end_of_this_month)
            calendar.append(self.month(date, maxdate, counter, self.term))
            date = start_of_next_month
        return calendar

    def month(mindate, maxdate, counter, term):
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
        week = TermAddView.week
        date = week_start(mindate, first_day_of_week)
        while date <= maxdate:
            weeks.append(week(date, mindate, maxdate, counter, term))
            date += datetime.timedelta(days=7)
        return {'title': month_title,
                'weeks': weeks}

    month = staticmethod(month)

    def week(start_of_week, mindate, maxdate, counter, term):
        """Prepare one week for display.

        `start_of_week` is the date when the week starts.

        `mindate` and `maxdate` are used to indicate which month (or part of
        the month) interests us -- days in this week that fall outside
        [mindate, maxdate] result in a dict containing None values for all
        keys.

        `counter` is an iterator that returns indexes for days
        (itertools.count(1) is handy for this purpose).

        `term` is an ITermCalendar that indicates which days are schooldays,
        and which are holidays.

        Returns a dict with these keys:

            title   -- week title ("Week 42")
            days    -- a list of exactly seven dicts

        Each day dict has the following keys

            date    -- date as a string (YYYY-MM-DD)
            number  -- day of month
                       (None when date is outside [mindate, maxdate])
            index   -- serial number of this day (used in Javascript)
            class   -- CSS class ('holiday' or 'schoolday')
            checked -- True for holidays, False for schooldays
            onclick -- onclick event handler that calls toggle(index)

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
                checked = not term.isSchoolday(date)
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

