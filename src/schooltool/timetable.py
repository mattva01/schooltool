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
for different time periods, such as semesters.

Global services
---------------

A list of all defined timetable schemas is available from the timetable schema
service (see getTimetableSchemaService, ITimetableSchemaService).

A list of all defined time periods is available from the time period service
(see getTermService, ITermService).

Timetable schemas and time periods are identified by alphanumeric IDs.

Every timetable is defined for a given schema and a given time period.  A tuple
consisting of the schema's ID and the time period's ID is often refered to as
a timetable's key.

Objects that have timetables
----------------------------

An object that has (or may have) timetables implements ITimettabled.

An object's composite timetable is derived by combining the object's timetable
with composite timetables of other objects, usually inherited through
relationships.  See also ICompositeTimetableProvider.

Timetables
----------

A timetable consists of several days, each of which has several periods (the
sets of periods for different days may be different), and each period may have
zero or more timetable activities (two or more activities represent scheduling
conflicts).  See ITimetable, ITimetableDay, ITimetableActivity.

A timetable may also have a list of exceptions that represent irregularities
in activities.  For example, a certain activity may be canceled on a certain
day, or an activity may be shifted in time, or it may be shortened.  See
ITimetableException.

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

A timetable schema is just a timetable that has no activities and no exeptions.
You can get a timetable schema by calling the cloneEmpty method of a timetable,
but usually cloneEmpty is used to create a new empty timetable from a schema.

Time periods
------------

A time period defines a range in time (e.g. September 1 to December 31,
2004) and for every day within that range it defines whether that day is a
schoolday or a holiday.


$Id$
"""

import socket
import datetime
import itertools
from sets import Set, ImmutableSet

from persistent import Persistent
from persistent.list import PersistentList
from persistent.dict import PersistentDict
import zope.event
from zope.interface import implements, moduleProvides, classProvides
from zope.interface import directlyProvides, implements, moduleProvides
from zope.app.traversing.api import getPath
from zope.app.location.traversing import LocationPhysicallyLocatable
from zope.component import provideAdapter, adapts
from zope.app.container.btree import BTreeContainer

from schoolbell.app.membership import URIGroup
from schoolbell.app.cal import CalendarEvent
from schoolbell.calendar.simple import ImmutableCalendar
from schoolbell.relationship import getRelatedObjects

from schooltool.interfaces import ITimetable, ITimetableWrite
from schooltool.interfaces import ITimetableDay, ITimetableDayWrite
from schooltool.interfaces import ITimetableActivity, ITimetableException
from schooltool.interfaces import ITimetableActivityAddedEvent
from schooltool.interfaces import ITimetableActivityRemovedEvent
from schooltool.interfaces import ITimetableExceptionList
from schooltool.interfaces import ITimetableExceptionEvent
from schooltool.interfaces import ITimetableExceptionAddedEvent
from schooltool.interfaces import ITimetableExceptionRemovedEvent
from schooltool.interfaces import ITimetableReplacedEvent
from schooltool.interfaces import ITimetableCalendarEvent
from schooltool.interfaces import IExceptionalTTCalendarEvent
from schooltool.interfaces import ISchooldayPeriod
from schooltool.interfaces import ISchooldayTemplate, ISchooldayTemplateWrite
from schooltool.interfaces import ITimetableModel
from schooltool.interfaces import ITimetableModelFactory
from schooltool.interfaces import ITimetabled, ICompositeTimetableProvider
from schooltool.interfaces import ITimetableSchemaService
from schooltool.interfaces import ITermService
from schooltool.interfaces import ILocation
from schooltool.interfaces import Unchanged
from schooltool.interfaces import IDateRange
from schooltool.interfaces import ITermCalendarWrite, ITermCalendar
from schooltool import getSchoolToolApplication

__metaclass__ = type



#
# Date ranges and schoolday models
#

class DateRange:

    implements(IDateRange)

    def __init__(self, first, last):
        self.first = first
        self.last = last
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))

    def __iter__(self):
        date = self.first
        while date <= self.last:
            yield date
            date += datetime.date.resolution

    def __len__(self):
        return (self.last - self.first).days + 1

    def __contains__(self, date):
        return self.first <= date <= self.last


class TermCalendar(DateRange, Persistent):

    implements(ITermCalendar, ITermCalendarWrite, ILocation)

    __name__ = None
    __parent__ = None

    def __init__(self, first, last):
        DateRange.__init__(self, first, last)
        self._schooldays = Set()

    def _validate(self, date):
        if not date in self:
            raise ValueError("Date %r not in term [%r, %r]" %
                             (date, self.first, self.last))

    def isSchoolday(self, date):
        self._validate(date)
        if date in self._schooldays:
            return True
        return False

    def add(self, date):
        self._validate(date)
        self._schooldays.add(date)
        self._schooldays = self._schooldays  # persistence

    def remove(self, date):
        self._validate(date)
        self._schooldays.remove(date)
        self._schooldays = self._schooldays  # persistence

    def addWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays and self.isSchoolday(date):
                self.remove(date)

    def toggleWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                if self.isSchoolday(date):
                    self.remove(date)
                else:
                    self.add(date)

    def reset(self, first, last):
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))
        self.first = first
        self.last = last
        self._schooldays.clear()


#
# Timetabling
#

class Timetable(Persistent):

    implements(ITimetable, ITimetableWrite)

    __name__ = None
    __parent__ = None

    def __init__(self, day_ids):
        """Create a new empty timetable.

        day_ids is a sequence of the day ids of this timetable.

        The caller must then assign a TimetableDay for each day ID and
        set the model before trying to use the timetable.
        """
        self.day_ids = day_ids
        self.days = PersistentDict()
        self.model = None
        self._exceptions = TimetableExceptionList(self)

    exceptions = property(lambda self: self._exceptions)

    def keys(self):
        return list(self.day_ids)

    def items(self):
        return [(day, self.days[day]) for day in self.day_ids]

    def __repr__(self):
        return '<Timetable: %s, %s, %s, %s>' % (self.day_ids, self.days,
                                                self.model, self.exceptions)

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
        for day, period, activity in other.itercontent():
            self[day].add(period, activity, False)
        self.exceptions.extend(other.exceptions)

    def cloneEmpty(self):
        other = Timetable(self.day_ids)
        other.model = self.model
        for day_id in self.day_ids:
            other[day_id] = TimetableDay(self[day_id].periods)
        return other

    def __eq__(self, other):
        if ITimetable.providedBy(other):
            return (self.items() == other.items()
                    and self.model == other.model
                    and self.exceptions == other.exceptions)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def itercontent(self):
        for day_id in self.day_ids:
            for period_id, iactivities in self.days[day_id].items():
                for activity in iactivities:
                    yield (day_id, period_id, activity)


class TimetableDay(Persistent):

    implements(ITimetableDay, ITimetableDayWrite)

    timetable = None
    day_id = None

    def __init__(self, periods=()):
        self.periods = periods
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

        if send_events:
            activity = activity.replace(timetable=self.timetable)
            event = TimetableActivityAddedEvent(activity, self.day_id, period)
            zope.event.notify(event)

    def remove(self, period, value, send_events=True):
        if period not in self.periods:
            raise ValueError("Key %r not in periods %r"
                             % (period, self.periods))
        self.activities[period].remove(value)
        if send_events:
            activity = value.replace(timetable=self.timetable)
            ev = TimetableActivityRemovedEvent(activity, self.day_id, period)
            zope.event.notify(ev)

    def __eq__(self, other):
        if not ITimetableDay.providedBy(other):
            return False
        if self.periods != other.periods:
            return False
        for period in self.periods:
            if Set(self.activities[period]) != Set(other.activities[period]):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class TimetableActivity:
    """Timetable activity.

    Instances are immutable.

    Equivalent timetable activities must compare and hash equally after
    pickling and unpickling.
    """

    implements(ITimetableActivity)

    def __init__(self, title=None, owner=None, resources=(), timetable=None):
        self._title = title
        self._owner = owner
        self._resources = ImmutableSet(resources)
        self._timetable = timetable

    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)
    resources = property(lambda self: self._resources)
    timetable = property(lambda self: self._timetable)

    def __repr__(self):
        return ("TimetableActivity(%r, %r, %r, %r)"
                % (self.title, self.owner, self.resources, self.timetable))

    def __eq__(self, other):
        # Is it really a good idea to ignore self.timetable?
        # On further thought it does not matter -- we never compare activities
        # that come from timetables with different keys.
        if ITimetableActivity.providedBy(other):
            return (self.title == other.title and self.owner == other.owner
                    and self.resources == other.resources)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.title, self.owner, self.resources))

    def replace(self, title=Unchanged, owner=Unchanged,
                      resources=Unchanged, timetable=Unchanged):
        if title is Unchanged: title = self.title
        if owner is Unchanged: owner = self.owner
        if resources is Unchanged: resources = self.resources
        if timetable is Unchanged: timetable = self.timetable
        return TimetableActivity(title=title, owner=owner,
                                 resources=resources, timetable=timetable)


class TimetableExceptionList:

    implements(ITimetableExceptionList)

    def __init__(self, timetable):
        self._list = PersistentList()
        self._timetable = timetable

    def __iter__(self):
        return iter(self._list)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, index):
        return self._list[index]

    def __eq__(self, other):
        return self._list == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def extend(self, exceptions):
        self._list.extend(exceptions)

    def append(self, exception):
        self._list.append(exception)
        tt = self._timetable
        if ILocation.providedBy(tt):
            event = TimetableExceptionAddedEvent(self._timetable, exception)
            zope.event.notify(event)

    def remove(self, exception):
        self._list.remove(exception)
        tt = self._timetable
        if ILocation.providedBy(tt) and IEventTarget.providedBy(tt.__parent__):
            event = TimetableExceptionRemovedEvent(self._timetable, exception)
            event.dispatch(tt.__parent__)


class TimetableReplacedEvent:

    implements(ITimetableReplacedEvent)

    def __init__(self, object, key, old_timetable, new_timetable):
        self.object = object
        self.key = key
        self.old_timetable = old_timetable
        self.new_timetable = new_timetable

    def __unicode__(self):
        return ("TimetableReplacedEvent object=%s (%s) key=%s"
                % (getPath(self.object), self.object.title, self.key))


class TimetableActivityEvent:

    def __init__(self, activity, day_id, period_id):
        self.activity = activity
        self.day_id = day_id
        self.period_id = period_id


class TimetableActivityAddedEvent(TimetableActivityEvent):
    implements(ITimetableActivityAddedEvent)


class TimetableActivityRemovedEvent(TimetableActivityEvent):
    implements(ITimetableActivityRemovedEvent)


class TimetableExceptionEvent:

    implements(ITimetableExceptionEvent)

    def __init__(self, timetable, exception):
        self.timetable = timetable
        self.exception = exception


class TimetableExceptionAddedEvent(TimetableExceptionEvent):
    implements(ITimetableExceptionAddedEvent)


class TimetableExceptionRemovedEvent(TimetableExceptionEvent):
    implements(ITimetableExceptionRemovedEvent)


class TimetableException(Persistent):

    implements(ITimetableException)

    def __init__(self, date, period_id, activity, replacement=None):
        self._date = date
        self._period_id = period_id
        self._activity = activity
        self.replacement = replacement

    def _setReplacement(self, replacement):
        if (replacement is not None and
            not IExceptionalTTCalendarEvent.providedBy(replacement)):
            raise ValueError("%r is not an exceptional TT event" % replacement)
        self._replacement = replacement

    date = property(lambda self: self._date)
    period_id = property(lambda self: self._period_id)
    activity = property(lambda self: self._activity)
    replacement = property(lambda self: self._replacement, _setReplacement)

    def __eq__(self, other):
        if ITimetableException.providedBy(other):
            return ((self.date, self.period_id, self.activity,
                     self.replacement) == (other.date, other.period_id,
                                           other.activity, other.replacement))
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return ('TimetableException(%r, %r, %r, %r)'
                % (self.date, self.period_id, self.activity, self.replacement))


#
#  Timetable model stuff
#


class TimetableCalendarEvent(CalendarEvent):

    implements(ITimetableCalendarEvent)

    period_id = property(lambda self: self._period_id)
    activity = property(lambda self: self._activity)

    def __init__(self, *args, **kwargs):
        self._period_id = kwargs.pop('period_id')
        self._activity = kwargs.pop('activity')
        CalendarEvent.__init__(self, *args, **kwargs)



class ExceptionalTTCalendarEvent(CalendarEvent):

    implements(IExceptionalTTCalendarEvent)

    exception = property(lambda self: self._exception)

    def __init__(self, *args, **kwargs):
        self._exception = kwargs.pop('exception')
        if not ITimetableException.providedBy(self._exception):
            raise ValueError('%r is not a timetable exception'
                             % self._exception)

        CalendarEvent.__init__(self, *args, **kwargs)



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

    # TODO: ideally, schoolday template should be an object that takes
    # a date and a period id and returns a schoolday period.  This way
    # we would get rid of the bizzare weekday -> schoolday template
    # mapping in the timetable model.

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

       def schooldayStrategy(self, date, day_iterator):
           '''Return a day_id for a certain date.

           Will be called sequentially for all school days.

           May return None if the schoolday model thinks that there should
           be no classes on this date.
           '''

       def _dayGenerator(self):
           '''Return an iterator to be passed to schooldayStrategy'''
    """
    implements(ITimetableModel)

    timetableDayIds = ()
    dayTemplates = {}

    def _validateDayTemplates(self):
        if None not in self.dayTemplates:
            for weekday in range(7):
                if weekday not in self.dayTemplates:
                    raise AssertionError("No day template for day %d,"
                                         " and no fallback either"
                                         % weekday)

    def createCalendar(self, schoolday_model, timetable):
        exceptions = {}
        for e in timetable.exceptions:
            exceptions[(e.date, e.period_id, e.activity)] = e
        uid_suffix = '%s@%s' % (getPath(timetable), socket.getfqdn())
        events = []
        day_id_gen = self._dayGenerator()

        for date in schoolday_model:
            day_id, periods = self._periodsInDay(schoolday_model, timetable,
                                                 date, day_id_gen)
            for period in periods:
                dt = datetime.datetime.combine(date, period.tstart)
                for activity in timetable[day_id][period.title]:
                    key = (date, period.title, activity)
                    exception = exceptions.get(key)
                    if exception is None:
                        # IDs for functionally derived calendars should be
                        # functionally derived, and not random
                        uid = '%d-%s' % (hash((activity.title, dt,
                                               period.duration)), uid_suffix)
                        event = TimetableCalendarEvent(
                                    dt, period.duration, activity.title,
                                    unique_id=uid,
                                    period_id=period.title, activity=activity)
                        events.append(event)
                    elif exception.replacement is not None:
                        events.append(exception.replacement)
        return ImmutableCalendar(events)

    def _periodsInDay(self, schoolday_model, timetable, day, day_id_gen=None):
        """Return a timetable day_id and a list of periods for a given day.

        if day_id_gen is not provided, a new generator is created and
        scrolled to the date requested.  If day_id_gen is provided, it
        is called once to gain a day_id.
        """
        if day_id_gen is None:
            # Scroll to the required day
            day_id_gen = self._dayGenerator()
            if day_id_gen is not None:
                for date in schoolday_model:
                    if date == day:
                        break
                    if schoolday_model.isSchoolday(date):
                        self.schooldayStrategy(date, day_id_gen)

        if not schoolday_model.isSchoolday(day):
            return None, []
        day_id = self.schooldayStrategy(day, day_id_gen)
        if day_id is None:
            return None, []

        # Now choose the periods that are in this day
        result = []
        day_template = self._getTemplateForDay(day)
        for period in day_template:
            dt = datetime.datetime.combine(day, period.tstart)
            if period.title in timetable[day_id].keys():
                result.append(period)

        result.sort(lambda x, y: cmp(x.tstart, y.tstart))
        return day_id, result

    def periodsInDay(self, schoolday_model, timetable, day):
        """See ITimetableModel.periodsInDay"""
        return self._periodsInDay(schoolday_model, timetable, day)[1]

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

    classProvides(ITimetableModelFactory)

    def __init__(self, day_ids, day_templates):
        self.timetableDayIds = day_ids
        self.dayTemplates = day_templates
        self._validateDayTemplates()

    def _dayGenerator(self):
        return itertools.cycle(self.timetableDayIds)

    def schooldayStrategy(self, date, generator):
        return generator.next()


class WeeklyTimetableModel(BaseTimetableModel):
    """A timetable model where the schedule depends only on weekdays."""

    timetableDayIds = "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"

    classProvides(ITimetableModelFactory)

    def __init__(self, day_ids=None, day_templates={}):
        self.dayTemplates = day_templates
        if day_ids is not None:
            self.timetableDayIds = day_ids
        self._validateDayTemplates()

    def schooldayStrategy(self, date, generator):
        try:
            return self.timetableDayIds[date.weekday()]
        except IndexError:
            return None

    def _dayGenerator(self):
        return None


#
#  Things for integrating timetabling into the core code.
#

class TimetableDict(PersistentDict):

    implements(ILocation)

    __name__ = 'timetables'
    __parent__ = None

    def __setitem__(self, key, value):
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

    def makeTimetableCalendar(self):
        events = []
        terms = getSchoolToolApplication().terms
        for term_id, schema_id in self.listCompositeTimetables():
            schoolday_model = terms[term_id]
            tt = self.getCompositeTimetable(term_id, schema_id)
            cal = tt.model.createCalendar(schoolday_model, tt)
            events += list(cal)
        result = ImmutableCalendar(events)
        # Parent is needed so that we can find out the owner of this calendar.
        # XXX Committing the following workaround without a unit or a
        #     functional test to get SchoolTool 0.8 out of the door without
        #     this bug.  See http://issues.schooltool.org/issue130
        #     Remove this comment once we have proper tests.
        directlyProvides(result, ILocation)
        result.__parent__ = self
        result.__name__ = 'timetable-calendar'
        return result


class TimetableSchemaService(Persistent):
    implements(ITimetableSchemaService)

    __parent__ = None
    __name__ = None

    _default_id = None

    def __init__(self):
        self.timetables = PersistentDict()

    def _set_default_id(self, new_id):
        if new_id is not None and new_id not in self.timetables:
            raise ValueError("Timetable schema %r does not exist" % new_id)
        self._default_id = new_id

    default_id = property(lambda self: self._default_id, _set_default_id)

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
        if self.default_id is None:
            self.default_id = schema_id

    def __delitem__(self, schema_id):
        del self.timetables[schema_id]
        if schema_id == self.default_id:
            self.default_id = None

    def getDefault(self):
        return self[self.default_id]


class TermService(BTreeContainer):

    implements(ITermService)


def getTermForDate(date):
    """Find the time period that contains `date`.

    Returns None if there is `date` falls outside all time periods.
    """

    terms = getSchoolToolApplication().terms
    for term_id in terms.keys():
        term = terms[term_id]
        if date in term:
            return term
    return None


def getPeriodsForDay(date):
    """Return a list of timetable periods defined for `date`.

    This function uses the default timetable schema and the appropriate time
    period for `date`.

    Returns a list of ISchooldayPeriod objects.

    Returns an empty list if there are no periods defined for `date` (e.g.
    if there is no default timetable schema, or `date` falls outside all
    time periods, or it happens to be a holiday).
    """
    schooldays = getTermForDate(date)
    ttservice = getSchoolToolApplication().timetableSchemaService
    if ttservice.default_id is None or schooldays is None:
        return []
    ttschema = ttservice.getDefault()
    return ttschema.model.periodsInDay(schooldays, ttschema, date)


#
# Module setup
#

class TimetablePhysicallyLocatable(LocationPhysicallyLocatable):
    """A traversal adapter for timetables.

    Timetables are special in that they have tuples (schema_id, period_id)
    as their __name__, so the standard getPath() will not work on them.
    """

    adapts(ITimetable)

    def getPath(self):
        if ITimetableSchemaService.providedBy(self.context.__parent__):
            # XXX Hacky!
            #     This hack is necessary because at the moment timetable
            #     objects in SchoolTool live in two places:
            #       - some timetables live in the timetable schema service,
            #         they have a regular unicode __name__, and their path
            #         looks like "/parent/path/__name__"
            #       - some timetables live in the timetables dict of an
            #         ITimetabledObject, and their name is a tuple
            #         (time_period_id, schema_id), and their path looks like
            #         "/parent/path/time_period_id/schema_id"
            path = LocationPhysicallyLocatable.getPath(self)
        else:
            path = (getPath(self.context.__parent__) + "/"
                    + u"/".join(self.context.__name__))
        return path


def setUp():
    provideAdapter(TimetablePhysicallyLocatable)
    registerTimetableModel('SequentialDaysTimetableModel',
                           SequentialDaysTimetableModel)
    registerTimetableModel('WeeklyTimetableModel', WeeklyTimetableModel)
