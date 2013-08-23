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
r"""
iCalendar parsing and generating.

iCalendar (RFC 2445) is a big and hard-to-read specification.  This module
supports only a subset of it: VEVENT and VFREEBUSY components with a limited
set of attributes and a limited recurrence model.  The subset should be
sufficient for interoperation with desktop calendaring applications like
Apple's iCal, Mozilla Calendar, Evolution and KOrganizer as well as the
Outlook meeting planner.

If you have a calendar, you can convert it to an iCalendar file like this:

    >>> from pytz import timezone
    >>> from datetime import datetime, timedelta
    >>> from schooltool.calendar.simple import ImmutableCalendar
    >>> from schooltool.calendar.simple import SimpleCalendarEvent
    >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 58, 47),
    ...                             timedelta(hours=1), "doctests",
    ...                             location=u"Matar\u00f3",
    ...                             description=u"Writing doctests",
    ...                             unique_id="12345678-5432@example.com")
    >>> calendar = ImmutableCalendar([event])

    >>> ical_file_as_string = "\r\n".join(
    ...         convert_calendar_to_ical(calendar) + [''])

The returned string is in UTF-8.

    >>> event.location.encode("UTF-8") in ical_file_as_string
    True

You can also parse iCalendar files back into calendars:

    >>> event_iterator = read_icalendar(ical_file_as_string)
    >>> new_calendar = ImmutableCalendar(event_iterator)
    >>> [e.title for e in new_calendar]
    [u'doctests']
    >>> e == event
    True

There is some trickery to make empty calendars work:

    >>> empty_calendar = ImmutableCalendar([])
    >>> ical_file_as_string = "\r\n".join(
    ...         convert_calendar_to_ical(empty_calendar) + [''])

    >>> list(read_icalendar(ical_file_as_string))
    []

"""

import pytz
import datetime
import re
from cStringIO import StringIO

from schooltool.calendar.simple import SimpleCalendarEvent


EMPTY_CALENDAR_PLACEHOLDER = 'empty-calendar-placeholder@schooltool.org'

def convert_event_to_vfb(event):
    r"""Convert an ICalendarEvent to iCalendar FREEBUSY entry.

    Returns a list of strings (without newlines) in UTF-8.

        >>> from datetime import datetime, timedelta
        >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 7, 29),
        ...                             timedelta(hours=1), "iCal rendering",
        ...                             location="Big room",
        ...                             description="Blah blah\nblah!",
        ...                             unique_id="12345678-5432@example.com")
        >>> lines = convert_event_to_vfb(event)
        >>> print "\n".join(lines)
        FREEBUSY:20041216T100729/20041216T11072900Z

    """
    # XXX: not handling recurrence yet
    # XXX: shouldn't assume event.dtstart is in UTC
    assert event.dtstart.tzname() == 'UTC'
    return ["FREEBUSY:%s/%s00Z" % (ical_datetime(event.dtstart),
                               ical_datetime(event.dtstart + event.duration))]


def convert_event_to_ical(event):
    r"""Convert an ICalendarEvent to iCalendar VEVENT component.

    Returns a list of strings (without newlines) in UTF-8.

        >>> from datetime import datetime, timedelta
        >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 7, 29),
        ...                             timedelta(hours=1), "iCal rendering",
        ...                             location="Big room",
        ...                             description="Blah blah\nblah!",
        ...                             unique_id="12345678-5432@example.com")
        >>> lines = convert_event_to_ical(event)
        >>> print "\n".join(lines)
        BEGIN:VEVENT
        UID:12345678-5432@example.com
        SUMMARY:iCal rendering
        LOCATION:Big room
        DESCRIPTION:Blah blah\nblah!
        DTSTART:20041216T100729Z
        DURATION:PT1H
        DTSTAMP:...
        END:VEVENT

        >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
        >>> event = SimpleCalendarEvent(datetime(2005, 2, 11, 22, 42, 50),
        ...                             timedelta(minutes=15), "iCal tests",
        ...                             recurrence=DailyRecurrenceRule(),
        ...                             unique_id="12345678-9876@example.com")
        >>> lines = convert_event_to_ical(event)
        >>> print "\n".join(lines)
        BEGIN:VEVENT
        UID:12345678-9876@example.com
        SUMMARY:iCal tests
        RRULE:FREQ=DAILY;INTERVAL=1
        DTSTART:20050211T224250Z
        DURATION:PT15M
        DTSTAMP:...
        END:VEVENT

    All-day events have DTSTART as a date:

        >>> from schooltool.calendar.recurrent import WeeklyRecurrenceRule
        >>> event = SimpleCalendarEvent(datetime(2005, 2, 11, 0, 0, 0),
        ...                             timedelta(days=2), "iCal tests",
        ...                             recurrence=WeeklyRecurrenceRule(),
        ...                             unique_id="12345678-9876@example.com",
        ...                             allday=True)
        >>> lines = convert_event_to_ical(event)
        >>> print "\n".join(lines)
        BEGIN:VEVENT
        UID:12345678-9876@example.com
        SUMMARY:iCal tests
        RRULE:FREQ=WEEKLY;BYDAY=FR;INTERVAL=1
        DTSTART;VALUE=DATE:20050211
        DURATION:P2D
        DTSTAMP:...
        END:VEVENT

    """
    dtstamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    result = [
        "BEGIN:VEVENT",
        "UID:%s" % ical_text(event.unique_id),
        "SUMMARY:%s" % ical_text(event.title)]
    if event.location:
        result.append("LOCATION:%s" % ical_text(event.location))
    if event.description:
        result.append("DESCRIPTION:%s" % ical_text(event.description))
    if event.recurrence is not None:
        start = event.dtstart
        result.extend(event.recurrence.iCalRepresentation(start))

    if event.allday:
        dtstart = 'DTSTART;VALUE=DATE:%s' % ical_date(event.dtstart)
    else:
        # XXX: shouldn't assume event.dtstart is in UTC
        assert event.dtstart.tzname() == 'UTC'
        dtstart = 'DTSTART:%sZ' % ical_datetime(event.dtstart)
    result += [dtstart,
               "DURATION:%s" % ical_duration(event.duration),
               "DTSTAMP:%s" % dtstamp,
               "END:VEVENT"]
    return result


def convert_calendar_to_vfb(calendar):
    r"""Convert an ICalendar to a VFREEBUSY component
    Returns a list of strings (without newlines) in UTF-8.  They should be
    joined with '\r\n' to get a valid iCalendar file.

        >>> from schooltool.calendar.simple import ImmutableCalendar
        >>> from schooltool.calendar.simple import SimpleCalendarEvent
        >>> from datetime import datetime, timedelta
        >>> event1 = SimpleCalendarEvent(datetime(2004, 11, 16, 10, 7, 29),
        ...                             timedelta(hours=1), "iCal rendering",
        ...                             location="Big room",
        ...                             unique_id="12345678-5432@example.com")
        >>> event2 = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 7, 29),
        ...                             timedelta(hours=2), "iCal rendering",
        ...                             location="Big room",
        ...                             unique_id="12345678-9876@example.com")
        >>> calendar = ImmutableCalendar([event1, event2])
        >>> lines = convert_calendar_to_vfb(calendar)
        >>> print "\n".join(lines)
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        METHOD:PUBLISH
        BEGIN:VFREEBUSY
        FREEBUSY:20041116T100729/20041116T11072900Z
        FREEBUSY:20041216T100729/20041216T12072900Z
        END:VFREEBUSY
        END:VCALENDAR

    XXX VFREEBUSY should just expand every occurence

        >>> lines = convert_calendar_to_vfb(ImmutableCalendar())
        >>> print "\n".join(lines)
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        METHOD:PUBLISH
        BEGIN:VFREEBUSY
        END:VFREEBUSY
        END:VCALENDAR


    """
    header = ["BEGIN:VCALENDAR",
              "VERSION:2.0",
              "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN",
              "METHOD:PUBLISH",
              "BEGIN:VFREEBUSY"]
    events = []
    for event in calendar:
        events += convert_event_to_vfb(event)
    footer = ["END:VFREEBUSY",
              "END:VCALENDAR"]
    return header + events + footer


def convert_calendar_to_ical(calendar):
    r"""Convert an ICalendar to iCalendar VCALENDAR component.

    Returns a list of strings (without newlines) in UTF-8.  They should be
    joined with '\r\n' to get a valid iCalendar file.

        >>> from schooltool.calendar.simple import ImmutableCalendar
        >>> from schooltool.calendar.simple import SimpleCalendarEvent
        >>> from datetime import datetime, timedelta
        >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 7, 29),
        ...                             timedelta(hours=1), "iCal rendering",
        ...                             location="Big room",
        ...                             unique_id="12345678-5432@example.com")
        >>> calendar = ImmutableCalendar([event])
        >>> lines = convert_calendar_to_ical(calendar)
        >>> print "\n".join(lines)
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        BEGIN:VEVENT
        UID:12345678-5432@example.com
        SUMMARY:iCal rendering
        LOCATION:Big room
        DTSTART:20041216T100729Z
        DURATION:PT1H
        DTSTAMP:...
        END:VEVENT
        END:VCALENDAR

    Empty calendars are not allowed by RFC 2445, so we have to invent a dummy
    event:

        >>> lines = convert_calendar_to_ical(ImmutableCalendar())
        >>> print "\n".join(lines)
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        BEGIN:VEVENT
        UID:...
        SUMMARY:Empty calendar
        DTSTART:19700101T000000Z
        DURATION:P0D
        DTSTAMP:...
        END:VEVENT
        END:VCALENDAR

    """
    header = ["BEGIN:VCALENDAR",
              "VERSION:2.0",
              "PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN"]
    footer = ["END:VCALENDAR"]
    events = []
    for event in calendar:
        events += convert_event_to_ical(event)
    if not events:
        placeholder = SimpleCalendarEvent(datetime.datetime(1970, 1, 1),
                                          datetime.timedelta(0),
                                          "Empty calendar",
                                          unique_id=EMPTY_CALENDAR_PLACEHOLDER)
        events += convert_event_to_ical(placeholder)
    return header + events + footer


def ical_text(value):
    r"""Format value according to iCalendar TEXT escaping rules.

    Converts Unicode strings to UTF-8 as well.

        >>> ical_text('Foo')
        'Foo'
        >>> ical_text(u'Matar\u00f3')
        'Matar\xc3\xb3'
        >>> ical_text('\\')
        '\\\\'
        >>> ical_text(';')
        '\\;'
        >>> ical_text(',')
        '\\,'
        >>> ical_text('\n')
        '\\n'
    """
    return (value.encode('UTF-8')
                 .replace('\\', '\\\\')
                 .replace(';', '\\;')
                 .replace(',', '\\,')
                 .replace('\n', '\\n'))


def ical_date(value):
    """Format a date as an iCalendar DATE value.

        >>> ical_date(datetime.date(2004, 3, 4))
        '20040304'
    """
    return value.strftime("%Y%m%d")


def ical_datetime(value):
    """Format a datetime as an iCalendar DATETIME value.

        >>> ical_datetime(datetime.datetime(2004, 12, 16, 10, 45, 07))
        '20041216T104507'

    """
    return value.strftime('%Y%m%dT%H%M%S')


def ical_duration(value):
    """Format a timedelta as an iCalendar DURATION value.

        >>> from datetime import timedelta
        >>> ical_duration(timedelta(11))
        'P11D'
        >>> ical_duration(timedelta(-14))
        '-P14D'
        >>> ical_duration(timedelta(1, 7384))
        'P1DT2H3M4S'
        >>> ical_duration(timedelta(1, 7380))
        'P1DT2H3M'
        >>> ical_duration(timedelta(1, 7200))
        'P1DT2H'
        >>> ical_duration(timedelta(0, 7200))
        'PT2H'
        >>> ical_duration(timedelta(0, 7384))
        'PT2H3M4S'
        >>> ical_duration(timedelta(0, 184))
        'PT3M4S'
        >>> ical_duration(timedelta(0, 22))
        'PT22S'
        >>> ical_duration(timedelta(0, 3622))
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


def read_icalendar(icalendar_text, charset='UTF-8', fallback_tz=pytz.utc):
    """Read an iCalendar file and return calendar events.

    Returns an iterator over calendar events.

    `icalendar_text` can be a file object or a string.  It is assumed that
    the iCalendar file contains UTF-8 text.

    `fallback_tz` is used for timestamps when the timezone is not specified
    or not recognized.

    Unsupported features of the iCalendar file (e.g. VTODO components, complex
    recurrence rules, unknown properties) are silently ignored.
    """

    if not hasattr(icalendar_text, 'read'):
        # It is not a file-like object -- let's assume it is a string
        icalendar_text = StringIO(icalendar_text)

    rows = RowParser.parse(icalendar_text, charset)
    vccol = VCalendarCollection.parse(rows)

    for calendar in vccol.vcalendars:
        for vevent in calendar.events:
            if vevent.uid == EMPTY_CALENDAR_PLACEHOLDER:
                continue # Ignore empty calendar placeholder "event"

            dtstart = vevent.dtstart
            if not isinstance(dtstart, datetime.datetime):
                dtstart = datetime.datetime.combine(dtstart,
                                                    datetime.time(0))
            # XXX regression test for events with a date as dtend
            dtend = vevent.dtend
            if not isinstance(dtend, datetime.datetime):
                dtend = datetime.datetime.combine(dtend,
                                                  datetime.time(0))

            if dtstart.tzinfo is None:
                dtstart_tz = calendar.timezones.get(vevent.dtstart_tzid, fallback_tz)
                dtstart = dtstart_tz.localize(dtstart).astimezone(pytz.utc)
            if dtend.tzinfo is None:
                dtend_tz = calendar.timezones.get(vevent.dtend_tzid, fallback_tz)
                dtend = dtend_tz.localize(dtend).astimezone(pytz.utc)
            duration = dtend - dtstart

            yield SimpleCalendarEvent(dtstart, duration,
                                      vevent.summary or '',
                                      location=vevent.location,
                                      description=vevent.description,
                                      unique_id=vevent.uid,
                                      recurrence=vevent.rrule,
                                      allday=vevent.all_day_event)


#
# The rest of this module could use some review and refactoring
#


ical_weekdays = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']


class RowParser(object):

    @staticmethod
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

        >>> RowParser._parseRow('foo:bar')
        ('FOO', 'bar', {})
        >>> RowParser._parseRow('foo;value=bar:BAZFOO')
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

    @staticmethod
    def parse(file, charset='UTF-8'):
        """A generator that returns one record at a time, as a tuple of
        (name, value, params).
        """
        record = []
        for line in file:
            if not line.strip():
                continue
            if line[0] in '\t ':
                line = line[1:]
            elif record:
                row = "".join(record).decode(charset)
                yield RowParser._parseRow(row)
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
            row = "".join(record).decode(charset)
            yield RowParser._parseRow(row)


def parse_block(rows):
    """Read a block from BEGIN until END.

    Returns a dict with sub blocks and a dict of properties.

        >>> parse_block([])
        ([], {})

        >>> lines = ["BEGIN:VTIMEZONE",
        ...          "SOME:Property",
        ...          "END:VTIMEZONE"]
        >>> parse_block(RowParser.parse(lines))
        ([], {u'VTIMEZONE': [[(u'BEGIN', u'VTIMEZONE', {}),
                              (u'SOME', u'Property', {}),
                              (u'END', u'VTIMEZONE', {})]]})

        >>> lines = ["BEGIN:VTIMEZONE",
        ...          "SOME:Property",
        ...          "END:VTIMEZONE",
        ...          "PROP1: VAL1",
        ...          "PROP2:",
        ...          " VAL2",
        ...          "prop3;value=bar:val3"]
        >>> props, blocks = parse_block(RowParser.parse(lines))
        >>> props
        [(u'PROP1', u' VAL1', {}),
         (u'PROP2', u'VAL2', {}),
         (u'PROP3', u'val3', {u'VALUE': u'BAR'})]
        >>> blocks
        {u'VTIMEZONE': [[(u'BEGIN', u'VTIMEZONE', {}),
                         (u'SOME', u'Property', {}),
                         (u'END', u'VTIMEZONE', {})]]}

        >>> lines = ["BEGIN:VTIMEZONE",
        ...          "SOME:Property",
        ...          "BEGIN:STANDARD",
        ...          "OTHER:Property",
        ...          "END:STANDARD",
        ...          "END:VTIMEZONE",
        ...          "BEGIN:VTIMEZONE",
        ...          "SOME:Property",
        ...          "BEGIN:DAYLIGHT",
        ...          "ANOTHER:Property",
        ...          "END:DAYLIGHT",
        ...          "END:VTIMEZONE",
        ...          "PROP1: VAL1",
        ...          "PROP2:",
        ...          " VAL2",
        ...          "prop3;value=bar:val3"]
        >>> props, blocks = parse_block(RowParser.parse(lines))
        >>> props
        [(u'PROP1', u' VAL1', {}),
         (u'PROP2', u'VAL2', {}),
         (u'PROP3', u'val3', {u'VALUE': u'BAR'})]
        >>> blocks
        {u'VTIMEZONE': [[(u'BEGIN', u'VTIMEZONE', {}),
                         (u'SOME', u'Property', {}),
                         (u'BEGIN', u'STANDARD', {}),
                         (u'OTHER', u'Property', {}),
                         (u'END', u'STANDARD', {}),
                         (u'END', u'VTIMEZONE', {})],
                        [(u'BEGIN', u'VTIMEZONE', {}),
                         (u'SOME', u'Property', {}),
                         (u'BEGIN', u'DAYLIGHT', {}),
                         (u'ANOTHER', u'Property', {}),
                         (u'END', u'DAYLIGHT', {}),
                         (u'END', u'VTIMEZONE', {})]]}

        >>> lines = ["BEGIN:VCALENDAR",
        ...          "BEGIN:VEVENT",
        ...          "DTSTART;VALUE=DATE:20010203"]
        >>> props, blocks = parse_block(RowParser.parse(lines))
        Traceback (most recent call last):
        ...
        ICalParseError: Mismatched BEGIN/END

    """
    blocks = {}
    props = []
    parse_stack = []
    block = []
    for key, value, params in rows:
        if key == "BEGIN":
            parse_stack.append(value)
            # if this is the first time we encounter this block in
            # top level
            if (len(parse_stack) == 1 and
                value not in blocks.keys()):
                blocks[value] = []
        if parse_stack:
            block.append((key, value, params))
        else:
            props.append((key, value, params))
        if key == "END":
            if not parse_stack or parse_stack[-1] != value:
                raise ICalParseError("Mismatched BEGIN/END")
            if len(parse_stack) == 1:
                blocks[parse_stack[0]].append(block)
                block = []
            parse_stack.pop(-1)
    if parse_stack:
        raise ICalParseError("Mismatched BEGIN/END")
    return props, blocks


class VCalendarCollection(object):

    def __init__(self, vcalendars):
        self.vcalendars = vcalendars

    @staticmethod
    def parse(rows):
        """Parse a list of rows into a VCalendarCollection object."""
        props, blocks = parse_block(rows)

        if props:
            raise ICalParseError("Text outside VCALENDAR component")

        # Handle empty ics files
        if not blocks:
            vcalendars = []
        elif 'VCALENDAR' not in blocks.keys():
            raise ICalParseError('This is not iCalendar')
        elif blocks.keys() != ['VCALENDAR']:
            raise ICalParseError("Text outside VCALENDAR component")
        else:
            vcalendars = [VCalendar.parse(block)
                          for block in blocks['VCALENDAR']]
        return VCalendarCollection(vcalendars)


class VCalendar(object):

    def __init__(self, events, timezones):
        self.events = events
        self.timezones = timezones

    @staticmethod
    def parse(rows):
        """Parse a list of rows into a VCalendar object."""
        props, blocks = parse_block(rows[1:-1])

        timezones = {'UTC': pytz.utc}
        for block in blocks.get('VTIMEZONE', []):
            vtimezone = VTimezone.parse(block)
            tzinfo = vtimezone.getTzinfo()
            if tzinfo is None:
                continue # couldn't parse it :/
                # TODO: the user should be informed
            timezones[vtimezone.tzid.upper()] = tzinfo
        events = [VEvent.parse(block)
                  for block in blocks.get('VEVENT', [])]
        return VCalendar(events, timezones)


class VTimezone(object):

    def __init__(self, tzid, tznames, x_lic_location=None):
        tzid = tzid.encode('US-ASCII')
        self.tzid = tzid
        self.tznames = tznames
        self.x_lic_location = x_lic_location

    def getTzinfo(self):
        """Deduce the pytz timezone from the VTIMEZONE block."""
        if self.tzid in pytz.all_timezones:
            return pytz.timezone(self.tzid)
        elif self.x_lic_location in pytz.all_timezones:
            return pytz.timezone(self.x_lic_location)
        else:
            for tzname in reversed(self.tznames):
                if tzname in pytz.all_timezones:
                    return pytz.timezone(tzname)
        # We don't know
        return None

    @staticmethod
    def parse(rows):
        """Parse a list of rows into a VTimezone object."""
        rows = list(rows)
        props, blocks = parse_block(rows[1:-1])

        tzid = None
        x_lic_location = None
        for key, value, params in props:
            if key == 'TZID':
                tzid = value
            elif key == 'X-LIC-LOCATION':
                x_lic_location = value
        if not tzid:
            raise ICalParseError("Missing TZID in VTIMEZONE block")

        tznames = []
        for block in blocks.get('STANDARD', []):
            for key, value, params in block:
                if key == 'TZNAME':
                    tznames.append(value)
        if not tznames:
            raise ICalParseError("Missing STANDARD section in VTIMEZONE block")

        return VTimezone(tzid, tznames, x_lic_location=x_lic_location)


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

    A simple usage example:

    >>> parse_date_time('20030405T060708')
    datetime.datetime(2003, 4, 5, 6, 7, 8)

    >>> parse_date_time('20030405T060708Z')
    datetime.datetime(2003, 4, 5, 6, 7, 8, tzinfo=<UTC>)

    Examples of invalid arguments:

    >>> parse_date_time('20030405T060708+05:00')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date-time: '20030405T060708+05:00'

    >>> parse_date_time('20030405T060708A')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date-time: '20030405T060708A'

    >>> parse_date_time('')
    Traceback (most recent call last):
      ...
    ValueError: Invalid iCalendar date-time: ''

    For timezone tests see tests.test_icalendar.TestParseDateTime.

    """
    datetime_rx = re.compile(r'(\d{4})(\d{2})(\d{2})'
                             r'T(\d{2})(\d{2})(\d{2})(Z?)$')
    match = datetime_rx.match(value)
    if match is None:
        raise ValueError('Invalid iCalendar date-time: %r' % value)
    y, m, d, hh, mm, ss, utc = match.groups()
    dt = datetime.datetime(int(y), int(m), int(d),
                           int(hh), int(mm), int(ss))
    if utc:
        return pytz.utc.localize(dt)
    return dt


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
    from schooltool.calendar.recurrent import WeeklyRecurrenceRule
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
    from schooltool.calendar.recurrent import MonthlyRecurrenceRule
    if 'BYDAY' in args:
        if args['BYDAY'][0] == '-':
            monthly = 'lastweekday'
        else:
            monthly = 'weekday'
    else:
        monthly = 'monthday'
    return MonthlyRecurrenceRule(monthly=monthly)


def parse_recurrence_rule(value):
    """Parse iCalendar RRULE entry.

    Returns the corresponding subclass of RecurrenceRule.

    params is a mapping from attribute names in RRULE to their string values,

    A trivial example of a daily recurrence:

    >>> parse_recurrence_rule('FREQ=DAILY')
    DailyRecurrenceRule(1, None, None, ())

    A slightly more complex example:

    >>> parse_recurrence_rule('FREQ=DAILY;INTERVAL=5;COUNT=7')
    DailyRecurrenceRule(5, 7, None, ())

    An example that includes use of UNTIL:

    >>> parse_recurrence_rule('FREQ=DAILY;UNTIL=20041008T000000')
    DailyRecurrenceRule(1, None, datetime.date(2004, 10, 8), ())
    >>> parse_recurrence_rule('FREQ=DAILY;UNTIL=20041008')
    DailyRecurrenceRule(1, None, datetime.date(2004, 10, 8), ())

    Of course, other recurrence frequencies may be used:

    >>> parse_recurrence_rule('FREQ=WEEKLY;BYDAY=MO,WE,SU')
    WeeklyRecurrenceRule(1, None, None, (), (0, 2, 6))
    >>> parse_recurrence_rule('FREQ=MONTHLY')
    MonthlyRecurrenceRule(1, None, None, (), 'monthday')
    >>> parse_recurrence_rule('FREQ=YEARLY')
    YearlyRecurrenceRule(1, None, None, ())

    You have to provide a valid recurrence frequency, or you will get an error:

    >>> parse_recurrence_rule('')
    Traceback (most recent call last):
      ...
    ValueError: Invalid frequency of recurrence: None
    >>> parse_recurrence_rule('FREQ=bogus')
    Traceback (most recent call last):
      ...
    ValueError: Invalid frequency of recurrence: 'bogus'

    Unknown keys in params are ignored silently:

    >>> parse_recurrence_rule('FREQ=DAILY;WHATEVER=IGNORED')
    DailyRecurrenceRule(1, None, None, ())

    >>> parse_recurrence_rule('FREQ=MONTHLY;INTERVAL=1;UNTIL=20070102;BYMONTHDAY=3')
    MonthlyRecurrenceRule(1, None, datetime.date(2007, 1, 2), (), 'monthday')

    """
    from schooltool.calendar.recurrent import DailyRecurrenceRule
    from schooltool.calendar.recurrent import YearlyRecurrenceRule

    # split up the given value into parameters
    params = {}
    if value:
        for pair in value.split(';'):
            k, v = pair.split('=', 1)
            params[k] = v

    # parse common recurrency attributes
    interval = int(params.pop('INTERVAL', '1'))
    count = params.pop('COUNT', None)
    if count is not None:
        count = int(count)
    until = params.pop('UNTIL', None)
    if until is not None:
        if len(until) == 8:
            until = parse_date(until)
        else:
            until = parse_date_time(until).date()

    # instantiate the corresponding recurrence rule
    freq = params.pop('FREQ', None)
    if freq == 'DAILY':
        rule = DailyRecurrenceRule()
    elif freq == 'WEEKLY':
        rule = _parse_recurrence_weekly(params)
    elif freq == 'MONTHLY':
        rule = _parse_recurrence_monthly(params)
    elif freq == 'YEARLY':
        rule = YearlyRecurrenceRule()
    else:
        raise ValueError('Invalid frequency of recurrence: %r' % freq)

    return rule.replace(interval=interval, count=count, until=until)


class VEventParser(object):
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
        'RECUR': parse_recurrence_rule,
    }

    singleton_properties = set([
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

    rdate_types = set(['DATE', 'DATE-TIME', 'PERIOD'])
    exdate_types = set(['DATE', 'DATE-TIME'])

    def __init__(self):
        self._props = {}

    def add(self, property, value, params=None):
        """Add a property.

        Property name is case insensitive.  Params should be a dict from
        uppercased parameter names to their values.

        Multiple calls to add with the same property name override the value.
        This is sufficient for now, but will have to be changed soon.
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
        """Check that this event has all the necessary properties."""
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
        elif self.hasProp('DURATION'):
            if self._getType('DURATION') != 'DURATION':
                raise ICalParseError("DURATION property should have type"
                                     " DURATION")

    def parse(self):
        """Construct the corresponding VEvent object.

        Returns a VEvent.
        """
        self.validate()
        uid = self.getOne('UID')
        summary = self.getOne('SUMMARY')

        all_day_event = self._getType('DTSTART') == 'DATE'

        dtstart = self.getOne('DTSTART')
        prop = self._props['DTSTART'][0]
        dtstart_tzid = prop[1].get('TZID')

        if self.hasProp('DURATION'):
            duration = self.getOne('DURATION')
            dtend = dtstart + duration
            dtend_tzid = dtstart_tzid
        else:
            dtend = self.getOne('DTEND', None)
            if dtend is not None:
                dtend_tzid = self._props['DTEND'][0][1].get('TZID')
            else:
                dtend_tzid = dtstart_tzid
            if dtend is None:
                dtend = dtstart
                if all_day_event:
                    dtend += datetime.date.resolution

        location = self.getOne('LOCATION', None)
        description = self.getOne('DESCRIPTION', None)

        if dtstart > dtend:
            raise ICalParseError("Event start time should precede end time")
        elif all_day_event and dtstart == dtend:
            raise ICalParseError("Event start time should precede end time")

        rdates = self._extractListOfDates('RDATE', self.rdate_types,
                                          all_day_event)
        exdates = self._extractListOfDates('EXDATE', self.exdate_types,
                                           all_day_event)

        rrule = self.getOne('RRULE', None)
        if rrule is not None and exdates:
            exceptions = [datetime.date(dt.year, dt.month, dt.day)
                          for dt in exdates]
            rrule = rrule.replace(exceptions=exceptions)

        return VEvent(uid=uid, summary=summary, all_day_event=all_day_event,
                      dtstart=dtstart, dtstart_tzid=dtstart_tzid, dtend=dtend,
                      dtend_tzid=dtend_tzid, location=location,
                      description=description, rrule=rrule, rdates=rdates,
                      exdates=exdates)

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
        """Return the type of the property value.

        Only call getType for properties that do not occur more than once.
        """
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


class VEvent(object):
    """A calendar event.

    Attributes:

          uid               The unique id of this event
          summary           Textual summary of this event
          all_day_event     True if this is an all-day event
          dtstart           start of the event (inclusive)
          dtstart_tzid      timezone for the start of the event
          dtend             end of the event (not inclusive)
          dtend_tzid        timezone for the end of the event
          location          location of the event
          description       description of the event
          rrule             recurrency rule
          rdates            a list of recurrence dates or periods
          exdates           a list of exception dates

    """

    def __init__(self, uid, summary, all_day_event, dtstart, dtstart_tzid,
                 dtend, dtend_tzid, location, description, rrule, rdates,
                 exdates):
        self.uid = uid
        self.summary = summary
        self.all_day_event = all_day_event
        self.dtstart = dtstart
        self.dtstart_tzid = dtstart_tzid
        self.dtend = dtend
        self.dtend_tzid = dtend_tzid
        self.location = location
        self.description = description
        self.rrule = rrule
        self.rdates = rdates
        self.exdates = exdates

    @staticmethod
    def parse(rows):
        """Parse a list of rows into a VEvent object."""
        parser = VEventParser()
        props, blocks = parse_block(rows[1:-1])

        for key, value, params in props:
            parser.add(key, value, params)

        return parser.parse()


class Period(object):
    """A period of time."""

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


class ICalParseError(Exception):
    """Invalid syntax in an iCalendar file."""
