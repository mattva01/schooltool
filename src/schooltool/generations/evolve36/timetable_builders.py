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
Timetable builders.
"""
from zope.intid.interfaces import IIntIds
from zope.container.interfaces import INameChooser
from zope.component import getUtility

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.generations.evolve36.helper import assert_not_broken
from schooltool.timetable.app import SchoolToolSchedules
from schooltool.timetable.timetable import TimetableContainer
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period

APP_TIMETABLES_KEY = 'schooltool.timetable.timetables'


class DayTemplateScheduleBuilder(object):
    schedule_attr = ''
    schedule_factory = None
    days = None

    def read(self, schema, context):
        # populate self.days
        raise NotImplementedError()

    def addDayTemplate(self, templates, day_key, day):
        # add day from self.days to the template
        raise NotImplementedError()

    def buildSchedule(self, timetable):
        if (self.schedule_factory is None or
            not self.schedule_attr):
            raise NotImplementedError()

        schedule = self.schedule_factory()
        setattr(timetable, self.schedule_attr, schedule)
        schedule.__parent__ = timetable
        schedule.__name__ = unicode(self.schedule_attr)
        schedule.initTemplates()
        return schedule

    def build(self, timetable, context):
        schedule = self.buildSchedule(timetable)
        for day in self.days:
            # XXX: title as key is not very safe, isn't it
            self.addDayTemplate(schedule.templates, day['title'], day)


class PeriodsBuilder(DayTemplateScheduleBuilder):
    days = None
    schedule_attr = 'periods'
    schedule_factory = None

    def readPeriods(self, schema_day):
        periods = []
        for period_name in schema_day.periods:
            homeroom = bool(period_name in schema_day.homeroom_period_ids)
            periods.append({
                    'title': unicode(period_name),
                    'activity_type': homeroom and 'homeroom' or 'lesson',
                    })
        return periods

    def read(self, schema, context):
        assert_not_broken(schema)
        self.days = []
        for day_id, day in schema.items():
            assert_not_broken(day)
            self.days.append({
                    'title': unicode(day_id),
                    'periods': self.readPeriods(day),
                    })

    def addDayTemplate(self, templates, day_key, day):
        template = DayTemplate(title=day['title'])
        templates[day_key] = template

        name_chooser = INameChooser(template)
        for item in day['periods']:
            period = Period(title=item['title'],
                            activity_type=item['activity_type'])
            key = name_chooser.chooseName('', period)
            template[key] = period


class WeekDayPeriodsBuilder(PeriodsBuilder):
    schedule_factory = WeekDayTemplates

    weekday_keys = ["Monday", "Tuesday", "Wednesday",
                    "Thursday", "Friday", "Saturday", "Sunday"]

    def getDay(self, weekday):
        key = self.weekday_keys[weekday]
        days = dict([(day['title'], day) for day in self.days])
        if key in days:
            return days[key]
        if 'None' in days:
            day = dict(days['None'])
            day['title'] = unicode(key) # XXX: hmmm
            return day
        return None

    def build(self, timetable, context):
        schedule = self.buildSchedule(timetable)

        for weekday in range(7):
            day = self.getDay(weekday)
            key = schedule.getWeekDayKey(weekday)
            self.addDayTemplate(schedule.templates, key, day)


class SchoolDayPeriodsBuilder(PeriodsBuilder):
    schedule_factory = SchoolDayTemplates


class TimeSlotsBuilder(DayTemplateScheduleBuilder):
    schedule_factory = None
    schedule_attr = 'time_slots'
    days = None

    def readSlots(self, school_day_template):
        if school_day_template is None:
            return []

        assert_not_broken(school_day_template)
        assert_not_broken(*list(school_day_template))

        slots = [{'tstart': slot.tstart,
                  'duration': slot.duration,
                  'activity_type': None, # XXX: !!!
                  }
                 for slot in school_day_template]
        return slots

    def read(self, schema, context):
        raise NotImplementedError()

    def addDayTemplate(self, templates, day_key, day):
        template = DayTemplate(title=day['title'])
        templates[day_key] = template

        name_chooser = INameChooser(template)
        for item in day['time_slots']:
            time_slot = TimeSlot(
                item['tstart'], item['duration'],
                activity_type=item['activity_type'])
            key = name_chooser.chooseName('', time_slot)
            template[key] = time_slot


class WeekDayTimeSlotsBuilder(TimeSlotsBuilder):
    schedule_factory = WeekDayTemplates

    weekdays = ["Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday", "Sunday"]

    def read(self, schema, context):
        model = schema.model
        assert_not_broken(model)

        self.days = []
        for weekday in range(7):
            template = model.dayTemplates.get(weekday)
            if template is None:
                template = model.dayTemplates.get(None)

            slots = self.readSlots(template)
            self.days.append({
                    'title': self.weekdays[weekday],
                    'time_slots': slots,
                    })

    def build(self, timetable, context):
        schedule = self.buildSchedule(timetable)

        for weekday, day in enumerate(self.days):
            key = schedule.getWeekDayKey(weekday)
            self.addDayTemplate(schedule.templates, key, day)


class SchoolDayTimeSlotsBuilder(TimeSlotsBuilder):
    schedule_factory = SchoolDayTemplates

    def read(self, schema, context):
        model = schema.model
        assert_not_broken(model)

        self.days = []
        for day_id in model.timetableDayIds:
            template = model.dayTemplates[day_id]
            slots = self.readSlots(template)
            self.days.append({
                    'title': unicode(day_id),
                    'time_slots': slots,
                    })


class TimetableBuilder(object):

    __name__ = None
    timezone = None
    title = None

    periods = None
    time_slosts = None
    set_default = False

    def read(self, schema, context):
        assert_not_broken(schema)

        self.timezone = unicode(schema.timezone)
        self.title = unicode(schema.title)
        self.__name__ = schema.__name__

        model_name = schema.model.__class__.__name__

        if model_name == 'SequentialDaysTimetableModel':
            self.periods = SchoolDayPeriodsBuilder()
            self.time_slots = WeekDayTimeSlotsBuilder()

        elif model_name == 'SequentialDayIdBasedTimetableModel':
            self.periods = SchoolDayPeriodsBuilder()
            self.time_slots = SchoolDayTimeSlotsBuilder()

        elif model_name == 'WeeklyTimetableModel':
            self.periods = WeekDayPeriodsBuilder()
            self.time_slots = WeekDayTimeSlotsBuilder()

        self.periods.read(schema, context())
        self.time_slots.read(schema, context())

    def build(self, timetables, context):
        # XXX: what if timezone is broken or outdated?
        if self.timezone is None:
            timezone = IApplicationPreferences(context.app).timezone
        else:
            timezone = self.timezone

        first, last = context.schoolyear.first, context.schoolyear.last

        timetable = Timetable(
            first, last,
            title=self.title,
            timezone=timezone)
        timetables[self.__name__] = timetable
        timetable.__parent__ = timetables

        self.periods.build(timetable, context(timetables=timetables))
        self.time_slots.build(timetable, context(timetables=timetables))

        if self.set_default:
            timetables.default = timetable


class TimetableContainerBuilder(object):
    year_int_id = None
    timetables = None

    def read(self, schema_container, context):
        assert_not_broken(schema_container)

        self.year_int_id = int(schema_container.__name__)

        default_id = schema_container._default_id

        self.timetables = []
        for key, schema in list(schema_container.items()):
            assert_not_broken(schema)
            builder = TimetableBuilder()
            if (default_id is not None and default_id == key):
                builder.set_default = True
            builder.read(schema, context(schema_container=schema_container))
            self.timetables.append(builder)

    def build(self, timetable_root, context):
        key = unicode(self.year_int_id)
        container = timetable_root[key] = TimetableContainer()
        schoolyear = getUtility(IIntIds).getObject(self.year_int_id)
        for builder in self.timetables:
            builder.build(container, context(timetable_root=timetable_root,
                                             schoolyear=schoolyear))


class SchoolTimetablesBuilder(object):
    builders = None

    def read(self, app, context):
        assert_not_broken(app)
        schema_root = app['schooltool.timetable.schooltt']
        self.builders = []
        for container in schema_root.values():
            builder = TimetableContainerBuilder()
            assert_not_broken(container)
            builder.read(container, context(app=app))
            self.builders.append(builder)

    def clean(self, app, context):
        del app['schooltool.timetable.schooltt']

    def build(self, app, context):
        if APP_TIMETABLES_KEY not in app:
            app[APP_TIMETABLES_KEY] = SchoolToolSchedules()
        timetable_root = app[APP_TIMETABLES_KEY]

        for builder in self.builders:
            builder.build(timetable_root, context(app=app))
