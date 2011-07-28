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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""Timetable integration with SchoolTool app.
XXX: move to schooltool/app/timetable.py or similar.
"""
import zope.lifecycleevent
import zope.lifecycleevent.interfaces
from zope.proxy import sameProxiedObjects
from zope.interface import implements, implementer
from zope.component import adapts, adapter, getUtility
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.interfaces import IContainer
from zope.container.btree import BTreeContainer
from zope.intid.interfaces import IIntIds

from schooltool.app.app import StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import DateRange
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.interfaces import ISchoolYear
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


# XXX: TimetableAppInit missing ?
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

