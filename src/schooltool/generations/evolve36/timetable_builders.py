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
Timetable builders.
"""
import itertools
import pytz
import datetime
from persistent.list import PersistentList

from zope.container.interfaces import INameChooser
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.generations.evolve36.helper import assert_not_broken
from schooltool.generations.evolve36.helper import BuildContext
from schooltool.timetable.app import SchoolToolSchedules
from schooltool.timetable.timetable import TimetableContainer
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period
from schooltool.timetable.schedule import MeetingException

APP_TIMETABLES_KEY = 'schooltool.timetable.timetables'


def createDayTemplates(timetable, factory, attr):
    schedule = factory()
    setattr(timetable, attr, schedule)
    schedule.__parent__ = timetable
    schedule.__name__ = unicode(attr)
    schedule.initTemplates()
    return schedule


class PeriodsBuilder(object):
    days = None

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
                    'id': day_id,
                    'title': unicode(day_id),
                    'periods': self.readPeriods(day),
                    })

    def addDayTemplate(self, templates, day_key, day):
        period_map = {}
        template = DayTemplate(title=day['title'])
        templates[day_key] = template

        name_chooser = INameChooser(template)
        for item in day['periods']:
            period = Period(title=item['title'],
                            activity_type=item['activity_type'])
            key = name_chooser.chooseName('', period)
            template[key] = period
            period_map[(day['id'], item['title'])] = period
        return BuildContext(period_map=period_map)


class WeekDayPeriodsBuilder(PeriodsBuilder):
    weekday_keys = ("Monday", "Tuesday", "Wednesday",
                    "Thursday", "Friday", "Saturday", "Sunday")
    timetable_day_keys = ()

    def read(self, schema, context):
        PeriodsBuilder.read(self, schema, context)
        if schema.model.timetableDayIds:
            self.timetable_day_keys = tuple(schema.model.timetableDayIds)

    def getDay(self, weekday):
        try:
            key = self.timetable_day_keys[weekday]
        except IndexError:
            key = self.weekday_keys[weekday]
        days = dict([(day['title'], day) for day in self.days])
        if key in days:
            return days[key]
        if 'None' in days:
            day = dict(days['None'])
            day['title'] = unicode(key) # XXX: hmmm
            return day
        return {'id': key,
                'title': unicode(key),
                'periods': []}

    def build(self, timetable, context):
        schedule = createDayTemplates(
            timetable, WeekDayTemplates, 'periods')

        result = BuildContext(period_map={})
        for weekday in range(7):
            day = self.getDay(weekday)
            key = unicode(weekday)
            built = self.addDayTemplate(schedule.templates, key, day)
            result.period_map.update(built.period_map)
        return result(schedule=schedule)


class SchoolDayPeriodsBuilder(PeriodsBuilder):

    def build(self, timetable, context):
        schedule = createDayTemplates(
            timetable, SchoolDayTemplates, 'periods')

        result = BuildContext(period_map={})
        for day in self.days:
            # XXX: title as key is not very safe, isn't it
            built = self.addDayTemplate(schedule.templates, day['title'], day)
            result.period_map.update(built.period_map)
        return result(schedule=schedule)


class TimeSlotsBuilder(object):
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
        schedule = createDayTemplates(
            timetable, WeekDayTemplates, 'time_slots')

        for weekday, day in enumerate(self.days):
            key = unicode(weekday)
            self.addDayTemplate(schedule.templates, key, day)
        return BuildContext(schedule=schedule)


class SchoolDayTimeSlotsBuilder(TimeSlotsBuilder):
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

    def build(self, timetable, context):
        schedule = createDayTemplates(
            timetable, SchoolDayTemplates, 'time_slots')

        for day in self.days:
            # XXX: title as key is not very safe, isn't it
            self.addDayTemplate(schedule.templates, day['title'], day)
        return BuildContext(schedule=schedule)


class ExceptionDayBuilder(object):

    def getOriginalDayId(self, term, schema, day_date):
        raise NotImplementedError()

    def getTimeSlotTemplate(self, schema, date, day_id):
        raise NotImplementedError()

    def readReplacementDay(self, schema, date):
        day_id = schema.model.exceptionDayIds[date]
        schema_day = schema[day_id]
        time_slots = self.getTimeSlotTemplate(schema, date, day_id)

        result = [
            (date, day_id, period, slot.tstart, slot.duration)
            for (period, slot) in zip(schema_day.keys()), sorted(time_slots)]
        return result

    def readExceptionDay(self, schema, date, day_id):
        exception_day = schema.model.exceptionDays[date]
        schema_day = schema[day_id]
        schema_periods = schema_day.keys()
        result = [
            (date, day_id, period, slot.tstart, slot.duration)
            for (period, slot) in exception_day
            if period in schema_periods]
        return result

    def getTerm(self, schoolyear, date):
        for term in schoolyear.values():
            if date in term:
                return term
        return None

    def read(self, schema, context):
        self.templates = []

        for date in schema.model.exceptionDays:
            term = self.getTerm(context.schoolyear, date)
            if term is None:
                continue
            if date in schema.model.exceptionDayIds:
                day_id = schema.model.exceptionDayIds[date]
            else:
                day_id = self.getOriginalDayId(term, schema, date)
            self.templates.append(self.readExceptionDay(schema, date, day_id))

        for date in schema.model.exceptionDayIds:
            if date not in schema.model.exceptionDays:
                self.templates.append(self.readReplacementDay(schema, date))

    def build(self, timetable, context):
        period_map = context.period_map
        tz = pytz.timezone(timetable.timezone)
        by_date = {}

        for day_templates in self.templates:
            for n, info in enumerate(day_templates):
                date, day_id, period_id, tstart, duration = info

                period_key = (day_id, period_id)
                period = period_map.get(period_key)

                dtstart = datetime.datetime.combine(date, tstart)
                dtstart = dtstart.replace(tzinfo=tz)
                if period is None:
                    meeting_id = None
                else:
                    meeting_id = timetable.periodMeetingId(
                        date, period, n+1)
                meeting = MeetingException(
                    dtstart, duration,
                    period=period,
                    meeting_id=meeting_id)
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append(meeting)

        for date in by_date:
            timetable.exceptions[date] = PersistentList(
                sorted(by_date[date], key=lambda m: m.dtstart))
        return BuildContext(exceptions=timetable.exceptions)


class SequentialModelExceptions(ExceptionDayBuilder):

    def getOriginalDayId(self, term, schema, day_date):
        generator = itertools.cycle(schema.model.timetableDayIds)
        for date in term:
            if date == day_date:
                break
            if term.isSchoolday(date):
                if date not in schema.model.exceptionDayIds:
                    generator.next()
        if not term.isSchoolday(day_date):
            return None
        return generator.next()


class SequentialDaysModelExceptions(SequentialModelExceptions):

    def getTimeSlotTemplate(self, schema, date, day_id):
        return self.dayTemplates[date.weekday()]


class SequentialDayIdModelExceptions(SequentialModelExceptions):

    def getTimeSlotTemplate(self, schema, date, day_id):
        return schema.dayTemplates[day_id]


class WeeklyModelExceptions(ExceptionDayBuilder):

    def getOriginalDayId(self, term, schema, day_date):
        try:
            return schema.model.timetableDayIds[day_date.weekday()]
        except IndexError:
            return None

    def getTimeSlotTemplate(self, schema, date, day_id):
        return self.dayTemplates[date.weekday()]


class TimetableBuilder(object):

    __name__ = None
    timezone = None
    title = None

    periods = None
    time_slosts = None
    exceptions = None
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
            self.exceptions = SequentialDaysModelExceptions()

        elif model_name == 'SequentialDayIdBasedTimetableModel':
            self.periods = SchoolDayPeriodsBuilder()
            self.time_slots = SchoolDayTimeSlotsBuilder()
            self.exceptions = SequentialDayIdModelExceptions()

        elif model_name == 'WeeklyTimetableModel':
            self.periods = WeekDayPeriodsBuilder()
            self.time_slots = WeekDayTimeSlotsBuilder()
            self.exceptions = WeeklyModelExceptions()

        self.periods.read(schema, context())
        self.time_slots.read(schema, context())
        self.exceptions.read(schema, context())

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

        built_periods = self.periods.build(
            timetable, context(timetables=timetables))
        built_time_slots = self.time_slots.build(
            timetable, context(timetables=timetables))
        built_exceptions = self.exceptions.build(
            timetable, context(timetables=timetables,
                               period_map=built_periods.period_map))

        if self.set_default:
            timetables.default = timetable

        return BuildContext(timetable=timetable,
                            schema_id=self.__name__,
                            period_map=built_periods.period_map)


class TimetableContainerBuilder(object):
    year_int_id = None
    timetables = None

    def read(self, schema_container, context):
        assert_not_broken(schema_container)

        self.year_int_id = context.year_int_id
        schoolyear = getUtility(IIntIds).getObject(self.year_int_id)

        default_id = schema_container._default_id

        self.timetables = []
        for key, schema in list(schema_container.items()):
            assert_not_broken(schema)
            builder = TimetableBuilder()
            if (default_id is not None and default_id == key):
                builder.set_default = True
            builder.read(schema, context(schema_container=schema_container,
                                         schoolyear=schoolyear))
            self.timetables.append(builder)

    def build(self, timetable_root, context):
        key = unicode(self.year_int_id)
        container = timetable_root[key] = TimetableContainer()
        schoolyear = getUtility(IIntIds).getObject(self.year_int_id)

        result = BuildContext(period_map={})

        for builder in self.timetables:
            built = builder.build(
                container, context(timetable_root=timetable_root,
                                   schoolyear=schoolyear))

            schema_period_map = dict(
                [((built.schema_id, day_id, period_id), period)
                 for (day_id, period_id), period
                 in built.period_map.items()])

            result.period_map.update(schema_period_map)

        return result(timetables=container,
                      year_int_id=self.year_int_id)


class SchoolTimetablesBuilder(object):
    builders = None

    def read(self, app, context):
        assert_not_broken(app)
        schema_root = app['schooltool.timetable.schooltt']
        self.builders = []
        for container in schema_root.values():
            year_int_id = int(container.__name__)
            schoolyear = getUtility(IIntIds).queryObject(year_int_id)
            if schoolyear is None:
                # Dirty database: year was deleted, but timetable schemas
                #                 were left
                continue

            builder = TimetableContainerBuilder()

            assert_not_broken(container)
            builder.read(container, context(app=app,
                                            year_int_id=year_int_id))
            self.builders.append(builder)

    def clean(self, app, context):
        del app['schooltool.timetable.schooltt']

    def build(self, app, context):
        if APP_TIMETABLES_KEY not in app:
            app[APP_TIMETABLES_KEY] = SchoolToolSchedules()
        timetable_root = app[APP_TIMETABLES_KEY]

        result = BuildContext(period_map={})

        for builder in self.builders:
            built = builder.build(timetable_root, context(app=app))

            year_period_map = dict(
                [((built.year_int_id, schema_id, day_id, period_id), period)
                 for (schema_id, day_id, period_id), period
                 in built.period_map.items()])

            result.period_map.update(year_period_map)

        return result(timetable_root=timetable_root)
