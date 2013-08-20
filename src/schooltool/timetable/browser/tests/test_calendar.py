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
Unit tests for schooltool.timetable.browser.calendar
"""
import doctest
import pytz
import unittest
from pprint import pprint
import  datetime

from schooltool.common import parse_time_range, format_time_range
from schooltool.timetable.browser.calendar import ScheduleDailyCalendarRowsView
from schooltool.timetable.schedule import iterMeetingsInTimezone


class MeetingStub(object):

    def __init__(self,
                 time="00:00-00:15",
                 year=2011, month=10, day=30,
                 timezone="UTC"):
        timezone = pytz.timezone(timezone)
        timestart, duration = parse_time_range(time)
        self.dtstart = timezone.localize(datetime.datetime(
            year, month, day,
            timestart.hour, timestart.minute))
        self.duration = duration


class ScheduleStub(object):
    timezone = "UTC"

    def __init__(self, meetings=None):
        if meetings:
            self.timezone = meetings[0].dtstart.tzinfo.zone
        self.meetings = meetings and list(meetings) or []

    def iterMeetings(self, start_date, until_date=None):
        if until_date is None:
            until_date = start_date
        for m in self.meetings:
            d = m.dtstart.date()
            if d >= start_date and d <= until_date:
                yield m


def test_ScheduleDailyCalendarRowsView_calendarRows():
    """Tests for ImmutableScheduleCalendar_calendarRows.

        >>> view = ScheduleDailyCalendarRowsView('context', 'request')

        >>> view._schedule = ScheduleStub([
        ...    MeetingStub("10:00-10:15"), MeetingStub("10:20-10:45"),
        ...    MeetingStub("10:55-12:30"), MeetingStub("14:00-14:55"),
        ...    ])

        >>> def getDefaultMeetings(d, tz):
        ...     return list(iterMeetingsInTimezone(view._schedule, tz, d))

        >>> view.getDefaultMeetings = getDefaultMeetings
        >>> view._timezone = 'UTC'
        >>> view.getPersonTimezone = lambda *a: pytz.timezone(view._timezone)
        >>> view.meetingTitle = lambda *a: 'meeting'
        >>> view.rowTitle = lambda *a: 'row'

        >>> def printRows(rows):
        ...     for r in rows:
        ...         dts = r[1].astimezone(pytz.timezone(view._timezone))
        ...         print '%-7s %s' % (r[0], format_time_range(dts.time(), r[2]))

    calendarRows generates rows for every hour in given range + 1 hour,
    inserting scheduled meetings where appropriate.

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             8, 17, 'dummy'))
        row     08:00-09:00
        row     09:00-10:00
        meeting 10:00-10:15
        row     10:15-10:20
        meeting 10:20-10:45
        row     10:45-10:55
        meeting 10:55-12:30
        row     12:30-13:00
        row     13:00-14:00
        meeting 14:00-14:55
        row     14:55-16:00
        row     16:00-17:00
        row     17:00-18:00

    It works properly when displayed in timezones other than source meetings.

        >>> view._timezone = 'Europe/Vilnius'

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             11, 17, 'dummy'))
        row     11:00-12:00
        meeting 12:00-12:15
        row     12:15-12:20
        meeting 12:20-12:45
        row     12:45-12:55
        meeting 12:55-14:30
        row     14:30-15:00
        row     15:00-16:00
        meeting 16:00-16:55
        row     16:55-18:00

    If we ask to display a time range, but there are earlier or later meetings,
    date range is streched to accomodate them.

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             13, 14, 'dummy'))
        meeting 12:00-12:15
        row     12:15-12:20
        meeting 12:20-12:45
        row     12:45-12:55
        meeting 12:55-14:30
        row     14:30-15:00
        row     15:00-16:00
        meeting 16:00-16:55

    If there are meetings during DST change, this will be reflected in
    calendar rows.  When clocks are adjusted backwards, the doubled hour
    is properly displayed as separate entries.

        >>> view._schedule = ScheduleStub([
        ...    MeetingStub("23:00-23:15", day=29),
        ...    MeetingStub("00:00-00:15"), MeetingStub("01:00-01:15"),
        ...    ])

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             1, 4, 'dummy'))
        row     01:00-02:00
        meeting 02:00-02:15
        row     02:15-03:00
        meeting 03:00-03:15
        row     03:15-04:00
        meeting 03:00-03:15
        row     03:15-04:00
        row     04:00-05:00

    Let's look at DST shift in a day without meetings:

        >>> view._schedule = ScheduleStub([])

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             2, 4, 'dummy'))
        row     02:00-03:00
        row     03:00-04:00
        row     03:00-04:00
        row     04:00-05:00

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             3, 5, 'dummy'))
        row     03:00-04:00
        row     04:00-05:00
        row     05:00-06:00

    Rows are limited to a given date in viewed timezone.

        >>> view._timezone = 'UTC'
        >>> view._schedule = ScheduleStub([
        ...    MeetingStub("23:00-00:00", day=29),
        ...    MeetingStub("23:00-23:30", day=30),
        ...    MeetingStub("23:30-00:00", day=30),
        ...    MeetingStub("00:00-01:00", day=31),
        ...    ])

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             22, 22, 'dummy'))
        row     22:00-23:00
        meeting 23:00-23:30
        meeting 23:30-00:00

    Views may pass 24 as the end hour.

        >>> printRows(view.calendarRows(datetime.date(2011, 10, 30),
        ...                             22, 24, 'dummy'))
        row     22:00-23:00
        meeting 23:00-23:30
        meeting 23:30-00:00

    """


def setUp(test=None):
    pass


def tearDown(test=None):
    pass


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE)
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown),
           ])
