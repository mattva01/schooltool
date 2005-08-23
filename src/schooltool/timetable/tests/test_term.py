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

$Id: test_timetable.py 4822 2005-08-19 01:35:11Z srichter $
"""
import calendar
import unittest
from datetime import date

from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.app.container.contained import Contained
from zope.app.location.interfaces import ILocation
from zope.app.testing.setup import placefulSetUp, placefulTearDown

from schooltool.timetable.interfaces import IDateRange
from schooltool.timetable.interfaces import ITerm, ITermWrite
from schooltool.timetable.interfaces import ITermContainer
from schooltool.timetable.term import DateRange
from schooltool.timetable.term import Term, TermContainer
from schooltool.timetable.term import getTermForDate, getNextTermForDate

from schooltool.testing import setup

class TermStub(Contained):

    implements(ITerm)

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


class TestDateRange(unittest.TestCase):

    def test(self):
        dr = DateRange(date(2003, 1, 1), date(2003, 1, 31))
        verifyObject(IDateRange, dr)

        # __contains__
        self.assert_(date(2002, 12, 31) not in dr)
        self.assert_(date(2003, 2, 1) not in dr)
        for day in range(1, 32):
            self.assert_(date(2003, 1, day) in dr)

        # __iter__
        days = list(dr)
        self.assertEqual(len(days), 31)
        self.assertEqual(len(dr), 31)

        days = DateRange(date(2003, 1, 1), date(2003, 1, 2))
        self.assertEqual(list(days), [date(2003, 1, 1), date(2003, 1, 2)])

        days = DateRange(date(2003, 1, 1), date(2003, 1, 1))
        self.assertEqual(list(days), [date(2003, 1, 1)])

        self.assertRaises(ValueError, DateRange,
                          date(2003, 1, 2), date(2003, 1, 1))


class TestTerm(unittest.TestCase):

    def test_interface(self):

        cal = Term('Sample', date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(ITerm, cal)
        verifyObject(ITermWrite, cal)
        verifyObject(ILocation, cal)

    def testAddRemoveSchoolday(self):
        cal = Term('Sample', date(2003, 9, 1), date(2003, 9, 14))

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
        cal = Term('Sample', date(2003, 9, 1), date(2003, 9, 15))
        cal.addWeekdays(1, 3, 5)

        new_first, new_last = date(2003, 8, 1), date(2003, 9, 30)
        cal.reset(new_first, new_last)

        self.assertEqual(cal.first, new_first)
        self.assertEqual(cal.last, new_last)
        for d in cal:
            self.assert_(not cal.isSchoolday(d))

        self.assertRaises(ValueError, cal.reset, new_last, new_first)

    def testMarkWeekday(self):
        cal = Term('Sample', date(2003, 9, 1), date(2003, 9, 17))
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
        cal = Term('Sample', date(2003, 9, 1), date(2003, 9, 16))
        self.assert_(date(2003, 8, 31) not in cal)
        self.assert_(date(2003, 9, 17) not in cal)
        for day in range(1, 17):
            self.assert_(date(2003, 9, day) in cal)
        self.assertRaises(TypeError, cal.__contains__, 'some string')


class TestTermContainer(unittest.TestCase):

    def test_interface(self):
        service = TermContainer()
        verifyObject(ITermContainer, service)

    def test(self):
        service = TermContainer()
        self.assertEqual(list(service.keys()), [])

        schooldays = TermStub()
        service['2003 fall'] = schooldays
        self.assertEqual(list(service.keys()), ['2003 fall'])
        self.assert_('2003 fall' in service)
        self.assert_('2004 spring' not in service)
        self.assert_(service['2003 fall'] is schooldays)
        self.assertEquals(schooldays.__name__, '2003 fall')
        self.assert_(schooldays.__parent__ is service)

        schooldays3 = TermStub()
        service['2004 spring'] = schooldays3
        self.assertEqual(sorted(service.keys()), ['2003 fall', '2004 spring'])
        self.assert_('2004 spring' in service)
        self.assert_(service['2004 spring'] is schooldays3)

        del service['2003 fall']
        self.assertEqual(list(service.keys()), ['2004 spring'])
        self.assert_('2003 fall' not in service)
        self.assert_('2004 spring' in service)
        self.assertRaises(KeyError, lambda: service['2003 fall'])

        # duplicate deletion
        self.assertRaises(KeyError, service.__delitem__, '2003 fall')


class TestGetTermForDate(unittest.TestCase):

    def setUp(self):
        placefulSetUp()
        app = setup.setupSchoolToolSite()

        self.term1 = Term('Sample', date(2004, 9, 1), date(2004, 12, 20))
        self.term2 = Term('Sample', date(2005, 1, 1), date(2005, 6, 1))
        app["terms"]['2004-fall'] = self.term1
        app["terms"]['2005-spring'] = self.term2

        class TimetableModelStub:
            def periodsInDay(self, schooldays, ttschema, date):
                return 'periodsInDay', schooldays, ttschema, date

        from schooltool.timetable.schema import TimetableSchema
        tt = TimetableSchema([])
        tt.model = TimetableModelStub()
        self.tt = tt
        app["ttschemas"]['default'] = tt
        self.app = app

    def tearDown(self):
        placefulTearDown()

    def test_getTermForDate(self):
        self.assert_(getTermForDate(date(2004, 8, 31)) is None)
        self.assert_(getTermForDate(date(2004, 9, 1)) is self.term1)
        self.assert_(getTermForDate(date(2004, 11, 5)) is self.term1)
        self.assert_(getTermForDate(date(2004, 12, 20)) is self.term1)
        self.assert_(getTermForDate(date(2004, 12, 21)) is None)
        self.assert_(getTermForDate(date(2005, 3, 17)) is self.term2)
        self.assert_(getTermForDate(date(2005, 11, 5)) is None)

    def test_getNextTermForDate(self):
        self.assert_(getNextTermForDate(date(2004, 8, 31)) is self.term1)
        self.assert_(getNextTermForDate(date(2004, 9, 1)) is self.term1)
        self.assert_(getNextTermForDate(date(2004, 11, 5)) is self.term1)
        self.assert_(getNextTermForDate(date(2004, 12, 20)) is self.term1)
        self.assert_(getNextTermForDate(date(2004, 12, 21)) is self.term2)
        self.assert_(getNextTermForDate(date(2005, 3, 17)) is self.term2)
        self.assert_(getNextTermForDate(date(2005, 11, 5)) is self.term2)
        self.term3 = Term('Sample', date(2006, 1, 1), date(2006, 6, 1))
        self.app["terms"]["term3"] = self.term3
        self.assert_(getNextTermForDate(date(2005, 11, 5)) is self.term3)
        self.assert_(getNextTermForDate(date(2004, 8, 31)) is self.term1)
        del self.app["terms"]["term3"]
        del self.app["terms"]['2004-fall']
        del self.app["terms"]['2005-spring']
        self.assert_(getNextTermForDate(date(2004, 8, 31)) is None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDateRange))
    suite.addTest(unittest.makeSuite(TestTerm))
    suite.addTest(unittest.makeSuite(TestTermContainer))
    suite.addTest(unittest.makeSuite(TestGetTermForDate))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
