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
More or less interesting code:

__init__.py

  TimetableDict
    Timetable
      TimetableDay
        TimetableActivity

  SchooldayTemplate (stored in models)
    SchooldaySlot

  TimetableInit (makes TimetableSchemaContainerContainer)
  CompositeTimetables (IHaveTimetables -> ICompositeTimetables)
  TimetablesAdapter (IOwnTimetables -> ITimetables,
                     stores TimetableDict in annotations)

schema.py

  TimetableSchemaContainerContainer
    TimetableSchemaContainer
      TimetableSchema
        TimetableSchemaDay

  getTimetableSchemaContainer (makes TimetableSchemaContainer if needed)
  clearTimetablesOnDeletion

model.py

  SequentialDaysTimetableModel
  SequentialDayIdBasedTimetableModel
  WeeklyTimetableModel

  TimetableCalendarEvent (non-persistent, for immutable calendars)

  addEventsToCalendar
  removeEventsFromCalendar
  handleTimetableReplacedEvent

  PersistentTimetableCalendarEvent

"""

import rwproperty
import zope.event
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.proxy import sameProxiedObjects
from zope.component import queryAdapter
from zope.component import adapter
from zope.component import adapts, subscribers
from zope.interface import implementer
from zope.interface import implements
from zope.interface import directlyProvides
from zope.annotation.interfaces import IAnnotations
from zope.location.interfaces import ILocation
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.traversing.api import getPath
from zope.container.interfaces import INameChooser
from zope.container.contained import NameChooser
from zope.app.generations.utility import findObjectsProviding

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.common import IDateRange, DateRange
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
from schooltool.app.app import InitBase
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber

from schooltool.common import SchoolToolMessage as _


class Timetable(Persistent):
    """A timetable.

    A timetable is an ordered collection of timetable days that contain
    periods. Each period either contains a class, or is empty.

    A timetable represents the repeating lesson schedule for just one
    pupil, or one teacher, or one bookable resource.

    Contained in a TimetableDict.
    """
    implements(ITimetable, ITimetableWrite)

    __name__ = None
    __parent__ = None

    _first = None
    _last = None

    timezone = 'UTC'
    consecutive_periods_as_one = False

    term = None # always set for bound timetables
    schooltt = None # schema, always set for bound timetables

    model = None # model, set from views
    day_ids = None # list of day ids, set from views

    # persistent dict of day templates
    # keys - subset of day_ids
    # values - ITimetableDay, ITimetableDay.timetable set to self
    days = None

    @property
    def title(self):
        if self.term and self.schooltt:
            return "%s.%s" % (self.term.__name__, self.schooltt.__name__)
        else:
            return _("Unbound timetable.")

    def __init__(self, day_ids):
        self.day_ids = day_ids
        self.days = PersistentDict()
        self.model = None

    @rwproperty.getproperty
    def first(self):
        if self._first is None:
            term = getattr(self, 'term', None)
            if term is None:
                return None
            return term.first
        return self._first

    @rwproperty.getproperty
    def last(self):
        if self._last is None:
            term = getattr(self, 'term', None)
            if term is None:
                return None
            return term.last
        return self._last

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days[day]) for day in self.day_ids]

    def __getitem__(self, key):
        return self.days[key]

    def clear(self, send_events=True):
        for day in self.days.itervalues():
            for period in day.periods:
                day.clear(period, send_events)

    def activities(self):
        """Return all activities in this timetable.

        Returns a list of tuples (day_id, period_id, activity).
        """
        act = []
        for day_id in self.day_ids:
            for period_id, iactivities in self.days[day_id].items():
                act.extend([(day_id, period_id, activity)
                            for activity in iactivities])
        return act


class TimetableDay(Persistent):
    """A day in a timetable.

    A timetable day is an ordered collection of periods that each have
    a set of activites that occur during that period.

    Different days within the same timetable may have different periods.
    """
    implements(ITimetableDay, ITimetableDayWrite)

    timetable = None
    day_id = None

    periods = None # list of periods (titles, or maybe IDs?)
    homeroom_period_ids = None # IDs of homeroom periods
    activities = None # persistent dict of (period, set of TimetableActivity)

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
            self.activities[p] = set()

    def keys(self):
        return self.periods

    def items(self):
        return [(period, self.activities[period]) for period in self.periods]

    def __getitem__(self, period):
        return self.activities[period]

    def clear(self, period, send_events=True):
        """
        self.activities[period].clear() then
        send TimetableActivityRemovedEvent(act, self.day_id, period)
        """

    def add(self, period, activity, send_events=True):
        """
        self.activities[period].add(activity)
        TimetableActivityAddedEvent(activity, self.day_id, period)
        """

    def remove(self, period, value, send_events=True):
        """
        self.activities[period].remove(value)
        TimetableActivityRemovedEvent(activity, self.day_id, period)
        """


class TimetableActivity(object):
    """Timetable activity.

    Instances are immutable.

    Equivalent timetable activities must compare and hash equally after
    pickling and unpickling.
    """
    implements(ITimetableActivity)

    _title = None # usually course title
    _owner = None # usually section object
    _timetable = None # bound timetable
    _resources = None # tuple of section resources, probably unused nowadays

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



#class TimetableReplacedEvent(object):
#    implements(ITimetableReplacedEvent)
#    object = None
#    key = None
#    old_timetable = None
#    new_timetable = None
#
#    def __init__(self, object, key, old_timetable, new_timetable):
#        self.object = object
#        self.key = key
#        self.old_timetable = old_timetable
#        self.new_timetable = new_timetable
#
#
#class TimetableActivityEvent(object):
#    activity = None
#    day_id = None
#    period_id = None
#
#    def __init__(self, activity, day_id, period_id):
#        self.activity = activity
#        self.day_id = day_id
#        self.period_id = period_id
#
#
#class TimetableActivityAddedEvent(TimetableActivityEvent):
#    implements(ITimetableActivityAddedEvent)
#
#
#class TimetableActivityRemovedEvent(TimetableActivityEvent):
#    implements(ITimetableActivityRemovedEvent)


class SchooldaySlot(object):
    """A non-persistent time interval during which a period can be scheduled."""
    implements(ISchooldaySlot)

    tstart = None
    duration = None

    def __init__(self, tstart, duration):
        self.tstart = tstart
        self.duration = duration

    def __cmp__(self, other):
        return cmp((self.tstart, self.duration),
                   (other.tstart, other.duration))


class SchooldayTemplate(object):
    """Note: non-persistent object."""
    implements(ISchooldayTemplate, ISchooldayTemplateWrite)

    events = None # set of SchooldaySlot

    def __init__(self):
        self.events = set()

    def __iter__(self):
        return iter(sorted(self.events))


class TimetableDict(PersistentDict):
    """Container for [section] timetables.

    The id of the timetable is composed by joining term id and
    timetable schema id with a dot.  For example,"2005-fall.default"
    means a timetable for a term "2005-fall" with a timetable schema
    "default".
    """
    implements(ILocation, ITimetableDict)

    __name__ = 'timetables'
    __parent__ = None

    def __setitem__(self, key, value):
        """
        assert ITimetable.providedBy(value)
        PersistentDict.__setitem__(self, key, value)
        TimetableReplacedEvent(self.__parent__, key, old_value, value)
        """

    def __delitem__(self, key):
        """
        TimetableReplacedEvent(self.__parent__, key, value, None)
        """

#
# Integration
#
#


TIMETABLES_KEY = 'schooltool.timetable.timetables'

class TimetablesAdapter(object):
    """This adapter adapts any annotatable [section] object to be timetabled.

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

    def lookup(self, term, schooltt):
        for timetable in self.timetables.values():
            if (timetable.term is term and
                timetable.schooltt is schooltt):
                return timetable

    @property
    def terms(self):
        return list(set([timetable.term
                         for timetable in self.timetables.values()]))


class CompositeTimetables(object):
    """Adapter of IHaveTimetables to ICompositeTimetables.

    It just wraps a IHaveTimetables object under an ICompositeTimetables
    interface.
    """
    adapts(IHaveTimetables)
    implements(ICompositeTimetables)

    def __init__(self, context):
        self.context = context

    def collectSources(self, context):
        result = []
        if IOwnTimetables.providedBy(context):
            # context: Section - the only thing that owns timetables ATM
            result.extend([context])

        if IHaveTimetables.providedBy(context):
            # context: Person, Group, BaseResource, SchoolToolApplication

            # (URIMembership, member=URIMember, group=URIGroup)
            sources = list(getRelatedObjects(context, URIGroup))

            # (URIInstruction, instructor=URIInstructor, section=URISection)
            # This one got disabled some time ago:
            # (URISectionBooking, section=URISection, resource=URIResource)
            sources += list(getRelatedObjects(context, URISection))
            for obj in set(sources):
                result.extend(self.collectSources(obj))
        return result

    def collectTimetableSourceObjects(self):
        """getTimetableSourceObjects of registered subscribers return:

        def collectSources(context):

        """
        #objs = []
        #for adapter in subscribers((self.context, ), ITimetableSource):
        #    objs.extend(adapter.getTimetableSourceObjects())
        #return set(objs)
        return set(self.collectSources(self.context))

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


class TimetableInit(InitBase):
    """
    Set up the TimetableSchemaContainerContainer.
    """
    def __call__(self):
        from schooltool.timetable.schema import TimetableSchemaContainerContainer
        container = TimetableSchemaContainerContainer()
        self.app['schooltool.timetable.schooltt'] = container


#class TimetableOverlapError(Exception):
#    def __init__(self, schema, first, last, overlapping):
#        self.schema = schema
#        self.first = first
#        self.last = last
#        self.overlapping = overlapping
#
#
#class TimetableOverflowError(Exception):
#    def __init__(self, schema, first, last, term):
#        self.schema = schema
#        self.first = first
#        self.last = last
#        self.term = term
#
#
#def validateAgainstTerm(schema, first, last, term):
#    term_daterange = IDateRange(term)
#    if ((first is not None and first not in term_daterange) or
#        (last is not None and last not in term_daterange)):
#        raise TimetableOverflowError(
#            schema, first, last, term)
#
#
#def validateAgainstOthers(schema, first, last, timetables):
#    if first is None or last is None:
#        return
#    daterange = DateRange(first, last)
#    overlapping_timetables = []
#    for other_tt in timetables:
#        if (other_tt.schooltt is None or
#            not sameProxiedObjects(other_tt.schooltt, schema)):
#            continue
#        if (other_tt.first is None or other_tt.last is None):
#            continue
#        if daterange.overlaps(DateRange(other_tt.first, other_tt.last)):
#            overlapping_timetables.append(other_tt)
#    if overlapping_timetables:
#        raise TimetableOverlapError(
#            schema, first, last, overlapping_timetables)


def validateTimetable(timetable):
    """
    Validation on IObjectAddedEvent and IObjectModifiedEvent.
    """
    # Timetable dates must fit in term.
    validateAgainstTerm(
        timetable.schooltt, timetable.first, timetable.last,
        timetable.term)
    # Timetables with same schema cannot overlap in time.
    validateAgainstOthers(
        timetable.schooltt, timetable.first, timetable.last,
        [tt for tt in timetable.__parent__.values()
         if tt.__name__ != timetable.__name__])

