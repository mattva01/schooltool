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
from datetime import date, time, timedelta, datetime
from StringIO import StringIO
from zope.interface.verify import verifyObject
from zope.interface import implements
from schooltool.tests.helpers import diff, dedent
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

    def testReset(self):
        from schooltool.cal import SchooldayModel
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 15))
        cal.addWeekdays(1, 3, 5)

        new_first, new_last = date(2003, 8, 1), date(2003, 9, 30)
        cal.reset(new_first, new_last)

        self.assertEqual(cal.first, new_first)
        self.assertEqual(cal.last, new_last)
        for d in cal:
            self.assert_(not cal.isSchoolday(d))

        self.assertRaises(ValueError, cal.reset, new_last, new_first)

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


class TestVEvent(unittest.TestCase):

    def test_add(self):
        from schooltool.cal import VEvent
        vevent = VEvent()
        value, params = 'bar', {'VALUE': 'TEXT'}
        vevent.add('foo', value, params)
        self.assertEquals(vevent._props, {'FOO': (value, params)})
        value2 = 'guug'
        vevent.add('fie', value2)
        self.assertEquals(vevent._props, {'FOO': (value, params),
                                          'FIE': (value2, {})})

    def test_get(self):
        from schooltool.cal import VEvent
        vevent = VEvent()
        vevent.add('foo', 'bar', {})
        self.assertEquals(vevent.get('foo'), 'bar')
        self.assertEquals(vevent.get('Foo'), 'bar')
        self.assertEquals(vevent.get('baz'), None)
        self.assertEquals(vevent.get('baz', 'quux'), 'quux')

    def test_hasProp(self):
        from schooltool.cal import VEvent
        vevent = VEvent()
        vevent.add('foo', 'bar', {})
        self.assert_(vevent.hasProp('foo'))
        self.assert_(vevent.hasProp('Foo'))
        self.assert_(not vevent.hasProp('baz'))

    def test_getType(self):
        from schooltool.cal import VEvent
        vevent = VEvent()
        vevent.add('x-explicit', '', {'VALUE': 'INTEGER'})
        vevent.add('dtstart', 'implicit type', {})
        vevent.add('x-default', '', {})
        self.assertEquals(vevent.getType('x-explicit'), 'INTEGER')
        self.assertEquals(vevent.getType('dtstart'), 'DATE-TIME')
        self.assertEquals(vevent.getType('x-default'), 'TEXT')
        self.assertEquals(vevent.getType('X-Explicit'), 'INTEGER')
        self.assertEquals(vevent.getType('DtStart'), 'DATE-TIME')
        self.assertEquals(vevent.getType('X-Default'), 'TEXT')
        self.assertRaises(KeyError, vevent.getType, 'nonexistent')

    def test_getValue(self):
        from schooltool.cal import VEvent
        vevent = VEvent()

        vevent.add('foo', 'bar', {})
        self.assertEquals(vevent.getValue('foo'), 'bar')
        self.assertEquals(vevent.getValue('Foo'), 'bar')
        self.assertEquals(vevent.getValue('baz'), None)
        self.assertEquals(vevent.getValue('baz', 'quux'), 'quux')

        vevent.add('int-foo', '42', {'VALUE': 'INTEGER'})
        vevent.add('int-bad', 'xyzzy', {'VALUE': 'INTEGER'})
        self.assertEquals(vevent.getValue('int-foo'), 42)
        self.assertEquals(vevent.getValue('Int-Foo'), 42)
        self.assertRaises(ValueError, vevent.getValue, 'int-bad')

        vevent.add('date-foo', '20030405', {'VALUE': 'DATE'})
        vevent.add('date-bad1', '20030405T1234', {'VALUE': 'DATE'})
        vevent.add('date-bad2', '2003', {'VALUE': 'DATE'})
        vevent.add('date-bad3', '200301XX', {'VALUE': 'DATE'})
        self.assertEquals(vevent.getValue('date-Foo'), date(2003, 4, 5))
        self.assertRaises(ValueError, vevent.getValue, 'date-bad1')
        self.assertRaises(ValueError, vevent.getValue, 'date-bad2')
        self.assertRaises(ValueError, vevent.getValue, 'date-bad3')

        vevent.add('datetime-foo1', '20030405T060708', {'VALUE': 'DATE-TIME'})
        vevent.add('datetime-foo2', '20030405T060708Z', {'VALUE': 'DATE-TIME'})
        vevent.add('datetime-bad1', '20030405T010203444444',
                                                        {'VALUE': 'DATE-TIME'})
        vevent.add('datetime-bad2', '2003', {'VALUE': 'DATE-TIME'})
        self.assertEquals(vevent.getValue('datetime-foo1'),
                          datetime(2003, 4, 5, 6, 7, 8))
        self.assertEquals(vevent.getValue('Datetime-Foo2'),
                          datetime(2003, 4, 5, 6, 7, 8))
        self.assertRaises(ValueError, vevent.getValue, 'datetime-bad1')
        self.assertRaises(ValueError, vevent.getValue, 'datetime-bad2')

        vevent.add('dur-foo1', '+P11D', {'VALUE': 'DURATION'})
        vevent.add('dur-foo2', '-P2W', {'VALUE': 'DURATION'})
        vevent.add('dur-foo3', 'P1DT2H3M4S', {'VALUE': 'DURATION'})
        vevent.add('dur-foo4', 'PT2H', {'VALUE': 'DURATION'})
        vevent.add('dur-bad1', 'xyzzy', {'VALUE': 'DURATION'})
        self.assertEquals(vevent.getValue('dur-foo1'), timedelta(days=11))
        self.assertEquals(vevent.getValue('Dur-Foo2'), -timedelta(weeks=2))
        self.assertEquals(vevent.getValue('Dur-Foo3'),
                          timedelta(days=1, hours=2, minutes=3, seconds=4))
        self.assertEquals(vevent.getValue('DUR-FOO4'), timedelta(hours=2))
        self.assertRaises(ValueError, vevent.getValue, 'dur-bad1')

    def test_iterDates(self):
        from schooltool.cal import VEvent
        vevent = VEvent()
        vevent.all_day_event = True
        vevent.dtstart = date(2003, 1, 2)
        vevent.dtend = date(2003, 1, 4)
        self.assertEquals(list(vevent.iterDates()),
                    [date(2003, 1, 2), date(2003, 1, 3), date(2003, 1, 4)])

    def test_validate(self):
        from schooltool.cal import VEvent, ICalParseError

        # error cases
        vevent = VEvent()
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEvent()
        vevent.add('dtstart', 'xyzzy', {'VALUE': 'TEXT'})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010203T0000', {'VALUE': 'DATE-TIME'})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010203', {'VALUE': 'DATE'})
        vevent.add('duration', 'P1D', {})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('duration', 'two years', {'VALUE': 'TEXT'})
        self.assertRaises(ICalParseError, vevent.validate)

        # all-day events
        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.validate()
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.dtend, date(2001, 2, 3))
        self.assertEquals(vevent.duration, timedelta(days=1))

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010204', {'VALUE': 'DATE'})
        vevent.validate()
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.dtend, date(2001, 2, 4))
        self.assertEquals(vevent.duration, timedelta(days=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('duration', 'P2D')
        vevent.validate()
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.dtend, date(2001, 2, 4))
        self.assertEquals(vevent.duration, timedelta(days=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010201', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, vevent.validate)

        # non-all-day events
        vevent = VEvent()
        vevent.add('dtstart', '20010203T040506')
        vevent.validate()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 5, 6))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 3, 4, 5, 6))
        self.assertEquals(vevent.duration, timedelta(days=0))

        vevent = VEvent()
        vevent.add('dtstart', '20010203T040000')
        vevent.add('dtend', '20010204T050102')
        vevent.validate()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))
        self.assertEquals(vevent.duration, timedelta(days=1, hours=1,
                                                     minutes=1, seconds=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203T040000')
        vevent.add('duration', 'P1DT1H1M2S')
        vevent.validate()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))
        self.assertEquals(vevent.duration, timedelta(days=1, hours=1,
                                                     minutes=1, seconds=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203T010203')
        vevent.add('dtend', '20010203T010202')
        self.assertRaises(ICalParseError, vevent.validate)


class TestICalReader(unittest.TestCase):

    example_ical = dedent("""
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
        DTEND
         ;VALUE=DATE
         :20031226
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
         :20030501
        DTSTAMP
         :20020430T114937Z
        END:VEVENT
        BEGIN:VEVENT
        DTSTART;VALUE=DATE:20031225
        SUMMARY:Christmas again!
        END:VEVENT
        END:VCALENDAR
        """)

    def test_markNonSchooldays(self):
        from schooltool.cal import ICalReader, SchooldayModel
        from schooltool.cal import markNonSchooldays
        cal = SchooldayModel(date(2003, 9, 01), date(2004, 01, 01))
        file = StringIO(self.example_ical)
        reader = ICalReader(file)
        cal.addWeekdays(0, 1, 2, 3, 4)
        self.assert_(cal.isSchoolday(date(2003, 12, 24)))
        self.assert_(cal.isSchoolday(date(2003, 12, 25)))
        self.assert_(cal.isSchoolday(date(2003, 12, 26)))
        markNonSchooldays(reader, cal)
        self.assert_(cal.isSchoolday(date(2003, 12, 24)))
        self.assert_(not cal.isSchoolday(date(2003, 12, 25)))
        self.assert_(not cal.isSchoolday(date(2003, 12, 26)))

    def test_iterEvents(self):
        from schooltool.cal import ICalReader, ICalParseError
        file = StringIO(self.example_ical)
        reader = ICalReader(file)
        result = list(reader.iterEvents())
        self.assertEqual(len(result), 3)
        vevent = result[0]
        self.assertEqual(vevent.get('x-mozilla-recur-default-units'), 'weeks')
        self.assertEqual(vevent.get('dtstart'), '20031225')
        self.assertEqual(vevent.dtstart, date(2003, 12, 25))
        self.assertEqual(vevent.get('dtend'), '20031226')
        self.assertEqual(vevent.dtend, date(2003, 12, 26))
        vevent = result[1]
        self.assertEqual(vevent.get('dtstart'), '20030501')
        self.assertEqual(vevent.dtstart, date(2003, 05, 01))
        vevent = result[2]
        self.assertEqual(vevent.get('dtstart'), '20031225')
        self.assertEqual(vevent.dtstart, date(2003, 12, 25))

        reader = ICalReader(StringIO(dedent("""
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    BEGIN:VALARM
                    X-PROP:foo
                    END:VALARM
                    END:VEVENT
                    END:VCALENDAR
                    """)))
        result = list(reader.iterEvents())
        self.assertEquals(len(result), 1)
        vevent = result[0]
        self.assert_(vevent.hasProp('dtstart'))
        self.assert_(not vevent.hasProp('x-prop'))

        reader = ICalReader(StringIO(dedent("""
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    END:VCALENDAR
                    END:VEVENT
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""
                    BEGIN:VCALENDAR
                    END:VCALENDAR
                    X-PROP:foo
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""
                    BEGIN:VCALENDAR
                    END:VCALENDAR
                    BEGIN:VEVENT
                    END:VEVENT
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    END:VEVENT
                    END:VCALENDAR
                    END:UNIVERSE
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""
                    DTSTART;VALUE=DATE:20010203
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""
                    This is just plain text
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(""))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

    def test_iterRow(self):
        from schooltool.cal import ICalReader
        file = StringIO("key1\n"
                        " :value1\n"
                        "key2\n"
                        " ;VALUE=foo\n"
                        " :value2\n"
                        "key3;VALUE=bar:value3\n")
        reader = ICalReader(file)
        self.assertEqual(list(reader._iterRow()),
                         [('KEY1', 'value1', {}),
                          ('KEY2', 'value2', {'VALUE': 'FOO'}),
                          ('KEY3', 'value3', {'VALUE': 'BAR'})])

        file = StringIO("key1:value1\n"
                        "key2;VALUE=foo:value2\n"
                        "key3;VALUE=bar:value3\n")
        reader = ICalReader(file)
        self.assertEqual(list(reader._iterRow()),
                         [('KEY1', 'value1', {}),
                          ('KEY2', 'value2', {'VALUE': 'FOO'}),
                          ('KEY3', 'value3', {'VALUE': 'BAR'})])

        file = StringIO("key1:value:with:colons:in:it\n")
        reader = ICalReader(file)
        self.assertEqual(list(reader._iterRow()),
                         [('KEY1', 'value:with:colons:in:it', {})])

        reader = ICalReader(StringIO("ke\r\n y1\n\t:value\r\n  1 \r\n ."))
        self.assertEqual(list(reader._iterRow()),
                         [('KEY1', 'value 1 .', {})])

    def test_parseRow(self):
        from schooltool.cal import ICalReader, ICalParseError
        parseRow = ICalReader._parseRow
        self.assertEqual(parseRow("key:"), ("KEY", "", {}))
        self.assertEqual(parseRow("key:value"), ("KEY", "value", {}))
        self.assertEqual(parseRow("key:va:lu:e"), ("KEY", "va:lu:e", {}))
        self.assertRaises(ICalParseError, parseRow, "key but no value")
        self.assertRaises(ICalParseError, parseRow, ":value but no key")
        self.assertRaises(ICalParseError, parseRow, "bad name:")

        self.assertEqual(parseRow("key;param=:value"),
                         ("KEY", "value", {'PARAM': ''}))
        self.assertEqual(parseRow("key;param=pvalue:value"),
                         ("KEY", "value", {'PARAM': 'PVALUE'}))
        self.assertEqual(parseRow('key;param=pvalue;param2=value2:value'),
                         ("KEY", "value", {'PARAM': 'PVALUE',
                                           'PARAM2': 'VALUE2'}))
        self.assertEqual(parseRow('key;param="pvalue":value'),
                         ("KEY", "value", {'PARAM': 'pvalue'}))
        self.assertEqual(parseRow('key;param=pvalue;param2="value2":value'),
                         ("KEY", "value", {'PARAM': 'PVALUE',
                                           'PARAM2': 'value2'}))
        self.assertRaises(ICalParseError, parseRow, "k;:no param")
        self.assertRaises(ICalParseError, parseRow, "k;a?=b:bad param")
        self.assertRaises(ICalParseError, parseRow, "k;a=\":bad param")
        self.assertRaises(ICalParseError, parseRow, "k;a=\001:bad char")
        self.assertEqual(parseRow("key;param=a,b,c:value"),
                         ("KEY", "value", {'PARAM': ['A', 'B', 'C']}))
        self.assertEqual(parseRow('key;param=a,"b,c",d:value'),
                         ("KEY", "value", {'PARAM': ['A', 'b,c', 'D']}))


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
        from schooltool.interfaces import ITimetableActivity

        periods = ('1', '2', '3', '4', '5')
        td = TimetableDay(periods)
        self.assertEqual(td.keys(), [])
        class ActivityStub:
            implements(ITimetableActivity)
        td["5"] = ActivityStub()
        td["1"] = ActivityStub()
        td["3"] = ActivityStub()
        td["2"] = ActivityStub()
        self.assertEqual(td.keys(), ['1', '2', '3', '5'])

    def test_getitem_setitem_items_delitem(self):
        from schooltool.cal import TimetableDay
        from schooltool.interfaces import ITimetableActivity

        periods = ('1', '2', '3', '4')
        td = TimetableDay(periods)
        self.assertRaises(KeyError, td.__getitem__, "Mo")
        self.assertRaises(KeyError, td.__getitem__, "1")

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
        self.assertRaises(KeyError, td.__getitem__, "2")


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
        from schooltool.cal import SequentialDaysTimetableModel
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
        # skip! tt["Friday"]["3"] = TimetableActivity("History")
        tt["Friday"]["4"] = TimetableActivity("Math")

        t, td = time, timedelta
        template = SchooldayTemplate()
        template.add(SchooldayPeriod('1', t(9, 0), td(minutes=45)))
        template.add(SchooldayPeriod('2', t(9, 50), td(minutes=45)))
        template.add(SchooldayPeriod('3', t(10, 50), td(minutes=45)))
        template.add(SchooldayPeriod('4', t(12, 0), td(minutes=45)))

        model = WeeklyTimetableModel(day_templates={None: template})
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
             # skip! datetime(2003, 11, 21, 10, 50): "History",
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
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDateRange))
    suite.addTest(unittest.makeSuite(TestSchooldayModel))
    suite.addTest(unittest.makeSuite(TestVEvent))
    suite.addTest(unittest.makeSuite(TestICalReader))
    suite.addTest(unittest.makeSuite(TestTimetable))
    suite.addTest(unittest.makeSuite(TestTimetableDay))
    suite.addTest(unittest.makeSuite(TestTimetableActivity))
    suite.addTest(unittest.makeSuite(TestTimetabling))
    suite.addTest(unittest.makeSuite(TestSchooldayPeriod))
    suite.addTest(unittest.makeSuite(TestSchooldayTemplate))
    suite.addTest(unittest.makeSuite(TestSequentialDaysTimetableModel))
    suite.addTest(unittest.makeSuite(TestWeeklyTimetableModel))
    suite.addTest(unittest.makeSuite(TestCalendar))
    suite.addTest(unittest.makeSuite(TestCalendarEvent))
    return suite
