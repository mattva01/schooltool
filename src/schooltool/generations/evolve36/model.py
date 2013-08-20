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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Various timetable classes from generation 35.

"""

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import Interface, implements
from zope.container.interfaces import IContainer, IContained
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer
from zope.location.interfaces import ILocation

from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
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


@substituteIn('schooltool.timetable.interfaces')
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


@substituteIn('schooltool.timetable.interfaces')
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


@substituteIn('schooltool.timetable.interfaces')
class ITimetableModel(Interface):
    pass


@substituteIn('schooltool.timetable.interfaces')
class IWeekdayBasedTimetableModel(ITimetableModel):
    pass


@substituteIn('schooltool.timetable.interfaces')
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


@substituteIn('schooltool.timetable.interfaces')
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
        if resource not in self.resources:
            raise ValueError('resource not booked')
        self._resources = tuple([r for r in self.resources
                                 if r is not resource])
        ISchoolToolCalendar(resource).removeEvent(self)


@substituteIn('schooltool.timetable.interfaces')
class ITimetableDict(IContainer, ILocation):
    """Container for [section] timetables."""


@substituteIn('schooltool.timetable')
class TimetableDict(PersistentDict):
    """The id of the timetable is composed by joining term id and
    timetable schema id with a dot.  For example,"2005-fall.default"
    means a timetable for a term "2005-fall" with a timetable schema
    "default".
    """
    implements(ILocation, ITimetableDict)

    __name__ = 'timetables'
    __parent__ = None # [section] this timetable is scheduled for


@substituteIn('schooltool.timetable.interfaces')
class ITimetable(ILocation):
    """A timetable interface."""


@substituteIn('schooltool.timetable')
class Timetable(Persistent):
    """A timetable.

    A timetable is an ordered collection of timetable days that contain
    periods. Each period either contains a class, or is empty.

    A timetable represents the repeating lesson schedule for just one
    pupil, or one teacher, or one bookable resource.

    Contained in a TimetableDict.
    """
    implements(ITimetable)

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
            return u"Unbound timetable."

    def __init__(self, day_ids):
        self.day_ids = day_ids
        self.days = PersistentDict()
        self.model = None

    @property
    def first(self):
        if self._first is None:
            term = getattr(self, 'term', None)
            if term is None:
                return None
            return term.first
        return self._first

    @property
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

    def activities(self):
        """Returns a list of tuples (day_id, period_id, activity)."""
        act = []
        for day_id in self.day_ids:
            for period_id, iactivities in self.days[day_id].items():
                act.extend([(day_id, period_id, activity)
                            for activity in iactivities])
        return act


@substituteIn('schooltool.timetable.interfaces')
class ITimetableDay(Interface):
    pass


@substituteIn('schooltool.timetable')
class TimetableDay(Persistent):
    """A day in a timetable.

    A timetable day is an ordered collection of periods that each have
    a set of activites that occur during that period.

    Different days within the same timetable may have different periods.
    """
    implements(ITimetableDay)

    timetable = None
    day_id = None
    periods = None # list of periods (titles, or maybe IDs?)
    homeroom_period_ids = None # IDs of homeroom periods
    activities = None # persistent dict of (period, set of TimetableActivity)

    def keys(self):
        return self.periods

    def items(self):
        return [(period, self.activities[period]) for period in self.periods]

    def __getitem__(self, period):
        return self.activities[period]


@substituteIn('schooltool.timetable.interfaces')
class ITimetableActivity(Interface):
    pass


@substituteIn('schooltool.timetable')
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

    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)
    timetable = property(lambda self: self._timetable)
    resources = property(lambda self: self._resources)
