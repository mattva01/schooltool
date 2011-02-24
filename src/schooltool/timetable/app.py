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
from zope.interface import Interface, implements, implementer
from zope.component import adapter
from zope.component import getUtility
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.interfaces import IContainer
from zope.container.btree import BTreeContainer
from zope.intid.interfaces import IIntIds

from schooltool.app.app import StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.course.interfaces import ISection
from schooltool.timetable import interfaces
from schooltool.timetable.schedule import ScheduleContainer

TIMETABLES_KEY = 'schooltool.timetable.schedules'


class ISchoolYearsScheduleContainer(IContainer):
    """A container of schedules."""


class SchoolYearsScheduleContainer(BTreeContainer):
    implements(ISchoolYearsScheduleContainer,
               IAttributeAnnotatable)


class TimetableStartUp(StartUpBase):
    def __call__(self):
        if TIMETABLES_KEY not in self.app:
            self.app[TIMETABLES_KEY] = SchoolYearsScheduleContainer()

# XXX: also init on startup if missing


@implementer(interfaces.IScheduleContainer)
def getScheduleContainer(obj):
    int_ids = getUtility(IIntIds)
    obj_id = str(int_ids.getId(obj))
    app = ISchoolToolApplication(None)
    container = app[TIMETABLES_KEY].get(obj_id, None)
    if container is None:
        container = app[TIMETABLES_KEY][obj_id] = ScheduleContainer()
    return container
