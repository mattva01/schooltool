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

import socket
import datetime
from sets import Set, ImmutableSet
from persistent import Persistent
from persistent.list import PersistentList
from persistent.dict import PersistentDict
from zope.interface import implements, moduleProvides
from schooltool.db import MaybePersistentKeysSet
from schooltool.interfaces import ITimetable, ITimetableWrite
from schooltool.interfaces import ITimetableDay, ITimetableDayWrite
from schooltool.interfaces import ITimetableActivity, ITimetableException
from schooltool.interfaces import ISchooldayPeriod
from schooltool.interfaces import ISchooldayTemplate, ISchooldayTemplateWrite
from schooltool.interfaces import ITimetableModel, IModuleSetup
from schooltool.interfaces import ITimetabled, ICompositeTimetableProvider
from schooltool.interfaces import ITimetableSchemaService
from schooltool.interfaces import ITimePeriodService
from schooltool.interfaces import ILocation, IMultiContainer
from schooltool.cal import Calendar, CalendarEvent
from schooltool.component import getRelatedObjects, FacetManager
from schooltool.component import getTimePeriodService
from schooltool.component import registerTimetableModel
from schooltool.component import getPath
from schooltool.uris import URIGroup

__metaclass__ = type

moduleProvides(IModuleSetup)


#
# Timetabling
#

class Timetable(Persistent):

    implements(ITimetable, ITimetableWrite, ILocation)

    def __init__(self, day_ids):
        """day_ids is a sequence of the day ids of this timetable."""
        self.day_ids = day_ids
        self.days = PersistentDict()
        self.__parent__ = None
        self.__name__ = None
        self.model = None
        self.exceptions = PersistentList()

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days.get(day, None)) for day in self.day_ids]

    def __getitem__(self, key):
        return self.days[key]

    def __setitem__(self, key, value):
        if not ITimetableDay.providedBy(value):
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
        #     the timetable days are compatible.  Maybe that'll be enough?

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
        other.model = self.model
        for day_id in self.day_ids:
            other[day_id] = TimetableDay(self[day_id].periods)
        return other

    def __eq__(self, other):
        if isinstance(other, Timetable):
            return self.items() == other.items() and self.model == other.model
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def itercontent(self):
        for day_id in self.day_ids:
            for period_id, iactivities in self.days[day_id].items():
                for activity in iactivities:
                    yield (day_id, period_id, activity)


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
        if not ITimetableActivity.providedBy(value):
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

    Equivalent timetable activities must compare and hash equally after
    pickling and unpickling.
    """

    implements(ITimetableActivity)

    def __init__(self, title=None, owner=None, resources=()):
        self._title = title
        self._owner = owner
        self._resources = ImmutableSet(resources)

    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)
    resources = property(lambda self: self._resources)

    def __repr__(self):
        return ("TimetableActivity(%r, %r, %r)"
                % (self.title, self.owner, self.resources))

    def __eq__(self, other):
        if isinstance(other, TimetableActivity):
            return (self.title == other.title and self.owner == other.owner
                    and self.resources == other.resources)
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.title, self.owner, self.resources))


class TimetableException:

    implements(ITimetableException)

    def __init__(self, date, period_id, activity, replacement):
        assert isinstance(date, datetime.date)
        self.date = date
        self.period_id = period_id
        self.activity = activity
        self.replacement = replacement


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
        if not ISchooldayPeriod.providedBy(other):
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
        if not ISchooldayPeriod.providedBy(obj):
            raise TypeError("SchooldayTemplate can only contain "
                            "ISchooldayPeriods (got %r)" % (obj,))
        self.events.add(obj)

    def remove(self, obj):
        self.events.remove(obj)

    def __eq__(self, other):
        if isinstance(other, SchooldayTemplate):
            return self.events == other.events
        else:
            return False

    def __ne__(self, other):
        return not self == other


class BaseTimetableModel(Persistent):
    """An abstract base class for timetable models.

    The models are persistent, but all the data structures inside,
    including the day templates, are not.  Timetable models are
    considered to be volatile.  Making the timetable models persistent
    is an optimisation.  Everything would work without that as well,
    but a separate pickle of a model would be included in each
    timetable.

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
        uid_suffix = '%s@%s' % (getPath(timetable), socket.getfqdn())
        cal = Calendar()
        day_id_gen = self._dayGenerator()
        for date in schoolday_model:
            if not schoolday_model.isSchoolday(date):
                continue
            day_id = self.schooldayStrategy(date, day_id_gen)
            day_template = self._getTemplateForDay(date)
            for period in day_template:
                dt = datetime.datetime.combine(date, period.tstart)
                if period.title not in timetable[day_id].keys():
                    continue
                for activity in timetable[day_id][period.title]:
                    # IDs for functionally derived calendars should be
                    # functionally derived, and not random
                    uid = '%d-%s' % (hash((activity.title, dt,
                                           period.duration)), uid_suffix)
                    event = CalendarEvent(dt, period.duration, activity.title,
                                          unique_id=uid)
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

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.timetableDayIds == other.timetableDayIds and
                    self.dayTemplates == other.dayTemplates)
        else:
            return False

    def __ne__(self, other):
        return not self == other


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

class TimetableDict(PersistentDict):

    implements(ILocation, IMultiContainer)

    __name__ = 'timetables'
    __parent__ = None

    def __setitem__(self, key, value):
        value.__parent__ = self
        value.__name__ = key
        PersistentDict.__setitem__(self, key, value)

    def __delitem__(self, key):
        value = self[key]
        value.__parent__ = None
        value.__name__ = None
        PersistentDict.__delitem__(self, key)

    def getRelativePath(self, child):
        if self[child.__name__]  != child:
            raise TypeError("Cannot determine path of  %r, because it does"
                            " not appear to be a child of %r"  %
                            (child, self))
        return "/".join(child.__name__)


class TimetabledMixin:
    """A mixin providing ITimetabled with the default semantics of
    timetable composition by membership and logic for searching for
    ICompositeTimetableProvider facets.
    """

    implements(ITimetabled, ICompositeTimetableProvider)

    timetableSource = ((URIGroup, True), )

    def __init__(self):
        self.timetables = TimetableDict()
        self.timetables.__parent__ = self

    def _sources(self):
        sources = list(self.timetableSource)
        for facet in FacetManager(self).iterFacets():
            if ICompositeTimetableProvider.providedBy(facet):
                sources += facet.timetableSource
        return sources

    def getCompositeTimetable(self, period_id, schema_id):
        timetables = []
        for role, composite in self._sources():
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

        parent = TimetableDict()
        parent.__parent__ = self
        parent.__name__ = 'composite-timetables'
        parent[period_id, schema_id] = result

        return result

    def listCompositeTimetables(self):
        keys = Set(self.timetables.keys())
        for role, composite in self._sources():
            for related in getRelatedObjects(self, role):
                if composite:
                    keys |= related.listCompositeTimetables()
                else:
                    keys.update(related.timetables.keys())
        return keys

    def makeCalendar(self):
        result = Calendar()
        result.__parent__ = self
        result.__name__ = 'timetable-calendar'
        timePeriodService = getTimePeriodService(self)
        for period_id, schema_id in self.listCompositeTimetables():
            schoolday_model = timePeriodService[period_id]
            tt = self.getCompositeTimetable(period_id, schema_id)
            cal = tt.model.createCalendar(schoolday_model, tt)
            result.update(cal)
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
        schema = self.timetables[schema_id].cloneEmpty()
        schema.__parent__ = self
        schema.__name__ = schema_id
        return schema

    def __setitem__(self, schema_id, timetable):
        prototype = timetable.cloneEmpty()
        self.timetables[schema_id] = prototype

    def __delitem__(self, schema_id):
        del self.timetables[schema_id]


class TimePeriodService(Persistent):
    implements(ITimePeriodService)

    __parent__ = None
    __name__ = None

    def __init__(self):
        self.periods = PersistentDict()

    def keys(self):
        return self.periods.keys()

    def __contains__(self, period_id):
        return period_id in self.periods

    def __getitem__(self, period_id):
        return self.periods[period_id]

    def __setitem__(self, period_id, schoolday_model):
        self.periods[period_id] = schoolday_model
        schoolday_model.__parent__ = self
        schoolday_model.__name__ = period_id

    def __delitem__(self, period_id):
        del self.periods[period_id]


def setUp():
    registerTimetableModel('SequentialDaysTimetableModel',
                           SequentialDaysTimetableModel)
    registerTimetableModel('WeeklyTimetableModel', WeeklyTimetableModel)
