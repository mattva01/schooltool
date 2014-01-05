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
"""Timetable integration with SchoolTool app.
XXX: move to schooltool/app/timetable.py or similar.
"""
import zope.lifecycleevent
import zope.lifecycleevent.interfaces
from zope.proxy import sameProxiedObjects
from zope.interface import implements, implementer
from zope.component import adapts, adapter, getUtility, queryAdapter
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.interfaces import IContainer
from zope.container.btree import BTreeContainer
from zope.intid.interfaces import IIntIds

from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.common import DateRange
from schooltool.course.section import InstructorsCrowd, LearnersCrowd
from schooltool.course.parent import ParentsOfLearnersCrowd
from schooltool.course.interfaces import ISection
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.securitypolicy.crowds import Crowd, ConfigurableCrowd
from schooltool.securitypolicy.crowds import AggregateCrowd
from schooltool.timetable import interfaces
from schooltool.timetable.schedule import ScheduleContainer
from schooltool.timetable.timetable import TimetableContainer

SCHEDULES_KEY = 'schooltool.timetable.schedules'
TIMETABLES_KEY = 'schooltool.timetable.timetables'


class ISchoolToolSchedules(IContainer):
    """A container of schedules."""


class SchoolToolSchedules(BTreeContainer):
    implements(ISchoolToolSchedules,
               IAttributeAnnotatable)


class TimetableInit(InitBase):
    def __call__(self):
        self.app[SCHEDULES_KEY] = SchoolToolSchedules()
        self.app[TIMETABLES_KEY] = SchoolToolSchedules()


class TimetableStartUp(StartUpBase):
    def __call__(self):
        if SCHEDULES_KEY not in self.app:
            self.app[SCHEDULES_KEY] = SchoolToolSchedules()
        if TIMETABLES_KEY not in self.app:
            self.app[TIMETABLES_KEY] = SchoolToolSchedules()


@adapter(interfaces.IHaveSchedule)
@implementer(interfaces.IScheduleContainer)
def getScheduleContainer(obj):
    int_ids = getUtility(IIntIds)
    obj_id = str(int_ids.getId(obj))
    app = ISchoolToolApplication(None)
    container = app[SCHEDULES_KEY].get(obj_id, None)
    if container is None:
        container = app[SCHEDULES_KEY][obj_id] = ScheduleContainer()
    return container


@implementer(interfaces.IHaveSchedule)
@adapter(interfaces.IScheduleContainer)
def getScheduleContainerOwner(container):
    int_ids = getUtility(IIntIds)
    obj_id = int(container.__name__)
    obj = int_ids.queryObject(obj_id)
    return obj


@implementer(interfaces.IHaveSchedule)
@adapter(interfaces.ISchedule)
def getScheduleOwner(schedule):
    container = schedule.__parent__
    return interfaces.IHaveSchedule(container, None)


@implementer(interfaces.ITimetableContainer)
@adapter(interfaces.ITimetable)
def getTimetableParent(timetable):
    return timetable.__parent__


@adapter(interfaces.IHaveTimetables)
@implementer(interfaces.ITimetableContainer)
def getTimetableContainer(obj):
    int_ids = getUtility(IIntIds)
    obj_id = str(int_ids.getId(obj))
    app = ISchoolToolApplication(None)
    container = app[TIMETABLES_KEY].get(obj_id, None)
    if container is None:
        container = app[TIMETABLES_KEY][obj_id] = TimetableContainer()
    return container


@adapter(interfaces.ITimetableContainer)
@implementer(interfaces.IHaveTimetables)
def getTimetableContainerOwner(container):
    int_ids = getUtility(IIntIds)
    obj_id = int(container.__name__)
    obj = int_ids.queryObject(obj_id)
    return obj


@implementer(interfaces.IHaveTimetables)
@adapter(interfaces.ISchedule)
def getScheduleTimetableOwner(schedule):
    container = schedule.__parent__
    return interfaces.IHaveTimetables(container, None)


def activityVocabularyFactory():
    return lambda context: interfaces.activity_types


class UpdateSelectedPeriodsSchedules(ObjectEventAdapterSubscriber):
    adapts(zope.lifecycleevent.interfaces.IObjectModifiedEvent,
           interfaces.ITimetable)

    def __call__(self):
        app = ISchoolToolApplication(None)
        # XXX: extremely nasty loop through all schedules.
        schedule_containers = app[SCHEDULES_KEY]
        for container in schedule_containers.values():
            notify_container = False
            for schedule in container.values():
                if (interfaces.ISelectedPeriodsSchedule.providedBy(schedule) and
                    sameProxiedObjects(schedule.timetable, self.object)):
                    notify_container = True
            if notify_container:
                zope.lifecycleevent.modified(container)


class RemoveRelatedSelectedPeriodsSchedules(ObjectEventAdapterSubscriber):
    adapts(zope.lifecycleevent.interfaces.IObjectRemovedEvent,
           interfaces.ITimetable)

    def __call__(self):
        app = ISchoolToolApplication(None)
        # XXX: extremely nasty loop through all schedules.
        schedule_containers = app[SCHEDULES_KEY]
        for container in schedule_containers.values():
            for schedule in container.values():
                if (interfaces.ISelectedPeriodsSchedule.providedBy(schedule) and
                    sameProxiedObjects(schedule.timetable, self.object)):
                    del container[schedule.__name__]


class SchooldaysForSchedule(object):
    adapts(interfaces.ISchedule)
    implements(interfaces.ISchooldays)

    def __init__(self, context):
        self.schedule = context

    @property
    def schoolyear(self):
        owner = interfaces.IHaveSchedule(self.schedule)
        return ISchoolYear(owner)

    def __contains__(self, date):
        for term in self.schoolyear.values():
            if date in term:
                return term.isSchoolday(date)
        return False

    def __iter__(self):
        schedule = self.schedule
        dates = DateRange(schedule.first, schedule.last)
        return self.iterDates(dates)

    def iterDates(self, dates):
        for date in dates:
            if date in self:
                yield date


class SchooldaysForTimetable(SchooldaysForSchedule):
    adapts(interfaces.ITimetable)

    @property
    def schoolyear(self):
        owner = interfaces.IHaveTimetables(self.schedule)
        return ISchoolYear(owner)


class AdaptingParentCrowdTemplate(Crowd):
    """A crowd that contains principals who are allowed to access the context."""

    adapter = None
    interface = None
    permission = ''

    def contains(self, principal):
        adapted = self.adapter(self.context)
        pcrowd = queryAdapter(adapted, self.interface, self.permission,
                              default=None)
        if pcrowd is not None:
            return pcrowd.contains(principal)
        else:
            return False


class ScheduleViewersCrowd(AdaptingParentCrowdTemplate):
    adapter = interfaces.IHaveSchedule
    interface = interfaces.IScheduleParentCrowd
    permission = "schooltool.view"


class ScheduleEditorsCrowd(AdaptingParentCrowdTemplate):
    adapter = interfaces.IHaveSchedule
    interface = interfaces.IScheduleParentCrowd
    permission = "schooltool.edit"


class SectionScheduleViewers(AggregateCrowd):
    """Crowd of those who can see the section schedule."""
    adapts(ISection)

    def crowdFactories(self):
        return [InstructorsCrowd, LearnersCrowd, ParentsOfLearnersCrowd]


class ConfigurableScheduleEditors(ConfigurableCrowd):
    setting_key = 'instructors_can_schedule_sections'


class SectionScheduleEditors(AggregateCrowd):
    """Crowd of those who can see the section schedule."""
    adapts(ISection)

    def contains(self, principal):
        setting = ConfigurableScheduleEditors(self.context)
        if not setting.contains(principal):
            return False
        section = ISection(self.context, None)
        if section is None:
            return False
        contains = InstructorsCrowd(section).contains(principal)
        return contains

    def crowdFactories(self):
        return [ConfigurableScheduleEditors]


class SynchronizeScheduleTimezones(ObjectEventAdapterSubscriber):
    adapts(zope.lifecycleevent.interfaces.IObjectModifiedEvent,
           IApplicationPreferences)

    def __call__(self):
        prefs = self.object
        app = prefs.__parent__
        schedule_containers = app[SCHEDULES_KEY]
        for container in schedule_containers.values():
            if container.timezone != prefs.timezone:
                container.timezone = prefs.timezone
                zope.lifecycleevent.modified(container)


class SynchronizeTimetableTimezones(ObjectEventAdapterSubscriber):
    adapts(zope.lifecycleevent.interfaces.IObjectModifiedEvent,
           IApplicationPreferences)

    def __call__(self):
        prefs = self.object
        app = prefs.__parent__
        schedule_containers = app[TIMETABLES_KEY]
        for container in schedule_containers.values():
            for timetable in container.values():
                if timetable.timezone != prefs.timezone:
                    timetable.timezone = prefs.timezone
                    zope.lifecycleevent.modified(timetable)
