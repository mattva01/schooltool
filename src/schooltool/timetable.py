#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
SchoolTool timetabling code.

$Id$
"""
import datetime
from sets import Set
from persistence import Persistent
from persistence.dict import PersistentDict
from zope.interface import implements
from schooltool.db import MaybePersistentKeysSet
from schooltool.interfaces import ITimetable, ITimetableWrite
from schooltool.interfaces import ITimetableDay, ITimetableDayWrite
from schooltool.interfaces import ITimetableActivity
from schooltool.interfaces import ISchooldayTemplate, ISchooldayTemplateWrite
from schooltool.interfaces import ITimetableModel
from schooltool.interfaces import ITimetabled, ICompositeTimetableProvider
from schooltool.interfaces import ITimetableSchemaService, ISchooldayPeriod
from schooltool.cal import Calendar, CalendarEvent
from schooltool.component import getRelatedObjects, FacetManager
from schooltool.uris import URIGroup

__metaclass__ = type


#
# Timetabling
#

class Timetable(Persistent):

    implements(ITimetable, ITimetableWrite)

    def __init__(self, day_ids=()):
        """day_ids is a sequence of the day ids of this timetable."""
        self.day_ids = day_ids
        self.days = PersistentDict()

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days.get(day, None)) for day in self.day_ids]

    def __getitem__(self, key):
        return self.days[key]

    def __setitem__(self, key, value):
        if not ITimetableDay.isImplementedBy(value):
            raise TypeError("Timetable cannot set a non-ITimetableDay "
                            "(got %r)" % (value,))
        if key not in self.day_ids:
            raise ValueError("Key %r not in day_ids %r" % (key, self.day_ids))
        self.days[key] = value

    def clear(self):
        for day in self.days.itervalues():
            for period in day.periods:
                day.clear(period)

    def update(self, other):
        # XXX Right now we're trusting the user that the periods of
        # XXX the timetable days are compatible.  Maybe that'll be enough?

        if self.day_ids != other.day_ids:
            raise ValueError("Cannot update -- timetables have different"
                             " sets of days: %r and %r" % (self.day_ids,
                                                           other.day_ids))
        for day_id in other.keys():
            for period, activities in other[day_id].items():
                for activity in activities:
                    self[day_id].add(period, activity)

    def cloneEmpty(self):
        other = Timetable(self.day_ids)
        for day_id in self.day_ids:
            other[day_id] = TimetableDay(self[day_id].periods)
        return other

    def __eq__(self, other):
        if isinstance(other, Timetable):
            return self.items() == other.items()
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, Timetable):
            return self.items() != other.items()
        else:
            return True


class TimetableDay(Persistent):

    implements(ITimetableDay, ITimetableDayWrite)

    def __init__(self, periods=()):
        self.periods = periods
        self.activities = PersistentDict()
        for p in periods:
            self.activities[p] = MaybePersistentKeysSet()

    def keys(self):
        return [period for period in self.periods if self.activities[period]]

    def items(self):
        return [(period, self.activities[period]) for period in self.periods]

    def __getitem__(self, key):
        return iter(self.activities[key])

    def clear(self, key):
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        self.activities[key].clear()

    def add(self, key, value):
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        if not ITimetableActivity.isImplementedBy(value):
            raise TypeError("TimetableDay cannot set a "
                            "non-ITimetableActivity (got %r)" % (value,))
        self.activities[key].add(value)

    def remove(self, key, value):
        if key not in self.periods:
            raise ValueError("Key %r not in periods %r" % (key, self.periods))
        self.activities[key].remove(value)

    def __eq__(self, other):
        if not isinstance(other, TimetableDay):
            return False
        if self.periods != other.periods:
            return False
        for period in self.periods:
            if Set(self.activities[period]) != Set(other.activities[period]):
                return False
        return True

    def __ne__(self, other):
        return not self == other


class TimetableActivity:
    """Timetable activity.

    Instances are immutable.
    """

    implements(ITimetableActivity)

    def __init__(self, title=None, owner=None):
        self._title = title
        self._owner = owner

    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)

    def __repr__(self):
        return "TimetableActivity(%r, %r)" % (self.title, self.owner)

    def __eq__(self, other):
        if isinstance(other, TimetableActivity):
            return self.title == other.title and self.owner == other.owner
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, TimetableActivity):
            return self.title != other.title or self.owner != other.owner
        else:
            return True

    def __hash__(self):
        return hash((self.title, self.owner))


#
#  Timetable model stuff
#

class SchooldayPeriod:

    implements(ISchooldayPeriod)

    def __init__(self, title, tstart, duration):
        self.title = title
        self.tstart = tstart
        self.duration = duration

    def __eq__(self, other):
        if not ISchooldayPeriod.isImplementedBy(other):
            return False
        return (self.title == other.title and
                self.tstart == other.tstart and
                self.duration == other.duration)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.title, self.tstart, self.duration))


class SchooldayTemplate:

    implements(ISchooldayTemplate, ISchooldayTemplateWrite)

    def __init__(self):
        self.events = Set()

    def __iter__(self):
        return iter(self.events)

    def add(self, obj):
        if not ISchooldayPeriod.isImplementedBy(obj):
            raise TypeError("SchooldayTemplate can only contain "
                            "ISchooldayPeriods (got %r)" % (obj,))
        self.events.add(obj)

    def remove(self, obj):
        self.events.remove(obj)


class BaseTimetableModel:
    """An abstract base class for timetable models.

    Subclasses must define these methods:

       def schooldayStrategy(self, date, generator):
           'Returns a day_id for a certain date'

       def _dayGenerator(self):
           'Returns a generator to be passed to each call to schooldayStrategy'
    """
    implements(ITimetableModel)

    timetableDayIds = ()
    dayTemplates = {}

    def createCalendar(self, schoolday_model, timetable):
        cal = Calendar(schoolday_model.first, schoolday_model.last)
        day_id_gen = self._dayGenerator()
        for date in schoolday_model:
            if schoolday_model.isSchoolday(date):
                day_id = self.schooldayStrategy(date, day_id_gen)
                day_template = self._getTemplateForDay(date)
                for period in day_template:
                    dt = datetime.datetime.combine(date, period.tstart)
                    if period.title in timetable[day_id].keys():
                        for activity in timetable[day_id][period.title]:
                            event = CalendarEvent(dt, period.duration,
                                                  activity.title)
                            cal.addEvent(event)
        return cal

    def _getTemplateForDay(self, date):
        try:
            return self.dayTemplates[date.weekday()]
        except KeyError:
            return self.dayTemplates[None]

    def schooldayStrategy(self, date, generator):
        raise NotImplementedError

    def _dayGenerator(self):
        raise NotImplementedError


class SequentialDaysTimetableModel(BaseTimetableModel):
    """A timetable model in which the school days go in sequence with
    shifts over non-schooldays:

    Mon     Day 1
    Tue     Day 2
    Wed     ----- National holiday!
    Thu     Day 3
    Fri     Day 4
    Sat     ----- Weekend
    Sun     -----
    Mon     Day 1
    Tue     Day 2
    Wed     Day 3
    Thu     Day 4
    Fri     Day 1
    Sat     ----- Weekend
    Sun     -----
    Mon     Day 2
    """

    def __init__(self, day_ids, day_templates):
        self.timetableDayIds = day_ids
        self.dayTemplates = day_templates

    def _dayGenerator(self):
        while True:
            for day_id in self.timetableDayIds:
                yield day_id

    def schooldayStrategy(self, date, generator):
        return generator.next()


class WeeklyTimetableModel(BaseTimetableModel):
    """A timetable model where the schedule depends only on weekdays."""

    timetableDayIds = "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"

    def __init__(self, day_ids=None, day_templates={}):
        self.dayTemplates = day_templates
        if day_ids is not None:
            self.timetableDayIds = day_ids

    def schooldayStrategy(self, date, generator):
        return self.timetableDayIds[date.weekday()]

    def _dayGenerator(self):
        return None


#
#  Things for integrating timetabling into the core code.
#

class TimetabledMixin:
    """A mixin providing ITimetabled with the default semantics of
    timetable composition by membership and logic for searching for
    ICompositeTimetableProvider facets.
    """

    implements(ITimetabled, ICompositeTimetableProvider)

    timetableSource = ((URIGroup, True), )

    def __init__(self):
        self.timetables = PersistentDict()

    def getCompositeTimetable(self, period_id, schema_id):
        sources = list(self.timetableSource)

        for facet in FacetManager(self).iterFacets():
            if ICompositeTimetableProvider.isImplementedBy(facet):
                sources += facet.timetableSource

        timetables = []
        for role, composite in sources:
            for related in getRelatedObjects(self, role):
                if composite:
                    tt = related.getCompositeTimetable(period_id, schema_id)
                else:
                    tt = related.timetables.get((period_id, schema_id))
                if tt is not None:
                    timetables.append(tt)
        try:
            timetables.append(self.timetables[period_id, schema_id])
        except KeyError:
            pass

        if not timetables:
            return None

        result = timetables[0].cloneEmpty()
        for tt in timetables:
            result.update(tt)

        return result


class TimetableSchemaService(Persistent):
    implements(ITimetableSchemaService)

    __parent__ = None
    __name__ = None

    def __init__(self):
        self.timetables = PersistentDict()

    def keys(self):
        return self.timetables.keys()

    def __getitem__(self, schema_id):
        return self.timetables[schema_id].cloneEmpty()

    def __setitem__(self, schema_id, timetable):
        prototype = timetable.cloneEmpty()
        self.timetables[schema_id] = prototype

    def __delitem__(self, schema_id):
        del self.timetables[schema_id]

