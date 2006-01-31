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
Tests for SchoolTool attendance sparkline views

$Id$
"""
import unittest
from datetime import date
from persistent import Persistent

from zope.testing import doctest
from zope.app.testing import setup, ztapi

from schooltool.attendance.interfaces import IDayAttendance
from schooltool.timetable.interfaces import ITimetables
from schooltool.testing import setup as stsetup
from schooltool.attendance.browser.sparkline import AttendanceSparklineView


def setUp(test):
    setup.placefulSetUp()
    setup.setUpTraversal()


def tearDown(test):
    setup.placefulTearDown()


class DayAttendanceStub:
    pass


class PersonStub(Persistent):
    username = 'boy'

    def __conform__(self, interface):
        if interface is IDayAttendance:
            return DayAttendanceStub()


class CalendarStub:
    def expand(self, *args):
        pass


class TimetablesStub:
    def makeTimetableCalendar(self):
        return CalendarStub()


class SectionStub:
    def __conform__(self, interface):
        if interface is ITimetables:
            return TimetablesStub()


def doctest_AttendanceSparklineView_call():
    """Doctest for AttendanceSparklineView.__call__ method.

    Set up all infrastructure:

        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> context = None
        >>> app = stsetup.setupSchoolToolSite()
        >>> view = AttendanceSparklineView(context, request)
        >>> view.update = lambda: None
        >>> view.person = PersonStub()
        >>> view.section = SectionStub()
        >>> view.date = date(2005, 10, 20)
        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> from schooltool.app.app import getApplicationPreferences
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

    And look what we get:

        >>> image = view()
        >>> print image.encode('base64')
        iVBORw0KGgoAAAANSUhEUgAAAB4AAAANCAIAAAAxEEnAAAAAhUlEQVR4nGL8//8/A20AAAAA//9i
        opG5DAwMAAAAAP//oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//
        oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//oqHRAAAAAP//AwAK
        rQMX3Fm3sgAAAABJRU5ErkJggg==
        <BLANKLINE>

    """


def doctest_AttendanceSparklineView_update():
    """Doctest for AttendanceSparklineView.update method.

        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest(form={'person': 'boy', 'date': '2005-10-20'})
        >>> context = 'Section'
        >>> app = stsetup.setupSchoolToolSite()
        >>> app['persons']['boy'] = PersonStub()
        >>> view = AttendanceSparklineView(context, request)
        >>> view.update()
        >>> view.section
        'Section'
        >>> view.person
        <schooltool.attendance.browser.tests.test_sparkline.PersonStub ...>
        >>> view.date
        datetime.date(2005, 10, 20)
    """


def test_suite():
    return doctest.DocTestSuite(
            optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
            setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
