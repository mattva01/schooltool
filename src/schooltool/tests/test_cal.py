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
from zope.interface import implements
from zope.testing.doctestunit import DocTestSuite
from datetime import date, time, timedelta
from StringIO import StringIO


class TestSchooldayModel(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayModel
        from schooltool.interfaces import ISchooldayModel, ILocation

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(ISchooldayModel, cal)
        verifyObject(ILocation, cal)

    def testAddRemoveSchoolday(self):
        from schooltool.cal import SchooldayModel

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
        from schooltool.cal import ICalReader
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


class TestTimetable(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import Timetable
        from schooltool.interfaces import ITimetable

        t = Timetable()
        verifyObject(ITimetable, t)

    def test_keys(self):
        from schooltool.cal import Timetable
        days = ('Mo', 'Tu', 'We', 'Th', 'Fr')
        t = Timetable(days)
        self.assertEqual(t.keys(), list(days))

    def test_getitem_setitem(self):
        from schooltool.cal import Timetable
        from schooltool.interfaces import ITimetableDay

        days = ('Mo', 'Tu', 'We', 'Th', 'Fr')
        t = Timetable(days)
        self.assertRaises(KeyError, t.__getitem__, "Mo")
        self.assertRaises(KeyError, t.__getitem__, "What!?")

        class DayStub:
            implements(ITimetableDay)

        self.assertRaises(TypeError, t.__setitem__, "Mo", object())
        self.assertRaises(ValueError, t.__setitem__, "Mon", DayStub())
        monday = DayStub()
        t["Mo"] = monday
        self.assertEqual(t["Mo"], monday)

    def test_items(self):
        from schooltool.cal import Timetable
        from schooltool.interfaces import ITimetableDay

        days = ('Mo', 'Tu', 'We', 'Th', 'Fr')
        t = Timetable(days)

        class DayStub:
            implements(ITimetableDay)

        monday = DayStub()
        t["Mo"] = monday
        self.assertEqual(t.items(),
                         [("Mo", monday), ("Tu", None), ("We", None),
                          ("Th", None), ("Fr", None)])
        tuesday = DayStub()
        t["Tu"] = tuesday
        self.assertEqual(t.items(),
                         [("Mo", monday), ("Tu", tuesday), ("We", None),
                          ("Th", None), ("Fr", None)])


class TestTimetableDay(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import TimetableDay
        from schooltool.interfaces import ITimetableDay

        td = TimetableDay()
        verifyObject(ITimetableDay, td)

    def test_keys(self):
        from schooltool.cal import TimetableDay
        periods = ('1', '2', '3', '4', '5')
        td = TimetableDay(periods)
        self.assertEqual(td.keys(), list(periods))

    def test_getitem_setitem_items_delitem(self):
        from schooltool.cal import TimetableDay
        from schooltool.interfaces import ITimetableActivity

        periods = ('1', '2', '3', '4')
        td = TimetableDay(periods)
        self.assertEqual(td["1"], None)
        self.assertRaises(KeyError, td.__getitem__, "Mo")

        class ActivityStub:
            implements(ITimetableActivity)

        self.assertRaises(TypeError, td.__setitem__, "1", object())
        self.assertRaises(ValueError, td.__setitem__, "0", ActivityStub())
        math = ActivityStub()
        td["1"] = math
        self.assertEqual(td["1"], math)

        self.assertEqual(td.items(), [('1', math), ('2', None), ('3', None),
                                      ('4', None)])
        english = ActivityStub()
        td["2"] = english
        self.assertEqual(td.items(), [('1', math), ('2', english), ('3', None),
                                      ('4', None)])

        self.assertEqual(td["2"], english)
        del td["2"]
        self.assertEqual(td["2"], None)


class TestTimetableActivity(unittest.TestCase):

    def test(self):
        from schooltool.cal import TimetableActivity
        from schooltool.interfaces import ITimetableActivity

        ta = TimetableActivity("Dancing")
        verifyObject(ITimetableActivity, ta)
        self.assertEqual(ta.title, "Dancing")


class TestTimetabling(unittest.TestCase):
    """A functional test for timetables"""

    def test(self):
        from schooltool.cal import Timetable, TimetableDay, TimetableActivity
        tt = Timetable(('A', 'B'))
        periods = ('Green', 'Blue')
        tt["A"] = TimetableDay(periods)
        tt["B"] = TimetableDay(periods)
        tt["A"]["Green"] = TimetableActivity("English")
        tt["A"]["Blue"] = TimetableActivity("Math")
        tt["B"]["Green"] = TimetableActivity("Biology")
        tt["B"]["Blue"] = TimetableActivity("Geography")


class TestSchooldayPeriodEvent(unittest.TestCase):

    def test(self):
        from schooltool.cal import SchooldayPeriodEvent
        from schooltool.interfaces import ISchooldayPeriodEvent

        ev = SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45))
        verifyObject(ISchooldayPeriodEvent, ev)
        self.assertEqual(ev.title, "1")
        self.assertEqual(ev.tstart, time(9,0))
        self.assertEqual(ev.duration, timedelta(seconds=2700))

    def test_eq(self):
        from schooltool.cal import SchooldayPeriodEvent
        self.assertEqual(
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45)))
        self.assertEqual(
            hash(SchooldayPeriodEvent("1", time(9, 0), timedelta(minutes=45))),
            hash(SchooldayPeriodEvent("1", time(9, 0), timedelta(minutes=45))))
        self.assertNotEqual(
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriodEvent("2", time(9, 00), timedelta(minutes=45)))
        self.assertNotEqual(
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriodEvent("1", time(9, 01), timedelta(minutes=45)))
        self.assertNotEqual(
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=90)))
        self.assertNotEqual(
            SchooldayPeriodEvent("1", time(9, 00), timedelta(minutes=45)),
            object())


class TestSchooldayTemplate(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayTemplate
        from schooltool.interfaces import ISchooldayTemplate

        tmpl = SchooldayTemplate()
        verifyObject(ISchooldayTemplate, tmpl)

    def test_add_remove_iter(self):
        from schooltool.cal import SchooldayTemplate, SchooldayPeriodEvent
        from schooltool.interfaces import ISchooldayPeriodEvent

        class SPEStub:
            implements(ISchooldayPeriodEvent)

        tmpl = SchooldayTemplate()
        self.assertEqual(list(iter(tmpl)), [])
        self.assertRaises(TypeError, tmpl.add, object())

        lesson1 = SchooldayPeriodEvent("1", time(9, 0), timedelta(minutes=45))
        lesson2 = SchooldayPeriodEvent("2", time(10, 0), timedelta(minutes=45))

        tmpl.add(lesson1)
        self.assertEqual(list(iter(tmpl)), [lesson1])

        # Adding the same thing again.
        tmpl.add(lesson1)
        self.assertEqual(list(iter(tmpl)), [lesson1])

        tmpl.add(lesson2)
        self.assertEqual(len(list(iter(tmpl))), 2)
        tmpl.remove(lesson1)
        self.assertEqual(list(iter(tmpl)), [lesson2])


def test_suite():
    import schooltool.cal
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayModel))
    suite.addTest(unittest.makeSuite(TestICalReader))
    suite.addTest(unittest.makeSuite(TestTimetable))
    suite.addTest(unittest.makeSuite(TestTimetableDay))
    suite.addTest(unittest.makeSuite(TestTimetableActivity))
    suite.addTest(unittest.makeSuite(TestTimetabling))
    suite.addTest(unittest.makeSuite(TestSchooldayPeriodEvent))
    suite.addTest(unittest.makeSuite(TestSchooldayTemplate))
    suite.addTest(DocTestSuite(schooltool.cal))
    return suite
