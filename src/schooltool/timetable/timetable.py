#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Timetables are meeting schedules created from scheduled day templates.
"""

import datetime

from persistent import Persistent
from persistent.list import PersistentList
from zope.interface import implements
from zope.container.btree import BTreeContainer

from schooltool.common import DateRange
from schooltool.timetable import interfaces
from schooltool.timetable.schedule import Meeting, Schedule


class Timetable(Persistent, Schedule):
    implements(interfaces.ITimetable)

    periods = None
    time_slots = None

    def iterMeetings(self, from_date, until_date):
        dates = DateRange(from_date, until_date)
        days = zip(dates, self.periods.iter(dates))
        for day_date, day_periods in days:
            meetings = []
            if day_periods is None:
                yield meetings
                continue
            for time_period in day_periods.values():
                tstart = time_period.tstart
                dtstart = datetime.datetime.combine(day_date, tstart)
                dtstart = dtstart.replace(tzinfo=self.timezone)
                meeting = Meeting(
                    dtstart, time_period.duration,
                    period=time_period,
                    meeting_id=None)
                meetings.append(meeting)
            yield sorted(meetings, key=lambda m: m.dtstart)


def combineTemplates(periods_template, time_slots_template):
    """Return ordered list of period, time_slot tuples."""
    result = []

    periods_by_activity = {}
    for period in periods_template.values():
        if period.activity_type not in periods_by_activity:
            periods_by_activity[period.activity_type] = []
        periods_by_activity[period.activity_type].append(period)

    for time_slot in time_slots_template.values():
        activity = time_slot.activity_type
        if (activity not in periods_by_activity or
            not periods_by_activity[activity]):
            continue # no more periods for this activity
        period = periods_by_activity[activity].pop(0)
        result.append((period, time_slot))
    return result


class TimetableContainer(BTreeContainer):
    implements(interfaces.ITimetableContainer)

    default_id = None

    @property
    def default(self):
        if self.default_id is None:
            return None
        return self.get(self.default_id, None)

    @default.setter
    def default(self, timetable):
        if timetable is None:
            self.default_id = None
            return
        key = timetable.__name__
        if key not in self:
            raise KeyError(key)
        self.default_id = key


class SelectedPeriodsSchedule(Persistent, Schedule):
    implements(interfaces.ISelectedPeriodsSchedule)

    # XXX: think about storing intid here
    # or maybe better - a relationship
    timetable = None

    _periods = None

    consecutive_periods_as_one = False

    def __init__(self, timetable, *args, **kw):
        Schedule.__init__(self, *args, **kw)
        self.timetable = timetable
        self._periods = PersistentList()

    @property
    def periods(self):
        result = []
        for day in self.timetable.periods.templates.values():
            result.extend([period for period in day.values()
                           if self.hasPeriod(period)])
        return result

    def periodKey(self, period):
        day = period.__parent__
        return (day.__name__, period.__name__)

    def hasPeriod(self, period):
        key = self.periodKey(period)
        return key in self._periods

    def addPeriod(self, period):
        key = self.periodKey(period)
        if key not in self._periods:
            self._periods.append(key)

    def removePeriod(self, period):
        key = self.periodKey(period)
        if key in self._periods:
            self._periods.remove(key)

    def iterMeetings(self, date, until_date=None):
        if self.schedule is None:
            return
        meetings = iterMeetingsInTimezone(
            self.schedule, self.timezone, date, until_date=until_date)
        periods = list(self.periods)
        for meeting in meetings:
            # XXX: update meetings by consecutive_periods_as_one
            # XXX: proxy issues may breed here
            if meeting.period in self.periods:
                yield meeting
