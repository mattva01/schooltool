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
Lyceum specific calendar views.

$Id$
"""
from schooltool.app.browser.cal import DailyCalendarRowsView
from schooltool.timetable.interfaces import ITimetableCalendarEvent


class LyceumDailyCalendarRowsView(DailyCalendarRowsView):

    def _addPeriodsToRows(self, rows, periods, events):
        """Add periods to rows and shift them a bit according to the events.

        If the time of the timetable event is different from the
        period that we got from the school timetable, the period is
        shifted to match the event.
        """
        tz = self.getPersonTimezone()

        if not periods:
            return rows

        for n, period in enumerate(periods):
            for event in events:
                if ITimetableCalendarEvent.providedBy(event.context):
                    if period[0] == event.context.period_id:
                        periods[n] = (period[0], event.context.dtstart, event.context.duration)

        fpid, fp_start, fp_duration = periods[0]
        lpid, lp_start, lp_duration = periods[-1]
        lp_end = (lp_start + lp_duration).astimezone(tz)

        for point in rows[:]:
            if fp_start < point < lp_end:
                rows.remove(point)

        # Put starts and ends of periods into rows
        for period in periods:
            period_id, pstart, duration = period
            pend = (pstart + duration).astimezone(tz)
            if pstart not in rows:
                rows.append(pstart)
            if pend not in rows:
                rows.append(pend)
        rows.sort()
        return rows
