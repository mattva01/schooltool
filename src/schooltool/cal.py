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
SchoolTool calendaring stuff.

$Id$
"""

import re
import datetime
import email.Utils
from sets import Set
from zope.interface import implements
from persistent import Persistent
from schooltool.auth import ACL
from schooltool.interfaces import ISchooldayModel, ISchooldayModelWrite
from schooltool.interfaces import ILocation, IDateRange
from schooltool.interfaces import ICalendar, ICalendarWrite, ICalendarEvent
from schooltool.interfaces import ICalendarOwner
from schooltool.interfaces import IACLCalendar
from schooltool.interfaces import ViewPermission
from schooltool.interfaces import ModifyPermission, AddPermission
from schooltool.interfaces import Unchanged
from schooltool.interfaces import IDailyRecurrenceRule, IYearlyRecurrenceRule
from schooltool.interfaces import IWeeklyRecurrenceRule, IMonthlyRecurrenceRule

__metaclass__ = type


#
# Date ranges and schoolday models
#

class DateRange:

    implements(IDateRange)

    def __init__(self, first, last):
        self.first = first
        self.last = last
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))

    def __iter__(self):
        date = self.first
        while date <= self.last:
            yield date
            date += datetime.date.resolution

    def __len__(self):
        return (self.last - self.first).days + 1

    def __contains__(self, date):
        return self.first <= date <= self.last


class SchooldayModel(DateRange, Persistent):

    implements(ISchooldayModel, ISchooldayModelWrite, ILocation)

    def __init__(self, first, last):
        DateRange.__init__(self, first, last)
        self._schooldays = Set()
        self.__parent__ = None
        self.__name__ = None

    def _validate(self, date):
        if not date in self:
            raise ValueError("Date %r not in period [%r, %r]" %
                             (date, self.first, self.last))

    def isSchoolday(self, date):
        self._validate(date)
        if date in self._schooldays:
            return True
        return False

    def add(self, date):
        self._validate(date)
        self._schooldays.add(date)
        self._schooldays = self._schooldays  # persistence

    def remove(self, date):
        self._validate(date)
        self._schooldays.remove(date)
        self._schooldays = self._schooldays  # persistence

    def addWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays and self.isSchoolday(date):
                self.remove(date)

    def toggleWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                if self.isSchoolday(date):
                    self.remove(date)
                else:
                    self.add(date)

    def reset(self, first, last):
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))
        self.first = first
        self.last = last
        self._schooldays.clear()


#
# iCalendar parsing
#


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


#
# Calendaring
#

class Calendar(Persistent):

    implements(ICalendar, ICalendarWrite, ILocation)

    def __init__(self):
        self.events = Set()
        self.__name__ = None
        self.__parent__ = None

    def __iter__(self):
        return iter(self.events)

    def find(self, unique_id):
        # We could speed it up by building and maintaining index
        for event in self:
            if event.unique_id == unique_id:
                return event
        raise KeyError(unique_id)

    def byDate(self, date):
        cal = Calendar()
        for event in self:
            event_start = event.dtstart.date()
            event_end = (event.dtstart + event.duration).date()
            if event_start <= date and event_end >= date:
                cal.addEvent(event)
        return cal

    def addEvent(self, event):
        self.events.add(event)
        self.events = self.events  # make persistence work

    def _removeEvent(self, event):
        self.events.remove(event)
        self.events = self.events  # make persistence work

    def removeEvent(self, event):
        self._removeEvent(event)
        # In SchoolTool resource booking works as follows:
        #   1. A CalendarEvent is created with owner == the user who booked
        #      the resource and context == the resource.
        #   2. That event is added to both the owner's calendar and the
        #   resource's calendar.
        # When that event is removed from either the owner's or the resource's
        # calendar, it should be removed from the other one as well.
        owner_calendar = event.owner is not None and event.owner.calendar
        context_calendar = event.context is not None and event.context.calendar
        if self is owner_calendar or self is context_calendar:
            if owner_calendar is not None and owner_calendar is not self:
                owner_calendar._removeEvent(event)
            if context_calendar is not None and context_calendar is not self:
                context_calendar._removeEvent(event)

    def update(self, calendar):
        for event in calendar:
            self.events.add(event)
        self.events = self.events  # make persistence work

    def clear(self):
        self.events.clear()
        self.events = self.events  # make persistence work


class CalendarEvent(Persistent):

    implements(ICalendarEvent)

    unique_id = property(lambda self: self._unique_id)
    dtstart = property(lambda self: self._dtstart)
    duration = property(lambda self: self._duration)
    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)
    context = property(lambda self: self._context)
    location = property(lambda self: self._location)
    recurrence = property(lambda self: self._recurrence)

    def __init__(self, dtstart, duration, title, owner=None, context=None,
                 location=None, unique_id=None, recurrence=None):
        self._dtstart = dtstart
        self._duration = duration
        self._title = title
        self._owner = owner
        self._context = context
        self._location = location
        self._recurrence = recurrence

        if unique_id is None:
            # & 0x7ffffff to avoid FutureWarnings with negative numbers
            nonnegative_hash = hash((self.dtstart, self.title, self.duration,
                                     self.owner, self.context,
                                     self.location)) & 0x7ffffff
            more_uniqueness = '%d.%08X' % (datetime.datetime.now().microsecond,
                                           nonnegative_hash)
            # generate an rfc-822 style id and strip angle brackets
            unique_id = email.Utils.make_msgid(more_uniqueness)[1:-1]
        self._unique_id = unique_id

    def replace(self, dtstart=Unchanged, duration=Unchanged, title=Unchanged,
                owner=Unchanged, context=Unchanged, location=Unchanged,
                unique_id=Unchanged):
        if dtstart is Unchanged: dtstart = self.dtstart
        if duration is Unchanged: duration = self.duration
        if title is Unchanged: title = self.title
        if owner is Unchanged: owner = self.owner
        if context is Unchanged: context = self.context
        if location is Unchanged: location = self.location
        if unique_id is Unchanged: unique_id = self.unique_id
        return CalendarEvent(dtstart, duration, title, owner, context,
                             location, unique_id)

    def __tuple_for_comparison(self):
        return (self.dtstart, self.title, self.duration, self.owner,
                self.context, self.location, self.unique_id)

    def __eq__(self, other):
        if not isinstance(other, CalendarEvent):
            return False
        return self.__tuple_for_comparison() == other.__tuple_for_comparison()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self.__tuple_for_comparison() < other.__tuple_for_comparison()

    def __le__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self.__tuple_for_comparison() <= other.__tuple_for_comparison()

    def __gt__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self.__tuple_for_comparison() > other.__tuple_for_comparison()

    def __ge__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self.__tuple_for_comparison() >= other.__tuple_for_comparison()

    def __hash__(self):
        # Technically speaking,
        #    return hash(self.unique_id)
        # should be enough, if the ID is really unique.
        return hash((self.dtstart, self.title, self.duration, self.owner,
                     self.context, self.location, self.unique_id))

    def __repr__(self):
        return ("CalendarEvent%r"
                % ((self.dtstart, self.duration, self.title, self.owner,
                    self.context, self.location, self.unique_id), ))


class ACLCalendar(Calendar):

    implements(IACLCalendar)

    def __init__(self):
        self.acl = ACL()
        self.acl.__parent__ = self
        self.acl.__name__ = 'acl'
        Calendar.__init__(self)


class CalendarOwnerMixin(Persistent):

    implements(ICalendarOwner)

    def __init__(self):
        self.calendar = ACLCalendar()
        self.calendar.__parent__ = self
        self.calendar.__name__ = 'calendar'

    def addSelfToCalACL(self):
        self.calendar.acl.add((self, ViewPermission))
        self.calendar.acl.add((self, AddPermission))
        self.calendar.acl.add((self, ModifyPermission))


class RecurrenceRule:

    def __init__(self, interval=None, count=None, until=None, exceptions=()):
        self.interval = interval
        self.count = count
        self.until = until
        self.exceptions = tuple(exceptions)
        self._validate()

    def _validate(self):
        if self.count is not None and self.until is not None:
            raise ValueError("count and until cannot be both set (%s, %s)"
                             % (self.count, self.until))
        for ex in self.exceptions:
            if not isinstance(ex, datetime.date):
                raise ValueError("Exceptions must be a sequence of"
                                 " datetime.dates (got %r in exceptions)"
                                 % (ex, ))

    def replace(self, interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged, monthly=Unchanged):
        if interval is Unchanged:
            interval = self.interval
        if count is Unchanged:
            count = self.count
        if until is Unchanged:
            until = self.until
        if exceptions is Unchanged:
            exceptions = tuple(self.exceptions)
        return self.__class__(interval, count, until, exceptions)

    def _tupleForHash(self):
        return (self.__class__.__name__, self.interval, self.count,
                self.until, tuple(self.exceptions))

    def __eq__(self, other):
        """See if self == other."""
        return hash(self) == hash(other)

    def __ne__(self, other):
        """See if self != other."""
        return not self == other

    def __hash__(self):
        """Return the hash value of this recurrence rule.

        It is guaranteed that if recurrence rules compare equal, hash will
        return the same value.
        """
        return hash(self._tupleForHash())


class DailyRecurrenceRule(RecurrenceRule):
    """Daily recurrence rule.

    Immutable hashable object.
    """
    implements(IDailyRecurrenceRule)



class YearlyRecurrenceRule(RecurrenceRule):
    """Yearly recurrence rule.

    Immutable hashable object.
    """
    implements(IYearlyRecurrenceRule)


class WeeklyRecurrenceRule(RecurrenceRule):
    """Weekly recurrence rule."""
    implements(IWeeklyRecurrenceRule)

    def __init__(self, interval=None, count=None, until=None, exceptions=(),
                 weekdays=()):
        self.interval = interval
        self.count = count
        self.until = until
        self.exceptions = exceptions
        self.weekdays = weekdays
        self._validate()

    def _validate(self):
        RecurrenceRule._validate(self)
        for dow in self.weekdays:
            if not isinstance(dow, int) or not  0 <= dow <= 6:
                raise ValueError("Day of week must be an integer 0..6 (got %r)"
                                 % (dow, ))

    def replace(self, interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged, monthly=Unchanged):
        if interval is Unchanged:
            interval = self.interval
        if count is Unchanged:
            count = self.count
        if until is Unchanged:
            until = self.until
        if exceptions is Unchanged:
            exceptions = tuple(self.exceptions)
        if weekdays is Unchanged:
            weekdays = self.weekdays
        return self.__class__(interval, count, until, exceptions, weekdays)

    def _tupleForHash(self):
        return (self.__class__.__name__, self.interval, self.count,
                self.until, self.exceptions, self.weekdays)


class MonthlyRecurrenceRule(RecurrenceRule):
    """Monthly recurrence rule.

    Immutable hashable object.
    """
    implements(IMonthlyRecurrenceRule)

    def __init__(self, interval=None, count=None, until=None, exceptions=(),
                 monthly=None):
        self.interval = interval
        self.count = count
        self.until = until
        self.exceptions = exceptions
        self.monthly = monthly
        self._validate()

    def _validate(self):
        RecurrenceRule._validate(self)
        if self.monthly not in (None, "monthday", "weekday", "lastweekday"):
                raise ValueError("monthly must be one of None, 'monthday',"
                                 " 'weekday', 'lastweekday'. Got %r"
                                 % (self.monthly, ))

    def replace(self, interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged, monthly=Unchanged):
        if interval is Unchanged:
            interval = self.interval
        if count is Unchanged:
            count = self.count
        if until is Unchanged:
            until = self.until
        if exceptions is Unchanged:
            exceptions = tuple(self.exceptions)
        if monthly is Unchanged:
            monthly = self.monthly
        return self.__class__(interval, count, until, exceptions, monthly)

    def _tupleForHash(self):
        return (self.__class__.__name__, self.interval, self.count,
                self.until, self.exceptions, self.monthly)
