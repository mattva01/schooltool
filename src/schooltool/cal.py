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
from schooltool.interfaces import ISchooldayCalendar
import datetime


__metaclass__ = type


class SchooldayCalendar:

    implements(ISchooldayCalendar)

    def __init__(self, start, end):
        self.start = start
        self.end = end
        self._schooldays = Set()

    def _validate(self, date):
        if not (self.start <= date < self.end):
            raise ValueError("Date %r not in period [%r, %r)" %
                             (date, self.start, self.end))

    def __contains__(self, date):
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
        for date in daterange(self.start, self.end):
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in daterange(self.start, self.end):
            if date.weekday() in weekdays and date in self:
                self.remove(date)


def daterange(date1, date2):
    """Returns a generator of the range of dates from date1 to date2.

    >>> from datetime import date
    >>> list(daterange(date(2003, 9, 1), date(2003, 9, 4)))
    [datetime.date(2003, 9, 1), datetime.date(2003, 9, 2), datetime.date(2003, 9, 3)]
    >>> list(daterange(date(2003, 9, 2), date(2003, 9, 1)))
    []

    """
    date = date1
    while date < date2:
        yield date
        date += datetime.date.resolution


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
