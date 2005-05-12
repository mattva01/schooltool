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
SchoolTool application views.

$Id$
"""

from datetime import datetime, time, timedelta

from schoolbell.app.browser.cal import DailyCalendarView as SBDailyCalView
from schoolbell.app.interfaces import ISchoolBellCalendar
from schooltool.timetable import getPeriodsForDay


class DailyCalendarView(SBDailyCalView):
    """Daily calendar view for SchoolTool.

    This view differs from the original view in SchoolBell in that it can
    also show day periods instead of hour numbers.
    """

    __used_for__ = ISchoolBellCalendar

    def calendarRows(self):
        """Iterates over (title, start, duration) of time slots that make up
        the daily calendar.
        """
# TODO: show periods only if set in preferences
#        if self.request.getCookie('cal_periods') != 'no':
        periods = getPeriodsForDay(self.cursor)
#        else:
#            periods = []
        today = datetime.combine(self.cursor, time())
        row_ends = [today + timedelta(hours=hour + 1)
                    for hour in range(self.starthour, self.endhour)]

        # Put starts and ends of periods into row_ends
        for period in periods:
            pstart = datetime.combine(self.cursor, period.tstart)
            pend = pstart + period.duration
            for point in row_ends:
                if pstart < point < pend:
                    row_ends.remove(point)
                if pstart not in row_ends:
                    row_ends.append(pstart)
                if pend not in row_ends:
                    row_ends.append(pend)

        if periods:
            row_ends.sort()

        def periodIsStarting(dt):
            if not periods:
                return False
            pstart = datetime.combine(self.cursor, periods[0].tstart)
            if pstart == dt:
                return True

        start = today + timedelta(hours=self.starthour)
        for end in row_ends:
            if periodIsStarting(start):
                period = periods.pop(0)
                pstart = datetime.combine(self.cursor, period.tstart)
                pend = pstart + period.duration
                yield (period.title, start, period.duration)
            else:
                duration =  end - start
                yield ('%d:%02d' % (start.hour, start.minute), start, duration)
            start = end
