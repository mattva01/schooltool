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
Unit tests for schooltool.timetable.timetable
"""
import doctest
import pytz
import unittest
from pprint import pprint
from datetime import date, time, datetime, timedelta

import zope.event
from zope.app.testing import setup
from zope.intid.interfaces import IIntIds
from zope.component import provideUtility
from zope.container.contained import containedEvent

from schooltool.common import DateRange
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import DayTemplateSchedule
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Meeting
from schooltool.timetable.schedule import Period
from schooltool.timetable.tests import ScheduleStub
from schooltool.timetable.timetable import Timetable

from schooltool.timetable.schedule import iterMeetingsInTimezone


class OneTemplateSchedule(DayTemplateSchedule):

    def initTemplates(self):
        super(OneTemplateSchedule, self).initTemplates()
        self.templates['default'] = DayTemplate('Day 1')

    @property
    def default(self):
        return self.templates['default']

    def iterDates(self, dates):
        schedule = self.__parent__
        scheduled_dates = DateRange(schedule.first, schedule.last)
        for cursor in dates:
            if cursor not in scheduled_dates:
                yield None
            else:
                yield self.default


class TimetableForTests(Timetable):

    def setUp(self, periods=(), time_slots=()):
        self.periods, event = containedEvent(
            OneTemplateSchedule(), self, 'periods')
        zope.event.notify(event)
        self.periods.initTemplates()
        self.time_slots, event = containedEvent(
            OneTemplateSchedule(), self, 'time_slots')
        zope.event.notify(event)
        self.time_slots.initTemplates()
        for n, title in enumerate(periods):
            self.periods.default['%d' % (n+1)] = Period(title=title)
        for n, tstart in enumerate(time_slots):
            duration = timedelta(0, 900)
            self.time_slots.default['%d' % (n+1)] = TimeSlot(tstart, duration)


def print_utc_times(meetings):
    for meeting in meetings:
        start_time_s = meeting.dtstart.strftime('%Y-%m-%d %H:%M %Z')
        utc_time = meeting.dtstart.astimezone(pytz.UTC)
        utc_time_s = utc_time.strftime('%Y-%m-%d %H:%M %Z')
        print start_time_s, '->', utc_time_s


def test_Timetable_timezones():
    """Tests for Timetable.

    Let's start with a timetable with a meeting every hour every day.

        >>> tt = TimetableForTests(
        ...     date(2011, 10, 28), date(2011, 11, 01), timezone='UTC')
        >>> periods = [chr(ord('A')+x) for x in range(24)]
        >>> time_slots = [time(x, 00) for x in range(24)]
        >>> tt.setUp(
        ...    periods=periods,
        ...    time_slots=time_slots)

        >>> pprint(list(tt.iterMeetings(tt.first, tt.last)))
        [<Meeting A on 2011-10-28 00:00 UTC>,
         <Meeting B on 2011-10-28 01:00 UTC>,
         <Meeting C on 2011-10-28 02:00 UTC>,
         ...
         <Meeting W on 2011-10-28 22:00 UTC>,
         <Meeting X on 2011-10-28 23:00 UTC>,
         <Meeting A on 2011-10-29 00:00 UTC>,
         ...
         <Meeting X on 2011-11-01 23:00 UTC>]

        >>> len(list(tt.iterMeetings(tt.first)))
        24

        >>> len(list(tt.iterMeetings(tt.first, tt.last)))
        120

     If the timetable is in a timezone and dst shift occurs, we can
     observe it:

        >>> tt.timezone = 'Europe/Vilnius'
        >>> pprint(list(tt.iterMeetings(tt.first, tt.last)))
        [<Meeting A on 2011-10-28 00:00 EEST>,
         ...
         <Meeting A on 2011-10-30 00:00 EEST>,
         <Meeting B on 2011-10-30 01:00 EEST>,
         <Meeting C on 2011-10-30 02:00 EEST>,
         <Meeting D on 2011-10-30 03:00 EET>,
         <Meeting E on 2011-10-30 04:00 EET>,
         <Meeting F on 2011-10-30 05:00 EET>,
         ...
         <Meeting X on 2011-11-01 23:00 EET>]

        >>> len(list(tt.iterMeetings(tt.first, tt.last)))
        120

        >>> print_utc_times(tt.iterMeetings(tt.first, tt.last))
        2011-10-28 00:00 EEST -> 2011-10-27 21:00 UTC
        2011-10-28 01:00 EEST -> 2011-10-27 22:00 UTC
        ...
        2011-10-30 02:00 EEST -> 2011-10-29 23:00 UTC
        2011-10-30 03:00 EET -> 2011-10-30 01:00 UTC
        ...
        2011-11-01 23:00 EET -> 2011-11-01 21:00 UTC

    We can look at the timetable from another timezone.  Note that
    we get 3 less meetings for the two dates, because first date
    2011-10-28 in UTC starts 3 hours later than in Vilnius.

        >>> pprint(list(iterMeetingsInTimezone(
        ...     tt, 'UTC', tt.first, date(2011, 10, 30))))
        [<Meeting D on 2011-10-28 03:00 EEST>,
         <Meeting E on 2011-10-28 04:00 EEST>,
         ...
         <Meeting B on 2011-10-30 01:00 EEST>,
         <Meeting C on 2011-10-30 02:00 EEST>,
         <Meeting D on 2011-10-30 03:00 EET>,
         <Meeting E on 2011-10-30 04:00 EET>,
         ...
         <Meeting X on 2011-10-30 23:00 EET>,
         <Meeting A on 2011-10-31 00:00 EET>,
         <Meeting B on 2011-10-31 01:00 EET>]

    Timetable exception dates are defined in timetable's timezone:

        >>> exception_starts = pytz.timezone(tt.timezone).localize(
        ...     datetime(2011, 10, 29, 11, 15))
        >>> ex_meeting = Meeting(exception_starts, timedelta(0, 900))
        >>> tt.exceptions[date(2011, 10, 29)] = [ex_meeting]

        >>> pprint(list(iterMeetingsInTimezone(
        ...     tt, 'UTC', tt.first, tt.last)))
        [<Meeting D on 2011-10-28 03:00 EEST>,
         <Meeting E on 2011-10-28 04:00 EEST>,
         ...
         <Meeting W on 2011-10-28 22:00 EEST>,
         <Meeting X on 2011-10-28 23:00 EEST>,
         <Meeting on 2011-10-29 11:15 EEST>,
         <Meeting A on 2011-10-30 00:00 EEST>,
         <Meeting B on 2011-10-30 01:00 EEST>,
         ...
         <Meeting X on 2011-11-01 23:00 EET>]

    """


def test_Timetable_duplicate_time_slot():
    """Tests for Timetable that falls into duplicate hour when
    clocks are adjusted forward in a timezone.

    Let's start with a timetable with a meeting every hour every day.

        >>> tt = TimetableForTests(
        ...     date(2011, 3, 26), date(2011, 3, 28),
        ...     timezone='Europe/Vilnius')
        >>> periods = [chr(ord('A')+x) for x in range(24)]
        >>> time_slots = [time(x, 00) for x in range(24)]
        >>> tt.setUp(
        ...    periods=periods,
        ...    time_slots=time_slots)

    Time period 03:00-04:00 does not exist in given timezone in 2011-03-27
    as a result of clocks adjusted forward.  SchoolTool timetables schedule
    the 03:xx and 04:xx entries at the same (adjusted) hour, so as not to
    lose planned events.

        >>> print_utc_times(tt.iterMeetings(tt.first, tt.last))
        2011-03-26 00:00 EET -> 2011-03-25 22:00 UTC
        ...
        2011-03-27 02:00 EET -> 2011-03-27 00:00 UTC
        2011-03-27 03:00 EET -> 2011-03-27 01:00 UTC
        2011-03-27 04:00 EEST -> 2011-03-27 01:00 UTC
        2011-03-27 05:00 EEST -> 2011-03-27 02:00 UTC
        ...

    """


def setUp(test=None):
    setup.placelessSetUp()
    provideUtility(object(), IIntIds)


def tearDown(test=None):
    setup.placelessTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE)
    return unittest.TestSuite([
            doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown),
           ])
