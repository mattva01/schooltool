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
Unit tests for schooltool.timetable.schedule
"""
import doctest
import pytz
import unittest
from pprint import pprint
from datetime import date, time

from schooltool.timetable.schedule import date_timespan
from schooltool.timetable.schedule import iterMeetingsInTimezone
from schooltool.timetable.tests import ScheduleStub


def test_date_timespan():
    """Tests for date_timespan.

    Let's look a simple UTC date

       >>> date_timespan(date(2011, 10, 30), pytz.UTC)
       (datetime.datetime(2011, 10, 30, 0, 0, tzinfo=<UTC>),
        datetime.datetime(2011, 10, 30, 23, 59, 59, 999999, tzinfo=<UTC>))

    Let's look at date with daylight saving transition.

       >>> span = date_timespan(
       ...     date(2011, 10, 30), pytz.timezone('Europe/Vilnius'))

       >>> span
       (datetime.datetime(2011, 10, 30, 0, 0,
            tzinfo=<DstTzInfo 'Europe/Vilnius' EEST+3:00:00 DST>),
       datetime.datetime(2011, 10, 30, 23, 59, 59, 999999,
            tzinfo=<DstTzInfo 'Europe/Vilnius' EET+2:00:00 STD>))

       >>> print span[1] - span[0]
       1 day, 0:59:59.999999

    And another transition in spring.

       >>> span = date_timespan(
       ...     date(2011, 3, 27), pytz.timezone('Europe/Vilnius'))

       >>> span
       (datetime.datetime(2011, 3, 27, 0, 0,
             tzinfo=<DstTzInfo 'Europe/Vilnius' EET+2:00:00 STD>),
        datetime.datetime(2011, 3, 27, 23, 59, 59, 999999,
             tzinfo=<DstTzInfo 'Europe/Vilnius' EEST+3:00:00 DST>))

       >>> print span[1] - span[0]
       22:59:59.999999

    Note, this implementation does not fully cover time shifts that happen at
    midnight.  Consider 1915 in Warsaw:

       >>> span1 = date_timespan(
       ...     date(1915, 8, 4), pytz.timezone('Europe/Warsaw'))

       >>> span1
       (datetime.datetime(1915, 8, 4, 0, 0,
            tzinfo=<DstTzInfo 'Europe/Warsaw' WMT+1:24:00 STD>),
        datetime.datetime(1915, 8, 4, 23, 59, 59, 999999,
            tzinfo=<DstTzInfo 'Europe/Warsaw' WMT+1:24:00 STD>))

       >>> span2 = date_timespan(
       ...     date(1915, 8, 5), pytz.timezone('Europe/Warsaw'))

       >>> span2
       (datetime.datetime(1915, 8, 5, 0, 0,
            tzinfo=<DstTzInfo 'Europe/Warsaw' CET+1:00:00 STD>),
        datetime.datetime(1915, 8, 5, 23, 59, 59, 999999,
            tzinfo=<DstTzInfo 'Europe/Warsaw' CET+1:00:00 STD>))

    But there was a 24 minute time shift when they switched from
    Warsaw Mean Time to Central European Time:

       >>> print span1[1] - span1[0]
       23:59:59.999999

       >>> print span2[1] - span2[0]
       23:59:59.999999

       >>> print (span1[1] - span1[0]) + (span2[1] - span2[0])
       1 day, 23:59:59.999998

       >>> print span2[1] - span1[0]
       2 days, 0:23:59.999999

    """


def test_iterMeetingsInTimezone():
    """Tests for iterMeetingsInTimezone.

    Let's define a simple schedule in UTC with meetings every hour.

        >>> schedule = ScheduleStub(
        ...      timezone='UTC',
        ...      first=date(2011, 10, 28),
        ...      last=date(2011, 11, 01))

        >>> schedule.meeting_times = tuple(
        ...     [time(h, 0) for h in range(24)])

        >>> pprint(list(schedule.iterMeetings(schedule.first, schedule.last)))
        [<Meeting on 2011-10-28 00:00 UTC>,
         <Meeting on 2011-10-28 01:00 UTC>,
         <Meeting on 2011-10-28 02:00 UTC>,
         <Meeting on 2011-10-28 03:00 UTC>,
         ...
         <Meeting on 2011-11-01 22:00 UTC>,
         <Meeting on 2011-11-01 23:00 UTC>]

    Let's iterate over meetings that occur at 2011 10 29 in Vilnius:

        >>> meetings_29_vilnius = list(iterMeetingsInTimezone(
        ...    schedule, 'Europe/Vilnius', date(2011, 10, 29)))

    Note that there are 24 meetings, as expected:

        >>> len(meetings_29_vilnius)
        24

        >>> pprint(meetings_29_vilnius)
        [<Meeting on 2011-10-28 21:00 UTC>,
         <Meeting on 2011-10-28 22:00 UTC>,
         <Meeting on 2011-10-28 23:00 UTC>,
         ...
         <Meeting on 2011-10-29 18:00 UTC>,
         <Meeting on 2011-10-29 19:00 UTC>,
         <Meeting on 2011-10-29 20:00 UTC>]

    But at Oct 30 there's a daylight saving switch in Vilnius:

        >>> meetings_30_vilnius = list(iterMeetingsInTimezone(
        ...    schedule, 'Europe/Vilnius', date(2011, 10, 30)))

        >>> len(meetings_30_vilnius)
        25

        >>> pprint(meetings_30_vilnius)
        [<Meeting on 2011-10-29 21:00 UTC>,
         <Meeting on 2011-10-29 22:00 UTC>,
         <Meeting on 2011-10-29 23:00 UTC>,
         ...
         <Meeting on 2011-10-30 17:00 UTC>,
         <Meeting on 2011-10-30 18:00 UTC>,
         <Meeting on 2011-10-30 19:00 UTC>,
         <Meeting on 2011-10-30 20:00 UTC>,
         <Meeting on 2011-10-30 21:00 UTC>]

        >>> len(list(iterMeetingsInTimezone(
        ...     schedule, 'Europe/Vilnius',
        ...     date(2011, 10, 29), date(2011, 10, 30))))
        49

    Same happens with sprint dst shift.

        >>> schedule.first = date(2011, 3, 25)
        >>> schedule.last = date(2011, 3, 28)

    Winter time:

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'Europe/Vilnius',
        ...     date(2011, 3, 26))))
        [<Meeting on 2011-03-25 22:00 UTC>,
         ...
         <Meeting on 2011-03-26 21:00 UTC>]

    Observe the shift:

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'Europe/Vilnius',
        ...     date(2011, 3, 27))))
        [<Meeting on 2011-03-26 22:00 UTC>,
         ...
         <Meeting on 2011-03-27 20:00 UTC>]

        >>> len(list(iterMeetingsInTimezone(
        ...     schedule, 'Europe/Vilnius',
        ...     date(2011, 3, 27))))
        23

    Back to summer time:

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'Europe/Vilnius',
        ...     date(2011, 3, 28))))
        [<Meeting on 2011-03-27 21:00 UTC>,
         ...
         <Meeting on 2011-03-28 20:00 UTC>]

    """


def test_iterMeetingsInTimezone_localized_schedule():
    """Tests for iterMeetingsInTimezone.

    Let's define a simple schedule in Europe/Vilnius.

        >>> schedule = ScheduleStub(
        ...      timezone='Europe/Vilnius',
        ...      first=date(2011, 3, 12),
        ...      last=date(2011, 3, 28))

    We can see that dst shift occurs in this schedule:

        >>> pprint(list(schedule.iterMeetings(schedule.first, schedule.last)))
        [<Meeting on 2011-03-12 00:05 EET>,
         <Meeting on 2011-03-12 05:00 EET>,
         <Meeting on 2011-03-12 23:55 EET>,
         <Meeting on 2011-03-13 00:05 EET>,
         ...
         <Meeting on 2011-03-27 00:05 EET>,
         <Meeting on 2011-03-27 05:00 EEST>,
         <Meeting on 2011-03-27 23:55 EEST>,
         <Meeting on 2011-03-28 00:05 EEST>,
         <Meeting on 2011-03-28 05:00 EEST>,
         <Meeting on 2011-03-28 23:55 EEST>]

    Let's set up meetings every hour:

        >>> schedule.meeting_times = tuple(
        ...     [time(h, 0) for h in range(24)])

    We have 24 meetings per day:

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'UTC', date(2011, 3, 26))))
        [<Meeting on 2011-03-26 02:00 EET>,
         <Meeting on 2011-03-26 03:00 EET>,
         ...
         <Meeting on 2011-03-27 00:00 EET>,
         <Meeting on 2011-03-27 01:00 EET>]

        >>> len(list(iterMeetingsInTimezone(
        ...     schedule, 'UTC', date(2011, 3, 26))))
        24

    But because of spring dst shift, we can get an extra meeting:

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'UTC', date(2011, 3, 27))))
        [<Meeting on 2011-03-27 02:00 EET>,
         <Meeting on 2011-03-27 03:00 EET>,
         <Meeting on 2011-03-27 04:00 EEST>,
         <Meeting on 2011-03-27 05:00 EEST>,
         ...
         <Meeting on 2011-03-28 00:00 EEST>,
         <Meeting on 2011-03-28 01:00 EEST>,
         <Meeting on 2011-03-28 02:00 EEST>]

        >>> len(list(iterMeetingsInTimezone(
        ...     schedule, 'UTC', date(2011, 3, 27))))
        25

    Let's observe from US/Eastern, during it's dst shift:

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'US/Eastern', date(2011, 3, 12))))
        [<Meeting on 2011-03-12 07:00 EET>,
         ...
         <Meeting on 2011-03-13 06:00 EET>]

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'US/Eastern', date(2011, 3, 13))))
        [<Meeting on 2011-03-13 07:00 EET>,
         ...
         <Meeting on 2011-03-14 05:00 EET>]

        >>> pprint(list(iterMeetingsInTimezone(
        ...     schedule, 'US/Eastern', date(2011, 3, 14))))
        [<Meeting on 2011-03-14 06:00 EET>,
         ...
         <Meeting on 2011-03-15 05:00 EET>]

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
