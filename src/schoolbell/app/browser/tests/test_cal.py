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
Tests for SchoolBell calendaring views.

$Id$
"""

import unittest
from datetime import datetime, date
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.app.tests import setup, ztapi
from zope.interface import directlyProvides
from zope.app.traversing.interfaces import IContainmentRoot


def doctest_PlainCalendarView():
    """Tests for PlainCalendarView.

        >>> from schoolbell.app.browser.cal import PlainCalendarView
        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> request = TestRequest()
        >>> view = PlainCalendarView(person, request)
        >>> view.update()
        >>> len(person.calendar)
        0

        >>> request = TestRequest()
        >>> request.form = {'GENERATE': ''}
        >>> view = PlainCalendarView(person, request)
        >>> view.update()
        >>> len(person.calendar)
        5

    """


class TestCalendarViewBase(unittest.TestCase):
    # Legacy unit tests from SchoolTool

    def test_dayTitle(self):
        from schoolbell.app.browser.cal import CalendarViewBase
        view = CalendarViewBase(None, None)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view.dayTitle(dt), "Thursday, 2004-07-01")


def doctest_CalendarViewBase():
    """Tests for CalendarViewBase.

        >>> from schoolbell.app.browser.cal import CalendarViewBase

        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> directlyProvides(person, IContainmentRoot)

    CalendarViewBase has a method calURL used for forming links to other
    calendar views on other dates.

        >>> request = TestRequest()
        >>> view = CalendarViewBase(person, request)
        >>> view.cursor = date(2005, 2, 3)

        >>> view.calURL("quarterly")
        'http://127.0.0.1/cal_quarterly.html?date=2005-02-03'
        >>> view.calURL("quarterly", date(2005, 12, 13))
        'http://127.0.0.1/cal_quarterly.html?date=2005-12-13'


    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
