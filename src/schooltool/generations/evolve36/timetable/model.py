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
Timetable model implementations.

A timetable model describes the mapping between timetable days and calendar
days, and also the mapping between period IDs and time of the day.  Currently
SchoolTool has two kinds of timetable models:

  - Sequential days model may jump over calendar days if they are not school
    days.  For example, if July 3 was timetable day 3, and July 4 is a holiday,
    then July 5 will be timetable day 4.

  - Weekly model maps week days directly to timetable days, that is, Monday is
    always timetable day 1, and sunday is always timetable day 7.

It is possible to define additional models.  See ITimetableModel.

$Id$
"""
import socket
import itertools
import datetime
import pytz

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements, classProvides
from zope.traversing.api import getPath
from zope.proxy import sameProxiedObjects

from schooltool.app.cal import CalendarEvent
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.app.interfaces import ISchoolToolCalendar

from schooltool.timetable.interfaces import IWeekdayBasedTimetableModel
from schooltool.timetable.interfaces import IDayIdBasedTimetableModel
from schooltool.timetable.interfaces import ITimetableModelFactory
from schooltool.timetable.interfaces import ITimetableCalendarEvent

__metaclass__ = type


class WeekdayBasedModelMixin:
    """A mixin for a timetable model that indexes day templates by weekday"""
    implements(IWeekdayBasedTimetableModel)

    dayTemplates = None # dict of day templates (default None + up to 7 weekdays)

    def _validateDayTemplates(self):
        if None not in self.dayTemplates:
            for weekday in range(7):
                if weekday not in self.dayTemplates:
                    raise AssertionError("No day template for day %d,"
                                         " and no fallback either" % weekday)

    def _getUsualTemplateForDay(self, date, day_id):
        """Returns the schoolday template for a certain date
        disregarding special days.
        """
        default = self.dayTemplates[None]
        return self.dayTemplates.get(date.weekday(), default)


class BaseTimetableModel(Persistent):
    """
    Interesting methods:
        createCalendar(self, term, timetable, first=None, last=None)
        getDayId(self, term, day, day_id_gen=None)
        periodsInDay(self, term, timetable, day)
        originalPeriodsInDay(self, term, timetable, day)
    """

    timetableDayIds = () # day ids of templates built by timetable
    dayTemplates = {} # day id -> [(period, SchoolDaySlot), ...]
    exceptionDays = None # date -> [(period, SchoolDaySlot), ...]
    exceptionDayIds = None # exception date -> day id in dayTemplates

    def __init__(self):
        self.exceptionDays = PersistentDict()
        self.exceptionDayIds = PersistentDict()

    def createCalendar(self, term, timetable, first=None, last=None):
        uid_suffix = '%s@%s' % (getPath(timetable), socket.getfqdn())
        events = []
        day_id_gen = self._dayGenerator()
        if first is None:
            first = timetable.first or term.first
        if last is None:
            last = timetable.last or term.last
        for date in term:
            if not first <= date <= last:
                # must call getDayId to keep track of days
                day_id = self.getDayId(term, date, day_id_gen)
                continue
            day_id, periods = self._periodsInDay(term, timetable,
                                                 date, day_id_gen)

            tz = pytz.timezone(timetable.timezone)

            for period, tstart, duration in periods:
                # We need to convert dtstart to UTC, because calendar
                # events insist on storing UTC time.
                dt = datetime.datetime.combine(date, tstart)
                dt = tz.localize(dt).astimezone(pytz.utc)
                for activity in timetable[day_id][period]:
                    key = (date, period, activity)
                    # IDs for functionally derived calendars should be
                    # functionally derived, and not random
                    uid = '%d-%s' % (hash((activity.title, dt,
                                           duration)), uid_suffix)
                    event = TimetableCalendarEvent(
                                dt, duration, activity.title,
                                unique_id=uid, day_id=day_id, period_id=period,
                                activity=activity)
                    events.append(event)
        return ImmutableCalendar(events)

    def getDayId(self, term, day, day_id_gen=None):
        """
        scroll day_id_gen to day
        if not schoolday:
            return None
        else:
            return self.schooldayStrategy(day)
        """
        if day_id_gen is None:
            # Scroll to the required day
            day_id_gen = self._dayGenerator()
            if day_id_gen is not None:
                for date in term:
                    if date == day:
                        break
                    if term.isSchoolday(date):
                        self.schooldayStrategy(date, day_id_gen)

        if not term.isSchoolday(day):
            return None
        return self.schooldayStrategy(day, day_id_gen)

    def _periodsInDay(self, term, timetable, day,
                      day_id_gen=None, original=False):
        """
        return day_id, sorted([(period, tstart, duration), ...])

        `original` is boolean flag that makes this method disregard
        exceptionDays.
        """

        day_id = self.getDayId(term, day, day_id_gen)
        if day_id is None:
            return None, []

        # Now choose the periods that are in this day
        result = []
        usual = self._getUsualTemplateForDay(day, day_id)
        periods = zip(timetable[day_id].keys(), sorted(usual))
        if not original:
            periods = self.exceptionDays.get(day, periods)

        for period, slot in periods:
            if period in timetable[day_id].keys():
                result.append((period, slot.tstart, slot.duration))

        result.sort(key=lambda x: x[1])
        return day_id, result

    def periodsInDay(self, term, timetable, day):
        """
        return sorted([(period, tstart, duration), ...])
        """
        return self._periodsInDay(term, timetable, day)[1]

    def originalPeriodsInDay(self, term, timetable, day):
        """
        return sorted([(period, tstart, duration), ...])
        Ignore exception days.
        """
        return self._periodsInDay(term, timetable, day, original=True)[1]

    def schooldayStrategy(self, date, generator):
        raise NotImplementedError

    def _dayGenerator(self):
        raise NotImplementedError

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.timetableDayIds == other.timetableDayIds and
                    self.dayTemplates == other.dayTemplates and
                    self.exceptionDays == other.exceptionDays and
                    self.exceptionDayIds == other.exceptionDayIds)
        else:
            return False

    def __ne__(self, other):
        return not self == other


class BaseSequentialTimetableModel(BaseTimetableModel):

    timetableDayIds = () # day ids of templates built by timetable
    dayTemplates = {} # day id -> [(period, SchoolDaySlot), ...]
    exceptionDays = None # date -> [(period, SchoolDaySlot), ...]
    exceptionDayIds = None # exception date -> day id in dayTemplates

    def __init__(self, day_ids, day_templates):
        BaseTimetableModel.__init__(self)
        self.timetableDayIds = day_ids
        self.dayTemplates = day_templates
        self._validateDayTemplates()

    def _dayGenerator(self):
        return itertools.cycle(self.timetableDayIds)

    def schooldayStrategy(self, date, generator):
        if date in self.exceptionDayIds:
            return self.exceptionDayIds[date]
        else:
            return generator.next()


#
#  Implementations of actually used models
#
#


class SequentialDaysTimetableModel(BaseSequentialTimetableModel,
                                   WeekdayBasedModelMixin):
    """A sequential days timetable model in which the days are chosen
    by weekday
    """
    classProvides(ITimetableModelFactory)

    factory_id = "SequentialDaysTimetableModel"

    timetableDayIds = () # day ids of templates built by timetable
    dayTemplates = {} # day id -> [(period, SchoolDaySlot), ...]
    exceptionDays = None # date -> [(period, SchoolDaySlot), ...]
    exceptionDayIds = None # exception date -> day id in dayTemplates

    def _validateDayTemplates(self):
        """
        if None not in self.dayTemplates:
            for weekday in range(7): assert weekday in self.dayTemplates
        """
        return WeekdayBasedModelMixin._validateDayTemplates(self)

    def _getUsualTemplateForDay(self, date, day_id):
        """
        return self.dayTemplates[date.weekday()] or self.dayTemplates[None]
        """
        return WeekdayBasedModelMixin._getUsualTemplateForDay(self, date, day_id)

    def _dayGenerator(self):
        """
        return itertools.cycle(self.timetableDayIds)
        """
        return BaseSequentialTimetableModel._dayGenerator(self)

    def schooldayStrategy(self, date, generator):
        """
        if exception: return self.exceptionDayIds[date]
        else: return generator.next()
        """
        return BaseSequentialTimetableModel.schooldayStrategy(self, date, generator)


class SequentialDayIdBasedTimetableModel(BaseSequentialTimetableModel):
    """A sequential timetable model in which the day templates are
    indexed by day id rather than weekday.
    """
    classProvides(ITimetableModelFactory)
    implements(IDayIdBasedTimetableModel)

    factory_id = "SequentialDayIdBasedTimetableModel"

    timetableDayIds = () # day ids of templates built by timetable
    dayTemplates = {} # day id -> [(period, SchoolDaySlot), ...]
    exceptionDays = None # date -> [(period, SchoolDaySlot), ...]
    exceptionDayIds = None # exception date -> day id in dayTemplates

    def _validateDayTemplates(self):
        for day_id in self.timetableDayIds:
            if day_id not in self.dayTemplates:
                raise AssertionError("No day template for day id %s" % day_id)

    def _getUsualTemplateForDay(self, date, day_id):
        """Returns the schoolday template for a certain date
        disregarding special days.
        """
        return self.dayTemplates[day_id]

    def _dayGenerator(self):
        """return itertools.cycle(self.timetableDayIds)"""
        return BaseSequentialTimetableModel._dayGenerator(self)

    def schooldayStrategy(self, date, generator):
        """
        if exception: return self.exceptionDayIds[date]
        else: return generator.next()
        """
        return BaseSequentialTimetableModel.schooldayStrategy(self, date, generator)


class WeeklyTimetableModel(BaseTimetableModel, WeekdayBasedModelMixin):
    """A timetable model where the schedule depends only on weekdays."""
    classProvides(ITimetableModelFactory)

    factory_id = "WeeklyTimetableModel"

    # day ids of templates built by timetable:
    timetableDayIds = "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"
    dayTemplates = {} # day id -> [(period, SchoolDaySlot), ...]
    exceptionDays = None # date -> [(period, SchoolDaySlot), ...]
    exceptionDayIds = None # exception date -> day id in dayTemplates

    def __init__(self, day_ids=None, day_templates={}):
        BaseTimetableModel.__init__(self)
        self.dayTemplates = day_templates
        if day_ids is not None:
            self.timetableDayIds = day_ids
        self._validateDayTemplates()

    def _validateDayTemplates(self):
        """
        if None not in self.dayTemplates:
            for weekday in range(7): assert weekday in self.dayTemplates
        """
        return WeekdayBasedModelMixin._validateDayTemplates(self)

    def _getUsualTemplateForDay(self, date, day_id):
        """return self.dayTemplates[date.weekday()] or self.dayTemplates[None]"""
        return WeekdayBasedModelMixin._getUsualTemplateForDay(self, date, day_id)

    def _dayGenerator(self):
        return None

    def schooldayStrategy(self, date, generator):
        """
        if exception: return self.exceptionDayIds[date]
        else: return self.timetableDayIds[date.weekday()]
        """
        if date in self.exceptionDayIds:
            return self.exceptionDayIds[date]
        try:
            return self.timetableDayIds[date.weekday()]
        except IndexError:
            return None

#
#  Calendar events
#
#
#

class TimetableCalendarEvent(CalendarEvent):
    """For the ImmutableCalendar generated in BaseTimetableModel.createCalendar."""
    implements(ITimetableCalendarEvent)

    day_id = property(lambda self: self._day_id)
    period_id = property(lambda self: self._period_id)
    activity = property(lambda self: self._activity)

    # de facto, tuple of section resources, probably unused anymore
    resources = property(lambda self: self.activity.resources)

    # XXX: is this used anywhere?
    owner = property(lambda self: self.activity.owner) # [section]

    def __init__(self, *args, **kwargs):
        self._day_id = kwargs.pop('day_id')
        self._period_id = kwargs.pop('period_id')
        self._activity = kwargs.pop('activity')
        CalendarEvent.__init__(self, *args, **kwargs)


class PersistentTimetableCalendarEvent(CalendarEvent):
    """A calendar event that has been created from a timetable."""
    implements(ITimetableCalendarEvent)

    __name__ = None
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

    def __init__(self, event):
        self.unique_id = event.unique_id
        self.__name__ = event.__name__
        self._day_id = event.day_id
        self._period_id = event.period_id
        self._activity = event.activity

        self.dtstart = event.dtstart
        self.duration = event.duration
        self.description = event.description
        self.location = event.location
        self.recurrence = event.recurrence
        self.allday = event.allday

        resources = list(event.resources)
        self._resources = ()
        for resource in resources:
            self.bookResource(resource)

    def schoolDay(self):
        tz_id = self.activity.timetable.timezone
        timezone = pytz.timezone(tz_id)
        return self.dtstart.astimezone(timezone).date()


#
#  More calendar integration for reference
#
#

def addEventsToCalendar(event):
    timetable = event.activity.timetable

    calendar = timetable.model.createCalendar(timetable.term, timetable)
    section_calendar = ISchoolToolCalendar(event.activity.owner)
    for cal_event in calendar:
        if (cal_event.activity == event.activity and
            cal_event.period_id == event.period_id and
            cal_event.day_id == event.day_id):
            tt_event = PersistentTimetableCalendarEvent(cal_event)
            section_calendar.addEvent(tt_event)


def removeEventsFromCalendar(event):
    timetable = event.activity.timetable

    events = []
    section_calendar = ISchoolToolCalendar(event.activity.owner)

    for cal_event in list(section_calendar):
        if ITimetableCalendarEvent.providedBy(cal_event):
            if (cal_event.activity == event.activity and
                cal_event.period_id == event.period_id and
                cal_event.day_id == event.day_id and
                sameProxiedObjects(cal_event.activity.timetable,
                                   event.activity.timetable)):
                section_calendar.removeEvent(cal_event)


def handleTimetableRemovedEvent(event):
    section_calendar = ISchoolToolCalendar(event.object)
    for cal_event in list(section_calendar):
        if ITimetableCalendarEvent.providedBy(cal_event):
            if sameProxiedObjects(cal_event.activity.timetable,
                                  event.old_timetable):
                section_calendar.removeEvent(cal_event)


def handleTimetableAddedEvent(event):
    timetable = event.new_timetable
    calendar = timetable.model.createCalendar(timetable.term, timetable)

    section_calendar = ISchoolToolCalendar(event.object)
    for cal_event in calendar:
        tt_event = PersistentTimetableCalendarEvent(cal_event)
        section_calendar.addEvent(tt_event)


def handleTimetableReplacedEvent(event):
    if event.old_timetable:
        handleTimetableRemovedEvent(event)
    if event.new_timetable:
        handleTimetableAddedEvent(event)
