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
Unit tests for the schooltool.timetable.term module.

$Id$
"""
import calendar
import unittest
from pytz import timezone
from datetime import date, datetime

from zope.testing import doctest
from zope.component import provideAdapter
from zope.interface import Interface
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.app.container.contained import Contained
from zope.location.interfaces import ILocation
from zope.app.testing.setup import placefulSetUp, placefulTearDown
from zope.app.testing.setup import placelessSetUp, placelessTearDown

from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.schoolyear import getSchoolYearContainer
from schooltool.term.term import getTermContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.term import interfaces, term
from schooltool.testing import setup


class TermStub(Contained):

    implements(interfaces.ITerm)

    #     November 2003
    #  Su Mo Tu We Th Fr Sa
    #                     1
    #   2  3  4  5  6  7  8
    #   9 10 11 12 13 14 15
    #  16 17 18 19<20-21>22
    #  23<24-25-26>27 28 29
    #  30

    first = date(2003, 11, 20)
    last = date(2003, 11, 26)

    def __iter__(self):
        return iter((date(2003, 11, 20),
                     date(2003, 11, 21),
                     date(2003, 11, 22),
                     date(2003, 11, 23),
                     date(2003, 11, 24),
                     date(2003, 11, 25),
                     date(2003, 11, 26)))

    def isSchoolday(self, day):
        return day in (date(2003, 11, 20),
                       date(2003, 11, 21),
                       date(2003, 11, 24),
                       date(2003, 11, 25),
                       date(2003, 11, 26))

    def __contains__(self, day):
        return date(2003, 11, 20) <= day <= date(2003, 11, 26)


class TestTerm(unittest.TestCase):

    def test_interface(self):

        cal = term.Term('Sample', date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(interfaces.ITerm, cal)
        verifyObject(interfaces.ITermWrite, cal)
        verifyObject(ILocation, cal)

    def testAddRemoveSchoolday(self):
        cal = term.Term('Sample', date(2003, 9, 1), date(2003, 9, 14))

        self.assert_(not cal.isSchoolday(date(2003, 9, 1)))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.isSchoolday, date(2003, 9, 15))

        cal.add(date(2003, 9, 2))
        self.assert_(cal.isSchoolday(date(2003, 9, 2)))
        cal.remove(date(2003, 9, 2))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.add, date(2003, 9, 15))
        self.assertRaises(ValueError, cal.remove, date(2003, 9, 15))

    def testReset(self):
        cal = term.Term('Sample', date(2003, 9, 1), date(2003, 9, 15))
        cal.addWeekdays(1, 3, 5)

        new_first, new_last = date(2003, 8, 1), date(2003, 9, 30)
        cal.reset(new_first, new_last)

        self.assertEqual(cal.first, new_first)
        self.assertEqual(cal.last, new_last)
        for d in cal:
            self.assert_(not cal.isSchoolday(d))

        self.assertRaises(ValueError, cal.reset, new_last, new_first)

    def testMarkWeekday(self):
        cal = term.Term('Sample', date(2003, 9, 1), date(2003, 9, 17))
        for day in 1, 8, 15:
            self.assert_(not cal.isSchoolday(date(2003, 9, day)))

        cal.addWeekdays(calendar.MONDAY)
        for day in 1, 8, 15:
            self.assert_(cal.isSchoolday(date(2003, 9, day)))
            self.assert_(not cal.isSchoolday(date(2003, 9, day+1)))

        cal.removeWeekdays(calendar.MONDAY, calendar.TUESDAY)
        for day in 1, 8, 15:
            self.assert_(not cal.isSchoolday(date(2003, 9, day)))
            self.assert_(not cal.isSchoolday(date(2003, 9, day+1)))

        cal.addWeekdays(calendar.MONDAY, calendar.TUESDAY)
        for day in 1, 8, 15:
            self.assert_(cal.isSchoolday(date(2003, 9, day)))
            self.assert_(cal.isSchoolday(date(2003, 9, day+1)))

        cal.toggleWeekdays(calendar.TUESDAY, calendar.WEDNESDAY)
        for day in 1, 8, 15:
            self.assert_(cal.isSchoolday(date(2003, 9, day)))
            self.assert_(not cal.isSchoolday(date(2003, 9, day+1)))
            self.assert_(cal.isSchoolday(date(2003, 9, day+2)))

    def test_contains(self):
        cal = term.Term('Sample', date(2003, 9, 1), date(2003, 9, 16))
        self.assert_(date(2003, 8, 31) not in cal)
        self.assert_(date(2003, 9, 17) not in cal)
        for day in range(1, 17):
            self.assert_(date(2003, 9, day) in cal)
        self.assertRaises(TypeError, cal.__contains__, 'some string')


class TestGetTermForDate(unittest.TestCase):

    def setUp(self):
        placefulSetUp()
        provideAdapter(getTermContainer, [Interface], ITermContainer)
        provideAdapter(getSchoolYearContainer)
        app = setup.setUpSchoolToolSite()

        schoolyear = SchoolYear("Sample", date(2004, 9, 1), date(2005, 12, 20))
        ISchoolYearContainer(app)['2004-2005'] = schoolyear

        self.term1 = term.Term('Sample', date(2004, 9, 1), date(2004, 12, 20))
        self.term2 = term.Term('Sample', date(2005, 1, 1), date(2005, 6, 1))
        terms = ITermContainer(app)
        terms['2004-fall'] = self.term1
        terms['2005-spring'] = self.term2
        self.app = app

    def tearDown(self):
        placefulTearDown()

    def test_getTermForDate(self):
        self.assert_(term.getTermForDate(date(2004, 8, 31)) is None)
        self.assert_(term.getTermForDate(date(2004, 9, 1)) is self.term1)
        self.assert_(term.getTermForDate(date(2004, 11, 5)) is self.term1)
        self.assert_(term.getTermForDate(date(2004, 12, 20)) is self.term1)
        self.assert_(term.getTermForDate(date(2004, 12, 21)) is None)
        self.assert_(term.getTermForDate(date(2005, 3, 17)) is self.term2)
        self.assert_(term.getTermForDate(date(2005, 11, 5)) is None)

    def test_getNextTermForDate(self):
        self.assert_(term.getNextTermForDate(date(2004, 8, 31)) is self.term1)
        self.assert_(term.getNextTermForDate(date(2004, 9, 1)) is self.term1)
        self.assert_(term.getNextTermForDate(date(2004, 11, 5)) is self.term1)
        self.assert_(term.getNextTermForDate(date(2004, 12, 20)) is self.term1)
        self.assert_(term.getNextTermForDate(date(2004, 12, 21)) is self.term2)
        self.assert_(term.getNextTermForDate(date(2005, 3, 17)) is self.term2)
        self.assert_(term.getNextTermForDate(date(2005, 11, 5)) is self.term2)
        self.term3 = term.Term('Sample', date(2005, 9, 1), date(2005, 12, 20))
        terms = ITermContainer(self.app)
        terms['2005-fall'] = self.term3
        self.assert_(term.getNextTermForDate(date(2005, 8, 30)) is self.term3)
        self.assert_(term.getNextTermForDate(date(2004, 8, 31)) is self.term1)
        self.assert_(term.getNextTermForDate(date(2004, 12, 22)) is self.term2)
        del terms['2004-fall']
        del terms['2005-spring']
        del terms['2005-fall']
        self.assert_(term.getNextTermForDate(date(2004, 8, 31)) is None)


def doctest_DateManagerUtility_today():
    """Test for today.

    Today returns the date of today, according to the application
    prefered timezone:

        >>> from schooltool.term.term import DateManagerUtility
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> dm = DateManagerUtility()
        >>> tz_name = "Europe/Vilnius"
        >>> class PrefStub(object):
        ...     @property
        ...     def timezone(self):
        ...         return tz_name

        >>> class STAppStub(dict):
        ...     def __init__(self, context):
        ...         pass
        ...     def __conform__(self, iface):
        ...         if iface == IApplicationPreferences:
        ...             return PrefStub()

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> provideAdapter(STAppStub, adapts=[None], provides=ISchoolToolApplication)

        >>> current_time = timezone('UTC').localize(datetime.utcnow())

        >>> tz_name = 'Pacific/Midway'
        >>> tz = timezone(tz_name)
        >>> today_date = current_time.astimezone(tz).date()
        >>> dm.today == today_date
        True

        >>> tz_name = 'Pacific/Funafuti'
        >>> tz = timezone('Pacific/Funafuti')
        >>> today_date = current_time.astimezone(tz).date()
        >>> dm.today == today_date
        True

    """


def setUp(test):
    placelessSetUp()


def tearDown(test):
    placelessTearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp,
                                       tearDown=tearDown))
    suite.addTest(unittest.makeSuite(TestTerm))
    suite.addTest(unittest.makeSuite(TestGetTermForDate))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
