#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for the schooltool.calendar module.

$Id$
"""
import unittest
import calendar
from zope.interface.verify import verifyObject
from zope.testing.doctestunit import DocTestSuite
from datetime import date
import schooltool.cal

class TestSchooldayCalendar(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayCalendar
        from schooltool.interfaces import ISchooldayCalendar

        cal = SchooldayCalendar(date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(ISchooldayCalendar, cal)

    def testAddRemoveContains(self):
        from schooltool.cal import SchooldayCalendar
        from schooltool.interfaces import ISchooldayCalendar

        cal = SchooldayCalendar(date(2003, 9, 1), date(2003, 9, 15))

        self.assert_(date(2003, 9, 1) not in cal)
        self.assert_(date(2003, 9, 2) not in cal)
        self.assertRaises(ValueError, cal.__contains__, date(2003, 9, 15))

        cal.add(date(2003, 9, 2))
        self.assert_(date(2003, 9, 2) in cal)
        cal.remove(date(2003, 9, 2))
        self.assert_(date(2003, 9, 2) not in cal)
        self.assertRaises(ValueError, cal.add, date(2003, 9, 15))
        self.assertRaises(ValueError, cal.remove, date(2003, 9, 15))

    def testMarkWeekday(self):
        from schooltool.cal import SchooldayCalendar
        from schooltool.interfaces import ISchooldayCalendar
        cal = SchooldayCalendar(date(2003, 9, 1), date(2003, 9, 17))
        for day in 1, 8, 15:
            self.assert_(date(2003, 9, day) not in cal)

        cal.addWeekdays(calendar.MONDAY)
        for day in 1, 8, 15:
            self.assert_(date(2003, 9, day) in cal)
            self.assert_(date(2003, 9, day+1) not in cal)

        cal.removeWeekdays(calendar.MONDAY, calendar.TUESDAY)
        for day in 1, 8, 15:
            self.assert_(date(2003, 9, day) not in cal)
            self.assert_(date(2003, 9, day+1) not in cal)

        cal.addWeekdays(calendar.MONDAY, calendar.TUESDAY)
        for day in 1, 8, 15:
            self.assert_(date(2003, 9, day) in cal)
            self.assert_(date(2003, 9, day+1) in cal)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayCalendar))
    suite.addTest(DocTestSuite(schooltool.cal))
    return suite
