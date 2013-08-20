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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Synchronisation between timetables and calendars.
"""
import pytz

import zope.lifecycleevent.interfaces
from zope.annotation.interfaces import IAnnotations
from zope.component import adapts, adapter, getUtility
from zope.interface import implements
from zope.intid.interfaces import IIntIds
from zope.security.proxy import removeSecurityProxy

from schooltool.timetable import interfaces
from schooltool.app.cal import CalendarEvent, Calendar
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber

SCHEDULE_CALENDAR_KEY = 'schooltool.timetable.app.ScheduleCalendar'


class ScheduleCalendarEvent(CalendarEvent):
    """Period scheduled in a calendar."""
    implements(interfaces.IScheduleCalendarEvent)

    schedule = None # schedule responsible for this event
    period = None
    meeting_id = None

    def __init__(self, *args, **kw):
        self.schedule = kw.pop('schedule', None)
        # XXX: int id would be more appropriate here maybe
        self.period = kw.pop('period', None)
        self.meeting_id = kw.pop('meeting_id', None)
        super(ScheduleCalendarEvent, self).__init__(*args, **kw)
        if self.meeting_id is None:
            self.meeting_id = self.unique_id


class UpdateEventTitles(ObjectEventAdapterSubscriber):
    adapts(zope.lifecycleevent.interfaces.IObjectModifiedEvent,
           interfaces.IHaveSchedule)

    def __call__(self):
        title = getattr(self.object, 'title', u'')
        if not title:
            return
        calendar = interfaces.IScheduleCalendar(self.object, None)
        if calendar is None:
            return
        for event in calendar:
            if (interfaces.IScheduleCalendarEvent.providedBy(event)):
                event.title = title


class ImmutableScheduleCalendar(ImmutableCalendar):
    adapts(interfaces.ISchedule)
    implements(interfaces.IImmutableScheduleCalendar)

    schedule = None

    def __init__(self, schedule):
        self.schedule = schedule
        events = tuple(self.createEvents())
        super(ImmutableScheduleCalendar, self).__init__(events=events)

    def makeGUID(self, date, period, int_ids=None):
        if int_ids is None:
            int_ids = getUtility(IIntIds)
        return u'%s.%s.%s' % (
            date.isoformat(),
            int_ids.getId(self.schedule),
            int_ids.getId(period),
            )

    def createEvents(self):
        int_ids = getUtility(IIntIds)
        owner = interfaces.IHaveSchedule(self.schedule)
        title = getattr(owner, 'title', u'')

        schedule = self.schedule
        if (schedule.first is None or
            schedule.last is None):
            return # Empty schedule

        meetings = schedule.iterMeetings(schedule.first, schedule.last)

        for meeting in meetings:
            # We need to convert dtstart to UTC, because calendar
            # events insist on storing UTC time.
            dtstart = meeting.dtstart.astimezone(pytz.UTC)
            guid = self.makeGUID(dtstart.date(), meeting.period,
                                 int_ids=int_ids)

            event = ScheduleCalendarEvent(
                dtstart, meeting.duration, title,
                schedule=schedule,
                period=meeting.period,
                meeting_id=meeting.meeting_id,
                unique_id=guid)

            yield event


class ScheduleCalendar(Calendar):
    implements(interfaces.IScheduleCalendar)

    _synchronised_attrs = ('dtstart', 'duration',
                           'period', 'meeting_id',
                           'title')

    def updateEvent(self, event, other_event):
        _unspecified = object()
        changed = False
        for attr in self._synchronised_attrs:
            new_val = getattr(other_event, attr, _unspecified)
            if (new_val is not _unspecified and
                new_val != getattr(event, attr)):
                setattr(event, attr, new_val)
                changed = True
        return changed

    def updateSchedule(self, schedule):
        schedule = removeSecurityProxy(schedule)
        schedule_cal = interfaces.IImmutableScheduleCalendar(schedule)
        if schedule_cal is None:
            self.removeSchedule(schedule)
            return

        old_events = dict(
            [(e.unique_id, e) for e in removeSecurityProxy(self)
              if e.schedule is schedule])

        new_events = dict([(e.unique_id, e) for e in schedule_cal])

        old_set = set(old_events)
        new_set = set(new_events)

        for uid in sorted(old_set - new_set):
            self.removeEvent(old_events[uid])

        for uid in sorted(new_set - old_set):
            self.addEvent(new_events[uid])

        for uid in sorted(new_set & old_set):
            self.updateEvent(old_events[uid], new_events[uid])

    def removeSchedule(self, schedule):
        schedule = removeSecurityProxy(schedule)
        old_events = sorted([e for e in removeSecurityProxy(self)])
        for event in old_events:
            self.removeEvent(event)


@adapter(interfaces.IHaveSchedule)
def getScheduleCalendar(owner):
    annotations = IAnnotations(owner)
    try:
        return annotations[SCHEDULE_CALENDAR_KEY]
    except KeyError:
        calendar = ScheduleCalendar(owner)
        annotations[SCHEDULE_CALENDAR_KEY] = calendar
        return calendar
getScheduleCalendar.factory = ScheduleCalendar


class UpdateScheduleCalendar(ObjectEventAdapterSubscriber):
    def __call__(self):
        owner = interfaces.IHaveSchedule(self.object, None)
        if owner is None:
            return
        calendar = interfaces.IScheduleCalendar(owner, None)
        if calendar is None:
            return
        container = interfaces.IScheduleContainer(owner, None)
        if container is None:
            return

        calendar.updateSchedule(container)


class RemoveScheduleCalendar(ObjectEventAdapterSubscriber):
    def __call__(self):
        owner = interfaces.IHaveSchedule(self.object, None)
        if owner is None:
            return
        calendar = interfaces.IScheduleCalendar(owner, None)
        if calendar is None:
            return
        container = interfaces.IScheduleContainer(owner, None)
        if container is None:
            return
        calendar.removeSchedule(self.object)

