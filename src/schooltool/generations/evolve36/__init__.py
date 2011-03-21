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
Upgrade SchoolTool to generation 36.


"""
from ZODB.broken import Broken
from zope.app.generations.utility import findObjectsProviding
from zope.app.publication.zopepublication import ZopePublication
from zope.intid.interfaces import IIntIds
from zope.container.interfaces import INameChooser
from zope.component import getUtility
from zope.component.hooks import getSite, setSite

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.testing.mock import ModulesSnapshot
from schooltool.timetable.app import SchoolToolSchedules
from schooltool.timetable.timetable import TimetableContainer
from schooltool.timetable.timetable import Timetable
from schooltool.timetable.daytemplates import WeekDayTemplates
from schooltool.timetable.daytemplates import SchoolDayTemplates
from schooltool.timetable.daytemplates import DayTemplate
from schooltool.timetable.daytemplates import TimeSlot
from schooltool.timetable.schedule import Period

APP_TIMETABLES_KEY = 'schooltool.timetable.timetables'


def assert_not_broken(*objects):
    for obj in objects:
        broken_list = []
        if isinstance(obj, Broken):
            broken_list.append(obj)
        try:
            attrs = sorted(set(list(obj.__dict__) +
                               list(obj.__class__.__dict__)))
        except:
            attrs = []
        finally:
            for name in attrs:
                a = getattr(obj, name)
                if isinstance(a, Broken):
                    broken_list.append((obj, name, a))
        assert not broken_list, broken_list


class BuildContext(object):
    _options = None
    def __init__(self, **kw):
        self._options = dict(kw)

    def __getattr__(self, name):
        if name in self._options:
            return self._options[name]
        return object.__getattr__(self, name)

    def expand(self, **options):
        new_options = dict(self._options)
        new_options.update(options)
        return BuildContext(**new_options)


class DayTemplateScheduleBuilder(object):
    schedule_attr = ''
    schedule_factory = None
    days = None

    def read(self, schema):
        # populate self.days
        raise NotImplementedError()

    def addDayTemplate(self, templates, day):
        # add day from self.days to the template
        raise NotImplementedError()

    def build(self, context):
        if (self.schedule_factory is None or
            not self.schedule_attr):
            raise NotImplementedError()

        schedule = self.schedule_factory()
        setattr(context.timetable, self.schedule_attr, schedule)
        schedule.__parent__ = context.timetable
        schedule.__name__ = unicode(self.schedule_attr)
        schedule.initTemplates()
        templates = schedule.templates

        for day in self.days:
            self.addDayTemplate(templates, day)


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

    def read(self, schema):
        assert_not_broken(schema)
        self.days = []
        for day_id, day in schema.items():
            assert_not_broken(day)
            self.days.append({
                    'title': unicode(day_id),
                    'periods': self.readPeriods(day),
                    })

    def addDayTemplate(self, templates, day):
        # XXX: umm, that's not very nice, isn't it
        day_key = day['title']

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

    def read(self, schema):
        raise NotImplementedError()

    def addDayTemplate(self, templates, day):
        # XXX: umm, that's not very nice, isn't it
        day_key = day['title']

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

    def read(self, schema):
        model = schema.model
        assert_not_broken(model)

        self.days = []
        for weekday in range(7):
            template = model.dayTemplates.get(weekday)
            if template is None:
                template = model.dayTemplates.get(None)

            slots = self.readSlots(template)
            self.days.append({
                    'title': u'%d' % weekday, # XXX: ummm???
                    'time_slots': slots,
                    })


class SchoolDayTimeSlotsBuilder(TimeSlotsBuilder):
    schedule_factory = SchoolDayTemplates

    def read(self, schema):
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

    def read(self, schema):
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

        self.periods.read(schema)
        self.time_slots.read(schema)

    def build(self, context):
        # XXX: what if timezone is broken or outdated?
        if self.timezone is None:
            timezone = IApplicationPreferences(context.app).timezone
        else:
            timezone = self.timezone

        # XXX: probably take some sane defaluts from context.schoolyear
        first, last = None, None

        timetable = Timetable(
            first, last,
            title=self.title,
            timezone=timezone)
        context.timetables[self.__name__] = timetable
        timetable.__parent__ = context.timetables

        self.periods.build(context.expand(timetable=timetable))
        self.time_slots.build(context.expand(timetable=timetable))

        if self.set_default:
            context.timetables.default = timetable


class TimetableContainerBuilder(object):
    year_int_id = None
    timetables = None

    def read(self, schema_container):
        assert_not_broken(schema_container)

        self.year_int_id = int(schema_container.__name__)

        default_id = schema_container._default_id

        self.timetables = []
        for key, schema in list(schema_container.items()):
            assert_not_broken(schema)
            builder = TimetableBuilder()
            if (default_id is not None and default_id == key):
                builder.set_default = True
            builder.read(schema)
            self.timetables.append(builder)

    def build(self, context):
        key = unicode(self.year_int_id)
        container = context.timetable_root[key] = TimetableContainer()
        schoolyear = getUtility(IIntIds).getObject(self.year_int_id)
        for builder in self.timetables:
            builder.build(context.expand(
                    timetables=container,
                    schoolyear=schoolyear))


class SchoolTimetablesBuilder(object):
    builders = None

    def read(self, app):
        assert_not_broken(app)
        schema_root = app['schooltool.timetable.schooltt']
        self.builders = []
        for container in schema_root.values():
            builder = TimetableContainerBuilder()
            assert_not_broken(container)
            builder.read(container)
            self.builders.append(builder)

    def clean(self, app):
        del app['schooltool.timetable.schooltt']

    def build(self, context):
        if APP_TIMETABLES_KEY not in context.app:
            context.app[APP_TIMETABLES_KEY] = SchoolToolSchedules()
        timetable_root = context.app[APP_TIMETABLES_KEY]
        for builder in self.builders:
            builder.build(context.expand(timetable_root=timetable_root))


# XXX: This holds references to substitute classes
#      so that they can be pickled afterwards.
from schooltool.generations.evolve36 import model

def evolveTimetables(app):
    modules = ModulesSnapshot()

    modules.mock_module('schooltool.timetable')
    modules.mock(model.substitutes)

    builders = [
        SchoolTimetablesBuilder()
        ]

    for builder in builders:
        builder.read(app)

    modules.restore()

    for builder in builders:
        builder.clean(app)

    for builder in builders:
        builder.build(BuildContext(app=app))


def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    old_site = getSite()

    apps = findObjectsProviding(root, ISchoolToolApplication)
    for app in apps:
        setSite(app)
        evolveTimetables(app)

    setSite(old_site)
