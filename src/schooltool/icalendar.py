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
SchoolTool iCalendar (RFC 2445) parser.

$Id$
"""

import re
import datetime
from sets import Set

__metaclass__ = type


ical_weekdays = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']


class ICalParseError(Exception):
    """Invalid syntax in an iCalendar file."""


def parse_text(value):
    r"""Parse iCalendar TEXT value.

    >>> parse_text('Foo')
    'Foo'
    >>> parse_text('\\\\')
    '\\'
    >>> parse_text('\\;')
    ';'
    >>> parse_text('\\,')
    ','
    >>> parse_text('\\n')
    '\n'
    >>> parse_text('A string with\\; some\\\\ characters\\nin\\Nit')
    'A string with; some\\ characters\nin\nit'
    >>> parse_text('Unterminated \\')
    Traceback (most recent call last):
      ...
    IndexError: string index out of range
    """
    if '\\' not in value:
        return value
    out = []
    prev = 0
    while True:
        idx = value.find('\\', prev)
        if idx == -1:
            break
        out.append(value[prev:idx])
        if value[idx + 1] in 'nN':
            out.append('\n')
        else:
            out.append(value[idx + 1])
        prev = idx + 2
    out.append(value[prev:])
    return "".join(out)


def ical_text(value):
    r"""Format value according to iCalendar TEXT escaping rules.

    >>> ical_text('Foo')
    'Foo'
    >>> ical_text('\\')
    '\\\\'
    >>> ical_text(';')
    '\\;'
    >>> ical_text(',')
    '\\,'
    >>> ical_text('\n')
    '\\n'
    """
    return (value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
                 .replace('\n', '\\n'))


def parse_duration(value):
    """Parse iCalendar DURATION value.  Returns a timedelta instance.

    >>> parse_duration('+P11D')
    datetime.timedelta(11)
    >>> parse_duration('-P2W')
    datetime.timedelta(-14)
    >>> parse_duration('P1DT2H3M4S')
    datetime.timedelta(1, 7384)
    >>> parse_duration('P1DT2H3M')
    datetime.timedelta(1, 7380)
    >>> parse_duration('P1DT2H')
    datetime.timedelta(1, 7200)
    >>> parse_duration('PT2H')
    datetime.timedelta(0, 7200)
    >>> parse_duration('PT2H3M4S')
    datetime.timedelta(0, 7384)
    >>> parse_duration('PT3M4S')
    datetime.timedelta(0, 184)
    >>> parse_duration('PT22S')
    datetime.timedelta(0, 22)
    >>> parse_duration('')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar duration: ''
    >>> parse_duration('xyzzy')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar duration: 'xyzzy'
    >>> parse_duration('P')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar duration: 'P'
    >>> parse_duration('P1WT2H')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar duration: 'P1WT2H'
    """
    date_part = r'(\d+)D'
    time_part = r'T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    datetime_part = '(?:%s)?(?:%s)?' % (date_part, time_part)
    weeks_part = r'(\d+)W'
    duration_rx = re.compile(r'([-+]?)P(?:%s|%s)$'
                             % (weeks_part, datetime_part))
    match = duration_rx.match(value)
    if match is None:
        raise ValueError('Invalid iCalendar duration: %r' % value)
    sign, weeks, days, hours, minutes, seconds = match.groups()
    if weeks:
        value = datetime.timedelta(weeks=int(weeks))
    else:
        if (days is None and hours is None
            and minutes is None and seconds is None):
            raise ValueError('Invalid iCalendar duration: %r'
                             % value)
        value = datetime.timedelta(days=int(days or 0),
                                   hours=int(hours or 0),
                                   minutes=int(minutes or 0),
                                   seconds=int(seconds or 0))
    if sign == '-':
        value = -value
    return value


def ical_duration(value):
    """Format a timedelta as an iCalendar DURATION value.

    >>> ical_duration(datetime.timedelta(11))
    'P11D'
    >>> ical_duration(datetime.timedelta(-14))
    '-P14D'
    >>> ical_duration(datetime.timedelta(1, 7384))
    'P1DT2H3M4S'
    >>> ical_duration(datetime.timedelta(1, 7380))
    'P1DT2H3M'
    >>> ical_duration(datetime.timedelta(1, 7200))
    'P1DT2H'
    >>> ical_duration(datetime.timedelta(0, 7200))
    'PT2H'
    >>> ical_duration(datetime.timedelta(0, 7384))
    'PT2H3M4S'
    >>> ical_duration(datetime.timedelta(0, 184))
    'PT3M4S'
    >>> ical_duration(datetime.timedelta(0, 22))
    'PT22S'
    >>> ical_duration(datetime.timedelta(0, 3622))
    'PT1H0M22S'
    """
    sign = ""
    if value.days < 0:
        sign = "-"
    timepart = ""
    if value.seconds:
        timepart = "T"
        hours = value.seconds // 3600
        minutes = value.seconds % 3600 // 60
        seconds = value.seconds % 60
        if hours:
            timepart += "%dH" % hours
        if minutes or (hours and seconds):
            timepart += "%dM" % minutes
        if seconds:
            timepart += "%dS" % seconds
    if value.days == 0 and timepart:
        return "%sP%s" % (sign, timepart)
    else:
        return "%sP%dD%s" % (sign, abs(value.days), timepart)


def parse_date(value):
    """Parse iCalendar DATE value.  Returns a date instance.

    >>> parse_date('20030405')
    datetime.date(2003, 4, 5)
    >>> parse_date('20030405T060708')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date: '20030405T060708'
    >>> parse_date('')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date: ''
    >>> parse_date('yyyymmdd')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date: 'yyyymmdd'
    """
    if len(value) != 8:
        raise ValueError('Invalid iCalendar date: %r' % value)
    try:
        y, m, d = int(value[0:4]), int(value[4:6]), int(value[6:8])
    except ValueError:
        raise ValueError('Invalid iCalendar date: %r' % value)
    else:
        return datetime.date(y, m, d)


def parse_date_time(value):
    """Parse iCalendar DATE-TIME value.  Returns a datetime instance.

    >>> parse_date_time('20030405T060708')
    datetime.datetime(2003, 4, 5, 6, 7, 8)
    >>> parse_date_time('20030405T060708Z')
    datetime.datetime(2003, 4, 5, 6, 7, 8)
    >>> parse_date_time('20030405T060708A')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date-time: '20030405T060708A'
    >>> parse_date_time('')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date-time: ''
    """
    datetime_rx = re.compile(r'(\d{4})(\d{2})(\d{2})'
                             r'T(\d{2})(\d{2})(\d{2})(Z?)$')
    match = datetime_rx.match(value)
    if match is None:
        raise ValueError('Invalid iCalendar date-time: %r' % value)
    y, m, d, hh, mm, ss, utc = match.groups()
    return datetime.datetime(int(y), int(m), int(d),
                             int(hh), int(mm), int(ss))


def ical_date_time(dt):
    """Return a date in iCalendar format as a string.

    >>> ical_date_time(datetime.datetime(2004, 10, 26, 13, 07, 16))
    '20041026T130716Z'
    """
    return dt.strftime("%Y%m%dT%H%M%SZ")


def parse_period(value):
    """Parse iCalendar PERIOD value.  Returns a Period instance.

    >>> p = parse_period('20030405T060708/20030405T060709')
    >>> print repr(p).replace('),', '),\\n      ')
    Period(datetime.datetime(2003, 4, 5, 6, 7, 8),
           datetime.datetime(2003, 4, 5, 6, 7, 9))
    >>> parse_period('20030405T060708/PT1H1M1S')
    Period(datetime.datetime(2003, 4, 5, 6, 7, 8), datetime.timedelta(0, 3661))
    >>> parse_period('xyzzy')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar period: 'xyzzy'
    >>> parse_period('foo/foe')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar period: 'foo/foe'
    """
    parts = value.split('/')
    if len(parts) != 2:
        raise ValueError('Invalid iCalendar period: %r' % value)
    try:
        start = parse_date_time(parts[0])
        try:
            end_or_duration = parse_date_time(parts[1])
        except ValueError:
            end_or_duration = parse_duration(parts[1])
    except ValueError:
        raise ValueError('Invalid iCalendar period: %r' % value)
    else:
        return Period(start, end_or_duration)


def _parse_recurrence_weekly(args):
    """Parse iCalendar weekly recurrence rule.

    args is a mapping from attribute names in RRULE to their string values.

    >>> _parse_recurrence_weekly({})
    WeeklyRecurrenceRule(1, None, None, (), ())
    >>> _parse_recurrence_weekly({'BYDAY': 'WE'})
    WeeklyRecurrenceRule(1, None, None, (), (2,))
    >>> _parse_recurrence_weekly({'BYDAY': 'MO,WE,SU'})
    WeeklyRecurrenceRule(1, None, None, (), (0, 2, 6))

    """
    # XXX Circular import!
    from schooltool.cal import WeeklyRecurrenceRule
    weekdays = []
    days = args.get('BYDAY', None)
    if days is not None:
        for day in days.split(','):
            weekdays.append(ical_weekdays.index(day))
    return WeeklyRecurrenceRule(weekdays=weekdays)

def _parse_recurrence_monthly(args):
    """Parse iCalendar monthly recurrence rule.

    args is a mapping from attribute names in RRULE to their string values.

    Month-day recurrency is the default:

    >>> _parse_recurrence_monthly({})
    MonthlyRecurrenceRule(1, None, None, (), 'monthday')

    3rd Tuesday in a month:

    >>> _parse_recurrence_monthly({'BYDAY': '3TU'})
    MonthlyRecurrenceRule(1, None, None, (), 'weekday')

    Last Wednesday:

    >>> _parse_recurrence_monthly({'BYDAY': '-1WE'})
    MonthlyRecurrenceRule(1, None, None, (), 'lastweekday')
    """
    # XXX Circular import!
    from schooltool.cal import MonthlyRecurrenceRule
    if 'BYDAY' in args:
        if args['BYDAY'][0] == '-':
            monthly = 'lastweekday'
        else:
            monthly = 'weekday'
    else:
        monthly = 'monthday'
    return MonthlyRecurrenceRule(monthly=monthly)


def parse_recurrence_rule(args, exdate=None):
    """Parse iCalendar RRULE and EXDATE entries.

    Returns the corresponding subclass of RecurrenceRule.

    args is a mapping from attribute names in RRULE to their string values,
    exdate is a string value of EXDATE, or None if EXDATE was not provided.

    A trivial example of a daily recurrence:

    >>> parse_recurrence_rule({'FREQ': 'DAILY'})
    DailyRecurrenceRule(1, None, None, ())

    A slightly more complex example with an exception:

    >>> parse_recurrence_rule({'FREQ': 'DAILY', 'INTERVAL': '5', 'COUNT': '7'},
    ...                       '20041006T000000Z')
    DailyRecurrenceRule(5, 7, None, (datetime.date(2004, 10, 6),))

    An example that includes use of UNTIL:

    >>> parse_recurrence_rule({'FREQ': 'DAILY', 'UNTIL': '20041008T000000Z'})
    DailyRecurrenceRule(1, None, datetime.datetime(2004, 10, 8, 0, 0), ())

    You may specify multiple exceptions:
    >>> rule = parse_recurrence_rule({'FREQ': 'DAILY'},
    ...              '20041006T000000Z,20041008T000000Z,20041010T000000Z')
    >>> len(rule.exceptions)
    3
    >>> rule.exceptions[0]
    datetime.date(2004, 10, 6)
    >>> rule.exceptions[1]
    datetime.date(2004, 10, 8)
    >>> rule.exceptions[2]
    datetime.date(2004, 10, 10)

    Of course, other recurrence frequencies may be used:

    >>> parse_recurrence_rule({'FREQ': 'WEEKLY', 'BYDAY': 'MO,WE,SU'})
    WeeklyRecurrenceRule(1, None, None, (), (0, 2, 6))
    >>> parse_recurrence_rule({'FREQ': 'MONTHLY'})
    MonthlyRecurrenceRule(1, None, None, (), 'monthday')
    >>> parse_recurrence_rule({'FREQ': 'YEARLY'})
    YearlyRecurrenceRule(1, None, None, ())

    You have to provide a valid recurrence frequency, or you will get an error:

    >>> parse_recurrence_rule({})
    Traceback (most recent call last):
      ...
    ValueError: Invalid frequency of recurrence: None
    >>> parse_recurrence_rule({'FREQ': 'bogus'})
    Traceback (most recent call last):
      ...
    ValueError: Invalid frequency of recurrence: 'bogus'

    Unknown keys in args are ignored silently:

    >>> parse_recurrence_rule({'FREQ': 'DAILY', 'WHATEVER': 'IGNORED'})
    DailyRecurrenceRule(1, None, None, ())

    """
    # XXX Circular import!
    from schooltool.cal import DailyRecurrenceRule, YearlyRecurrenceRule

    # parse the list of exceptions
    exceptions = []
    if exdate is not None:
        for dt in exdate.split(','):
            exceptions.append(parse_date_time(dt).date())

    # parse common recurrency attributes
    interval = int(args.pop('INTERVAL', '1'))
    count = args.pop('COUNT', None)
    if count is not None:
        count = int(count)
    until = args.pop('UNTIL', None)
    if until is not None:
        until = parse_date_time(until)

    # instantiate the corresponding recurrence rule
    freq = args.pop('FREQ', None)
    if freq == 'DAILY':
        rule = DailyRecurrenceRule()
    elif freq == 'WEEKLY':
        rule = _parse_recurrence_weekly(args)
    elif freq == 'MONTHLY':
        rule = _parse_recurrence_monthly(args)
    elif freq == 'YEARLY':
        rule = YearlyRecurrenceRule()
    else:
        raise ValueError('Invalid frequency of recurrence: %r' % freq)

    return rule.replace(interval=interval, count=count, until=until,
                        exceptions=exceptions)


class Period:
    """A period of time"""

    def __init__(self, start, end_or_duration):
        self.start = start
        self.end_or_duration = end_or_duration
        if isinstance(end_or_duration, datetime.timedelta):
            self.duration = end_or_duration
            self.end = self.start + self.duration
        else:
            self.end = end_or_duration
            self.duration = self.end - self.start
        if self.start > self.end:
            raise ValueError("Start time is greater than end time")

    def __repr__(self):
        return "Period(%r, %r)" % (self.start, self.end_or_duration)

    def __cmp__(self, other):
        if not isinstance(other, Period):
            raise NotImplementedError('Cannot compare Period with %r' % other)
        return cmp((self.start, self.end), (other.start, other.end))

    def overlaps(self, other):
        if self.start > other.start:
            return other.overlaps(self)
        if self.start <= other.start < self.end:
            return True
        return False


class VEvent:
    """iCalendar event.

    Life cycle: when a VEvent is created, a number of properties should be
    added to it using the add method.  Then validate should be called.
    After that you can start using query methods (getOne, hasProp, iterDates).

    Events are classified into two kinds:
     - normal events
     - all-day events

    All-day events are identified by their DTSTART property having a DATE value
    instead of the default DATE-TIME.  All-day events should satisfy the
    following requirements (otherwise an exception will be raised):
     - DURATION property (if defined) should be an integral number of days
     - DTEND property (if defined) should have a DATE value
     - any RDATE and EXDATE properties should only contain DATE values

    The first two requirements are stated in RFC 2445; I'm not so sure about
    the third one.
    """

    default_type = {
        # Default value types for some properties
        'DTSTAMP': 'DATE-TIME',
        'DTSTART': 'DATE-TIME',
        'CREATED': 'DATE-TIME',
        'DTEND': 'DATE-TIME',
        'DURATION': 'DURATION',
        'LAST-MODIFIED': 'DATE-TIME',
        'PRIORITY': 'INTEGER',
        'RECURRENCE-ID': 'DATE-TIME',
        'SEQUENCE': 'INTEGER',
        'URL': 'URI',
        'ATTACH': 'URI',
        'EXDATE': 'DATE-TIME',
        'EXRULE': 'RECUR',
        'RDATE': 'DATE-TIME',
        'RRULE': 'RECUR',
        'LOCATION': 'TEXT',
        'UID': 'TEXT',
    }

    converters = {
        'INTEGER': int,
        'DATE': parse_date,
        'DATE-TIME': parse_date_time,
        'DURATION': parse_duration,
        'PERIOD': parse_period,
        'TEXT': parse_text,
    }

    singleton_properties = Set([
        'DTSTAMP',
        'DTSTART',
        'UID',
        'CLASS',
        'CREATED',
        'DESCRIPTION',
        'DTEND',
        'DURATION',
        'GEO',
        'LAST-MODIFIED',
        'LOCATION',
        'ORGANIZER',
        'PRIORITY',
        'RECURRENCE-ID',
        'SEQUENCE',
        'STATUS',
        'SUMMARY',
        'TRANSP',
        'URL',
    ])

    rdate_types = Set(['DATE', 'DATE-TIME', 'PERIOD'])
    exdate_types = Set(['DATE', 'DATE-TIME'])

    def __init__(self):
        self._props = {}

    def add(self, property, value, params=None):
        """Add a property.

        Property name is case insensitive.  Params should be a dict from
        uppercased parameter names to their values.

        Multiple calls to add with the same property name override the
        value.  This is sufficient for now, but will have to be changed
        soon.
        """
        if params is None:
            params = {}
        key = property.upper()
        if key in self._props:
            if key in self.singleton_properties:
                raise ICalParseError("Property %s cannot occur more than once"
                                     % key)
            self._props[key].append((value, params))
        else:
            self._props[key] = [(value, params)]

    def validate(self):
        """Check that this VEvent has all the necessary properties.

        Also sets the following attributes:
          uid               The unique id of this event
          summary           Textual summary of this event
          all_day_event     True if this is an all-day event
          dtstart           start of the event (inclusive)
          dtend             end of the event (not inclusive)
          duration          length of the event
          location          location of the event
          rdates            a list of recurrence dates or periods
          exdates           a list of exception dates
        """
        if not self.hasProp('UID'):
            raise ICalParseError("VEVENT must have a UID property")
        if not self.hasProp('DTSTART'):
            raise ICalParseError("VEVENT must have a DTSTART property")
        if self._getType('DTSTART') not in ('DATE', 'DATE-TIME'):
            raise ICalParseError("DTSTART property should have a DATE or"
                                 " DATE-TIME value")
        if self.hasProp('DTEND'):
            if self._getType('DTEND') != self._getType('DTSTART'):
                raise ICalParseError("DTEND property should have the same type"
                                     " as DTSTART")
            if self.hasProp('DURATION'):
                raise ICalParseError("VEVENT cannot have both a DTEND"
                                     " and a DURATION property")
        if self.hasProp('DURATION'):
            if self._getType('DURATION') != 'DURATION':
                raise ICalParseError("DURATION property should have type"
                                     " DURATION")

        self.uid = self.getOne('UID')
        self.summary = self.getOne('SUMMARY')

        self.all_day_event = self._getType('DTSTART') == 'DATE'
        self.dtstart = self.getOne('DTSTART')
        if self.hasProp('DURATION'):
            self.duration = self.getOne('DURATION')
            self.dtend = self.dtstart + self.duration
        else:
            self.dtend = self.getOne('DTEND', None)
            if self.dtend is None:
                self.dtend = self.dtstart
                if self.all_day_event:
                    self.dtend += datetime.date.resolution
            self.duration = self.dtend - self.dtstart

        self.location = self.getOne('LOCATION', None)

        if self.dtstart > self.dtend:
            raise ICalParseError("Event start time should precede end time")
        if self.all_day_event and self.dtstart == self.dtend:
            raise ICalParseError("Event start time should precede end time")

        self.rdates = self._extractListOfDates('RDATE', self.rdate_types,
                                               self.all_day_event)
        self.exdates = self._extractListOfDates('EXDATE', self.exdate_types,
                                                self.all_day_event)

    def _extractListOfDates(self, key, accepted_types, all_day_event):
        """Parse a comma separated list of values.

        If all_day_event is True, only accepts DATE values.  Otherwise accepts
        all value types listed in 'accepted_types'.
        """
        dates = []
        default_type = self.default_type[key]
        for value, params in self._props.get(key, []):
            value_type = params.get('VALUE', default_type)
            if value_type not in accepted_types:
                raise ICalParseError('Invalid value type for %s: %s'
                                     % (key, value_type))
            if all_day_event and value_type != 'DATE':
                raise ICalParseError('I do not understand how to interpret '
                                     '%s values in %s for all-day events.'
                                     % (value_type, key))
            converter = self.converters.get(value_type)
            dates.extend(map(converter, value.split(',')))
        return dates

    def _getType(self, property):
        """Return the type of the property value."""
        key = property.upper()
        values = self._props[key]
        assert len(values) == 1
        value, params = values[0]
        default_type = self.default_type.get(key, 'TEXT')
        return params.get('VALUE', default_type)

    def getOne(self, property, default=None):
        """Return the value of a property as an appropriate Python object.

        Only call getOne for properties that do not occur more than once.
        """
        try:
            values = self._props[property.upper()]
            assert len(values) == 1
            value, params = values[0]
        except KeyError:
            return default
        else:
            converter = self.converters.get(self._getType(property))
            if converter is None:
                return value
            else:
                return converter(value)

    def hasProp(self, property):
        """Return True if this VEvent has a named property."""
        return property.upper() in self._props

    def iterDates(self):
        """Iterate over all dates within this event.

        This is only valid for all-day events at the moment.
        """
        if not self.all_day_event:
            raise ValueError('iterDates is only defined for all-day events')

        # Find out the set of start dates
        start_set = {self.dtstart: None}
        for rdate in self.rdates:
            start_set[rdate] = rdate
        for exdate in self.exdates:
            if exdate in start_set:
                del start_set[exdate]

        # Find out the set of all dates
        date_set = Set(start_set)
        duration = self.duration.days
        for d in start_set:
            for n in range(1, duration):
                d += datetime.date.resolution
                date_set.add(d)

        # Yield all dates in chronological order
        dates = list(date_set)
        dates.sort()
        for d in dates:
            yield d


class ICalReader:
    """An object which reads in an iCal of public holidays and marks
    them off the schoolday calendar.

    Short grammar of iCalendar files (RFC 2445 is the full spec):

      contentline        = name *(";" param ) ":" value CRLF
        ; content line first must be unfolded by replacing CRLF followed by a
        ; single WSP with an empty string
      name               = x-name / iana-token
      x-name             = "X-" [vendorid "-"] 1*(ALPHA / DIGIT / "-")
      iana-token         = 1*(ALPHA / DIGIT / "-")
      vendorid           = 3*(ALPHA / DIGIT)
      param              = param-name "=" param-value *("," param-value)
      param-name         = iana-token / x-token
      param-value        = paramtext / quoted-string
      paramtext          = *SAFE-CHAR
      value              = *VALUE-CHAR
      quoted-string      = DQUOTE *QSAFE-CHAR DQUOTE

      NON-US-ASCII       = %x80-F8
      QSAFE-CHAR         = WSP / %x21 / %x23-7E / NON-US-ASCII
                         ; Any character except CTLs and DQUOTE
      SAFE-CHAR          = WSP / %x21 / %x23-2B / %x2D-39 / %x3C-7E
                          / NON-US-ASCII
                         ; Any character except CTLs, DQUOTE, ";", ":", ","
      VALUE-CHAR         = WSP / %x21-7E / NON-US-ASCII  ; anything except CTLs
      CR                 = %x0D
      LF                 = %x0A
      CRLF               = CR LF
      CTL                = %x00-08 / %x0A-1F / %x7F
      ALPHA              = %x41-5A / %x61-7A             ; A-Z / a-z
      DIGIT              = %x30-39                       ; 0-9
      DQUOTE             = %x22                          ; Quotation Mark
      WSP                = SPACE / HTAB
      SPACE              = %x20
      HTAB               = %x09
    """

    def __init__(self, file):
        self.file = file

    def _parseRow(record_str):
        """Parse a single content line.

        A content line consists of a property name (optionally followed by a
        number of parameters) and a value, separated by a colon.  Parameters
        (if present) are separated from the property name and from each other
        with semicolons.  Parameters are of the form name=value; value
        can be double-quoted.

        Returns a tuple (name, value, param_dict).  Case-insensitive values
        (i.e. property names, parameter names, unquoted parameter values) are
        uppercased.

        Raises ICalParseError on syntax errors.

        >>> ICalReader._parseRow('foo:bar')
        ('FOO', 'bar', {})
        >>> ICalReader._parseRow('foo;value=bar:BAZFOO')
        ('FOO', 'BAZFOO', {'VALUE': 'BAR'})
        """

        it = iter(record_str)
        getChar = it.next

        def err(msg):
            raise ICalParseError("%s in line:\n%s" % (msg, record_str))

        try:
            c = getChar()
            # name
            key = ''
            while c.isalnum() or c == '-':
                key += c
                c = getChar()
            if not key:
                err("Missing property name")
            key = key.upper()
            # optional parameters
            params = {}
            while c == ';':
                c = getChar()
                # param name
                param = ''
                while c.isalnum() or c == '-':
                    param += c
                    c = getChar()
                if not param:
                    err("Missing parameter name")
                param = param.upper()
                # =
                if c != '=':
                    err("Expected '='")
                # value (or rather a list of values)
                pvalues = []
                while True:
                    c = getChar()
                    if c == '"':
                        c = getChar()
                        pvalue = ''
                        while c >= ' ' and c not in ('\177', '"'):
                            pvalue += c
                            c = getChar()
                        # value is case-sensitive in this case
                        if c != '"':
                            err("Expected '\"'")
                        c = getChar()
                    else:
                        # unquoted value
                        pvalue = ''
                        while c >= ' ' and c not in ('\177', '"', ';', ':',
                                                     ','):
                            pvalue += c
                            c = getChar()
                        pvalue = pvalue.upper()
                    pvalues.append(pvalue)
                    if c != ',':
                        break
                if len(pvalues) > 1:
                    params[param] = pvalues
                else:
                    params[param] = pvalues[0]
            # colon and value
            if c != ':':
                err("Expected ':'")
            value = ''.join(it)
        except StopIteration:
            err("Syntax error")
        else:
            return (key, value, params)

    _parseRow = staticmethod(_parseRow)

    def _iterRow(self):
        """A generator that returns one record at a time, as a tuple of
        (name, value, params).
        """
        record = []
        for line in self.file.readlines():
            if line[0] in '\t ':
                line = line[1:]
            elif record:
                yield self._parseRow("".join(record))
                record = []
            if line.endswith('\r\n'):
                record.append(line[:-2])
            elif line.endswith('\n'):
                # strictly speaking this is a violation of RFC 2445
                record.append(line[:-1])
            else:
                # strictly speaking this is a violation of RFC 2445
                record.append(line)
        if record:
            yield self._parseRow("".join(record))

    def iterEvents(self):
        """Iterate over all VEVENT objects in an ICalendar file."""
        iterator = self._iterRow()

        # Check that the stream begins with BEGIN:VCALENDAR
        try:
            key, value, params = iterator.next()
            if (key, value, params) != ('BEGIN', 'VCALENDAR', {}):
                raise ICalParseError('This is not iCalendar')
        except StopIteration:
            # The file is empty.  Mozilla produces a 0-length file when
            # publishing an empty calendar.  Let's accept it as a valid
            # calendar that has no events.  XXX I'm not sure if a 0-length
            # file is a valid text/calendar object according to RFC 2445.
            raise
        component_stack = ['VCALENDAR']

        # Extract all VEVENT components
        obj = None
        for key, value, params in iterator:
            if key == "BEGIN":
                if obj is not None:
                    # Subcomponents terminate the processing of a VEVENT
                    # component.  We can get away with this now, because we're
                    # not interested in alarms and RFC 2445 specifies, that all
                    # properties inside a VEVENT component ought to precede any
                    # VALARM subcomponents.
                    obj.validate()
                    yield obj
                    obj = None
                if not component_stack and value != "VCALENDAR":
                    raise ICalParseError("Text outside VCALENDAR component")
                if value == "VEVENT":
                    obj = VEvent()
                component_stack.append(value)
            elif key == "END":
                if obj is not None and value == "VEVENT":
                    obj.validate()
                    yield obj
                    obj = None
                if not component_stack or component_stack[-1] != value:
                    raise ICalParseError("Mismatched BEGIN/END")
                component_stack.pop()
            elif obj is not None:
                obj.add(key, value, params)
            elif not component_stack:
                raise ICalParseError("Text outside VCALENDAR component")
        if component_stack:
            raise ICalParseError("Unterminated components")


def markNonSchooldays(ical_reader, schoolday_model):
    """Mark all all-day events in the iCal file as non-schooldays in a given
    SchooldayModel.
    """
    for event in ical_reader.iterEvents():
        if event.all_day_event:
            for day in event.iterDates():
                try:
                    schoolday_model.remove(day)
                except (KeyError, ValueError):
                    # They day was already marked as non-schoolday or is
                    # outside the school period.  This is not an error.
                    pass
