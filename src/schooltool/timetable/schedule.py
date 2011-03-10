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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Scheduling of meetings.
"""
import pytz
import datetime
from persistent import Persistent
from persistent.list import PersistentList

from zope.interface import implements
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer

from schooltool.timetable import interfaces


class Period(Contained):
    implements(interfaces.IPeriod)

    title = None
    activity_type = None

    def __init__(self, title=None, activity_type=None):
        Contained.__init__(self)
        self.title = title
        self.activity_type = activity_type


class Meeting(Persistent):
    implements(interfaces.IMeeting)

    def __init__(self, dtstart, duration, period=None, meeting_id=None):
        self.dtstart = dtstart
        self.duration = duration
        self.period = period
        self.meeting_id = meeting_id


class Schedule(Contained):
    """A non-persistent abstract schedule."""
    implements(interfaces.ISchedule)

    first = None
    last = None
    title = None
    timezone = None

    def __init__(self, first, last, title=None, timezone='UTC'):
        Contained.__init__(self)
        self.title = title
        self.first = first
        self.last = last
        self.timezone = timezone

    def iterMeetings(date, until_date=None):
        return iter([])


def date_timespan(date, tzinfo=None):
    starts = datetime.datetime.combine(date, datetime.min).replace(tzinfo=tzinfo)
    ends = datetime.datetime.combine(date, datetime.max).replace(tzinfo=tzinfo)
    return starts, ends


def iterMeetingsInTimezone(schedule, other_timezone, date, until_date=None):
    if until_date == None:
        until_date = date
    start_time = date_timespan(date, tzinfo=other_timezone)[0]
    end_time = date_timespan(until_date, tzinfo=other_timezone)[1]

    tt_start_date = start_time.astimezone(schedule.timezone).date()
    tt_end_date = end_time.astimezone(schedule.timezone).date()
    if tt_start_date == tt_end_date:
        tt_end_date = None

    meetings = schedule.iterMeetings(tt_start_date, until_date=tt_end_date)
    for meeting in meetings:
        if (meeting.dtstart >= start_time or
            meeting.dtstart <= end_time):
            yield meeting


class SelectedPeriodsSchedule(Persistent, Schedule):
    implements(interfaces.ISelectedPeriodsSchedule)

    # XXX: think about storing intid here
    # or maybe better - a relationship
    schedule = None

    periods = None # XXX: think about storing list of intids here

    def __init__(self, schedule, *args, **kw):
        Schedule.__init__(self, *args, **kw)
        self.schedule = schedule
        self.periods = PersistentList()

    def iterMeetings(self, date, until_date=None):
        if self.schedule is None:
            return
        meetings = iterMeetingsInTimezone(
            self.schedule, self.timezone, date, until_date=until_date)
        for meeting in meetings:
            # XXX: proxy issues may breed here
            if meeting.period in self.periods:
                yield meeting


class ScheduleContainer(BTreeContainer):
    implements(interfaces.IScheduleContainer)

    timezone = None

    def __init__(self, timezone=pytz.utc):
        BTreeContainer.__init__(self)
        self.timezone = timezone

    @property
    def first(self):
        dates = [schedule.first for schedule in self.values()
                 if schedule.first is not None]
        return dates and min(dates) or None

    @property
    def last(self):
        dates = [schedule.last for schedule in self.values()
                 if schedule.last is not None]
        return dates and max(dates) or None

    def iterMeetings(self, date, until_date=None):
        meetings = []
        for schedule in self.values():
            tt_meetings = iterMeetingsInTimezone(
                schedule, self.timezone, date, until_date=until_date)
            meetings.append(list(tt_meetings))
        for meeting in sorted(meetings, key=lambda m: m.dtstart):
            yield meeting

