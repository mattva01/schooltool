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
from sets import Set
from zope.interface import implements
from persistence import Persistent
from persistence.dict import PersistentDict
from schooltool.db import MaybePersistentKeysSet
from schooltool.interfaces import ISchooldayModel, ISchooldayModelWrite
from schooltool.interfaces import ILocation, ISchooldayPeriod
from schooltool.interfaces import ITimetable, ITimetableWrite
from schooltool.interfaces import ITimetableDay, ITimetableDayWrite
from schooltool.interfaces import ITimetableActivity
from schooltool.interfaces import ISchooldayTemplate, ISchooldayTemplateWrite
from schooltool.interfaces import ITimetableModel, IDateRange
from schooltool.interfaces import ICalendar, ICalendarEvent

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


class SchooldayModel(DateRange):

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

    def remove(self, date):
        self._validate(date)
        self._schooldays.remove(date)

    def addWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays and self.isSchoolday(date):
                self.remove(date)

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
    time_part = r'T(\d+)H(?:(\d+)M(?:(\d+)S)?)?'
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
        if days is None and hours is None:
            raise ValueError('Invalid iCalendar duration: %r'
                             % value)
        value = datetime.timedelta(days=int(days or 0),
                                   hours=int(hours or 0),
                                   minutes=int(minutes or 0),
                                   seconds=int(seconds or 0))
    if sign == '-':
        value = -value
    return value


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
    }

    converters = {
        'INTEGER': int,
        'DATE': parse_date,
        'DATE-TIME': parse_date_time,
        'DURATION': parse_duration,
        'PERIOD': parse_period,
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
          all_day_event     True if this is an all-day event
          dtstart           start of the event (inclusive)
          dtend             end of the event (not inclusive)
          duration          length of the event
          rdates            a list of recurrence dates or periods
          exdates           a list of exception dates
        """
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
        ('FOO', 'BAZFOO', '{'VALUE': 'BAR'})
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
            raise ICalParseError('This is not iCalendar')
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
# Timetabling
#

class Timetable(Persistent):

    implements(ITimetable, ITimetableWrite)

    def __init__(self, day_ids=()):
        """day_ids is a sequence of the day ids of this timetable.
        """
        self.day_ids = day_ids
        self.days = PersistentDict()

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days.get(day, None)) for day in self.day_ids]

    def __getitem__(self, key):
        return self.days[key]

    def __setitem__(self, key, value):
        if not ITimetableDay.isImplementedBy(value):
            raise TypeError("Timetable cannot set a non-ITimetableDay "
                            "(got %r)" % (value,))
        if key not in self.day_ids:
            raise ValueError("Key %r not in day_ids %r" % (key, self.day_ids))
        self.days[key] = value

    def update(self, other):
        # XXX Right now we're trusting the user that the periods of
        # XXX the timetable days are compatible.  Maybe that'll be enough?

        if self.day_ids != other.day_ids:
            raise ValueError("Cannot update -- timetables have different"
                             " sets of days: %r and %r" % (self.day_ids,
                                                           other.day_ids))
        for day_id in other.keys():
            for period, activities in other[day_id].items():
                for activity in activities:
                    self[day_id].add(period, activity)


class TimetableDay(Persistent):

    implements(ITimetableDay, ITimetableDayWrite)

    def __init__(self, periods=()):
        self.periods = periods
        self.activities = PersistentDict()
        for p in periods:
            self.activities[p] = MaybePersistentKeysSet()

    def keys(self):
        return [period for period in self.periods if self.activities[period]]

    def items(self):
        return [(period, self.activities[period]) for period in self.periods]

    def __getitem__(self, key):
        return iter(self.activities[key])

    def clear(self, key):
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        self.activities[key].clear()

    def add(self, key, value):
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        if not ITimetableActivity.isImplementedBy(value):
            raise TypeError("TimetableDay cannot set a "
                            "non-ITimetableActivity (got %r)" % (value,))
        self.activities[key].add(value)

    def remove(self, key, value):
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        self.activities[key].remove(value)


class TimetableActivity:
    # This is immutable!   Otherwise, need to make it persistent.

    implements(ITimetableActivity)

    def __init__(self, title=None):
        self.title = title

    def __repr__(self):
        return "<TimetableActivity %s>" % repr(self.title)


class SchooldayPeriod:

    implements(ISchooldayPeriod)

    def __init__(self, title, tstart, duration):
        self.title = title
        self.tstart = tstart
        self.duration = duration

    def __eq__(self, other):
        if not ISchooldayPeriod.isImplementedBy(other):
            return False
        return (self.title == other.title and
                self.tstart == other.tstart and
                self.duration == other.duration)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.title, self.tstart, self.duration))


class SchooldayTemplate:

    implements(ISchooldayTemplate, ISchooldayTemplateWrite)

    def __init__(self):
        self.events = Set()

    def __iter__(self):
        return iter(self.events)

    def add(self, obj):
        if not ISchooldayPeriod.isImplementedBy(obj):
            raise TypeError("SchooldayTemplate can only contain "
                            "ISchooldayPeriods (got %r)" % (obj,))
        self.events.add(obj)

    def remove(self, obj):
        self.events.remove(obj)


class BaseTimetableModel:
    """An abstract base class for timetable models.

    Subclasses must define these methods:

       def schooldayStrategy(self, date, generator):
           'Returns a day_id for a certain date'

       def _dayGenerator(self):
           'Returns a generator to be passed to each call to schooldayStrategy'
    """
    implements(ITimetableModel)

    timetableDayIds = ()
    dayTemplates = {}

    def createCalendar(self, schoolday_model, timetable):
        cal = Calendar(schoolday_model.first, schoolday_model.last)
        day_id_gen = self._dayGenerator()
        for date in schoolday_model:
            if schoolday_model.isSchoolday(date):
                day_id = self.schooldayStrategy(date, day_id_gen)
                day_template = self._getTemplateForDay(date)
                for period in day_template:
                    dt = datetime.datetime.combine(date, period.tstart)
                    if period.title in timetable[day_id].keys():
                        for activity in timetable[day_id][period.title]:
                            event = CalendarEvent(dt, period.duration,
                                                  activity.title)
                            cal.addEvent(event)
        return cal

    def _getTemplateForDay(self, date):
        try:
            return self.dayTemplates[date.weekday()]
        except KeyError:
            return self.dayTemplates[None]

    def schooldayStrategy(self, date, generator):
        raise NotImplementedError

    def _dayGenerator(self):
        raise NotImplementedError


class SequentialDaysTimetableModel(BaseTimetableModel):
    """A timetable model in which the school days go in sequence with
    shifts over non-schooldays:

    Mon     Day 1
    Tue     Day 2
    Wed     ----- National holiday!
    Thu     Day 3
    Fri     Day 4
    Sat     ----- Weekend
    Sun     -----
    Mon     Day 1
    Tue     Day 2
    Wed     Day 3
    Thu     Day 4
    Fri     Day 1
    Sat     ----- Weekend
    Sun     -----
    Mon     Day 2
    """

    def __init__(self, day_ids, day_templates):
        self.timetableDayIds = day_ids
        self.dayTemplates = day_templates

    def _dayGenerator(self):
        while True:
            for day_id in self.timetableDayIds:
                yield day_id

    def schooldayStrategy(self, date, generator):
        return generator.next()


class WeeklyTimetableModel(BaseTimetableModel):
    """A timetable model where the schedule depends only on weekdays."""

    timetableDayIds = "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"

    def __init__(self, day_ids=None, day_templates={}):
        self.dayTemplates = day_templates
        if day_ids is not None:
            self.timetableDayIds = day_ids

    def schooldayStrategy(self, date, generator):
        return self.timetableDayIds[date.weekday()]

    def _dayGenerator(self):
        return None


#
# Calendaring
#

class Calendar:
    implements(ICalendar)

    def __init__(self, first, last):
        self.daterange = DateRange(first, last)
        self.events = Set()

    def __iter__(self):
        return iter(self.events)

    def byDate(self, date):
        cal = Calendar(date, date)
        for event in self:
            if cal._overlaps(event):
                cal.addEvent(event)
        return cal

    def addEvent(self, event):
        self.events.add(event)

    def _overlaps(self, event):
        """Returns whether the event's timespan overlaps with the timespan
        of this calendar.
        """
        event_end = (event.dtstart + event.duration).date()
        event_start = event.dtstart.date()
        cal_start = self.daterange.first
        cal_end = self.daterange.last

        if event_start in self.daterange:
            return True
        elif event_end in self.daterange:
            return True
        elif event_start <= cal_start <= cal_end <= event_end:
            return True
        else:
            return False


class CalendarEvent:
    implements(ICalendarEvent)

    def __init__(self, dt, duration, title):
        self.dtstart = dt
        self.duration = duration
        self.title = title

