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
from pprint import pformat
from zope.interface.verify import verifyObject
from zope.interface import implements
from zope.testing.doctestunit import DocTestSuite
from datetime import date, time, timedelta, datetime
from StringIO import StringIO
from schooltool.tests.helpers import diff
from schooltool.tests.utils import EqualsSortedMixin
from schooltool.interfaces import ISchooldayModel


class TestSchooldayModel(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayModel
        from schooltool.interfaces import ISchooldayModel, ISchooldayModelWrite
        from schooltool.interfaces import ILocation

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(ISchooldayModel, cal)
        verifyObject(ISchooldayModelWrite, cal)
        verifyObject(ILocation, cal)

    def testAddRemoveSchoolday(self):
        from schooltool.cal import SchooldayModel

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 14))

        self.assert_(not cal.isSchoolday(date(2003, 9, 1)))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.isSchoolday, date(2003, 9, 15))

        cal.add(date(2003, 9, 2))
        self.assert_(cal.isSchoolday(date(2003, 9, 2)))
        cal.remove(date(2003, 9, 2))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.add, date(2003, 9, 15))
        self.assertRaises(ValueError, cal.remove, date(2003, 9, 15))

    def testClear(self):
        from schooltool.cal import SchooldayModel, daterange
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 15))
        cal.addWeekdays(1, 3, 5)
        cal.clear()
        for d in daterange(cal.first, cal.last):
            self.assert_(not cal.isSchoolday(d))

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
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 16))
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
        from schooltool.interfaces import ITimetable, ITimetableWrite

        t = Timetable()
        verifyObject(ITimetable, t)
        verifyObject(ITimetableWrite, t)

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
        from schooltool.interfaces import ITimetableDay, ITimetableDayWrite

        td = TimetableDay()
        verifyObject(ITimetableDay, td)
        verifyObject(ITimetableDayWrite, td)

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


class TestSchooldayPeriod(unittest.TestCase):

    def test(self):
        from schooltool.cal import SchooldayPeriod
        from schooltool.interfaces import ISchooldayPeriod

        ev = SchooldayPeriod("1", time(9, 00), timedelta(minutes=45))
        verifyObject(ISchooldayPeriod, ev)
        self.assertEqual(ev.title, "1")
        self.assertEqual(ev.tstart, time(9,0))
        self.assertEqual(ev.duration, timedelta(seconds=2700))

    def test_eq(self):
        from schooltool.cal import SchooldayPeriod
        self.assertEqual(
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=45)))
        self.assertEqual(
            hash(SchooldayPeriod("1", time(9, 0), timedelta(minutes=45))),
            hash(SchooldayPeriod("1", time(9, 0), timedelta(minutes=45))))
        self.assertNotEqual(
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriod("2", time(9, 00), timedelta(minutes=45)))
        self.assertNotEqual(
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriod("1", time(9, 01), timedelta(minutes=45)))
        self.assertNotEqual(
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=45)),
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=90)))
        self.assertNotEqual(
            SchooldayPeriod("1", time(9, 00), timedelta(minutes=45)),
            object())


class TestSchooldayTemplate(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayTemplate
        from schooltool.interfaces import ISchooldayTemplate
        from schooltool.interfaces import ISchooldayTemplateWrite

        tmpl = SchooldayTemplate()
        verifyObject(ISchooldayTemplate, tmpl)
        verifyObject(ISchooldayTemplateWrite, tmpl)

    def test_add_remove_iter(self):
        from schooltool.cal import SchooldayTemplate, SchooldayPeriod
        from schooltool.interfaces import ISchooldayPeriod

        class SPEStub:
            implements(ISchooldayPeriod)

        tmpl = SchooldayTemplate()
        self.assertEqual(list(iter(tmpl)), [])
        self.assertRaises(TypeError, tmpl.add, object())

        lesson1 = SchooldayPeriod("1", time(9, 0), timedelta(minutes=45))
        lesson2 = SchooldayPeriod("2", time(10, 0), timedelta(minutes=45))

        tmpl.add(lesson1)
        self.assertEqual(list(iter(tmpl)), [lesson1])

        # Adding the same thing again.
        tmpl.add(lesson1)
        self.assertEqual(list(iter(tmpl)), [lesson1])

        tmpl.add(lesson2)
        self.assertEqual(len(list(iter(tmpl))), 2)
        tmpl.remove(lesson1)
        self.assertEqual(list(iter(tmpl)), [lesson2])


class SchooldayModelStub:

    implements(ISchooldayModel)

    #     November 2003
    #  Su Mo Tu We Th Fr Sa
    #                     1
    #   2  3  4  5  6  7  8
    #   9 10 11 12 13 14 15
    #  16 17 18 19 20 21 22
    #  23 24 25 26 27 28 29
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


class BaseTestTimetableModel:

    def extractCalendarEvents(self, cal):
        result = []
        for d in cal.daterange:
            calday = cal.byDate(d)
            events = []
            for event in calday:
                events.append(event)
            result.append(dict([(event.dtstart, event.title)
                           for event in events]))
        return result


class TestSequentialDaysTimetableModel(unittest.TestCase,
                                       BaseTestTimetableModel):

    def test_interface(self):
        from schooltool.cal import SequentialDaysTimetableModel
        from schooltool.interfaces import ITimetableModel

        model = SequentialDaysTimetableModel(("A","B"), {})
        verifyObject(ITimetableModel, model)

    def test_createCalendar(self):
        from schooltool.cal import SequentialDaysTimetableModel, daterange
        from schooltool.cal import SchooldayTemplate, SchooldayPeriod
        from schooltool.cal import Timetable, TimetableDay, TimetableActivity
        from schooltool.interfaces import ICalendar

        tt = Timetable(('A', 'B'))
        periods = ('Green', 'Blue')
        tt["A"] = TimetableDay(periods)
        tt["B"] = TimetableDay(periods)
        tt["A"]["Green"] = TimetableActivity("English")
        tt["A"]["Blue"] = TimetableActivity("Math")
        tt["B"]["Green"] = TimetableActivity("Biology")
        tt["B"]["Blue"] = TimetableActivity("Geography")

        t, td = time, timedelta
        template1 = SchooldayTemplate()
        template1.add(SchooldayPeriod('Green', t(9, 0), td(minutes=90)))
        template1.add(SchooldayPeriod('Blue', t(11, 0), td(minutes=90)))
        template2 = SchooldayTemplate()
        template2.add(SchooldayPeriod('Green', t(9, 0), td(minutes=90)))
        template2.add(SchooldayPeriod('Blue', t(10, 30), td(minutes=90)))

        model = SequentialDaysTimetableModel(("A", "B"),
                                             {None: template1,
                                              calendar.FRIDAY: template2})
        schooldays = SchooldayModelStub()

        cal = model.createCalendar(schooldays, tt)
        verifyObject(ICalendar, cal)

        self.assertEqual(cal.daterange.first, date(2003, 11, 20))
        self.assertEqual(cal.daterange.last, date(2003, 11, 26))

        result = self.extractCalendarEvents(cal)

        expected = [{datetime(2003, 11, 20, 9, 0): "English",
                     datetime(2003, 11, 20, 11, 0): "Math"},
                    {datetime(2003, 11, 21, 9, 0): "Biology",
                     datetime(2003, 11, 21, 10, 30): "Geography"},
                    {}, {},
                    {datetime(2003, 11, 24, 9, 0): "English",
                     datetime(2003, 11, 24, 11, 0): "Math"},
                    {datetime(2003, 11, 25, 9, 0): "Biology",
                     datetime(2003, 11, 25, 11, 0): "Geography"},
                    {datetime(2003, 11, 26, 9, 0): "English",
                     datetime(2003, 11, 26, 11, 0): "Math"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))


class TestWeeklyTimetableModel(unittest.TestCase, BaseTestTimetableModel):

    def test(self):
        from schooltool.cal import WeeklyTimetableModel
        from schooltool.cal import SchooldayTemplate, SchooldayPeriod
        from schooltool.interfaces import ITimetableModel
        from schooltool.cal import Timetable, TimetableDay, TimetableActivity

        days = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
        tt = Timetable(days)
        periods = ('1', '2', '3', '4')
        for day_id in days:
            tt[day_id] = TimetableDay(periods)

        tt["Monday"]["1"] = TimetableActivity("English")
        tt["Monday"]["2"] = TimetableActivity("History")
        tt["Monday"]["3"] = TimetableActivity("Biology")
        tt["Monday"]["4"] = TimetableActivity("Physics")

        tt["Tuesday"]["1"] = TimetableActivity("Geography")
        tt["Tuesday"]["2"] = TimetableActivity("Math")
        tt["Tuesday"]["3"] = TimetableActivity("English")
        tt["Tuesday"]["4"] = TimetableActivity("Music")

        tt["Wednesday"]["1"] = TimetableActivity("English")
        tt["Wednesday"]["2"] = TimetableActivity("History")
        tt["Wednesday"]["3"] = TimetableActivity("Biology")
        tt["Wednesday"]["4"] = TimetableActivity("Physics")

        tt["Thursday"]["1"] = TimetableActivity("Chemistry")
        tt["Thursday"]["2"] = TimetableActivity("English")
        tt["Thursday"]["3"] = TimetableActivity("English")
        tt["Thursday"]["4"] = TimetableActivity("Math")

        tt["Friday"]["1"] = TimetableActivity("Geography")
        tt["Friday"]["2"] = TimetableActivity("Drawing")
        tt["Friday"]["3"] = TimetableActivity("History")
        tt["Friday"]["4"] = TimetableActivity("Math")

        t, td = time, timedelta
        template = SchooldayTemplate()
        template.add(SchooldayPeriod('1', t(9, 0), td(minutes=45)))
        template.add(SchooldayPeriod('2', t(9, 50), td(minutes=45)))
        template.add(SchooldayPeriod('3', t(10, 50), td(minutes=45)))
        template.add(SchooldayPeriod('4', t(12, 0), td(minutes=45)))

        model = WeeklyTimetableModel({None: template})
        verifyObject(ITimetableModel, model)

        cal = model.createCalendar(SchooldayModelStub(), tt)

        result = self.extractCalendarEvents(cal)

        expected = [
            {datetime(2003, 11, 20, 9, 0): "Chemistry",
             datetime(2003, 11, 20, 9, 50): "English",
             datetime(2003, 11, 20, 10, 50): "English",
             datetime(2003, 11, 20, 12, 00): "Math"},
            {datetime(2003, 11, 21, 9, 0): "Geography",
             datetime(2003, 11, 21, 9, 50): "Drawing",
             datetime(2003, 11, 21, 10, 50): "History",
             datetime(2003, 11, 21, 12, 00): "Math"},
            {}, {},
            {datetime(2003, 11, 24, 9, 0): "English",
             datetime(2003, 11, 24, 9, 50): "History",
             datetime(2003, 11, 24, 10, 50): "Biology",
             datetime(2003, 11, 24, 12, 00): "Physics"},
            {datetime(2003, 11, 25, 9, 0): "Geography",
             datetime(2003, 11, 25, 9, 50): "Math",
             datetime(2003, 11, 25, 10, 50): "English",
             datetime(2003, 11, 25, 12, 00): "Music"},
            {datetime(2003, 11, 26, 9, 0): "English",
             datetime(2003, 11, 26, 9, 50): "History",
             datetime(2003, 11, 26, 10, 50): "Biology",
             datetime(2003, 11, 26, 12, 00): "Physics"},
            ]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))


class TestDateRange(unittest.TestCase):

    def test(self):
        from schooltool.cal import DateRange
        from schooltool.interfaces import IDateRange

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


class TestCalendar(unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.cal import Calendar
        from schooltool.interfaces import ICalendar

        cal = Calendar(date(2003, 11, 25), date(2003, 11, 26))
        verifyObject(ICalendar, cal)

        self.assertRaises(ValueError, Calendar,
                          date(2003, 11, 26), date(2003, 11, 25))

    def test_iter(self):
        from schooltool.cal import Calendar
        from schooltool.cal import CalendarEvent
        from schooltool.interfaces import ICalendar

        cal = Calendar(date(2003, 11, 25), date(2003, 11, 26))
        self.assertEqual(list(cal), [])

        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")

        cal.addEvent(ev1)
        self.assertEqual(list(cal), [ev1])

    def test_byDate(self):
        from schooltool.cal import Calendar
        from schooltool.cal import CalendarEvent

        cal = Calendar(date(2003, 11, 25), date(2003, 11, 26))

        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")
        ev2 = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                            timedelta(minutes=10),
                            "Latin")
        ev3 = CalendarEvent(datetime(2003, 11, 26, 10, 0),
                            timedelta(minutes=10),
                            "German")
        cal.addEvent(ev1)
        cal.addEvent(ev2)
        cal.addEvent(ev3)

        self.assertEqual(list(cal.byDate(date(2003, 11, 26))), [ev3])

        # event end date within the period
        ev4 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(1),
                            "Solar eclipse")
        cal.addEvent(ev4)
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3, ev4])

        # calendar daterange is within the event period
        ev4.duration = timedelta(2)
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3, ev4])

        # only the event start date falls within the period
        ev4.dtstart = datetime(2003, 11, 26, 10, 0)
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3, ev4])

        # the event is after the period
        ev4.dtstart = datetime(2003, 11, 27, 10, 0)
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3])


class TestCalendarEvent(unittest.TestCase):

    def test(self):
        from schooltool.cal import CalendarEvent
        from schooltool.interfaces import ICalendarEvent

        ce = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                           timedelta(minutes=10),
                           "reality check")
        verifyObject(ICalendarEvent, ce)


def test_suite():
    import schooltool.cal
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayModel))
    suite.addTest(unittest.makeSuite(TestICalReader))
    suite.addTest(unittest.makeSuite(TestTimetable))
    suite.addTest(unittest.makeSuite(TestTimetableDay))
    suite.addTest(unittest.makeSuite(TestTimetableActivity))
    suite.addTest(unittest.makeSuite(TestTimetabling))
    suite.addTest(unittest.makeSuite(TestSchooldayPeriod))
    suite.addTest(unittest.makeSuite(TestSchooldayTemplate))
    suite.addTest(unittest.makeSuite(TestSequentialDaysTimetableModel))
    suite.addTest(unittest.makeSuite(TestWeeklyTimetableModel))
    suite.addTest(unittest.makeSuite(TestDateRange))
    suite.addTest(unittest.makeSuite(TestCalendar))
    suite.addTest(unittest.makeSuite(TestCalendarEvent))
    suite.addTest(DocTestSuite(schooltool.cal))
    return suite
