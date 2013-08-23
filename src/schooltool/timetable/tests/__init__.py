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
schooltool.timetable unit test commons.
"""
import pytz
from datetime import datetime, date, time, timedelta

from schooltool.timetable.schedule import Meeting


class ScheduleStub(object):

    meeting_times = (
        time(0, 5),
        time(5, 0),
        time(23, 55),
        )

    def __init__(self,
                 timezone='UTC',
                 first=date(2011, 10, 29),
                 last=date(2011, 10, 31)):
        self.timezone = timezone
        self.first = first
        self.last = last

    def iterMeetings(self, start_date, until_date=None):
        if until_date is None:
            until_date = start_date

        tz = pytz.timezone(self.timezone)
        cursor = start_date
        while cursor <= until_date:
            if (cursor >= self.first and
                cursor <= self.last):
                for time_cursor in self.meeting_times:
                    starts = tz.localize(datetime.combine(cursor, time_cursor))
                    duration = timedelta(0, 900)
                    yield Meeting(starts, duration)
            cursor += cursor.resolution
