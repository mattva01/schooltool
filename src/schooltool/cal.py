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

import datetime
from sets import Set
from zope.interface import implements
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

class VEvent(dict):
    pass


class ICalParseError(Exception):
    """Invalid syntax in an iCalendar file."""


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

    default_type = {
        # Default value types for some properties
        'DTSTAMP': 'DATE-TIME',
        'DTSTART': 'DATE-TIME',
        'CREATED': 'DATE-TIME',
        'DTEND': 'DATE-TIME',
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
                    yield obj
                    obj = None
                if not component_stack and value != "VCALENDAR":
                    raise ICalParseError("Text outside VCALENDAR component")
                if value == "VEVENT":
                    obj = VEvent()
                component_stack.append(value)
            elif key == "END":
                if obj is not None and value == "VEVENT":
                    yield obj
                    obj = None
                if not component_stack or component_stack[-1] != value:
                    raise ICalParseError("Mismatched BEGIN/END")
                component_stack.pop()
            elif obj is not None:
                # Some properties may occur more than once, and this trick will
                # not work when we become interested in them.
                obj[key.lower()] = value
                default_type =  self.default_type.get(key, None)
                value_type = params.get('VALUE', default_type)
                if value_type == 'DATE':
                    y, m, d = int(value[0:4]), int(value[4:6]), int(value[6:8])
                    name = key.lower().replace('-', '_')
                    value = datetime.date(y, m, d)
                    setattr(obj, name, value)
            elif not component_stack:
                raise ICalParseError("Text outside VCALENDAR component")
        if component_stack:
            raise ICalParseError("Unterminated components")


def markNonSchooldays(ical_reader, schoolday_model):
    """Mark all all-day events in the iCal file as non-schooldays in a given
    SchooldayModel.
    """
    for event in ical_reader.iterEvents():
        if hasattr(event, 'dtstart'):
            # We rely on the fact that ICalReader only sets dtstart/dtend
            # attributes on VEvent instances when the value type is DATE,
            # and does not do so when the value type is DATE-TIME.
            dtend = getattr(event, 'dtend', event.dtstart)
            for day in DateRange(event.dtstart, dtend):
                try:
                    schoolday_model.remove(day)
                except (KeyError, ValueError):
                    # They day was already marked as non-schoolday or is
                    # outside the school period.  This is not an error.
                    pass


#
# Timetabling
#

class Timetable:

    implements(ITimetable, ITimetableWrite)

    def __init__(self, day_ids=()):
        """day_ids is a sequence of the day ids of this timetable.
        """
        self.day_ids = day_ids
        self.days = {}

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


class TimetableDay:

    implements(ITimetableDay, ITimetableDayWrite)

    def __init__(self, periods=()):
        self.periods = periods
        self.activities = {}

    def keys(self):
        return [period for period in self.periods if period in self.activities]

    def items(self):
        return [(period, self.activities.get(period, None))
                for period in self.periods]

    def __getitem__(self, key):
        return self.activities[key]

    def __setitem__(self, key, value):
        if not ITimetableActivity.isImplementedBy(value):
            raise TypeError("TimetableDay cannot set a non-ITimetableActivity "
                            "(got %r)" % (value,))
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        self.activities[key] = value

    def __delitem__(self, key):
        del self.activities[key]


class TimetableActivity:

    implements(ITimetableActivity)

    def __init__(self, title=None):
        self.title = title


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
                        activity = timetable[day_id][period.title]
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

