"""
Unit tests for schoolbell.icalendar
"""

import unittest
import difflib
import time
import os
from pprint import pformat
from textwrap import dedent
from datetime import date, timedelta, datetime
from StringIO import StringIO

from zope.testing import doctest


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
        from schoolbell.icalendar import parse_date_time

        if not self.have_tzset:
            return # Do not run this test on Windows

        self.setTZ('UTC')
        dt = parse_date_time('20041029T125031Z')
        self.assertEquals(dt, datetime(2004, 10, 29, 12, 50, 31))

        self.setTZ('EET-2EEST')
        dt = parse_date_time('20041029T095031Z') # daylight savings
        self.assertEquals(dt, datetime(2004, 10, 29, 12, 50, 31))
        dt = parse_date_time('20041129T095031Z') # no daylight savings
        self.assertEquals(dt, datetime(2004, 11, 29, 11, 50, 31))


class TestPeriod(unittest.TestCase):

    def test(self):
        from schoolbell.icalendar import Period
        dt1 = datetime(2001, 2, 3, 14, 30, 5)
        dt2 = datetime(2001, 2, 3, 16, 35, 20)
        td = dt2 - dt1
        p1 = Period(dt1, dt2)
        self.assertEquals(p1.start, dt1)
        self.assertEquals(p1.end, dt2)
        self.assertEquals(p1.duration, td)

        p2 = Period(dt1, td)
        self.assertEquals(p2.start, dt1)
        self.assertEquals(p2.end, dt2)
        self.assertEquals(p2.duration, td)

        self.assertEquals(p1, p2)

        p = Period(dt1, timedelta(0))
        self.assertEquals(p.start, dt1)
        self.assertEquals(p.end, dt1)
        self.assertEquals(p.duration, timedelta(0))

        self.assertRaises(ValueError, Period, dt2, dt1)
        self.assertRaises(ValueError, Period, dt1, -td)

    def test_overlap(self):
        from schoolbell.icalendar import Period
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


class TestVEvent(unittest.TestCase):

    def test_add(self):
        from schoolbell.icalendar import VEvent, ICalParseError
        vevent = VEvent()
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
        from schoolbell.icalendar import VEvent
        vevent = VEvent()
        vevent.add('foo', 'bar', {})
        self.assert_(vevent.hasProp('foo'))
        self.assert_(vevent.hasProp('Foo'))
        self.assert_(not vevent.hasProp('baz'))

    def test__getType(self):
        from schoolbell.icalendar import VEvent
        vevent = VEvent()
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
        from schoolbell.icalendar import VEvent
        vevent = VEvent()

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

    def test_iterDates(self):
        from schoolbell.icalendar import VEvent
        vevent = VEvent()
        vevent.all_day_event = True
        vevent.dtstart = date(2003, 1, 2)
        vevent.dtend = date(2003, 1, 5)
        vevent.duration = timedelta(days=3)
        vevent.rdates = []
        vevent.exdates = []
        self.assertEquals(list(vevent.iterDates()),
                    [date(2003, 1, 2), date(2003, 1, 3), date(2003, 1, 4)])

        vevent.all_day_event = False;
        self.assertRaises(ValueError, list, vevent.iterDates())

    def test_iterDates_with_rdate_exdate(self):
        from schoolbell.icalendar import VEvent
        vevent = VEvent()
        vevent.all_day_event = True
        vevent.dtstart = date(2003, 1, 5)
        vevent.dtend = date(2003, 1, 6)
        vevent.duration = timedelta(days=1)
        vevent.rdates = [date(2003, 1, 2), date(2003, 1, 8), date(2003, 1, 8)]
        vevent.exdates = []
        expected = [date(2003, 1, 2), date(2003, 1, 5), date(2003, 1, 8)]
        self.assertEquals(list(vevent.iterDates()), expected)

        vevent.exdates = [date(2003, 1, 6)]
        expected = [date(2003, 1, 2), date(2003, 1, 5), date(2003, 1, 8)]
        self.assertEquals(list(vevent.iterDates()), expected)

        vevent.exdates = [date(2003, 1, 2), date(2003, 1, 2)]
        expected = [date(2003, 1, 5), date(2003, 1, 8)]
        self.assertEquals(list(vevent.iterDates()), expected)

        vevent.exdates = [date(2003, 1, 5)]
        expected = [date(2003, 1, 2), date(2003, 1, 8)]
        self.assertEquals(list(vevent.iterDates()), expected)

        vevent.dtend = date(2003, 1, 7)
        vevent.duration = timedelta(days=2)
        vevent.exdates = [date(2003, 1, 5), date(2003, 1, 3)]
        expected = [date(2003, 1, 2), date(2003, 1, 3),
                    date(2003, 1, 8), date(2003, 1, 9)]
        self.assertEquals(list(vevent.iterDates()), expected)

    def test_validate_error_cases(self):
        from schoolbell.icalendar import VEvent, ICalParseError

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

    def test_validate_all_day_events(self):
        from schoolbell.icalendar import VEvent, ICalParseError

        vevent = VEvent()
        vevent.add('summary', 'An event', {})
        vevent.add('uid', 'unique', {})
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.validate()
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.summary, 'An event')
        self.assertEquals(vevent.uid, 'unique')
        self.assertEquals(vevent.dtend, date(2001, 2, 4))
        self.assertEquals(vevent.duration, timedelta(days=1))

        vevent = VEvent()
        vevent.add('summary', 'An\\nevent\\; with backslashes', {})
        vevent.add('uid', 'unique2', {})
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('dtend', '20010205', {'VALUE': 'DATE'})
        vevent.validate()
        self.assertEquals(vevent.summary, 'An\nevent; with backslashes')
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.uid, 'unique2')
        self.assertEquals(vevent.dtend, date(2001, 2, 5))
        self.assertEquals(vevent.duration, timedelta(days=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('uid', 'unique3', {})
        vevent.add('duration', 'P2D')
        vevent.validate()
        self.assertEquals(vevent.summary, None)
        self.assert_(vevent.all_day_event)
        self.assertEquals(vevent.dtstart, date(2001, 2, 3))
        self.assertEquals(vevent.uid, 'unique3')
        self.assertEquals(vevent.dtend, date(2001, 2, 5))
        self.assertEquals(vevent.duration, timedelta(days=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('uid', 'unique4', {})
        vevent.add('dtend', '20010201', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, vevent.validate)

        vevent = VEvent()
        vevent.add('dtstart', '20010203', {'VALUE': 'DATE'})
        vevent.add('uid', 'unique5', {})
        vevent.add('dtend', '20010203', {'VALUE': 'DATE'})
        self.assertRaises(ICalParseError, vevent.validate)

    def test_validate_not_all_day_events(self):
        from schoolbell.icalendar import VEvent, ICalParseError

        vevent = VEvent()
        vevent.add('dtstart', '20010203T040506')
        vevent.add('uid', 'unique', {})
        vevent.validate()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 5, 6))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 3, 4, 5, 6))
        self.assertEquals(vevent.duration, timedelta(days=0))
        self.assertEquals(vevent.rdates, [])

        vevent = VEvent()
        vevent.add('dtstart', '20010203T040000')
        vevent.add('uid', 'unique', {})
        vevent.add('dtend', '20010204T050102')
        vevent.validate()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))
        self.assertEquals(vevent.duration, timedelta(days=1, hours=1,
                                                     minutes=1, seconds=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203T040000')
        vevent.add('uid', 'unique', {})
        vevent.add('duration', 'P1DT1H1M2S')
        vevent.validate()
        self.assert_(not vevent.all_day_event)
        self.assertEquals(vevent.dtstart, datetime(2001, 2, 3, 4, 0, 0))
        self.assertEquals(vevent.dtend, datetime(2001, 2, 4, 5, 1, 2))
        self.assertEquals(vevent.duration, timedelta(days=1, hours=1,
                                                     minutes=1, seconds=2))

        vevent = VEvent()
        vevent.add('dtstart', '20010203T010203')
        vevent.add('uid', 'unique', {})
        vevent.add('rdate', '20010205T040506')
        vevent.add('exdate', '20010206T040506')
        vevent.validate()
        self.assertEquals(vevent.rdates, [datetime(2001, 2, 5, 4, 5, 6)])
        self.assertEquals(vevent.exdates, [datetime(2001, 2, 6, 4, 5, 6)])

        vevent = VEvent()
        vevent.add('dtstart', '20010203T010203')
        vevent.add('uid', 'unique', {})
        vevent.add('exdate', '20010206,20020307', {'VALUE': 'DATE'})
        vevent.add('rrule', 'FREQ=DAILY')
        vevent.validate()
        self.assertEquals(vevent.exdates, [date(2001, 2, 6), date(2002, 3, 7)])

        vevent = VEvent()
        vevent.add('dtstart', '20010203T010203')
        vevent.add('uid', 'unique', {})
        vevent.add('dtend', '20010203T010202')
        self.assertRaises(ICalParseError, vevent.validate)

    def test_validate_location(self):
        from schoolbell.icalendar import VEvent
        vevent = VEvent()
        vevent.add('dtstart', '20010203T040506')
        vevent.add('uid', 'unique5', {})
        vevent.add('location', 'Somewhere')
        vevent.validate()
        self.assertEquals(vevent.location, 'Somewhere')

# TODO: recurring events
##  def test_validate_rrule(self):
##      from schoolbell.icalendar import VEvent
##      vevent = VEvent()
##      vevent.add('dtstart', '20010203T040506')
##      vevent.add('uid', 'unique5', {})
##      vevent.add('location', 'Somewhere')
##      vevent.add('rrule', 'FREQ=DAILY;COUNT=3')
##      vevent.validate()
##
##      self.assertEquals(vevent.rrule.interval, 1)
##      self.assertEquals(vevent.rrule.count, 3)
##      self.assertEquals(vevent.rrule.until, None)
##      self.assertEquals(vevent.rrule.exceptions, ())
##
##  def test_validate_rrule_exceptions(self):
##      from schoolbell.icalendar import VEvent
##      vevent = VEvent()
##      vevent.add('dtstart', '20010203T040506')
##      vevent.add('uid', 'unique5', {})
##      vevent.add('location', 'Somewhere')
##      vevent.add('rrule', 'FREQ=MONTHLY;BYDAY=3MO')
##      vevent.add('exdate', '19960402T010000,19960404T010000',)
##      vevent.validate()
##
##      self.assertEquals(vevent.rrule.interval, 1)
##      self.assertEquals(vevent.rrule.count, None)
##      self.assertEquals(vevent.rrule.until, None)
##      self.assertEquals(vevent.rrule.monthly, 'weekday')
##      self.assertEquals(vevent.rrule.exceptions,
##                        (date(1996, 4, 2), date(1996, 4, 4)))
##      self.assert_(not isinstance(vevent.rrule.exceptions[0], datetime))

    def test_extractListOfDates(self):
        from schoolbell.icalendar import VEvent, Period, ICalParseError

        vevent = VEvent()
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

        vevent = VEvent()
        vevent.add('rdate', '20010205T040506', {'VALUE': 'TEXT'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'RDATE',
                                          vevent.rdate_types, False)

        vevent = VEvent()
        vevent.add('exdate', '20010205T040506/P1D', {'VALUE': 'PERIOD'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'EXDATE',
                                          vevent.exdate_types, False)

        vevent = VEvent()
        vevent.add('rdate', '20010208', {'VALUE': 'DATE'})
        rdates = vevent._extractListOfDates('RDATE', vevent.rdate_types, True)
        expected = [date(2001, 2, 8)]
        self.assertEqual(expected, rdates,
                         diff(pformat(expected), pformat(rdates)))

        vevent = VEvent()
        vevent.add('rdate', '20010205T040506', {'VALUE': 'DATE-TIME'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'RDATE',
                                          vevent.rdate_types, True)

        vevent = VEvent()
        vevent.add('rdate', '20010209T000000/20010210T000000',
                   {'VALUE': 'PERIOD'})
        self.assertRaises(ICalParseError, vevent._extractListOfDates, 'RDATE',
                                          vevent.rdate_types, True)


class TestICalReader(unittest.TestCase):

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

    def test_iterEvents(self):
        from schoolbell.icalendar import ICalReader, ICalParseError
        file = StringIO(self.example_ical)
        reader = ICalReader(file)
        result = list(reader.iterEvents())
        self.assertEqual(len(result), 3)
        vevent = result[0]
        self.assertEqual(vevent.getOne('x-mozilla-recur-default-units'),
                         'weeks')
        self.assertEqual(vevent.getOne('dtstart'), date(2003, 12, 25))
        self.assertEqual(vevent.dtstart, date(2003, 12, 25))
        self.assertEqual(vevent.getOne('dtend'), date(2003, 12, 26))
        self.assertEqual(vevent.dtend, date(2003, 12, 26))
        vevent = result[1]
        self.assertEqual(vevent.getOne('dtstart'), date(2003, 05, 01))
        self.assertEqual(vevent.dtstart, date(2003, 05, 01))
        vevent = result[2]
        self.assertEqual(vevent.getOne('dtstart'), date(2003, 12, 25))
        self.assertEqual(vevent.dtstart, date(2003, 12, 25))

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    UID:hello
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
        self.assert_(vevent.hasProp('uid'))
        self.assert_(vevent.hasProp('dtstart'))
        self.assert_(not vevent.hasProp('x-prop'))

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    END:VEVENT
                    END:VCALENDAR
                    """)))
        # missing UID
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    END:VCALENDAR
                    END:VEVENT
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    END:VCALENDAR
                    X-PROP:foo
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    END:VCALENDAR
                    BEGIN:VEVENT
                    END:VEVENT
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    BEGIN:VCALENDAR
                    BEGIN:VEVENT
                    DTSTART;VALUE=DATE:20010203
                    END:VEVENT
                    END:VCALENDAR
                    END:UNIVERSE
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    DTSTART;VALUE=DATE:20010203
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(dedent("""\
                    This is just plain text
                    """)))
        self.assertRaises(ICalParseError, list, reader.iterEvents())

        reader = ICalReader(StringIO(""))
        self.assertEquals(list(reader.iterEvents()), [])

    def test_iterRow(self):
        from schoolbell.icalendar import ICalReader
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

        reader = ICalReader(StringIO("key;param=\xe2\x98\xbb:\r\n"
                                     " value \xe2\x98\xbb\r\n"))
        self.assertEqual(list(reader._iterRow()),
                         [("KEY", u"value \u263B", {'PARAM': u'\u263B'})])

    def test_parseRow(self):
        from schoolbell.icalendar import ICalReader, ICalParseError
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
        self.assertRaises(ICalParseError, parseRow, "k;a=\"\177:bad param")
        self.assertRaises(ICalParseError, parseRow, "k;a=\001:bad char")
        self.assertEqual(parseRow("key;param=a,b,c:value"),
                         ("KEY", "value", {'PARAM': ['A', 'B', 'C']}))
        self.assertEqual(parseRow('key;param=a,"b,c",d:value'),
                         ("KEY", "value", {'PARAM': ['A', 'b,c', 'D']}))
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



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('schoolbell.icalendar',
                        optionflags=doctest.ELLIPSIS | doctest.REPORT_UDIFF))
    suite.addTest(unittest.makeSuite(TestParseDateTime))
    suite.addTest(unittest.makeSuite(TestPeriod))
    suite.addTest(unittest.makeSuite(TestVEvent))
    suite.addTest(unittest.makeSuite(TestICalReader))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
