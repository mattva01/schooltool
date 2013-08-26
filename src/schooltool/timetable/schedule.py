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
"""
Scheduling of meetings.
"""
import pytz
import datetime
from persistent import Persistent
from persistent.dict import PersistentDict

from zope.component import getUtility
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer
from zope.intid.interfaces import IIntIds
from zope.interface import implements
from zope.proxy import sameProxiedObjects

from schooltool.common import DateRange
from schooltool.timetable import interfaces


class Period(Persistent, Contained):
    implements(interfaces.IPeriod)

    title = None
    activity_type = None

    def __init__(self, title=None, activity_type=None):
        Contained.__init__(self)
        self.title = title
        self.activity_type = activity_type


class Meeting(object):
    implements(interfaces.IMeeting)

    def __init__(self, dtstart, duration, period=None, meeting_id=None):
        self.dtstart = dtstart
        self.duration = duration
        self.period = period
        self.meeting_id = meeting_id

    def clone(self, **kw):
        dtstart = kw.get('dtstart', self.dtstart)
        duration = kw.get('duration', self.duration)
        period = kw.get('period', self.period)
        meeting_id = kw.get('meeting_id', self.meeting_id)
        return self.__class__(dtstart, duration,
                              period=period, meeting_id=meeting_id)

    def __repr__(self):
        parts = []
        if self.period is not None and self.period.title:
            parts.append(self.period.title)
        if self.dtstart is not None:
            parts.append('on %s' % self.dtstart.strftime('%Y-%m-%d %H:%M %Z'))
        return '<%s%s>' % (
            self.__class__.__name__, parts and ' '+' '.join(parts) or '')


class MeetingException(Persistent, Meeting):
    implements(interfaces.IMeetingException)

    _period_id = None

    @property
    def period(self):
        if self._period_id is None:
            return None
        int_ids = getUtility(IIntIds)
        return int_ids.queryObject(self._period_id)

    @period.setter
    def period(self, value):
        if value is None:
            self._period_id = None
        else:
            int_ids = getUtility(IIntIds)
            self._period_id = int_ids.getId(value)


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


def date_timespan(date, tzinfo=pytz.UTC):
    starts = datetime.datetime.combine(date, datetime.time.min)
    starts = tzinfo.localize(starts)
    ends = datetime.datetime.combine(date, datetime.time.max)
    ends = tzinfo.localize(ends)
    return starts, ends


def iterMeetingsInTimezone(schedule, other_timezone, date, until_date=None):
    if until_date == None:
        until_date = date
    other_timezone = pytz.timezone(other_timezone)
    schedule_timezone = pytz.timezone(schedule.timezone)

    start_time = date_timespan(date, tzinfo=other_timezone)[0]
    end_time = date_timespan(until_date, tzinfo=other_timezone)[1]

    tt_start_date = start_time.astimezone(schedule_timezone).date()
    tt_end_date = end_time.astimezone(schedule_timezone).date()
    if tt_start_date == tt_end_date:
        tt_end_date = None

    meetings = schedule.iterMeetings(tt_start_date, until_date=tt_end_date)
    for meeting in meetings:
        if (meeting.dtstart >= start_time and
            meeting.dtstart <= end_time):
            yield meeting


def iterMeetingsWithExceptions(meetings, exceptions, timezone,
                               date, until_date=None):
    if until_date is None:
        until_date = date

    by_date = {}
    for d in DateRange(date, until_date):
        if d in exceptions:
            by_date[d] = list(exceptions[d])

    tz = pytz.timezone(timezone)

    for original_meeting in meetings:
        meeting_date = original_meeting.dtstart.astimezone(tz).date()

        if meeting_date in exceptions:
            continue

        if meeting_date not in by_date:
            by_date[meeting_date] = list()
        by_date[meeting_date].append(original_meeting)

    for d in sorted(by_date):
        for meeting in sorted(by_date[d], key=lambda m: m.dtstart):
            yield meeting


class ScheduleContainer(BTreeContainer):
    implements(interfaces.IScheduleContainer)

    timezone = None
    exceptions = None

    def __init__(self, timezone='UTC'):
        BTreeContainer.__init__(self)
        self.timezone = timezone
        self.exceptions = PersistentDict()

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

    def iterOriginalMeetings(self, date, until_date=None):
        if until_date is None:
            until_date = date
        meetings = []
        for schedule in self.values():
            if not sameProxiedObjects(schedule.__parent__, self):
                # We are likely in the process of deleting/moving
                # this schedule.  Ignore.
                continue
            tt_meetings = iterMeetingsInTimezone(
                schedule, self.timezone, date, until_date=until_date)
            meetings.extend(list(tt_meetings))
        return sorted(meetings, key=lambda m: m.dtstart)

    def iterMeetings(self, date, until_date=None):
        meetings = self.iterOriginalMeetings(date, until_date=until_date)
        return iterMeetingsWithExceptions(
            meetings, self.exceptions, self.timezone,
            date, until_date=until_date)
