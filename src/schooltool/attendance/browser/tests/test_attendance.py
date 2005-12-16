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
Tests for SchoolTool attendance views

$Id$
"""
import unittest
import datetime

from pytz import utc
from zope.testing import doctest
from zope.app.testing import ztapi
from zope.publisher.browser import TestRequest
from zope.interface import implements, Interface
from zope.component import adapts

from schooltool.timetable import ITimetables
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.timetable.model import TimetableCalendarEvent


class StubTimetables(object):
    adapts(Interface)
    implements(ITimetables)
    def __init__(self, context):
        self.context = context

    def makeTimetableCalendar(self):
        return ImmutableCalendar([
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 14, 10, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Math", period_id="A", activity=None),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 14, 11, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Arts", period_id="D", activity=None),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Math", period_id="B", activity=None),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Arts",
                period_id="C", activity=None),
            ])


def doctest_verifyPeriodForSection():
    """Doctest for verifyPeriodForSection

    When traversing to the realtime attendance form, we want to verify
    that the section has the given period takes place on the given
    date.  We have a utility function for that:

        >>> from schooltool.attendance.browser.attendance import \\
        ...     verifyPeriodForSection

        >>> section = StubTimetables(None)

    Now we can try our helper function:

        >>> for date in [datetime.date(2005, 12, d) for d in (14, 15, 16)]:
        ...     for period_id in 'A', 'B', 'C', 'D':
        ...         result = verifyPeriodForSection(section, date,
        ...                                         period_id, utc)
        ...         print date, period_id, result
        2005-12-14 A True
        2005-12-14 B False
        2005-12-14 C False
        2005-12-14 D True
        2005-12-15 A False
        2005-12-15 B True
        2005-12-15 C True
        2005-12-15 D False
        2005-12-16 A False
        2005-12-16 B False
        2005-12-16 C False
        2005-12-16 D False

    """

def doctest_SectionAttendanceTraverserPlugin():
    r"""Tests for SectionAttendanceTraverserPlugin

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

        >>> from schooltool.attendance.browser.attendance import \
        ...          SectionAttendanceTraverserPlugin
        >>> from schooltool.traverser.interfaces import ITraverserPlugin

        >>> ITraverserPlugin.implementedBy(SectionAttendanceTraverserPlugin)
        True

    If we traverse a name this plugin does not handle, we get a
    NotFound error.

        >>> plugin = SectionAttendanceTraverserPlugin("request", "context")
        >>> plugin.publishTraverse(None, 'name')
        Traceback (most recent call last):
        ...
        NotFound: Object: 'request', name: 'name'

    We must register the view we are traversing to first:

        >>> class AttendanceViewStub(object):
        ...     def __init__(self, context, request): pass
        ...     def __repr__(self):
        ...         return "%s, %s" % (self.date, self.period_id)
        >>> ztapi.browserView(None, 'attendance', AttendanceViewStub)

    Now we can try the typical case:

        >>> request = TestRequest()
        >>> request.setTraversalStack(['B', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        2005-12-15, B

        >>> request.getTraversalStack()
        []

    If there are more elements on the traversal stack, they remain there:

        >>> request.setTraversalStack(['extra', 'C', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        2005-12-15, C

        >>> request.getTraversalStack()
        ['extra']

    What if the date is invalid?

        >>> request.setTraversalStack(['A', '2005-02-29'])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    What if the period is invalid?

        >>> request.setTraversalStack(['A', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    If there are no date and period id following, we also get a NotFound:

        >>> request.setTraversalStack([])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS)])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
