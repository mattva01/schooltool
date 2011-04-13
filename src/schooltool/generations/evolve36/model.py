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
Various timetable classes from generation 35.

"""

from persistent import Persistent
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import Interface, implements
from zope.container.interfaces import IContained
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer

from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.calendar.simple import SimpleCalendarEvent


substitutes = {}
def substituteIn(module):
    def register(target):
        name = '%s.%s' % (module, target.__name__)
        substitutes[name] = target
        return target
    return register


@substituteIn('schooltool.timetable.schema')
class TimetableSchemaContainerContainer(BTreeContainer):
    pass


@substituteIn('schooltool.timetable.schema')
class TimetableSchemaContainer(BTreeContainer):
    _default_id = None # default schema for calendars

    default_id = property(lambda self: self._default_id)

    def __delitem__(self, schema_id):
        BTreeContainer.__delitem__(self, schema_id)
        if schema_id == self.default_id:
            self._default_id = None

    def getDefault(self):
        return self[self.default_id]


@substituteIn('schooltool.timetable.interface')
class ITimetableSchemaDay(Interface):
    pass


@substituteIn('schooltool.timetable.schema')
class TimetableSchemaDay(Persistent):
    implements(ITimetableSchemaDay)
    periods = None # list of period IDs for this day
    homeroom_period_ids = None # list of homeroom period IDs

    def keys(self):
        return self.periods

    def items(self):
        return [(period, set()) for period in self.periods]

    def __getitem__(self, period):
        # XXX: wow...
        if period not in self.periods:
            raise KeyError(period)
        return set()


@substituteIn('schooltool.timetable.interface')
class ITimetableSchema(IContained):
    pass


@substituteIn('schooltool.timetable.schema')
class TimetableSchema(Persistent, Contained):
    implements(ITimetableSchema)

    title = None
    model = None
    timezone = None
    day_ids = None
    days = None

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days[day]) for day in self.day_ids]

    def __getitem__(self, key):
        return self.days[key]


@substituteIn('schooltool.timetable.interface')
class ITimetableModel(Interface):
    pass


@substituteIn('schooltool.timetable.interface')
class IWeekdayBasedTimetableModel(ITimetableModel):
    pass


@substituteIn('schooltool.timetable.interface')
class IDayIdBasedTimetableModel(ITimetableModel):
    pass


@substituteIn('schooltool.timetable.model')
class WeekdayBasedModelMixin:
    implements(IWeekdayBasedTimetableModel)


@substituteIn('schooltool.timetable.model')
class BaseTimetableModel(Persistent):
    timetableDayIds = () # day ids of templates built by timetable
    dayTemplates = {} # day id -> [(period, SchoolDaySlot), ...]
    exceptionDays = None # date -> [(period, SchoolDaySlot), ...]
    exceptionDayIds = None # exception date -> day id in dayTemplates


@substituteIn('schooltool.timetable.model')
class BaseSequentialTimetableModel(BaseTimetableModel):
    pass


@substituteIn('schooltool.timetable.model')
class WeeklyTimetableModel(BaseTimetableModel,
                           WeekdayBasedModelMixin):
    factory_id = "WeeklyTimetableModel"
    timetableDayIds = "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"


@substituteIn('schooltool.timetable.model')
class SequentialDaysTimetableModel(BaseSequentialTimetableModel,
                                   WeekdayBasedModelMixin):
    factory_id = "SequentialDaysTimetableModel"


@substituteIn('schooltool.timetable.model')
class SequentialDayIdBasedTimetableModel(BaseSequentialTimetableModel):
    implements(IDayIdBasedTimetableModel)
    factory_id = "SequentialDayIdBasedTimetableModel"


@substituteIn('schooltool.timetable')
class SchooldaySlot(object):
    tstart = None
    duration = None

    def __cmp__(self, other):
        return cmp((self.tstart, self.duration),
                   (other.tstart, other.duration))


@substituteIn('schooltool.timetable')
class SchooldayTemplate(object):
    events = ()
    def __iter__(self):
        return iter(sorted(self.events))


@substituteIn('schooltool.timetable.interface')
class ITimetableCalendarEvent(ISchoolToolCalendarEvent):
    """A calendar event that has been created from a timetable."""


class STAppCalendarEvent(SimpleCalendarEvent, Persistent, Contained):
    """Taken from schooltool.app.cal.CalendarEvent"""
    implements(ISchoolToolCalendarEvent, IAttributeAnnotatable)


@substituteIn('schooltool.timetable.model')
class PersistentTimetableCalendarEvent(STAppCalendarEvent):
    """A calendar event that has been created from a timetable."""
    implements(ITimetableCalendarEvent)

    __name__ = None
    __parent__ = None # calendar
    unique_id = None

    _day_id = None
    _period_id = None
    _activity = None
    _resources = None

    dtstart = None
    duration = None
    description = None
    location = None
    recurrence = None # XXX: for timetables? really?
    allday = None # XXX: for timetables? really?

    day_id = property(lambda self: self._day_id)
    period_id = property(lambda self: self._period_id)
    activity = property(lambda self: self._activity)
    title = property(lambda self: self.activity.title)
    resources = property(lambda self: self._resources)

    def unbookResource(self, resource):
        # XXX: Free the resources!
        #      Rebook them to real events if feasible.
        #if resource not in self.resources:
        #    raise ValueError('resource not booked')
        #self._resources = tuple([r for r in self.resources
        #                         if r is not resource])
        #ISchoolToolCalendar(resource).removeEvent(self)
        pass
