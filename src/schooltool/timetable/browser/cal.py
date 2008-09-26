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
Timetable specific calendar views.

$Id$
"""
from datetime import datetime, time, timedelta
from pytz import timezone

from zope.viewlet.interfaces import IViewlet
from zope.interface import implements
from zope.cachedescriptors.property import CachedProperty

from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.interfaces import IPerson
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.browser.cal import DailyCalendarRowsView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.term.term import getTermForDate


class TimetablingYearlyCalendarView(YearlyCalendarView):
    """Yearly calendar view that displays term information."""

    def __init__(self, context, request):
        super(YearlyCalendarView, self).__init__(context,request)
        self.numterms = 1
        self.calendar = None

    @CachedProperty
    def legend(self):
        numterms = 1
        legend = {}
        for quarter in self.getYear(self.cursor):
            for month in quarter:
                for week in month:
                    for day in week:
                        term = getTermForDate(day.date)
                        if term and not term in legend:
                            legend[term] = self.numterms
                            numterms += 1
        return legend

    def renderRow(self, week, month):
        result = []

        for day in week:
            term = getTermForDate(day.date)
            cssClass = "term%d" % self.legend.get(term, 0)

            result.append('<td class="cal_yearly_day">')
            if day.date.month == month:
                if day.today():
                    cssClass += ' today'
                # Let us hope that URLs will not contain < > & or "
                # This is somewhat related to
                #   http://issues.schooltool.org/issue96
                result.append('<a href="%s" class="%s">%s</a>' %
                              (self.calURL('daily', day.date), cssClass,
                               day.date.day))
            result.append('</td>')

        return "\n".join(result)


class TermLegendViewlet(object):
    implements(IViewlet)

    def legend(self):
        terms = self.__parent__.legend.items()
        terms.sort(key=lambda t: t[0].first)
        return [{'title': term.title,
                 'cssclass': "legend-item term%s" % cssClass}
                for term, cssClass in terms]


class DailyTimetableCalendarRowsView(DailyCalendarRowsView):
    """Daily calendar rows view for SchoolTool.

    This view differs from the original view in SchoolBell in that it can
    also show day periods instead of hour numbers.
    """

    __used_for__ = ISchoolToolCalendar

    def getPeriodsForDay(self, date):
        """Return a list of timetable periods defined for `date`.

        This function uses the default timetable schema and the appropriate time
        period for `date`.

        Retuns a list of (id, dtstart, duration) tuples.  The times
        are timezone-aware and in the timezone of the timetable.

        Returns an empty list if there are no periods defined for `date` (e.g.
        if there is no default timetable schema, or `date` falls outside all
        time periods, or it happens to be a holiday).
        """
        schooldays = getTermForDate(date)
        ttcontainer = ITimetableSchemaContainer(ISchoolToolApplication(None), None)
        if ttcontainer is None:
            return []
        if ttcontainer.default_id is None or schooldays is None:
            return []
        ttschema = ttcontainer.getDefault()
        tttz = timezone(ttschema.timezone)
        displaytz = self.getPersonTimezone()

        # Find out the days in the timetable that our display date overlaps
        daystart = displaytz.localize(datetime.combine(date, time(0)))
        dayend = daystart + date.resolution
        day1 = daystart.astimezone(tttz).date()
        day2 = dayend.astimezone(tttz).date()

        def resolvePeriods(date):
            term = getTermForDate(date)
            if not term:
                return []

            periods = ttschema.model.periodsInDay(term, ttschema, date)
            result = []
            for id, tstart, duration in  periods:
                dtstart = datetime.combine(date, tstart)
                dtstart = tttz.localize(dtstart)
                result.append((id, dtstart, duration))
            return result

        periods = resolvePeriods(day1)
        if day2 != day1:
            periods += resolvePeriods(day2)

        result = []

        # Filter out periods outside date boundaries and chop off the
        # ones overlapping them.
        for id, dtstart, duration in periods:
            if (dtstart + duration <= daystart) or (dayend <= dtstart):
                continue
            if dtstart < daystart:
                duration -= daystart - dtstart
                dtstart = daystart.astimezone(tttz)
            if dayend < dtstart + duration:
                duration = dayend - dtstart
            result.append((id, dtstart, duration))

        return result

    def getPeriods(self, cursor):
        """Return the date we get from getPeriodsForDay.

        Checks user preferences, returns an empty list if no user is
        logged in.
        """
        person = IPerson(self.request.principal, None)
        if (person is not None and
            IPersonPreferences(person).cal_periods):
            return self.getPeriodsForDay(cursor)
        else:
            return []

    def _addPeriodsToRows(self, rows, periods, events):
        """Populate the row list with rows from periods."""
        tz = self.getPersonTimezone()

        # Put starts and ends of periods into rows
        for period in periods:
            period_id, pstart, duration = period
            pend = (pstart + duration).astimezone(tz)
            for point in rows[:]:
                if pstart < point < pend:
                    rows.remove(point)
            if pstart not in rows:
                rows.append(pstart)
            if pend not in rows:
                rows.append(pend)
        rows.sort()
        return rows

    def calendarRows(self, cursor, starthour, endhour, events):
        """Iterate over (title, start, duration) of time slots that make up
        the daily calendar.

        Returns a generator.
        """
        tz = self.getPersonTimezone()
        periods = self.getPeriods(cursor)

        daystart = tz.localize(datetime.combine(cursor, time()))
        rows = [daystart + timedelta(hours=hour)
                for hour in range(starthour, endhour+1)]

        if periods:
            rows = self._addPeriodsToRows(rows, periods, events)

        calendarRows = []

        start, row_ends = rows[0], rows[1:]
        start = start.astimezone(tz)
        for end in row_ends:
            if periods and periods[0][1] == start:
                period = periods.pop(0)
                calendarRows.append((period[0], start, period[2]))
            else:
                duration = end - start
                calendarRows.append(('%d:%02d' % (start.hour, start.minute),
                                     start, duration))
            start = end
        return calendarRows
