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
Timetabling in SchoolTool
=========================

Note: timetabling here refers to the management of timetables of resources,
persons and groups.  It is not related to automatic timetable generation
or constraint solving.

Every application object (person, group or a resource) can have a number of
timetables.  First, the timetables can vary in the timetable schema (e.g. a
school may have a 4-day rotating timetable for classes, and then another
timetable for events that recur weekly). Second, there are separate timetables
for different time periods (terms).

Global containers
-----------------

A list of all defined timetable schemas is available in app['ttschemas']
(see ISchoolToolApplication, ITimetableSchemaContainer).

A list of all defined terms is available in app['terms'] (see
ISchoolToolApplication, ITermContainer).

Every timetable is defined for a given schema and a given term.  A tuple
consisting of the schema's ID and the terms's ID is often refered to as a
timetable's key.

Objects that have timetables
----------------------------

An object that has (or may have) timetables implements
IHaveTimetables.  The timetables themselves are stored in annotations
and can be accessed through by adapting the owner to ITimetables.

An object's composite timetable is derived by combining the object's
timetable with composite timetables of other objects, acquired by
calling subscribers of ITimetableSource interface.

Timetables
----------

A timetable consists of several days, each of which has several periods (the
sets of periods for different days may be different), and each period may have
zero or more timetable activities (two or more activities represent scheduling
conflicts).  See ITimetable, ITimetableDay, ITimetableActivity.

A timetable model describes the mapping between timetable days and calendar
days, and also the mapping between period IDs and time of the day.  Currently
SchoolTool has two kinds of timetable models:

  - Sequential days model may jump over calendar days if they are not school
    days.  For example, if July 3 was timetable day 3, and July 4 is a holiday,
    then July 5 will be timetable day 4.

  - Weekly model maps week days directly to timetable days, that is, Monday is
    always timetable day 1, and sunday is always timetable day 7.

It is possible to define additional models.  See ITimetableModel.

Example of a timetable::

    day_id:     Monday      Tuesday     ... Friday
    period_ids: 8:00-8:45   8:00-8:45   ... 8:00-8:40
                9:00-9:45   9:00-9:45   ... 8:55-9:35
                10:00-10:45 10:00-10:45 ... 10:50-10:30
                ...         ...         ... ...
                17:00-17:45 17:00-17:45 ... 16:15-16:55

    For this particular timetable, timetable days are named after week days
    (but note that there is no Saturday or Sunday because there are no classes
    on those days), periods are named after time periods, and the set of
    periods is the same for all days except for Friday.  This timetable
    will be used with a weekly timetable model.

Another example:

    day_id:     Day 1  Day 2 ... Day 10
    period_ids: 8:00   8:00  ... 8:00
                9:00   9:00  ... 9:00
                10:00  10:00 ... 10:00
                ...    ...   ... ...
                17:00  17:00 ... 17:00

    For this particular timetable, timetable days are named sequentially,
    periods are named after time periods (but only include the starting time),
    and the set of periods is the same for all days.  This timetable will
    be used with a sequential timetable model.

Another example:

    day_id:     Day 1  Day 2 ... Day 4
    period_ids: A      B     ... D
                B      C     ... A
                C      D     ... B
                D      A     ... C

    For this particular timetable, timetable days are named sequentially,
    periods are named arbitrarily, and the set of periods is the same for all
    days, but listed in a different order.  This timetable will be used with a
    sequential timetable model.

Timetable schemas
-----------------

A timetable schema is like a timetable that has no activities and no exeptions.
You can create an empty timetable by calling the createTimetable method of a
schema.  See ITimetableSchema, ITimetableSchemaDay.

$Id$
"""

from sets import Set

import zope.event
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.component import adapts, subscribers
from zope.interface import directlyProvides, implements

from zope.annotation.interfaces import IAnnotations
from zope.location.interfaces import ILocation
from zope.traversing.api import getPath
from zope.app.generations.utility import findObjectsProviding

from schooltool.calendar.simple import ImmutableCalendar

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar

from schooltool.timetable.interfaces import ITimetableCalendarEvent
from schooltool.timetable.interfaces import ITimetable, ITimetableWrite
from schooltool.timetable.interfaces import ITimetableDay, ITimetableDayWrite
from schooltool.timetable.interfaces import ITimetableDict
from schooltool.timetable.interfaces import ITimetableActivity
from schooltool.timetable.interfaces import ITimetableActivityAddedEvent
from schooltool.timetable.interfaces import ITimetableActivityRemovedEvent
from schooltool.timetable.interfaces import ITimetableReplacedEvent
from schooltool.timetable.interfaces import ISchooldaySlot
from schooltool.timetable.interfaces import ISchooldayTemplate
from schooltool.timetable.interfaces import ISchooldayTemplateWrite
from schooltool.timetable.interfaces import ITimetables, IHaveTimetables, IOwnTimetables
from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.timetable.interfaces import ITimetableSource
from schooltool.timetable.interfaces import ITimetableSchema
from schooltool.timetable.interfaces import Unchanged
from schooltool.term.interfaces import ITerm
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.app import InitBase

##############################################################################

#
# Timetabling
#

class Timetable(Persistent):

    implements(ITimetable, ITimetableWrite)

    __name__ = None
    __parent__ = None

    timezone = 'UTC'

    @property
    def title(self):
        return self.__name__

    @property
    def term(self):
        term_id = self.__name__.split('.')[0]
        return ISchoolToolApplication(None)['terms'][term_id]

    @property
    def schooltt(self):
        schooltt_id = self.__name__.split('.')[1]
        return ISchoolToolApplication(None)['ttschemas'][schooltt_id]

    def __init__(self, day_ids):
        """Create a new empty timetable.

        day_ids is a sequence of the day ids of this timetable.

        The caller must then assign a TimetableDay for each day ID and
        set the model before trying to use the timetable.
        """
        self.day_ids = day_ids
        self.days = PersistentDict()
        self.model = None

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days[day]) for day in self.day_ids]

    def __repr__(self):
        return '<Timetable: %s, %s, %s>' % (self.day_ids, dict(self.days),
                                            self.model)

    def __getitem__(self, key):
        return self.days[key]

    def __setitem__(self, key, value):
        if not ITimetableDay.providedBy(value):
            raise TypeError("Timetable can only contain ITimetableDay objects "
                            "(got %r)" % (value,))
        elif key not in self.day_ids:
            raise ValueError("Key %r not in day_ids %r" % (key, self.day_ids))
        elif value.timetable is not None:
            raise ValueError("%r already belongs to timetable %r"
                             % (value, value.timetable))
        value.timetable = self
        value.day_id = key
        self.days[key] = value

    def clear(self, send_events=True):
        for day in self.days.itervalues():
            for period in day.periods:
                day.clear(period, send_events)

    def update(self, other):
        if self.cloneEmpty() != other.cloneEmpty():
            raise ValueError("Timetables have different schemas")
        for day, period, activity in other.activities():
            self[day].add(period, activity, send_events=False)

    def cloneEmpty(self):
        other = Timetable(self.day_ids)
        other.model = self.model
        other.timezone = self.timezone
        for day_id in self.day_ids:
            other[day_id] = TimetableDay(self[day_id].periods,
                                         self[day_id].homeroom_period_ids)
        return other

    def __eq__(self, other):
        if ITimetable.providedBy(other):
            return (self.items() == other.items()
                    and self.model == other.model
                    and self.timezone == other.timezone)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def activities(self):
        act = []
        for day_id in self.day_ids:
            for period_id, iactivities in self.days[day_id].items():
                act.extend([(day_id, period_id, activity) for activity in iactivities])
        return act


class TimetableDay(Persistent):

    implements(ITimetableDay, ITimetableDayWrite)

    timetable = None
    day_id = None

    def __init__(self, periods=(), homeroom_period_ids=None):
        if homeroom_period_ids is not None:
            for id in homeroom_period_ids:
                assert id in periods
        else:
            homeroom_period_ids = []
        self.periods = periods
        self.homeroom_period_ids = homeroom_period_ids
        self.activities = PersistentDict()
        for p in periods:
            self.activities[p] = Set() # MaybePersistentKeysSet()

    def keys(self):
        return self.periods

    def items(self):
        return [(period, self.activities[period]) for period in self.periods]

    def __getitem__(self, period):
        return self.activities[period]

    def clear(self, period, send_events=True):
        if period not in self.periods:
            raise ValueError("Key %r not in periods %r" % (period,
                                                           self.periods))
        activities = [act.replace(timetable=self.timetable)
                      for act in self.activities[period]]
        self.activities[period].clear()
        # ping persistent dict, because we just modified a
        # non-persistent set
        self.activities[period] = self.activities[period]
        if send_events:
            for act in activities:
                ev = TimetableActivityRemovedEvent(act, self.day_id, period)
                zope.event.notify(ev)

    def add(self, period, activity, send_events=True):
        if period not in self.periods:
            raise ValueError("Key %r not in periods %r" % (period,
                                                           self.periods))
        if not ITimetableActivity.providedBy(activity):
            raise TypeError("TimetableDay can only contain ITimetableActivity"
                            " objects (got %r)" % (activity, ))

        if activity.timetable is None:
            activity = activity.replace(timetable=self.timetable)
        self.activities[period].add(activity)
        # ping persistent dict, because we just modified a
        # non-persistent set
        self.activities[period] = self.activities[period]

        if send_events:
            activity = activity.replace(timetable=self.timetable)
            event = TimetableActivityAddedEvent(activity, self.day_id, period)
            zope.event.notify(event)

    def remove(self, period, value, send_events=True):
        if period not in self.periods:
            raise ValueError("Key %r not in periods %r"
                             % (period, self.periods))
        self.activities[period].remove(value)
        # ping persistent dict, because we just modified a
        # non-persistent set
        self.activities[period] = self.activities[period]
        if send_events:
            activity = value.replace(timetable=self.timetable)
            ev = TimetableActivityRemovedEvent(activity, self.day_id, period)
            zope.event.notify(ev)

    def __eq__(self, other):
        if not ITimetableDay.providedBy(other):
            return False
        if self.periods != other.periods:
            return False
        if self.homeroom_period_ids != other.homeroom_period_ids:
            return False
        for period in self.periods:
            if Set(self.activities[period]) != Set(other.activities[period]):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class TimetableActivity(object):
    """Timetable activity.

    Instances are immutable.

    Equivalent timetable activities must compare and hash equally after
    pickling and unpickling.
    """

    implements(ITimetableActivity)

    def __init__(self, title=None, owner=None, timetable=None, resources=None):
        self._title = title
        self._owner = owner
        self._timetable = timetable
        if resources:
            self._resources = tuple(resources)
        else:
            self._resources = ()

    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)
    timetable = property(lambda self: self._timetable)
    resources = property(lambda self: self._resources)

    def __repr__(self):
        return ("TimetableActivity(%r, %r, %r, %r)"
                % (self.title, self.owner, self.timetable, self.resources))

    def __eq__(self, other):
        # Is it really a good idea to ignore self.timetable?
        # On further thought it does not matter -- we never compare activities
        # that come from timetables with different keys.
        if ITimetableActivity.providedBy(other):
            return self.title == other.title and self.owner == other.owner
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.title, self.owner))

    def replace(self, title=Unchanged, owner=Unchanged, timetable=Unchanged,
                resources=Unchanged):
        if title is Unchanged: title = self.title
        if owner is Unchanged: owner = self.owner
        if timetable is Unchanged: timetable = self.timetable
        if resources is Unchanged: resources = self.resources
        return TimetableActivity(title=title, owner=owner, timetable=timetable,
                                 resources=resources)


class TimetableReplacedEvent(object):

    implements(ITimetableReplacedEvent)

    def __init__(self, object, key, old_timetable, new_timetable):
        self.object = object
        self.key = key
        self.old_timetable = old_timetable
        self.new_timetable = new_timetable

    def __unicode__(self):
        return ("TimetableReplacedEvent object=%s (%s) key=%s"
                % (getPath(self.object), self.object.title, self.key))


class TimetableActivityEvent(object):

    def __init__(self, activity, day_id, period_id):
        self.activity = activity
        self.day_id = day_id
        self.period_id = period_id


class TimetableActivityAddedEvent(TimetableActivityEvent):
    implements(ITimetableActivityAddedEvent)


class TimetableActivityRemovedEvent(TimetableActivityEvent):
    implements(ITimetableActivityRemovedEvent)


class SchooldaySlot(object):

    implements(ISchooldaySlot)

    def __init__(self, tstart, duration):
        self.tstart = tstart
        self.duration = duration

    def __eq__(self, other):
        if not ISchooldaySlot.providedBy(other):
            return False
        return (self.tstart == other.tstart and
                self.duration == other.duration)

    def __ne__(self, other):
        return not (self == other)

    def __cmp__(self, other):
        return cmp((self.tstart, self.duration),
                   (other.tstart, other.duration))

    def __hash__(self):
        return hash((self.tstart, self.duration))


class SchooldayTemplate(object):

    # TODO: ideally, schoolday template should be an object that takes
    # a date and a period id and returns a schoolday period.  This way
    # we would get rid of the bizzare weekday -> schoolday template
    # mapping in the timetable model.

    implements(ISchooldayTemplate, ISchooldayTemplateWrite)

    def __init__(self):
        self.events = Set()

    def __iter__(self):
        return iter(sorted(self.events))

    def add(self, obj):
        if not ISchooldaySlot.providedBy(obj):
            raise TypeError("SchooldayTemplate can only contain "
                            "ISchooldaySlots (got %r)" % (obj,))
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



#
#  Things for integrating timetabling into the core code.
#

class TimetableDict(PersistentDict):

    implements(ILocation, ITimetableDict)

    __name__ = 'timetables'
    __parent__ = None

    def __setitem__(self, key, value):
        assert ITimetable.providedBy(value)
        keys = key.split(".")
        if len(keys) != 2 or not keys[0] or not keys[1]:
            raise ValueError("The key should be composed of a term id and a"
                             " schema id separated with a . (got %r)" % key)
        old_value = self.get(key)
        if old_value is not None:
            old_value.__parent__ = None
            old_value.__name__ = None
        value.__parent__ = self
        value.__name__ = key
        PersistentDict.__setitem__(self, key, value)
        event = TimetableReplacedEvent(self.__parent__, key, old_value, value)
        zope.event.notify(event)

    def __delitem__(self, key):
        value = self[key]
        value.__parent__ = None
        value.__name__ = None
        PersistentDict.__delitem__(self, key)
        zope.event.notify(
            TimetableReplacedEvent(self.__parent__, key, value, None))

    def clear(self):
        for key, value in self.items():
            del self[key]

    def _not_implemented(self, *args, **kw):
        raise NotImplementedError(
                "This method is not implemented in TimetableDict.  Feel free"
                " to implement it, if you need it, but make sure the semantics"
                " of changes are preserved (i.e. update __parent__ and"
                " __name__, and send out events when needed).")

    update = _not_implemented
    setdefault = _not_implemented
    pop = _not_implemented
    popitem = _not_implemented


TIMETABLES_KEY = 'schooltool.timetable.timetables'

class TimetablesAdapter(object):
    """This adapter adapts any annotatable object to be timetabled.

    It provides ``ITimetables`` with the default semantics of
    timetable composition by membership and logic for searching for
    ``ICompositeTimetableProvider`` facets.
    """
    implements(ITimetables)
    adapts(IOwnTimetables)

    def __init__(self, context):
        self.object = context
        annotations = IAnnotations(context)
        self.timetables = annotations.get(TIMETABLES_KEY)
        if self.timetables is None:
            self.timetables = annotations[TIMETABLES_KEY] = TimetableDict()
            self.timetables.__parent__ = context

    @property
    def terms(self):
        term_container = ISchoolToolApplication(None)['terms']
        term_ids = set()
        for key in self.timetables.keys():
            term_id = key.split('.')[0]
            term_ids.add(term_id)
        terms = [term_container[term_id]
                 for term_id in term_ids]
        return terms


class CompositeTimetables(object):
    """Adapter of IHaveTimetables to ICompositeTimetables.

    It just wraps a IHaveTimetables object under an ICompositeTimetables
    interface.

        >>> from schooltool.timetable.tests.test_timetable import Parent
        >>> obj = Parent()
        >>> ct = CompositeTimetables(obj)
        >>> ICompositeTimetables.providedBy(ct)
        True

        >>> obj.getCompositeTimetable = lambda term, schema: [term, schema]
        >>> ct.getCompositeTimetable("term", "schema")
        ['term', 'schema']

    """
    adapts(IHaveTimetables)
    implements(ICompositeTimetables)

    def __init__(self, context):
        self.context = context

    def collectTimetableSourceObjects(self):
        objs = []
        for adapter in subscribers((self.context, ), ITimetableSource):
            objs.extend(adapter.getTimetableSourceObjects())
        return set(objs)

    def makeTimetableCalendar(self, first=None, last=None):

        limited = (first is not None and
                   last is not None)
        def inRange(event):
            return first <= event.schoolDay() <= last

        events = []
        for obj in self.collectTimetableSourceObjects():
            cal = ISchoolToolCalendar(obj)
            for event in cal:
                if (ITimetableCalendarEvent.providedBy(event) and
                    (not limited or inRange(event))):
                    events.append(event)
        result = ImmutableCalendar(events)
        # Parent is needed so that we can find out the owner of this calendar.
        directlyProvides(result, ILocation)
        result.__parent__ = self.context
        result.__name__ = 'timetable-calendar'
        return result


def findRelatedTimetables(ob):
    """Finds all timetables in the app instance that use a given object

    The object can be either a school timetable or a term.

    Returns a list of Timetable objects.
    """
    if ITerm.providedBy(ob):
        index = 0
    elif ITimetableSchema.providedBy(ob):
        index = 1
    else:
        raise TypeError("Expected a Term or a TimetableSchema, got %r" %
                        (ob, ))

    app = getSchoolToolApplication(ob)
    timetables = []

    for ttowner in findObjectsProviding(app, IOwnTimetables):
        timetables += ITimetables(ttowner).timetables.values()

    result = []
    for tt in timetables:
        if tt.__name__.split('.')[index] == ob.__name__:
            result.append(tt)

    return result


class TimetableInit(InitBase):

    def __call__(self):
        from schooltool.timetable.schema import TimetableSchemaContainer
        self.app['ttschemas'] = TimetableSchemaContainer()


def registerTestSetup():
    from schooltool.testing import registry

    def addTTSchemasContainer(app):
        from schooltool.timetable.schema import TimetableSchemaContainer
        app['ttschemas'] = TimetableSchemaContainer()

    registry.register('ApplicationContainers', addTTSchemasContainer)

registerTestSetup()
del registerTestSetup
