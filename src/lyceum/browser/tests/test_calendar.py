#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Unit tests for lyceum person views.

$Id$
"""
import unittest
from pytz import utc

from zope.app.testing import setup
from zope.testing import doctest

from schooltool.common import parse_datetime


def dt(timestr):
    dt = parse_datetime('2004-11-05 %s:00' % timestr)
    return dt.replace(tzinfo=utc)


def doctest_LyceumDailyCalendarRowsView():
    """Tests for LyceumDailyCalendarRowsView.

        >>> from lyceum.browser.calendar import LyceumDailyCalendarRowsView
        >>> from zope.publisher.browser import TestRequest
        >>> view = LyceumDailyCalendarRowsView(None, TestRequest())
        >>> from datetime import timedelta
        >>> rows = [dt('%d:00' % i)
        ...         for i in range(8, 19)]

    If there are no periods rows are retrurned unmodified:

        >>> view._addPeriodsToRows(rows, [], []) == rows
        True

    All the rows between the first and last period are deleted, and
    periods themselves get added to rows:

        >>> view._addPeriodsToRows(rows, [("lesson 1", dt('10:00'), timedelta(minutes=45)),
        ...                               ("lesson 2", dt('17:00'), timedelta(minutes=45))], [])
        [datetime.datetime(2004, 11, 5, 8, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 9, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 45, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 17, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 17, 45, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 18, 0, tzinfo=<UTC>)]

    If there are simple calendar events in the even list, they are
    ignored:

        >>> class CalendarEventStub(object):
        ...     pass

        >>> from schooltool.timetable.interfaces import ITimetableCalendarEvent
        >>> from zope.interface import implements
        >>> class TTCalendarEventStub(object):
        ...     implements(ITimetableCalendarEvent)
        ...     def __init__(self, period_id, start):
        ...         self.period_id = period_id
        ...         self.dtstart = start
        ...         self.duration = timedelta(minutes=45)

        >>> class EventForDisplay(object):
        ...     def __init__(self, context):
        ...         self.context = context

        >>> view._addPeriodsToRows(rows, [("lesson 1", dt('10:00'), timedelta(minutes=45)),
        ...                               ("lesson 2", dt('17:00'), timedelta(minutes=45))],
        ...                               map(EventForDisplay,
        ...                                   [CalendarEventStub(),
        ...                                    CalendarEventStub()]))
        [datetime.datetime(2004, 11, 5, 8, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 9, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 45, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 17, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 17, 45, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 18, 0, tzinfo=<UTC>)]

    But if events are timetable calendar events

        >>> view._addPeriodsToRows(rows, [("lesson 1", dt('10:00'), timedelta(minutes=45)),
        ...                               ("lesson 2", dt('17:00'), timedelta(minutes=45))],
        ...                               map(EventForDisplay,
        ...                                   [CalendarEventStub(),
        ...                                    CalendarEventStub(),
        ...                                    TTCalendarEventStub("lesson 1", dt("10:05")),
        ...                                    TTCalendarEventStub("lesson 2", dt("17:00"))]))
        [datetime.datetime(2004, 11, 5, 8, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 9, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 5, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 10, 50, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 17, 0, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 17, 45, tzinfo=<UTC>),
         datetime.datetime(2004, 11, 5, 18, 0, tzinfo=<UTC>)]

    """

def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
