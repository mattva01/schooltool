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
import datetime


__metaclass__ = type


def daterange(date1, date2):
    """Returns a generator of the range of dates from date1 to date2.

    >>> from datetime import date
    >>> list(daterange(date(2003, 9, 1), date(2003, 9, 3)))
    [datetime.date(2003, 9, 1), datetime.date(2003, 9, 2), datetime.date(2003, 9, 3)]
    >>> list(daterange(date(2003, 9, 2), date(2003, 9, 1)))
    []

    """
    date = date1
    while date <= date2:
        yield date
        date += datetime.date.resolution


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
        for date in daterange(self.first, self.last):
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in daterange(self.first, self.last):
            if date.weekday() in weekdays and self.isSchoolday(date):
                self.remove(date)

    def clear(self):
        self._schooldays.clear()


class VEvent(dict):
    pass


class ICalReader:
    """An object which reads in an iCal of public holidays and marks
    them off the schoolday calendar.
    """

    def __init__(self, file):
        self.file = file

    def markNonSchooldays(self, cal):
        """Mark all the events in the iCal file as non-schooldays in a given
        SchooldayCalendar.
        """
        for event in self.read():
            if hasattr(event, 'dtstart'):
                cal.remove(event.dtstart)

    def readRecord(self):
        """A generator that returns one record at a time, as a tuple of
        (key, value, type).

        type can be None if not specified as ;VALUE=type kind of thing.
        """
        record = []

        def splitRecord():
            """Unfortunately, this doctest is not run by the suite.

            >>> record = ['FOO', ';VALUE=BAR', ':BAZ', 'FOO']
            >>> splitRecord()
            ('FOO', 'BAZFOO', 'BAR')
            """
            record_str = "".join(record)
            key_opts_str, value = record_str.split(":")
            # XXX -- the following works only by accident
            key_type = key_opts_str.split(";VALUE=")
            key = key_type[0]
            if len(key_type) > 1:
                type = key_type[1]
            else:
                type = None
            return key, value, type

        for line in self.file.readlines():
            if record and line[0] not in '\t ':
                yield splitRecord()
                record = [line.strip()]
            else:
                record.append(line.strip())
        yield splitRecord()

    def read(self):
        result = []
        obj = None
        for key, value, type in self.readRecord():
            if key == "BEGIN" and value == "VEVENT":
                obj = VEvent()
            elif key == "END" and value == "VEVENT":
                result.append(obj)
                obj = None
            elif type == 'DATE' and obj is not None:
                key = key.lower()
                y, m, d = int(value[0:4]), int(value[4:6]), int(value[6:8])
                setattr(obj, key, datetime.date(y, m, d))
                obj[key] = value
            elif obj is not None:
                key = key.lower()
                obj[key] = value
        return result


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
        return list(self.periods)

    def items(self):
        return [(period, self.activities.get(period, None))
                for period in self.periods]

    def __getitem__(self, key):
        if key in self.periods and not key in self.activities:
            return None
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


class SequentialDaysTimetableModel:

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

    implements(ITimetableModel)

    def __init__(self, day_ids, day_templates):
        self.timetableDayIds = day_ids
        self.dayTemplates = day_templates

    def createCalendar(self, schoolday_model, timetable):
        cal = Calendar(schoolday_model.first, schoolday_model.last)
        day_id_gen = self._nextDayId()
        for date in schoolday_model:
            if schoolday_model.isSchoolday(date):
                day_id = day_id_gen.next()
                day_template = self._getTemplateForDay(date)
                for period in day_template:
                    dt = datetime.datetime.combine(date, period.tstart)
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

    def _nextDayId(self):
        while True:
            for day_id in self.timetableDayIds:
                yield day_id


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
