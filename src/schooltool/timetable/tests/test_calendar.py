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
from datetime import datetime, date, time, timedelta

from zope.app.testing import setup
from zope.intid.interfaces import IIntIds
from zope.component import provideUtility, provideAdapter
from test_schedule import ScheduleStub

from schooltool.timetable.calendar import ImmutableScheduleCalendar
from schooltool.timetable.interfaces import IHaveSchedule


class ImmutableScheduleCalendarForTest(ImmutableScheduleCalendar):

    def makeGUID(self, date, period, int_ids=None):
        return u'%s.%s' % (
            date.isoformat(),
            period and period.title or '?',
            )


def print_events(cal):
    for event in cal:
        print event.title, 'on', event.dtstart.strftime('%Y-%m-%d %H:%M %Z')


def test_ImmutableScheduleCalendar():
    """Tests for ImmutableScheduleCalendar.

    Let's take a simple schedule that spans a dst shift in some timezone.

        >>> schedule = ScheduleStub(timezone='Europe/Vilnius')

        >>> pprint(list(schedule.iterMeetings(schedule.first, schedule.last)))
        [<Meeting on 2011-10-29 00:05 EEST>,
         <Meeting on 2011-10-29 05:00 EEST>,
         <Meeting on 2011-10-29 23:55 EEST>,
         <Meeting on 2011-10-30 00:05 EEST>,
         <Meeting on 2011-10-30 05:00 EET>,
         <Meeting on 2011-10-30 23:55 EET>,
         <Meeting on 2011-10-31 00:05 EET>,
         <Meeting on 2011-10-31 05:00 EET>,
         <Meeting on 2011-10-31 23:55 EET>]

    Let's build a calendar for, say, math class:

        >>> class Math(object):
        ...     ___init__ = lambda self, schedule: None
        ...     title = 'Math'
        >>> provideAdapter(lambda s: Math, (ScheduleStub, ), IHaveSchedule)

        >>> cal = ImmutableScheduleCalendarForTest(schedule)

    Calendar events are always localized to UTC, but we can still see
    the correct compensation for dst shift:

        >>> print_events(cal)
        Math on 2011-10-28 21:05 UTC
        Math on 2011-10-29 02:00 UTC
        Math on 2011-10-29 20:55 UTC
        Math on 2011-10-29 21:05 UTC
        Math on 2011-10-30 03:00 UTC
        Math on 2011-10-30 21:55 UTC
        Math on 2011-10-30 22:05 UTC
        Math on 2011-10-31 03:00 UTC
        Math on 2011-10-31 21:55 UTC

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
