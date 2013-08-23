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

from schooltool.course.interfaces import ISection
from schooltool.generations.evolve36.helper import assert_not_broken
from schooltool.generations.evolve36.helper import BuildContext
from schooltool.generations.evolve36.timetable_builders import (
    APP_TIMETABLES_KEY)
from schooltool.timetable.schedule import ScheduleContainer
from schooltool.timetable.timetable import SelectedPeriodsSchedule
from schooltool.timetable.app import SchoolToolSchedules


TIMETABLE_DICT_KEY = 'schooltool.timetable.timetables'
APP_SCHEDULES_KEY = 'schooltool.timetable.schedules'


class ScheduleBuilder(object):

    data = None
    store_data = ('__name__', 'first', 'last',
                   'timezone', 'term',
                   'consecutive_periods_as_one')
    schema_id = None
    year_int_id = None

    def read(self, timetable, context):
        self.data = {}
        for name in self.store_data:
            self.data[name] = getattr(timetable, name, None)

        for value in self.data.values():
            assert_not_broken(value)

        schema = timetable.schooltt
        assert_not_broken(schema)
        self.schema_id = schema.__name__
        self.year_int_id = int(schema.__parent__.__name__)

        self.selected_period_keys = [
            (self.year_int_id, self.schema_id, day_id, period_id)
            for day_id, period_id, activity in timetable.activities()]

    def build(self, container, context):
        timetables = context.shared.timetable_root[unicode(self.year_int_id)]
        timetable = timetables[self.schema_id]

        schedule = SelectedPeriodsSchedule(
            timetable, self.data['first'], self.data['last'],
            timezone=self.data['timezone'] or 'UTC')

        result = BuildContext(
            schedule=schedule,
            unique_key=(self.data['term'],
                        context.owner,
                        self.data['__name__'])
            )

        schedule.consecutive_periods_as_one = \
            self.data['consecutive_periods_as_one']

        for key in self.selected_period_keys:
            period = context.shared.period_map[key]
            schedule.addPeriod(period)

        container[self.data['__name__']] = schedule
        return result(term=self.data['term'])


class SchedulesBuilder(object):
    builders = None

    owner = None

    def read(self, timetable_dict, context):
        self.builders = []
        self.owner = timetable_dict.__parent__
        for key, timetable in sorted(timetable_dict.items()):
            assert_not_broken(timetable)
            builder = ScheduleBuilder()
            builder.read(timetable, context(owner=self.owner, key=key))
            self.builders.append(builder)

    def clean(self, context):
        annotations = IAnnotations(self.owner, None)
        if TIMETABLE_DICT_KEY in annotations:
            del annotations[TIMETABLE_DICT_KEY]

    def build(self, schedule_root, context):
        result = BuildContext(schedule_map={})
        if not ISection.providedBy(self.owner):
            return result(schedules=None)

        owner_int_id = getUtility(IIntIds).getId(self.owner)
        key = unicode(owner_int_id)
        container = schedule_root[key] = ScheduleContainer()

        for builder in self.builders:
            built = builder.build(
                container, context(schedule_root=schedule_root,
                                   owner=self.owner))
            result.schedule_map[built.unique_key] = built.schedule

        return result(schedules=container)


class AppSchedulesBuilder(object):
    builders = None

    def read(self, app, context):
        self.builders = []
        # Find objects that may have provided IOwnTimetables
        candidates = findObjectsProviding(app, IAnnotatable)
        for candidate in candidates:
            assert_not_broken(candidate)
            annotations = IAnnotations(candidate, None)
            if annotations is None:
                continue
            timetable_dict = annotations.get(TIMETABLE_DICT_KEY)
            if timetable_dict is None:
                continue
            assert_not_broken(timetable_dict)
            builder = SchedulesBuilder()
            builder.read(timetable_dict, context(app=app))
            self.builders.append(builder)

    def clean(self, app, context):
        for builder in self.builders:
            builder.clean(context)

    def build(self, app, context):

        if APP_SCHEDULES_KEY not in app:
            app[APP_SCHEDULES_KEY] = SchoolToolSchedules()
        schedule_root = app[APP_SCHEDULES_KEY]

        result = BuildContext(schedule_map={})

        for builder in self.builders:
            built = builder.build(schedule_root, context(app=app))
            result.schedule_map.update(built.schedule_map)

        return result(schedule_root=schedule_root)
