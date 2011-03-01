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
"""
Timetable integration.

XXX: should be moved out of shchooltool.term
"""

from zope.interface import implements, implementer
from zope.component import adapts, adapter
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.security.proxy import removeSecurityProxy

from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISubscriber
from schooltool.schoolyear.subscriber import EventAdapterSubscriber
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable.schema import clearTimetablesOnDeletion
from schooltool.term.interfaces import ITerm
from schooltool.term.term import getTermForDate, EmergencyDayEvent


class RemoveTimetablesOnTermDeletion(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ITerm)

    def __call__(self):
        return clearTimetablesOnDeletion(self.object, self.event)


class EmergencyDayTimetableSubscriber(EventAdapterSubscriber):
    adapts(EmergencyDayEvent)
    implements(ISubscriber)

    def __call__(self):
        term = getTermForDate(self.event.date)
        if term is None:
            return
        # Update all schemas
        ttschemas = ITimetableSchemaContainer(term)
        for schema in ttschemas.values():
            model = schema.model
            # XXX: removing of security proxies is evil
            exceptionDays = removeSecurityProxy(model.exceptionDays)
            exceptionDayIds = removeSecurityProxy(model.exceptionDayIds)
            exceptionDays[self.event.date] = SchooldayTemplate()
            day_id = removeSecurityProxy(model.getDayId(term, self.event.date))
            exceptionDayIds[self.event.replacement_date] = day_id


@adapter(ITerm)
@implementer(ITimetableSchemaContainer)
def getTimetableSchemaContainerForTerm(term):
    return ITimetableSchemaContainer(ISchoolYear(term))
