#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
SchoolTool application interfaces
"""

import datetime

from zope.interface import Interface, Attribute, implements
from zope.schema import Field, Object, Int, TextLine, List, Tuple
from zope.schema import Dict, Date, Timedelta
from zope.schema import Iterable, Bool
from zope.schema.interfaces import IField
from zope.annotation.interfaces import IAnnotatable
from zope.container.constraints import contains, containers
from zope.container.interfaces import IContainer, IContained
from zope.location.interfaces import ILocation

from schooltool.term.interfaces import ITerm
from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.calendar.interfaces import Unchanged

#
# Time field used in timetabling interfaces
#

class ITime(IField):
    u"""Field containing time."""


class Time(Field):
    __doc__ = ITime.__doc__
    _type = datetime.time

    implements(ITime)


#
#  Timetabling
#

class ISchooldayTemplate(Interface):
    """A school-day template represents the times that periods are
    scheduled during a prototypical school day.

    Some schools need only one school-day template. For example, they
    have seven periods in a day, and the periods are always in the
    sequence 1 to 7, and start and end at the same time on each school
    day.

    Other schools will need more than one school-day template. For
    example, a school that has shorter school days on Wednesdays will
    have one template for Wednesdays, and one other template for
    Monday, Tuesday, Thursday and Friday.
    """

    def __iter__():
        """Return an iterator over the ISchooldaySlots of this template."""


class ISchooldayTemplateWrite(Interface):
    """Write access to schoolday templates."""

    def add(obj):
        """Add an ISchooldaySlot to the template.

        Raises a TypeError if obj is not an ISchooldaySlot."""

    def remove(obj):
        """Remove an object from the template."""


class ISchooldaySlot(Interface):
    """A time interval during which a period can be scheduled."""

    tstart = Time(
        title=u"Time of the start of the event")

    duration = Timedelta(
        title=u"Timedelta of the duration of the event")

    def __eq__(other):
        """SchooldaySlots are equal if their start times and durations
        are equal.

        Raises TypeError if other does not implement ISchooldaySlot.
        """

    def __ne__(other):
        """SchooldaySlots are not equal if either their start times
        and durations are not equal.

        Raises TypeError if other does not implement ISchooldaySlot.
        """

    def __hash__():
        """Hashes of ISchooldaySlots are equal iff those
        ISchooldaySlots are equal.
        """


class ITimetableModel(Interface):
    """A timetable model knows how to create an ICalendar object when
    it is given a School-day model and a Timetable.

    The implementation of the timetable model knows how to arrange
    timetable days within the available school days.

    For example, a school with four timetable days 1, 2, 3, 4 has its
    timetable days laid out in sequence across consecutive school
    days. A school with a timetable days for Monday through Friday has
    its timetable days laid out to match the day of the week that a
    school day occurs on.

    The ICalendar produced will use an appropriate school-day template
    for each day, depending on (for example) what day of the week that
    day occurs on, or whatever other rules the implementation of the
    timetable model is coded to use.
    """

    factory_id = Attribute("""Name of the ITimetableModelFactory utility
                              that was used to create this model.""")

    timetableDayIds = List(
        title=u"A sequence of day_ids which can be used in the timetable.",
        value_type=TextLine(title=u"Day id"))

    exceptionDays = Dict(
        title=u"Exception schoolday templates",
        key_type=Date(title=u"Date"),
        value_type=List(title=u"Schoolday template"),
        description=u"""
        Timetables for special days

        The values are lists of tuples of (period_id, SchooldaySlot).
        """)

    exceptionDayIds = Dict(
        title=u"Day ids for special dates",
        key_type=Date(title=u"Date"),
        value_type=Object(title=u"Schoolday template",
                          schema=ISchooldayTemplate),
        description=u"""
        Day ids for special dates

        This allows to indicate, that a certain timetable day id
        should be used for a particular date, for example when the day
        is a replacement for some other day.
        """)

    def createCalendar(term, timetable, first=None, last=None):
        """Return an ICalendar composed out of term and timetable.

        This method has model-specific knowledge as to how the schooldays,
        weekends and holidays map affects the mapping of the timetable
        onto the real-world calendar.

        You can specify a range of dates to generate a calendar spanning a
        given date range (inclusive) only.
        """

    def periodsInDay(term, timetable, date):
        """Return a sequence of periods defined in this day"""

    def originalPeriodsInDay(term, timetable, date):
        """Return a sequence of original periods defined in this day.

        This method is similar to periodsInDay, but it disregards the
        exceptionDays.
        """

    def getDayId(term, timetable, date):
        """Return what day id a certain date will use in this model"""


class IWeekdayBasedTimetableModel(ITimetableModel):
    """A model that chooses the day template according to the day of week."""

    dayTemplates = Dict(
        title=u"Schoolday templates",
        key_type=Int(title=u"Weekday", required=False),
        value_type=Object(title=u"Schoolday template",
                          schema=ISchooldayTemplate),
        description=u"""
        Schoolday templates.

        The template with the key of None is used if there is no template
        for a particular weekday.
        """)


class IDayIdBasedTimetableModel(ITimetableModel):
    """A model that chooses the day template according to the day id."""

    dayTemplates = Dict(
        title=u"Schoolday templates",
        key_type=TextLine(title=u"Day Id", required=False),
        value_type=Object(title=u"Schoolday template",
                          schema=ISchooldayTemplate),
        description=u"""
        Schoolday templates indexed by day id.
        """)


class ITimetableModelFactory(Interface):
    """A factory of a timetable model"""

    def __call__(day_ids, day_templates):
        """Return a timetable model.

        `day_ids` is a sequence of day ids.

        `day_templates` is a dict ITimetableDay objects as values and
        implementation dependent keys.
        """


class ITimetableActivity(Interface):
    """An event in a timetable.

    Something that happens on a certain period_id in a certain day_id.

    Timetable activities are immutable and can be hashed or compared for
    equality.
    """

    title = TextLine(
        title=u"The title of the activity.")

    owner = Field(
        title=u"The group or person or other object that owns the activity.",
        description=u"""
        The activity lives in the owner's timetable.
        """)

    resources = Iterable(
        title=u"A set of resources assigned to this activity.",
        description=u"""
        The activity is also present in the timetables of all resources
        assigned to this activity.
        """)

    timetable = Field(
        title=u"The timetable that contains this activity.",
        description=u"""
        This attribute refers to the timetable of `owner`.  It never refers
        to a composite timetable or a timetable of a resource.
        """)

    def replace(title=Unchanged, owner=Unchanged, timetable=Unchanged):
        """Return a copy of this activity with some fields changed."""

    def __eq__(other):
        """Is this timetable activity equal to `other`?

        Timetable activities are equal iff their title and owner
        attributes are equal.

        Returns false if other is not a timetable activity.
        """

    def __ne__(other):
        """Is this timetable activity different from `other`?

        The opposite of __eq__.
        """

    def __hash__():
        """Calculate the hash value of a timetable activity."""


class ITimetableException(Interface):
    """An exception in a timetable.

    An exception specifies that on a particular day a particular activity
    either does not occur, or occurs but at a different time, or is replaced
    by a different activity.
    """

    date = Date(
        title=u"Date of the exception")

    period_id = TextLine(
        title=u"ID of the period that is exceptional.")

    activity = Object(
        title=u"The activity that does not occur.",
        schema=ITimetableActivity)

    replacement = Field(
        title=u"A replacement calendar event",
        # schema=IExceptionalTTCalendarEvent,
        required=False,
        description=u"""
        A calendar event that should replace the exceptional activity.
        If None, then the activity is simply removed.
        """)

    def __eq__(other):
        """See if self == other."""

    def __ne__(other):
        """See if self != other."""


class ITimetableSchema(IContained):
    """A timetable schema.

    A timetable schema is an ordered collection of timetable days that contain
    periods.
    """

    title = TextLine(
        title=u"The title of the timetable schema.")

    model = Object(
        title=u"A timetable model this timetable should be used with.",
        schema=ITimetableModel)

    timezone = TextLine(title=u"The name of a timezone of this timetable")

    def keys():
        """Return a sequence of identifiers for days within the timetable.

        The order of day IDs is fixed.
        """

    def items():
        """Return a sequence of tuples of (day_id, ITimetableSchemaDay).

        The order of day IDs is fixed and is the same as returned by keys().
        """

    def __getitem__(key):
        """Return a ITimetableSchemaDay for a given day id."""

    def createTimetable(term):
        """Return a new empty timetable with the same structure.

        The new timetable has the same set of day_ids, and the sets of
        period ids within each day.  It has no activities.

        The new timetable is bound to the term passed as the argument.
        """


class ITimetableSchemaWrite(Interface):
    """Interface for initializing timetable schemas."""

    def __setitem__(key, value):
        """Set an ITimetableSchemaDay for a given day id.

        Throws a TypeError if the value does not implement ITimetableSchemaDay.
        Throws a ValueError if the key is not a valid day id.
        """


class ITimetableSchemaDay(Interface):
    """A day in a timetable schema.

    A timetable day is an ordered collection of periods.

    Different days within the same timetable schema may have different periods.

    ITimetableSchemaDay has keys, items and __getitem__ for interface
    compatibility with ITimetableDay -- so that, for example, views for
    ITimetable can be used to render ITimetableSchemas.
    """

    periods = List(
        title=u"A list of period IDs for this day.",
        value_type=TextLine(title=u"A period id"))

    homeroom_period_ids = List(
        title=u"A list of homeroom period IDs for this day",
        required=False)

    def keys():
        """Return self.periods."""

    def items():
        """Return a sequence of (period_id, empty_set)."""

    def __getitem__(key):
        """Return an empty set, if key is in periods, otherwise raise KeyError.
        """


class ITimetable(ILocation):
    """A timetable.

    A timetable is an ordered collection of timetable days that contain
    periods. Each period either contains a class, or is empty.

    A timetable represents the repeating lesson schedule for just one
    pupil, or one teacher, or one bookable resource.
    """
    containers('.ITimetableDict')

    title = TextLine(title=u"Title", required=True)

    model = Object(
        title=u"A timetable model this timetable should be used with.",
        schema=ITimetableModel)

    timezone = TextLine(title=u"The name of a timezone of this timetable")

    consecutive_periods_as_one = Bool(
        title=u"Consecutive periods appear as one column in the journal",
        required=False)

    term = Object(
        title=u"The term this timetable is for.",
        schema=ITerm)

    schooltt = Object(
        title=u"The school timetable this timetable is for.",
        schema=ITimetableSchema)

    def keys():
        """Return a sequence of identifiers for days within the timetable.

        The order of day IDs is fixed.
        """

    def items():
        """Return a sequence of tuples of (day_id, ITimetableDay).

        The order of day IDs is fixed and is the same as returned by keys().
        """

    def __getitem__(key):
        """Return a ITimetableDay for a given day id."""

    def activities():
        """Return all activities in this timetable.

        Returns a list of tuples (day_id, period_id, activity).
        """

    def cloneEmpty():
        """Return a new empty timetable with the same structure.

        The new timetable has the same set of day_ids, and the sets of
        period ids within each day.  It has no activities.
        """

    def __eq__(other):
        """Is this timetable equal to other?

        Timetables are equal iff they have the same model,
        set of day IDs, and their corresponding days are equal.

        Returns False if other is not a timetable.
        """

    def __ne__(other):
        """Is this timetable different from other?

        The opposite of __eq__.
        """


class ITimetableWrite(Interface):
    """Write access to timetables."""

    def __setitem__(key, value):
        """Set an ITimetableDay for a given day id.

        Throws a TypeError if the value does not implement ITimetableDay.
        Throws a ValueError if the key is not a valid day id.
        """

    def clear(send_events=True):
        """Remove all activities for all periods.

        If send_events is True, sends ITimetableActivityRemovedEvents for
        all removed activities.
        """

    def update(timetable):
        """Add all the events from timetable to self.

        Useful for producing combined timetables.

        Does not send any events.
        """


class ITimetableDay(Interface):
    """A day in a timetable.

    A timetable day is an ordered collection of periods that each have
    a set of activites that occur during that period.

    Different days within the same timetable may have different periods.
    """

    timetable = Object(
        title=u"The timetable that contains this day.",
        schema=ITimetable)

    day_id = TextLine(
        title=u"The day id of this timetable day.")

    periods = List(
        title=u"A list of period IDs for this day.",
        value_type=TextLine(title=u"A period id"))

    homeroom_period_ids = TextLine(
        title=u"IDs of homeroom periods",
        required=False)

    def keys():
        """Return self.periods."""

    def items():
        """Return a sequence of (period_id, set_of_ITimetableActivity)."""

    def __getitem__(key):
        """Return the set of ITimetableActivities for a given period.

        If there is no activity for the period, an empty set is returned.
        """

    def __eq__(other):
        """Return True iff other is a TimetableDay with the same set of
        periods and with the same activities scheduled for those periods.
        """

    def __ne__(other):
        """Return True iff __eq__ returns False."""


class ITimetableDayWrite(Interface):
    """Writable timetable day.

    Note that all clients which use ITimetableDayWrite or ITimetableWrite
    to modify timetables should maintain the following invariant:
     - every TimetableActivity is present in the timetable of its owner
       and all the timetables of its resources.
    """

    def clear(period):
        """Remove all the activities for a certain period id.

        If send_events is True, sends an ITimetableActivityRemovedEvent
        for each removed activity.
        """

    def add(period, activity, send_event=True):
        """Add a single activity to the set of activities planned for
        a given period.

        If send_events is True, sends an ITimetableActivityAddedEvent.
        """

    def remove(period, value):
        """Remove a certain activity from a set of activities planned
        for a given period.

        Raises KeyError if there is no matching activity.

        If send_events is True, sends an ITimetableActivityRemovedEvent.
        """


class ITimetableActivityEvent(Interface):
    """Event that gets sent when an activity is added to a timetable day."""

    activity = Object(
        title=u"The timetable activity.",
        schema=ITimetableActivity)

    day_id = TextLine(
        title=u"The day_id of the containing timetable day.")

    period_id = TextLine(
        title=u"The period_id of the containing period.")


class ITimetableActivityAddedEvent(ITimetableActivityEvent):
    """Event that gets sent when an activity is added to a timetable."""


class ITimetableActivityRemovedEvent(ITimetableActivityEvent):
    """Event that gets sent when an activity is removed from a timetable."""


class ITimetableCalendarEvent(ISchoolToolCalendarEvent):
    """A calendar event that has been created from a timetable."""

    day_id = TextLine(
        title=u"The id of the timetable day.")

    period_id = TextLine(
        title=u"The period id of the corresponding timetable event.")

    activity = Object(
        title=u"The activity from which this event was created.",
        schema=ITimetableActivity)


class ITimetableDict(IContainer, ILocation):
    """Container for timetables.

    The id of the timetable is composed by joining term id and
    timetable schema id with a dot.  For example,"2005-fall.default"
    means a timetable for a term "2005-fall" with a timetable schema
    "default".
    """
    contains(ITimetable)


class IHaveTimetables(Interface):
    """A marker interface for content objects to declare themselves as having
       timetables."""


class IOwnTimetables(IHaveTimetables, IAnnotatable):
    """A marker interface for content objects to declare themselves as having
       timetables."""


class IBookResources(Interface):
    """An object that can have booked resources."""

    resources = Iterable(
        title=u"Booked resources")


class ITimetables(Interface):
    """The timetable content related to an object -- either its own,
    or composed of the timetables of related objects.
    """

    object = Attribute("The object these timetables are for.")

    terms = Attribute(
        """A list of terms this object was scheduled for.""")

    timetables = Object(
        schema=ITimetableDict,
        title=u"Private timetables of this object",
        description=u"""

        These timetables can be directly manipulated.  Adding, changing
        or removing a timetable will result in a ITimetableReplacedEvent
        being sent.

        For a lot of objects this mapping will be empty.  Instead, they
        will inherit timetable events through composition (see
        getCompositeTimetable).
        """)

    def lookup(term, schooltt):
        """ """

class ICompositeTimetables(Interface):
    """An interface for objects that have composite timetables."""

    def collectTimetableSourceObjects():
        """Collect objects timetables of which are included in the composite timetable."""

    def makeTimetableCalendar(first=None, last=None):
        """Generate and return a calendar from all composite timetables.

        You can specify a range of dates to generate a calendar spanning a
        given date range (inclusive) only.
        """


class ITimetableSource(Interface):
    """Timetable source.

    A subscription adapter that contributes a timetable to the
    composite timetable of the context.
    """

    def getTimetableSourceObjects():
        """Return objects calendars of which will be merged to the composite
        timetable of the context."""


class ITimetableReplacedEvent(Interface):
    """Event that gets sent when a timetable is replaced."""

    object = Object(
        title=u"The owner of the timetable.",
        schema=ITimetables)

    key = Tuple(
        title=u"Tuple (time_period_id, schema_id).",
        value_type=TextLine(),
        min_length=2,
        max_length=2)

    old_timetable = Object(
        title=u"The old timetable (can be None).",
        schema=ITimetable,
        required=False)

    new_timetable = Object(
        title=u"The new timetable (can be None).",
        schema=ITimetable,
        required=False)


class ITimetableModelRegistry(Interface):
    """A registry of timetable model classes present in the system.

    The timetable model classes are identified by the dotted class names.

    Timetable model classes are acquired as named utilities
    implementing ITimetableModelFactory.
    """

    def registerTimetableModel(id, factory):
        """Register a timetable schema identified by a given id."""


class ITimetableSchemaContainer(IContainer, ILocation):
    """Service for creating timetables of a certain schema.

    This service stores timetable prototypes (empty timetables) and
    can return a new timetable of a certain schema on request.
    """

    contains(ITimetableSchema)

    default_id = TextLine(
        title=u"Schema id of the default schema")

    def getDefault():
        """Return the default schema for the school"""


class ITimetableSchemaContainerContainer(IContainer, ILocation):
    contains(ITimetableSchemaContainer)


class ITimetableSchemaContained(ITimetableSchema, IContained):
    """Timetable Schema contained in an ITimetableSchemaContainer."""

    containers(ITimetableSchemaContainer)
