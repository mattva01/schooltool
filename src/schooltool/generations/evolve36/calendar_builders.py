#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
from zope.app.generations.utility import findObjectsProviding
from zope.annotation.interfaces import IAnnotatable, IAnnotations
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

from schooltool.app.overlay import URICalendarSubscriber
from schooltool.app.overlay import CalendarOverlayInfo
from schooltool.course.interfaces import ISection
from schooltool.generations.evolve36.helper import assert_not_broken
from schooltool.generations.evolve36.helper import BuildContext
from schooltool.generations.evolve36.model import ITimetableCalendarEvent
from schooltool.relationship import relate, unrelate
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.timetable.calendar import ScheduleCalendar

ST_CALENDAR_KEY = 'schooltool.app.calendar.Calendar'
SCHEDULE_CALENDAR_KEY = 'schooltool.timetable.app.ScheduleCalendar'


def getScheduleCalendar(owner):
    if not ISection.providedBy(owner):
        return None
    annotations = IAnnotations(owner)
    try:
        return annotations[SCHEDULE_CALENDAR_KEY]
    except KeyError:
        calendar = ScheduleCalendar(owner)
        annotations[SCHEDULE_CALENDAR_KEY] = calendar
        return calendar


class CalendarBuilder(object):

    events = None
    calendar = None

    store_data = ('__name__', 'first', 'last',
                   'timezone', 'term',
                   'consecutive_periods_as_one')

    def read(self, calendar, context):
        self.calendar = calendar
        self.events = []
        for event in calendar:
            assert_not_broken(event)
            if not ITimetableCalendarEvent.providedBy(event):
                continue
            if event.__parent__ != calendar:
                # Event does not belong directly to this calendar
                # Probably this is a booked resource
                continue
            activity = event.activity

            schema = activity.timetable.schooltt
            year_int_id = int(schema.__parent__.__name__)
            period_key = (year_int_id,
                          schema.__name__,
                          event.day_id,
                          event.period_id)

            timetable_key = (activity.timetable.term,
                             activity.owner,
                             activity.timetable.__name__)

            self.events.append({
                    'dtstart': event.dtstart,
                    'duration': event.duration,
                    'unique_id': event.unique_id,
                    'timetable_key': timetable_key,
                    'period_key': period_key,
                    # copy
                    'description': event.description,
                    'location': event.location,
                    'resources': event.resources,
                    })

    def clean(self, context):
        for event_info in self.events:
            event = self.calendar.find(event_info['unique_id'])
            self.calendar.removeEvent(event)

    def findEvent(self, calendar, period, dtstart, duration):
        for event in calendar:
            if (event.period is period and
                event.dtstart == dtstart and
                event.duration == duration):
                return event
        return None

    def build(self, context):
        int_ids = getUtility(IIntIds)
        schedule_calendars = set()
        calendar = getScheduleCalendar(self.calendar.__parent__)
        if calendar is None:
            return

        schedule_calendars.add(calendar)

        for event in self.events:
            schedule = context.shared.schedule_map.get(event['timetable_key'])
            if schedule is None:
                continue

            period = context.shared.period_map[event['period_key']]
            owner_int_id = int(schedule.__parent__.__name__)
            owner = int_ids.getObject(owner_int_id)

            calendar = getScheduleCalendar(owner)
            if calendar is None:
                continue

            if calendar not in schedule_calendars:
                schedule_calendars.add(calendar)

            new_event = self.findEvent(
                calendar, period, event['dtstart'], event['duration'])
            if new_event is not None:
                new_event.description = event['description']
                new_event.location = event['location']
                for resource in event['resources']:
                    if resource not in new_event.resources:
                        new_event.bookResource(resource)

        # XXX: maybe copy over old "free" section events here

        schedule_cal_relationships = [
            (cal, IRelationshipLinks(cal)) for cal in schedule_calendars]

        old_relationships = IRelationshipLinks(self.calendar)
        old_subscriptions = list(
            old_relationships.getLinksByRole(URICalendarSubscriber))

        for link in old_subscriptions:
            old_info = link.extra_info
            for schedule_cal, relationships in schedule_cal_relationships:
                info = CalendarOverlayInfo(schedule_cal, old_info.show,
                                           old_info.color1, old_info.color2)
                info.__parent__ = old_info.__parent__
                try:
                    relationships.find(
                        link.my_role, link.target, link.role, link.rel_type)
                except ValueError:
                    relate(link.rel_type,
                           (schedule_cal, link.my_role),
                           (link.target, link.role),
                           extra_info = info)

        for link in old_subscriptions:
            unrelate(link.rel_type,
                     (self.calendar, link.my_role),
                     (link.target, link.role))


class AppTimetableCalendarBuilder(object):
    builders = None

    def read(self, app, context):
        self.builders = []
        candidates = findObjectsProviding(app, IAnnotatable)
        for candidate in candidates:
            assert_not_broken(candidate)
            annotations = IAnnotations(candidate, None)
            if annotations is None:
                continue
            calendar = annotations.get(ST_CALENDAR_KEY)
            if calendar is None:
                continue
            assert_not_broken(calendar)
            builder = CalendarBuilder()
            builder.read(calendar, context(app=app))
            self.builders.append(builder)

    def clean(self, app, context):
        for builder in self.builders:
            builder.clean(context)

    def build(self, app, context):
        result = BuildContext()
        for builder in self.builders:
            built = builder.build(context(app=app))
        return result
