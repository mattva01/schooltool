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
from StringIO import StringIO

class TestSchooldayModel(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayModel
        from schooltool.interfaces import ISchooldayModel

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(ISchooldayModel, cal)

    def testAddRemoveSchoolday(self):
        from schooltool.cal import SchooldayModel
        from schooltool.interfaces import ISchooldayModel

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 15))

        self.assert_(not cal.isSchoolday(date(2003, 9, 1)))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.isSchoolday, date(2003, 9, 15))

        cal.add(date(2003, 9, 2))
        self.assert_(cal.isSchoolday(date(2003, 9, 2)))
        cal.remove(date(2003, 9, 2))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.add, date(2003, 9, 15))
        self.assertRaises(ValueError, cal.remove, date(2003, 9, 15))

    def testMarkWeekday(self):
        from schooltool.cal import SchooldayModel
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 17))
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

    def test_contains(self):
        from schooltool.cal import SchooldayModel
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 17))
        self.assert_(date(2003, 8, 31) not in cal)
        self.assert_(date(2003, 9, 17) not in cal)
        for day in range(1, 17):
            self.assert_(date(2003, 9, day) in cal)
        self.assertRaises(TypeError, cal.__contains__, 'some string')


example_ical = """\
BEGIN:VCALENDAR
VERSION
 :2.0
PRODID
 :-//Mozilla.org/NONSGML Mozilla Calendar V1.0//EN
METHOD
 :PUBLISH
BEGIN:VEVENT
UID
 :956630271
SUMMARY
 :Christmas Day
CLASS
 :PUBLIC
X-MOZILLA-ALARM-DEFAULT-UNITS
 :minutes
X-MOZILLA-ALARM-DEFAULT-LENGTH
 :15
X-MOZILLA-RECUR-DEFAULT-UNITS
 :weeks
X-MOZILLA-RECUR-DEFAULT-INTERVAL
 :1
DTSTART
 ;VALUE=DATE
 :20031225
DTSTAMP
 :20020430T114937Z
END:VEVENT
END:VCALENDAR
BEGIN:VCALENDAR
VERSION
 :2.0
PRODID
 :-//Mozilla.org/NONSGML Mozilla Calendar V1.0//EN
METHOD
 :PUBLISH
BEGIN:VEVENT
UID
 :911737808
SUMMARY
 :Boxing Day
CLASS
 :PUBLIC
X-MOZILLA-ALARM-DEFAULT-UNITS
 :minutes
X-MOZILLA-ALARM-DEFAULT-LENGTH
 :15
X-MOZILLA-RECUR-DEFAULT-UNITS
 :weeks
X-MOZILLA-RECUR-DEFAULT-INTERVAL
 :1
DTSTART
 ;VALUE=DATE
 :20031226
DTSTAMP
 :20020430T114937Z
END:VEVENT
END:VCALENDAR
"""


class TestICalReader(unittest.TestCase):

    def test_markNonSchooldays(self):
        from schooltool.cal import ICalReader, SchooldayModel
        cal = SchooldayModel(date(2003, 9, 01), date(2004, 01, 01))
        file = StringIO(example_ical)
        reader = ICalReader(file)
        cal.addWeekdays(0, 1, 2, 3, 4)
        self.assert_(cal.isSchoolday(date(2003, 12, 24)))
        self.assert_(cal.isSchoolday(date(2003, 12, 25)))
        self.assert_(cal.isSchoolday(date(2003, 12, 26)))
        reader.markNonSchooldays(cal)
        self.assert_(cal.isSchoolday(date(2003, 12, 24)))
        self.assert_(not cal.isSchoolday(date(2003, 12, 25)))
        self.assert_(not cal.isSchoolday(date(2003, 12, 26)))

    def test_read(self):
        from schooltool.cal import ICalReader, SchooldayModel
        cal = SchooldayModel(date(2003, 9, 01), date(2004, 01, 01))
        file = StringIO(example_ical)
        reader = ICalReader(file)
        result = reader.read()
        self.assertEqual(len(result), 2)
        vevent = result[0]
        self.assertEqual(vevent['x-mozilla-recur-default-units'], 'weeks')
        self.assertEqual(vevent['dtstart'], '20031225')
        self.assertEqual(vevent.dtstart, date(2003, 12, 25))
        vevent = result[1]
        self.assertEqual(vevent['dtstart'], '20031226')
        self.assertEqual(vevent.dtstart, date(2003, 12, 26))

    def test_readRecord(self):
        from schooltool.cal import ICalReader, SchooldayModel
        file = StringIO("key1\n"
                        " :value1\n"
                        "key2\n"
                        " ;VALUE=foo\n"
                        " :value2\n"
                        "key3;VALUE=bar:value3\n")
        reader = ICalReader(file)
        self.assertEqual(list(reader.readRecord()),
                         [('key1', 'value1', None),
                          ('key2', 'value2', 'foo'),
                          ('key3', 'value3', 'bar')])

        file = StringIO("key1:value1\n"
                        "key2;VALUE=foo:value2\n"
                        "key3;VALUE=bar:value3\n")
        reader = ICalReader(file)
        self.assertEqual(list(reader.readRecord()),
                         [('key1', 'value1', None),
                          ('key2', 'value2', 'foo'),
                          ('key3', 'value3', 'bar')])


def test_suite():
    import schooltool.cal
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayModel))
    suite.addTest(unittest.makeSuite(TestICalReader))
    suite.addTest(DocTestSuite(schooltool.cal))
    return suite
