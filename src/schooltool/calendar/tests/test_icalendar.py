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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for schooltool.calendar.icalendar
"""

import unittest
import doctest
import difflib
import time
import os
from pprint import pformat, pprint
from textwrap import dedent
from datetime import date, timedelta, datetime
from StringIO import StringIO


def diff(old, new, oldlabel="expected output", newlabel="actual output"):
    """Display a unified diff between old text and new text."""
    old = old.splitlines()
    new = new.splitlines()

    diff = ['--- %s' % oldlabel, '+++ %s' % newlabel]

    def dump(tag, x, lo, hi):
        for i in xrange(lo, hi):
            diff.append(tag + x[i])

    differ = difflib.SequenceMatcher(a=old, b=new)
    for tag, alo, ahi, blo, bhi in differ.get_opcodes():
        if tag == 'replace':
            dump('-', old, alo, ahi)
            dump('+', new, blo, bhi)
        elif tag == 'delete':
            dump('-', old, alo, ahi)
        elif tag == 'insert':
            dump('+', new, blo, bhi)
        elif tag == 'equal':
            dump(' ', old, alo, ahi)
        else:
            raise AssertionError('unknown tag %r' % tag)
    return "\n".join(diff)


class TimezoneTestMixin:
    """A mixin for tests that fiddle with timezones."""

    def setUp(self):
        self.have_tzset = hasattr(time, 'tzset')
        self.touched_tz = False
        self.old_tz = os.getenv('TZ')

    def tearDown(self):
        if self.touched_tz:
            self.setTZ(self.old_tz)

    def setTZ(self, tz):
        self.touched_tz = True
        if tz is None:
            os.unsetenv('TZ')
        else:
            os.putenv('TZ', tz)
        time.tzset()


class TestParseDateTime(TimezoneTestMixin, unittest.TestCase):

    def test_timezones(self):
        # The simple tests are in the doctest of parse_date_time.
        from schooltool.calendar.icalendar import parse_date_time
        from pytz import utc

        if not self.have_tzset:
            return # Do not run this test on Windows

        self.setTZ('UTC')
        dt = parse_date_time('20041029T125031Z')
        self.assertEquals(dt, datetime(2004, 10, 29, 12, 50, 31, tzinfo=utc))

        self.setTZ('EET-2EEST')
        dt = parse_date_time('20041029T095031Z') # daylight savings
        self.assertEquals(dt, datetime(2004, 10, 29, 9, 50, 31, tzinfo=utc))
        dt = parse_date_time('20041129T095031Z') # no daylight savings
        self.assertEquals(dt, datetime(2004, 11, 29, 9, 50, 31, tzinfo=utc))


class TestPeriod(unittest.TestCase):

    def test(self):
        from schooltool.calendar.icalendar import Period
        dt1 = datetime(2001, 2, 3, 14, 30, 5)
        dt2 = datetime(2001, 2, 3, 16, 35, 20)
        td = dt2 - dt1
        p1 = Period(dt1, dt2)
        self.assertEquals(p1.start, dt1)
        self.assertEquals(p1.end, dt2)

        p2 = Period(dt1, td)
        self.assertEquals(p2.start, dt1)
        self.assertEquals(p2.end, dt2)

        self.assertEquals(p1, p2)

        p = Period(dt1, timedelta(0))
        self.assertEquals(p.start, dt1)
        self.assertEquals(p.end, dt1)

        self.assertRaises(ValueError, Period, dt2, dt1)
        self.assertRaises(ValueError, Period, dt1, -td)

    def test_overlap(self):
        from schooltool.calendar.icalendar import Period
        p1 = Period(datetime(2004, 1, 1, 12, 0), timedelta(hours=1))
        p2 = Period(datetime(2004, 1, 1, 11, 30), timedelta(hours=1))
        p3 = Period(datetime(2004, 1, 1, 12, 30), timedelta(hours=1))
        p4 = Period(datetime(2004, 1, 1, 11, 0), timedelta(hours=3))

        self.assert_(p1.overlaps(p2))
        self.assert_(p2.overlaps(p1))

        self.assert_(p1.overlaps(p3))
        self.assert_(p3.overlaps(p1))

        self.assert_(not p2.overlaps(p3))
        self.assert_(not p3.overlaps(p2))

        self.assert_(p1.overlaps(p4))
        self.assert_(p4.overlaps(p1))

        self.assert_(p1.overlaps(p1))

    def test_cmp(self):
        from schooltool.calendar.icalendar import Period
        p1 = Period(datetime(2004, 1, 1, 12, 0), timedelta(hours=1))
        p2 = Period(datetime(2004, 1, 1, 12, 0), timedelta(hours=1))
        p3 = Period(datetime(2004, 1, 1, 12, 0), timedelta(hours=4))

        self.assert_(p1 == p2)
        self.assert_(p1 != p3)
        self.assertRaises(NotImplementedError, p1.__cmp__, "NOT A PERIOD")


class TestVEvent(unittest.TestCase):

    def test_add(self):
        from schooltool.calendar.icalendar import VEventParser, ICalParseError
        vevent = VEventParser()
        value, params = 'bar', {'VALUE': 'TEXT'}
        vevent.add('foo', value, params)
        self.assertEquals(vevent._props, {'FOO': [(value, params)]})
        value2 = 'guug'
        vevent.add('fie', value2)
        self.assertEquals(vevent._props, {'FOO': [(value, params)],
                                          'FIE': [(value2, {})]})
        vevent.add('fie', value, params)
        self.assertEquals(vevent._props, {'FOO': [(value, params)],
                                          'FIE': [(value2, {}),
                                                  (value, params)]})

        # adding a singleton property twice
        vevent.add('uid', '1')
        self.assertRaises(ICalParseError, vevent.add, 'uid', '2')

    def test_hasProp(self):
        from schooltool.calendar.icalendar import VEventParser
        vevent = VEventParser()
        vevent.add('foo', 'bar', {})
        self.assert_(vevent.hasProp('foo'))
        self.assert_(vevent.hasProp('Foo'))
        self.assert_(not vevent.hasProp('baz'))

    def test__getType(self):
        from schooltool.calendar.icalendar import VEventParser
        vevent = VEventParser()
        vevent.add('x-explicit', '', {'VALUE': 'INTEGER'})
        vevent.add('dtstart', 'implicit type', {})
        vevent.add('x-default', '', {})
        self.assertEquals(vevent._getType('x-explicit'), 'INTEGER')
        self.assertEquals(vevent._getType('dtstart'), 'DATE-TIME')
        self.assertEquals(vevent._getType('x-default'), 'TEXT')
        self.assertEquals(vevent._getType('X-Explicit'), 'INTEGER')
        self.assertEquals(vevent._getType('DtStart'), 'DATE-TIME')
        self.assertEquals(vevent._getType('X-Default'), 'TEXT')
        self.assertRaises(KeyError, vevent._getType, 'nonexistent')

    def test_getOne(self):
        from schooltool.calendar.icalendar import VEventParser
        vevent = VEventParser()

        vevent.add('foo', 'bar', {})
        self.assertEquals(vevent.getOne('foo'), 'bar')
        self.assertEquals(vevent.getOne('Foo'), 'bar')
        self.assertEquals(vevent.getOne('baz'), None)
        self.assertEquals(vevent.getOne('baz', 'quux'), 'quux')
        self.assertEquals(vevent.getOne('dtstart', 'quux'), 'quux')

        vevent.add('int-foo', '42', {'VALUE': 'INTEGER'})
        vevent.add('int-bad', 'xyzzy', {'VALUE': 'INTEGER'})
        self.assertEquals(vevent.getOne('int-foo'), 42)
        self.assertEquals(vevent.getOne('Int-Foo'), 42)
        self.assertRaises(ValueError, vevent.getOne, 'int-bad')

        vevent.add('date-foo', '20030405', {'VALUE': 'DATE'})
        vevent.add('date-bad1', '20030405T1234', {'VALUE': 'DATE'})
        vevent.add('date-bad2', '2003', {'VALUE': 'DATE'})
        vevent.add('date-bad3', '200301XX', {'VALUE': 'DATE'})
        self.assertEquals(vevent.getOne('date-Foo'), date(2003, 4, 5))
        self.assertRaises(ValueError, vevent.getOne, 'date-bad1')
        self.assertRaises(ValueError, vevent.getOne, 'date-bad2')
        self.assertRaises(ValueError, vevent.getOne, 'date-bad3')

        vevent.add('datetime-foo1', '20030405T060708', {'VALUE': 'DATE-TIME'})
        vevent.add('datetime-foo2', '20030405T060708', {'VALUE': 'DATE-TIME'})
        vevent.add('datetime-bad1', '20030405T010203444444',
                                                        {'VALUE': 'DATE-TIME'})
        vevent.add('datetime-bad2', '2003', {'VALUE': 'DATE-TIME'})
        self.assertEquals(vevent.getOne('datetime-foo1'),
                          datetime(2003, 4, 5, 6, 7, 8))
        self.assertEquals(vevent.getOne('Datetime-Foo2'),
                          datetime(2003, 4, 5, 6, 7, 8))
        self.assertRaises(ValueError, vevent.getOne, 'datetime-bad1')
        self.assertRaises(ValueError, vevent.getOne, 'datetime-bad2')

        vevent.add('dur-foo1', '+P11D', {'VALUE': 'DURATION'})
        vevent.add('dur-foo2', '-P2W', {'VALUE': 'DURATION'})
        vevent.add('dur-foo3', 'P1DT2H3M4S', {'VALUE': 'DURATION'})
        vevent.add('dur-foo4', 'PT2H', {'VALUE': 'DURATION'})
        vevent.add('dur-bad1', 'xyzzy', {'VALUE': 'DURATION'})
        self.assertEquals(vevent.getOne('dur-foo1'), timedelta(days=11))
        self.assertEquals(vevent.getOne('Dur-Foo2'), -timedelta(weeks=2))
        self.assertEquals(vevent.getOne('Dur-Foo3'),
                          timedelta(days=1, hours=2, minutes=3, seconds=4))
        self.assertEquals(vevent.getOne('DUR-FOO4'), timedelta(hours=2))
        self.assertRaises(ValueError, vevent.getOne, 'dur-bad1')

        vevent.add('unknown', 'magic', {'VALUE': 'UNKNOWN-TYPE'})
        self.assertEquals(vevent.getOne('unknown'), 'magic')

    def test_validate_error_cases(self):
        from schooltool.calendar.icalendar import VEventParser, ICalParseError

        vevent = VEventParser()
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEventParser()
        vevent.add('dtstart', 'xyzzy', {'VALUE': 'TEXT'})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEventParser()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010203T0000', {'VALUE': 'DATE-TIME'})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEventParser()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010203', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEventParser()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, vevent.validate)

    def test_validate_all_day_events(self):
        from schooltool.calendar.icalendar import VEventParser, ICalParseError

        parser = VEventParser()
        parser.add('summary', 'An event', {})
        parser.add('uid', 'unique', {})
        parser.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent = parser.parse()
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.summary, 'An event')
        self.assertEquals(vevent.uid, 'unique')
        self.assertEquals(vevent.dtend, date(2001, 2, 4))

        parser = VEventParser()
        parser.add('summary', 'An\\nevent\\; with backslashes', {})
        parser.add('uid', 'unique2', {})
        parser.add('dtstart', '20010203', {'VALUE': 'DATE'})
        parser.add('dtend', '20010205', {'VALUE': 'DATE'})
        vevent = parser.parse()
        self.assertEquals(vevent.summary, 'An\nevent; with backslashes')
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.uid, 'unique2')
        self.assertEquals(vevent.dtend, date(2001, 2, 5))

        parser = VEventParser()
        parser.add('dtstart', '20010203', {'VALUE': 'DATE'})
        parser.add('uid', 'unique3', {})
        parser.add('duration', 'P2D')
        vevent = parser.parse()
        self.assertEquals(vevent.summary, None)
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.uid, 'unique3')
        self.assertEquals(vevent.dtend, date(2001, 2, 5))

        parser = VEventParser()
        parser.add('dtstart', '20010203', {'VALUE': 'DATE'})
        parser.add('uid', 'unique4', {})
        parser.add('dtend', '20010201', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, parser.parse)

        parser = VEventParser()
        parser.add('dtstart', '20010203', {'VALUE': 'DATE'})
        parser.add('uid', 'unique5', {})
        parser.add('dtend', '20010203', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, parser.parse)

    def test_validate_not_all_day_events(self):
        from schooltool.calendar.icalendar import VEventParser, ICalParseError

        parser = VEventParser()
        parser.add('dtstart', '20010203T040506')
        parser.add('uid', 'unique', {})
        vevent = parser.parse()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 5, 6))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 3, 4, 5, 6))
        self.assertEquals(vevent.rdates, [])

        parser = VEventParser()
        parser.add('dtstart', '20010203T040000')
        parser.add('uid', 'unique', {})
        parser.add('dtend', '20010204T050102')
        vevent = parser.parse()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))

        parser = VEventParser()
        parser.add('dtstart', '20010203T040000')
        parser.add('uid', 'unique', {})
        parser.add('duration', 'P1DT1H1M2S')
        vevent = parser.parse()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))

        parser = VEventParser()
        parser.add('dtstart', '20010203T010203')
        parser.add('uid', 'unique', {})
        parser.add('rdate', '20010205T040506')
        parser.add('exdate', '20010206T040506')
        vevent = parser.parse()
        self.assertEquals(vevent.rdates, [datetime(2001, 2, 5, 4, 5, 6)])
        self.assertEquals(vevent.exdates, [datetime(2001, 2, 6, 4, 5, 6)])

        parser = VEventParser()
        parser.add('dtstart', '20010203T010203')
        parser.add('uid', 'unique', {})
        parser.add('exdate', '20010206,20020307', {'VALUE': 'DATE'})
        parser.add('rrule', 'FREQ=DAILY')
        vevent = parser.parse()
        self.assertEquals(vevent.exdates, [date(2001, 2, 6), date(2002, 3, 7)])

        parser = VEventParser()
        parser.add('dtstart', '20010203T010203')
        parser.add('uid', 'unique', {})
        parser.add('dtend', '20010203T010202')
        self.assertRaises(ICalParseError, parser.parse)

    def test_timezones(self):
        from schooltool.calendar.icalendar import VEventParser

        parser = VEventParser()
        parser.add('dtstart', '20010203T040000', params={'TZID': 'Vilnius'})
        parser.add('uid', 'unique', {})
        parser.add('dtend', '20010204T050102', params={'TZID': 'Kaunas'})
        vevent = parser.parse()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtstart_tzid, 'Vilnius')
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))
        self.assertEquals(vevent.dtend_tzid, 'Kaunas')

        parser = VEventParser()
        parser.add('dtstart', '20010203T040000', params={'TZID': 'Vilnius'})
        parser.add('uid', 'unique', {})
        parser.add('duration', 'P1DT1H1M2S')
        vevent = parser.parse()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtstart_tzid, 'Vilnius')
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))
        self.assertEquals(vevent.dtend_tzid, 'Vilnius')

    def test_validate_location(self):
        from schooltool.calendar.icalendar import VEventParser
        parser = VEventParser()
        parser.add('dtstart', '20010203T040506')
        parser.add('uid', 'unique5', {})
        parser.add('location', 'Somewhere')
        vevent = parser.parse()
        self.assertEquals(vevent.location, 'Somewhere')

    def test_validate_description(self):
        from schooltool.calendar.icalendar import VEventParser
        parser = VEventParser()
        parser.add('dtstart', '20010203T040506')
        parser.add('uid', 'unique5', {})
        parser.add('description', 'Some long text')
        vevent = parser.parse()
        self.assertEquals(vevent.description, 'Some long text')

    def test_validate_rrule(self):
        from schooltool.calendar.icalendar import VEventParser
        parser = VEventParser()
        parser.add('dtstart', '20010203T040506')
        parser.add('uid', 'unique5', {})
        parser.add('location', 'Somewhere')
        parser.add('rrule', 'FREQ=DAILY;COUNT=3')
        vevent = parser.parse()

        self.assertEquals(vevent.rrule.interval, 1)
        self.assertEquals(vevent.rrule.count, 3)
        self.assertEquals(vevent.rrule.until, None)
        self.assertEquals(vevent.rrule.exceptions, ())

    def test_validate_rrule_exceptions(self):
        from schooltool.calendar.icalendar import VEventParser
        parser = VEventParser()
        parser.add('dtstart', '20010203T040506')
        parser.add('uid', 'unique5', {})
        parser.add('location', 'Somewhere')
        parser.add('rrule', 'FREQ=MONTHLY;BYDAY=3MO')
        parser.add('exdate', '19960402T010000,19960404T010000')
        parser.add('exdate', '19960406T010000,19960408T010000')
        vevent = parser.parse()

        self.assertEquals(vevent.rrule.interval, 1)
        self.assertEquals(vevent.rrule.count, None)
        self.assertEquals(vevent.rrule.until, None)
        self.assertEquals(vevent.rrule.monthly, 'weekday')
        self.assertEquals(vevent.rrule.exceptions,
                          (date(1996, 4, 2), date(1996, 4, 4),
                           date(1996, 4, 6), date(1996, 4, 8)))
        self.assert_(not isinstance(vevent.rrule.exceptions[0], datetime))

    def test_extractListOfDates(self):
        from schooltool.calendar.icalendar import VEventParser, Period, ICalParseError

        vevent = VEventParser()
        vevent.add('rdate', '20010205T040506')
        vevent.add('rdate', '20010206T040506,20010207T000000')
        vevent.add('rdate', '20010208', {'VALUE': 'DATE'})
        vevent.add('rdate', '20010209T000000/20010210T000000',
                   {'VALUE': 'PERIOD'})
        rdates = vevent._extractListOfDates('RDATE', vevent.rdate_types, False)
        expected = [datetime(2001, 2, 5, 4, 5, 6),
                    datetime(2001, 2, 6, 4, 5, 6),
                    datetime(2001, 2, 7, 0, 0, 0),
                    date(2001, 2, 8),
                    Period(datetime(2001, 2, 9), datetime(2001, 2, 10)),
                   ]
        self.assertEqual(expected, rdates,
                         diff(pformat(expected), pformat(rdates)))

        vevent = VEventParser()
        vevent.add('rdate', '20010205T040506', {'VALUE': 'TEXT'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'RDATE',
                                          vevent.rdate_types, False)

        vevent = VEventParser()
        vevent.add('exdate', '20010205T040506/P1D', {'VALUE': 'PERIOD'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'EXDATE',
                                          vevent.exdate_types, False)

        vevent = VEventParser()
        vevent.add('rdate', '20010208', {'VALUE': 'DATE'})
        rdates = vevent._extractListOfDates('RDATE', vevent.rdate_types, True)
        expected = [date(2001, 2, 8)]
        self.assertEqual(expected, rdates,
                         diff(pformat(expected), pformat(rdates)))

        vevent = VEventParser()
        vevent.add('rdate', '20010205T040506', {'VALUE': 'DATE-TIME'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'RDATE',
                                          vevent.rdate_types, True)

        vevent = VEventParser()
        vevent.add('rdate', '20010209T000000/20010210T000000',
                   {'VALUE': 'PERIOD'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'RDATE',
                                          vevent.rdate_types, True)


class TestReadIcalendar(unittest.TestCase):

    example_ical = dedent("""\
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
        UID
         :wh4t3v3r
        DTSTART;VALUE=DATE:20031225
        SUMMARY:Christmas again!
        END:VEVENT

        END:VCALENDAR
        """)

    ical_with_timezones = dedent("""\
        BEGIN:VCALENDAR
        VERSION:2.0
        X-WR-CALNAME:testas
        PRODID:-//Apple Computer\, Inc//iCal 1.5//EN
        X-WR-RELCALID:42A41871-B382-11DA-BA4E-000A95CA5872
        X-WR-TIMEZONE:Europe/Helsinki
        CALSCALE:GREGORIAN
        METHOD:PUBLISH
        BEGIN:VTIMEZONE
        TZID:Europe/Berlin
        LAST-MODIFIED:20060314T174500Z
        BEGIN:STANDARD
        DTSTART:20051030T010000
        TZOFFSETTO:+0100
        TZOFFSETFROM:+0000
        TZNAME:CET
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:20060326T020000
        TZOFFSETTO:+0200
        TZOFFSETFROM:+0100
        TZNAME:CEST
        END:DAYLIGHT
        END:VTIMEZONE
        BEGIN:VTIMEZONE
        TZID:Asia/Shanghai
        LAST-MODIFIED:20060314T174500Z
        BEGIN:STANDARD
        DTSTART:19321213T204552
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0000
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19400603T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19401001T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19410316T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19411001T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19860504T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19860914T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19870412T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19870913T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19880410T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19880911T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19890416T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19890917T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19900415T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19900916T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:19910414T000000
        TZOFFSETTO:+0900
        TZOFFSETFROM:+0800
        TZNAME:CDT
        END:DAYLIGHT
        BEGIN:STANDARD
        DTSTART:19910915T000000
        TZOFFSETTO:+0800
        TZOFFSETFROM:+0900
        TZNAME:CST
        END:STANDARD
        END:VTIMEZONE
        BEGIN:VTIMEZONE
        TZID:Europe/Helsinki
        LAST-MODIFIED:20060314T174500Z
        BEGIN:STANDARD
        DTSTART:20051030T010000
        TZOFFSETTO:+0200
        TZOFFSETFROM:+0000
        TZNAME:EET
        END:STANDARD
        BEGIN:DAYLIGHT
        DTSTART:20060326T040000
        TZOFFSETTO:+0300
        TZOFFSETFROM:+0200
        TZNAME:EEST
        END:DAYLIGHT
        END:VTIMEZONE
        BEGIN:VEVENT
        DTSTART;TZID=Europe/Helsinki:20060307T200000
        SUMMARY:Europe/helsinki
        UID:42A40DBE-B382-11DA-BA4E-000A95CA5872
        SEQUENCE:1
        DTSTAMP:20060314T174340Z
        DURATION:PT1H
        END:VEVENT
        BEGIN:VEVENT
        DTSTART;TZID=Asia/Shanghai:20060308T200000
        SUMMARY:Asia/Shanghai
        UID:42A411C1-B382-11DA-BA4E-000A95CA5872
        SEQUENCE:2
        DTSTAMP:20060314T174418Z
        DURATION:PT1H
        END:VEVENT
        BEGIN:VEVENT
        DTSTART;TZID=Europe/Berlin:20060309T200000
        SUMMARY:Europe/Berlin
        UID:42A4138F-B382-11DA-BA4E-000A95CA5872
        SEQUENCE:2
        DTSTAMP:20060314T174433Z
        DURATION:PT1H
        END:VEVENT
        END:VCALENDAR
        """)

    def doctest_error_handling(self):
        r"""Test for read_icalendar error handling.

        Let's try parsing some invalid icalendar files:

            >>> from schooltool.calendar.icalendar import read_icalendar

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             DTSTART;VALUE=DATE:20010203
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: VEVENT must have a UID property

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             UID:hello
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: VEVENT must have a DTSTART property

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             UID:hello
            ...             DTSTART;VALUE=DATUM:20010203T101516
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: DTSTART property should have a DATE or DATE-TIME value

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             UID:hello
            ...             DTSTART;VALUE=DATE-TIME:20010203T101516
            ...             DTEND;VALUE=DATE:20010203
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: DTEND property should have the same type as DTSTART

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             UID:hello
            ...             DTSTART;VALUE=DATE:20010201
            ...             DURATION;VALUE=DAYS:P1DT1H1M2S
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: DURATION property should have type DURATION

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             DTSTART;VALUE=DATE:20010203
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Mismatched BEGIN/END

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             DTSTART;VALUE=DATE:20010203
            ...             END:VCALENDAR
            ...             END:VEVENT
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Mismatched BEGIN/END


            >>> file = StringIO(dedent('''\
            ...             BEGIN:VEVENT
            ...             END:VEVENT
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: This is not iCalendar

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             END:VCALENDAR
            ...             X-PROP:foo
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Text outside VCALENDAR component

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             END:VCALENDAR
            ...             BEGIN:VEVENT
            ...             END:VEVENT
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Text outside VCALENDAR component

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             DTSTART;VALUE=DATE:20010203
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             END:UNIVERSE
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Mismatched BEGIN/END

            >>> file = StringIO(dedent('''\
            ...             DTSTART;VALUE=DATE:20010203
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Text outside VCALENDAR component

            >>> file = StringIO(dedent('''\
            ...             This is just plain text
            ...             '''))
            >>> list(read_icalendar(file))
            Traceback (most recent call last):
            ...
            ICalParseError: Expected ':' in line:
            This is just plain text

        If you pass both DTEND and DURATION, no errors are raised:

            >>> file = StringIO(dedent('''\
            ...             BEGIN:VCALENDAR
            ...             BEGIN:VEVENT
            ...             UID:hello
            ...             DTSTART;VALUE=DATE:20010201
            ...             DTEND;VALUE=DATE:20010203
            ...             DURATION:P1D
            ...             END:VEVENT
            ...             END:VCALENDAR
            ...             '''))
            >>> event = list(read_icalendar(file))[0]

        The DURATION is used, while DTEND gets ignored:

            >>> event.duration
            datetime.timedelta(1)

        """

    def test_read_icalendar_with_timezones(self):
        from schooltool.calendar.icalendar import read_icalendar
        from pytz import utc

        file = StringIO(self.ical_with_timezones)
        result = list(read_icalendar(file))
        self.assertEqual(len(result), 3)
        event = result[0]

        self.assertEqual(event.dtstart, datetime(2006, 3, 7, 18, 0, tzinfo=utc))

        event = result[1]
        self.assertEqual(event.dtstart, datetime(2006, 3, 8, 12, 0, tzinfo=utc))

        event = result[2]
        self.assertEqual(event.dtstart, datetime(2006, 3, 9, 19, 0, tzinfo=utc))

    def test_read_icalendar(self):
        from schooltool.calendar.icalendar import read_icalendar
        from pytz import utc
        file = StringIO(self.example_ical)
        result = list(read_icalendar(file))
        self.assertEqual(len(result), 3)
        event = result[0]


        self.assertEqual(event.dtstart, datetime(2003, 12, 25, 0, 0, tzinfo=utc))
        self.assertEqual(event.duration, timedelta(days=1))
        event = result[1]
        self.assertEqual(event.dtstart, datetime(2003, 5, 1, 0, 0, tzinfo=utc))
        event = result[2]
        self.assertEqual(event.duration, timedelta(days=1))

        result = list(read_icalendar(StringIO(dedent("""\
                    BEGIN:VCALENDAR

                    BEGIN:VEVENT
                    UID:hello
                    DTSTART;VALUE=DATE:20010203
                    BEGIN:VALARM
                    X-PROP:foo
                    END:VALARM
                    END:VEVENT

                    END:VCALENDAR
                    """))))
        self.assertEquals(len(result), 1)
        event = result[0]
        self.assertEquals(event.unique_id, 'hello')
        self.assert_(event.dtstart)

        file = StringIO("")
        self.assertEquals(list(read_icalendar(file)), [])


def doctest_read_icalendar_floating():
    r"""Tests for reading of events with floating time.

        >>> from schooltool.calendar.icalendar import read_icalendar
        >>> calendar = dedent('''\
        ...     BEGIN:VCALENDAR
        ...     BEGIN:VEVENT
        ...     UID:hello
        ...     DTSTART;VALUE=DATE-TIME:20010203T101516
        ...     BEGIN:VALARM
        ...     X-PROP:foo
        ...     END:VALARM
        ...     END:VEVENT
        ...
        ...     END:VCALENDAR''')

    If no fallback_tz is passed, floating time events are converted to
    UTC:

        >>> event = list(read_icalendar(calendar))[0]
        >>> event.dtstart
        datetime.datetime(2001, 2, 3, 10, 15, 16, tzinfo=<UTC>)

    But if we pass a fallback_tz it should be used:

        >>> import pytz
        >>> tzinfo = pytz.timezone('Europe/Vilnius')
        >>> event = list(read_icalendar(calendar, fallback_tz=tzinfo))[0]
        >>> event.dtstart
        datetime.datetime(2001, 2, 3, 8, 15, 16, tzinfo=<UTC>)

    """


def doctest_read_icalendar_unrecognized_timezone():
    r"""Tests for reading of events with unrecognized timezone.

    If event has a timezone we can't recognize set:

        >>> from schooltool.calendar.icalendar import read_icalendar
        >>> calendar = dedent('''\
        ...     BEGIN:VCALENDAR
        ...
        ...     BEGIN:VTIMEZONE
        ...     TZID:Yurop/Berlin
        ...     BEGIN:STANDARD
        ...     TZNAME:YNAME
        ...     END:STANDARD
        ...     END:VTIMEZONE
        ...
        ...     BEGIN:VEVENT
        ...     UID:some-random-uid@example.com
        ...     DTSTART;TZID=Yurop/Berlin:20050226T160000
        ...     DURATION:PT6H
        ...     DTSTAMP:20050203T150000
        ...     END:VEVENT
        ...
        ...     END:VCALENDAR''')

    they are treated as if they were happening in UTC:

        >>> event = list(read_icalendar(calendar))[0]
        >>> event.dtstart
        datetime.datetime(2005, 2, 26, 16, 0, tzinfo=<UTC>)

    But if we pass a fallback_tz it should be used:

        >>> import pytz
        >>> tzinfo = pytz.timezone('Europe/Vilnius')
        >>> event = list(read_icalendar(calendar, fallback_tz=tzinfo))[0]
        >>> event.dtstart
        datetime.datetime(2005, 2, 26, 14, 0, tzinfo=<UTC>)

    """


def doctest_read_icalendar_allday_dtend():
    r"""Tests for reading of allday events with DTEND.

    Duration of all-day events should get properly calculated:

        >>> from schooltool.calendar.icalendar import read_icalendar
        >>> calendar = dedent('''\
        ...     BEGIN:VCALENDAR
        ...
        ...     BEGIN:VEVENT
        ...     UID:some-random-uid@example.com
        ...     DTSTART;VALUE=DATE:20050226
        ...     DTEND;VALUE=DATE:20050228
        ...     DTSTAMP:20050203T150000
        ...     END:VEVENT
        ...
        ...     END:VCALENDAR''')

        >>> event = list(read_icalendar(calendar))[0]
        >>> event.dtstart
        datetime.datetime(2005, 2, 26, 0, 0, tzinfo=<UTC>)
        >>> event.duration
        datetime.timedelta(2)

    """


class TestRowParser(unittest.TestCase):

    def test_parse(self):
        from schooltool.calendar.icalendar import RowParser
        file = StringIO("key1\n"
                        " :value1\n"
                        " \n"
                        "key2\n"
                        " ;VALUE=foo\n"
                        " :value2\n"
                        "key3;VALUE=bar:value3\n")
        self.assertEqual(list(RowParser.parse(file)),
                         [('KEY1', 'value1', {}),
                          ('KEY2', 'value2', {'VALUE': 'FOO'}),
                          ('KEY3', 'value3', {'VALUE': 'BAR'})])

        file = StringIO("key1:value1\n"
                        "key2;VALUE=foo:value2\n"
                        "key3;VALUE=bar:value3\n")
        self.assertEqual(list(RowParser.parse(file)),
                         [('KEY1', 'value1', {}),
                          ('KEY2', 'value2', {'VALUE': 'FOO'}),
                          ('KEY3', 'value3', {'VALUE': 'BAR'})])

        file = StringIO("key1:value:with:colons:in:it\n")
        self.assertEqual(list(RowParser.parse(file)),
                         [('KEY1', 'value:with:colons:in:it', {})])

        file = StringIO("ke\r\n y1\n\t:value\r\n  1 \r\n .")
        self.assertEqual(list(RowParser.parse(file)),
                         [('KEY1', 'value 1 .', {})])

        file = StringIO("key;param=\xe2\x98\xbb:\r\n"
                        " value \xe2\x98\xbb\r\n")
        self.assertEqual(list(RowParser.parse(file)),
                         [("KEY", u"value \u263B", {'PARAM': u'\u263B'})])

    def test_parseRow(self):
        from schooltool.calendar.icalendar import RowParser, ICalParseError
        parseRow = RowParser._parseRow
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
        self.assertRaises(ICalParseError, parseRow, "k;a=\"\177:bad param")
        self.assertRaises(ICalParseError, parseRow, "k;a=\001:bad char")
        self.assertEqual(parseRow("key;param=a,b,c:value"),
                         ("KEY", "value", {'PARAM': ['A', 'B', 'C']}))
        self.assertEqual(parseRow('key;param=a,"b,c",d:value'),
                         ("KEY", "value", {'PARAM': ['A', 'b,c', 'D']}))


def doctest_VTimezone():
    r"""Test for VTimezone.

        >>> from schooltool.calendar.icalendar import VTimezone, RowParser
        >>> tz = VTimezone('SchoolTool-Europe/Vilnius', ['foo'])
        >>> tz.tzid
        'SchoolTool-Europe/Vilnius'
        >>> tz.tznames
        ['foo']

        >>> example_vtimezone = dedent('''
        ... BEGIN:VTIMEZONE
        ... TZID:Europe/Berlin
        ... LAST-MODIFIED:20060314T174500Z
        ... BEGIN:STANDARD
        ... DTSTART:20051030T010000
        ... TZOFFSETTO:+0100
        ... TZOFFSETFROM:+0000
        ... TZNAME:CET
        ... END:STANDARD
        ... BEGIN:DAYLIGHT
        ... DTSTART:20060326T020000
        ... TZOFFSETTO:+0200
        ... TZOFFSETFROM:+0100
        ... TZNAME:CEST
        ... END:DAYLIGHT
        ... END:VTIMEZONE
        ... ''')

        >>> rows = RowParser.parse(example_vtimezone.splitlines())
        >>> vtz = VTimezone.parse(rows)

        >>> vtz.tzid
        'Europe/Berlin'
        >>> vtz.tznames
        [u'CET']

    In Evolution calendars X-LIC-LOCATION is very useful for mapping to
    actual pytz timezones, so we store it too if we find it:

        >>> example_vtimezone = dedent('''
        ... BEGIN:VTIMEZONE
        ... TZID:Evolution-blahblah@@obscure_Europe/Berlin
        ... X-LIC-LOCATION:Europe/Berlin
        ... LAST-MODIFIED:20060314T174500Z
        ... BEGIN:STANDARD
        ... DTSTART:20051030T010000
        ... TZOFFSETTO:+0100
        ... TZOFFSETFROM:+0000
        ... TZNAME:CET
        ... END:STANDARD
        ... END:VTIMEZONE
        ... ''')
        >>> rows = RowParser.parse(example_vtimezone.splitlines())
        >>> vtz = VTimezone.parse(rows)
        >>> vtz.tzid
        'Evolution-blahblah@@obscure_Europe/Berlin'
        >>> vtz.x_lic_location
        u'Europe/Berlin'

    """


def doctest_VTimezone_getTzinfo():
    """Tests for VTimezone.getTzinfo()

        >>> from schooltool.calendar.icalendar import VTimezone

    If tzid has a matching timezone, we use it, ignoring other
    arguments:

        >>> vtimezone = VTimezone("Europe/Berlin",
        ...                       ['CET', 'CEST'],
        ...                       x_lic_location="Europe/Vilnius")
        >>> vtimezone.getTzinfo()
        <DstTzInfo 'Europe/Berlin' CET+1:00:00 STD>

    If not, we iterate through tzname list and return the first match:

        >>> vtimezone = VTimezone("Evolution-blahblah@@obscure_Europe/Berlin",
        ...                       ['CET', 'CEST'])
        >>> vtimezone.getTzinfo()
        <DstTzInfo 'CET' CET+1:00:00 STD>

    We iterate from end to front, because in most ics files more
    recent tznames are in the end of the list:

        >>> vtimezone = VTimezone("Evolution-blahblah@@obscure_Europe/Berlin",
        ...                       ['CET', 'EET'])
        >>> vtimezone.getTzinfo()
        <DstTzInfo 'EET' EET+2:00:00 STD>

    If x_lic_location is supplied and has a matching timezone, tznames
    are ignored. x_lic_location is used only if tzid has no matching
    timezone:

        >>> vtimezone = VTimezone("Evolution-blahblah@@obscure_Europe/Berlin",
        ...                       ['CET', 'CEST'],
        ...                       x_lic_location="Europe/Vilnius")
        >>> vtimezone.getTzinfo()
        <DstTzInfo 'Europe/Vilnius' WMT+1:24:00 STD>

    """


def doctest_VTimezone_errors():
    r"""Test for VTimezone error handling.

        >>> from schooltool.calendar.icalendar import VTimezone, RowParser

    First, let's omit the timezone ID:

        >>> example_vtimezone = dedent('''
        ... BEGIN:VTIMEZONE
        ... LAST-MODIFIED:20060314T174500Z
        ... BEGIN:STANDARD
        ... DTSTART:20051030T010000
        ... TZOFFSETTO:+0100
        ... TZOFFSETFROM:+0000
        ... TZNAME:CET
        ... END:STANDARD
        ... END:VTIMEZONE
        ... ''')
        >>> rows = RowParser.parse(example_vtimezone.splitlines())
        >>> VTimezone.parse(rows)
        Traceback (most recent call last):
            ...
        ICalParseError: Missing TZID in VTIMEZONE block

    Then omit the STANDARD section:

        >>> example_vtimezone = dedent('''
        ... BEGIN:VTIMEZONE
        ... TZID:Europe/Berlin
        ... LAST-MODIFIED:20060314T174500Z
        ... END:VTIMEZONE
        ... ''')
        >>> rows = RowParser.parse(example_vtimezone.splitlines())
        >>> VTimezone.parse(rows)
        Traceback (most recent call last):
            ...
        ICalParseError: Missing STANDARD section in VTIMEZONE block

    """


def doctest_VCalendar():
    """Test for VCalendar.

        >>> from schooltool.calendar.icalendar import VCalendar, RowParser
        >>> vcal = VCalendar(['event1'], ['timezone2'])
        >>> vcal.events
        ['event1']
        >>> vcal.timezones
        ['timezone2']

    Now we will check the parser

        >>> example_ical = dedent('''
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ...
        ... BEGIN:VTIMEZONE
        ... TZID:Europe/Berlin
        ... BEGIN:STANDARD
        ... TZNAME:CET
        ... END:STANDARD
        ... END:VTIMEZONE
        ...
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... DTSTART:20050226T160000
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''')
        >>> rows = list(RowParser.parse(example_ical.splitlines()))
        >>> vcal = VCalendar.parse(rows)
        >>> pprint(vcal.timezones)
        {'EUROPE/BERLIN': <DstTzInfo 'Europe/Berlin' CET+1:00:00 STD>,
         'UTC': <UTC>}
        >>> vcal.events
        [<schooltool.calendar.icalendar.VEvent object at ...>]

    If there is a vtimezone block that we can't find a tzinfo for we
    are skipping it:

        >>> example_ical = dedent('''
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ...
        ... BEGIN:VTIMEZONE
        ... TZID:Europe/Berlin
        ... BEGIN:STANDARD
        ... TZNAME:CET
        ... END:STANDARD
        ... END:VTIMEZONE
        ...
        ... BEGIN:VTIMEZONE
        ... TZID:Yurop/Berlin
        ... BEGIN:STANDARD
        ... TZNAME:YNAME
        ... END:STANDARD
        ... END:VTIMEZONE
        ...
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... DTSTART:20050226T160000
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''')
        >>> rows = list(RowParser.parse(example_ical.splitlines()))
        >>> vcal = VCalendar.parse(rows)
        >>> pprint(vcal.timezones)
        {'EUROPE/BERLIN': <DstTzInfo 'Europe/Berlin' CET+1:00:00 STD>,
         'UTC': <UTC>}
        >>> vcal.events
        [<schooltool.calendar.icalendar.VEvent object at ...>]

    """


def doctest_ical_reader_empty_summary():
    r"""Regression test for read_icalendar

    Mozilla Calendar allows events with an empty summary.  This used to be
    read as a CalendarEvent with title = None in schooltool, which broke
    things.

        >>> from schooltool.calendar.icalendar import read_icalendar
        >>> events = list(read_icalendar('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... DTSTART:20050226T160000
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... '''))
        >>> [e.title for e in events]
        ['']

    We support reading calendars when ical files are using different
    charset too:

        >>> events = list(read_icalendar('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... SUMMARY:LAN party %s
        ... DTSTART:20050226T160000
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''' %  chr(163), charset='latin-1'))
        >>> titles = [e.title for e in events]
        >>> titles[0]
        u'LAN party \xa3'

    """


def doctest_read_icalendar_all_day():
    r"""Test for generation of allday events.

    SchoolTool should import all day events as such:

        >>> from schooltool.calendar.icalendar import read_icalendar
        >>> events = list(read_icalendar('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ... BEGIN:VEVENT
        ... SUMMARY:All day event
        ... UID:some-random-uid@example.com
        ... DTSTART;VALUE=DATE:20050226
        ... DURATION:P2D
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... '''))
        >>> len(events)
        1

        >>> event = list(events)[0]
        >>> event.title
        u'All day event'
        >>> event.duration
        datetime.timedelta(2)
        >>> event.allday
        True
        >>> event.dtstart
        datetime.datetime(2005, 2, 26, 0, 0, tzinfo=<UTC>)

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
                        optionflags=doctest.ELLIPSIS | doctest.REPORT_UDIFF |
                                    doctest.NORMALIZE_WHITESPACE))
    suite.addTest(doctest.DocTestSuite('schooltool.calendar.icalendar',
                        optionflags=doctest.ELLIPSIS | doctest.REPORT_UDIFF |
                                    doctest.NORMALIZE_WHITESPACE))
    suite.addTest(unittest.makeSuite(TestParseDateTime))
    suite.addTest(unittest.makeSuite(TestPeriod))
    suite.addTest(unittest.makeSuite(TestVEvent))
    suite.addTest(unittest.makeSuite(TestReadIcalendar))
    suite.addTest(unittest.makeSuite(TestRowParser))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
