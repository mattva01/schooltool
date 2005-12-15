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
            TimetableCalendarEvent(datetime.datetime(2005, 12, 15, 10, 00),
                                   datetime.timedelta(minutes=45),
                                   "Math",
                                   period_id="B", activity=None),
            TimetableCalendarEvent(datetime.datetime(2005, 12, 15, 11, 00),
                                   datetime.timedelta(minutes=45),
                                   "Arts",
                                   period_id="C", activity=None),
            ])



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
        ...         return "%s, %s, %s" % (self.date,
        ...                                self.schooltt_id,
        ...                                self.period_id)
        >>> ztapi.browserView(None, 'attendance', AttendanceViewStub)

    Now we can try the typical case:

        >>> request = TestRequest()
        >>> request.setTraversalStack(['B', 'default', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        2005-12-15, default, B

        >>> request.getTraversalStack()
        []

    If there are more elements on the traversal stack, they remain there:

        >>> request.setTraversalStack(['extra', 'C', 'default', '2005-12-15'])
        >>> plugin.publishTraverse(request, "attendance")
        2005-12-15, default, C

        >>> request.getTraversalStack()
        ['extra']

    What if the date is invalid?

        >>> request.setTraversalStack(['A', 'default', '2005-02-29'])
        >>> plugin.publishTraverse(request, "attendance")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'request', name: 'attendance'

    What if the period is invalid?

        >>> request.setTraversalStack(['A', 'default', '2005-12-15'])
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
