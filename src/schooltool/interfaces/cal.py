#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
Interfaces for calendaring objects in SchoolTool.

$Id$
"""

from schooltool.unchanged import Unchanged  # reexport from here
from zope.interface import Interface
from zope.schema import Field, Object, Int, TextLine, List, Set
from zope.schema import Choice, Date, Datetime, BytesLine, Dict

from schooltool.interfaces.fields import Timedelta
from schooltool.interfaces.auth import IACLOwner


class IDateRange(Interface):
    """A range of dates (inclusive).

    If r is an IDateRange, then the following invariant holds:
    r.first <= r.last

    Note that empty date ranges cannot be represented.
    """

    first = Date(
        title=u"The first day of the period of time covered.")

    last = Date(
        title=u"The last day of the period covered.")

    def __iter__():
        """Iterate over all dates in the range from the first to the last."""

    def __contains__(date):
        """Return True if the date is within the range, otherwise False.

        Raises a TypeError if date is not a datetime.date.
        """

    def __len__():
        """Return the number of dates covered by the range."""


class ISchooldayModel(IDateRange):
    """A calendar which can tell whether a day is a school day or not
    for a certain period of time.
    """

    def isSchoolday(date):
        """Return whether the date is a schoolday.

        Raises a ValueError if the date is outside of the period covered.
        """


class ISchooldayModelWrite(Interface):

    def add(day):
        """Mark the day as a schoolday.

        Raises a ValueError if the date is outside of the period covered.
        """

    def remove(day):
        """Mark the day as a holiday.

        Raises a ValueError if the date is outside of the period covered.
        """

    def reset(first, last):
        """Change the period and mark all days as holidays.

        If first is later than last, a ValueError is raised.
        """

    def addWeekdays(*weekdays):
        """Mark that all days of week with a number in weekdays within the
        period will be schooldays.

        The numbering used is the same as one used by datetime.date.weekday()
        method, or the calendar module: 0 is Monday, 1 is Tuesday, etc.
        """

    def removeWeekdays(*weekdays):
        """Mark that all days of week with a number in weekdays within the
        period will be holidays.

        The numbering used is the same as one used by datetime.date.weekday()
        method, or the calendar module: 0 is Monday, 1 is Tuesday, etc.
        """

    def toggleWeekdays(*weekdays):
        """Toggle the state of all days of week with a number in weekdays.

        The numbering used is the same as one used by datetime.date.weekday()
        method, or the calendar module: 0 is Monday, 1 is Tuesday, etc.
        """


class ICalendar(Interface):
    """A calendar containing days, which in turn contain events."""

    def __iter__():
        """Return an iterator over the events in this calendar."""

    def find(unique_id):
        """Return an event with the given unique id.

        Raises a KeyError if there is no event with this id.
        """

    def byDate(date):
        """Return an ICalendar for the given date.

        All events that overlap with the given day are included.  The timing of
        the events is not modified even if it falls outside the given date.
        """

    def expand(first, last):
        """Expand recurring events.

        Returns an ICalendar with all the IExpandedCalendarEvents in
        that occur in the given date range.  Recurrences of all events
        in the calendar happening during the specified period are
        included.
        """


class ICalendarWrite(Interface):
    """Writable calendar."""

    def clear():
        """Remove all events."""

    def addEvent(event):
        """Add an event to the calendar."""

    def removeEvent(event):
        """Remove event from the calendar."""

    def update(calendar):
        """Add all events from another calendar."""


class IACLCalendar(ICalendarWrite, IACLOwner):
    """A calendar that has an ACL."""


class IRecurrenceRule(Interface):
    """Base interface of the recurrence rules."""

    interval = Int(
        title=u"Interval of recurrence.",
        description=u"""
        A positive integer.

        For example, for yearly recurrence the interval equal to 2
        will indicate that the event will recur once in two years.
        """)

    count = Int(
        title=u"Number of times the event is repeated.",
        required=False,
        description=u"""
        Can be None or an integer value.  If count is not None then
        until must be None.  If both count and until are None the
        event repeats forever.
        """)

    until = Date(
        title=u"The date of the last recurrence of the event.",
        required=False,
        description=u"""
        If until is not None then count must be None.  If both count and until
        are None the event repeats forever.
        """)

    exceptions = List(
        title=u"A list of days when this event does not occur.",
        value_type=Date(title=u"A day when an event does not occur"))

    def replace(interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged):
        """Return a copy of this recurrence rule with new specified fields."""

    def apply(event, enddate=None):
       """Apply this rule to an event.

       This is a generator function that returns the dates on which
       the event should recur.  Be careful when iterating over these
       dates -- rules that do not have either 'until' or 'count'
       attributes will go on forever.

       The optional enddate attribute can be used to set a range on
       the dates generated by this function (inclusive).
       """

    def __eq__(other):
        """See if self == other."""

    def __ne__(other):
        """See if self != other."""

    def __hash__():
        """Return the hash value of this recurrence rule.

        It is guaranteed that if recurrence rules compare equal, hash will
        return the same value.
        """

    def iCalRepresentation(dtstart):
        """Return the rule in iCalendar format.

        Returns a list of strings.

        dtstart is a datetime representing the date that the recurring
        event starts on.
        """


class IDailyRecurrenceRule(IRecurrenceRule):
    """Daily recurrence."""


class IYearlyRecurrenceRule(IRecurrenceRule):
    """Yearly recurrence."""


class IWeeklyRecurrenceRule(IRecurrenceRule):

    weekdays = Set(
        title=u"A set of weekdays when this event occurs.",
        value_type=Int(),
        description=u"""
        Weekdays are represented as integers from 0 (Monday) to 6 (Sunday).

        The event repeats on the weekday of the first occurence even
        if that weekday is not in this set.
        """)

    def replace(interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged):
        """Return a copy of this recurrence rule with new specified fields."""


class IMonthlyRecurrenceRule(IRecurrenceRule):

    monthly = Choice(
        title=u"Specification of a monthly occurence.",
        required=False,
        values=['monthday', 'weekday', 'lastweekday'],
        description=u"""
        'monthday'    specifies that the event recurs on the same
                      monthday.

        'weekday'     specifies that the event recurs on the same week
                      within a month on the same weekday, indexed from the
                      first (e.g. 3rd friday of a month).

        'lastweekday' specifies that the event recurs on the same week
                      within a month on the same weekday, indexed from the
                      end of month (e.g. 2nd last friday of a month).
        """)

    def replace(interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, monthly=Unchanged):
        """Return a copy of this recurrence rule with new specified fields."""


class ICalendarEvent(Interface):
    """A calendar event.

    Calendar events are immutable, hashable and comparable.  Events are
    compared in chronological order (i.e., if e1 and e2 are events, then
    e1.dtstart < e2.dtstart implies e1 < e2.  If events start at the same
    time, their relative ordering is determined lexicographically comparing
    their titles.
    """

    unique_id = TextLine(
        title=u"A globally unique id for this calendar event.")

    dtstart = Datetime(
        title=u"The datetime.datetime of the start of the event.")

    duration = Timedelta(
        title=u"The duration of the event.")

    title = TextLine(
        title=u"The title of the event.")

    owner = Field(
        title=u"The object that created this event.")

    context = Field(
        title=u"The object in whose calendar this event lives.",
        description=u"""
        For example, when booking resources, the person who's booking
        will be the owner of the booking event, and the resource will
        be the context.
        """)

    location = TextLine(
        title=u"The title of the location where this event takes place.")

    recurrence = Object(
        title=u"The recurrence rule.",
        schema=IRecurrenceRule,
        required=False,
        description=u"""
        None if the event is not recurrent.
        """)

    privacy = Choice(
        title=u"The privacy setting",
        values=['public', 'private', 'hidden'],
        default=u"public",
        description=u"""
        Events that are "private" will be rendered as busy blocks to
        other users, and events that are "hidden" will not be shown to
        other users at all.
        """)

    replace_kw = List(
        title=u"A sequence of keywords that can be passed to replace()",
        value_type=BytesLine(title=u"Keyword"))

    def replace(**kw):
        """Return a calendar event with new specified fields."""

    def __eq__(other): """See if self == other."""
    def __ne__(other): """See if self != other."""
    def __lt__(other): """See if self < other."""
    def __gt__(other): """See if self > other."""
    def __le__(other): """See if self <= other."""
    def __ge__(other): """See if self >= other."""

    def __hash__():
        """Return the hash value of this event.

        It is guaranteed that if calendar events compare equal, hash will
        return the same value.
        """

    def hasOccurrences():
        """Does the event have any occurrences?

        Normally all events have at least one occurrence.  However if you have
        a repeating event that repeats a finite number of times, and all those
        repetitions are listed as exceptions, then hasOccurrences() will return
        False.
        """


class IExpandedCalendarEvent(ICalendarEvent):
    """A calendar event that may be a recurrence of a recurrent event."""


class IInheritedCalendarEvent(ICalendarEvent):
    """A calendar event that was inherited from a group by composition.

    A person may select several groups, whose calendar events she would like
    to see in his personal calendar.  Such events implement this interface.
    """

    calendar = Object(
        title=u"The calendar in which this event resides.",
        schema=ICalendar)


class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Object(
        title=u"The object's calendar.",
        schema=ICalendar)

    # XXX Temporary for SB09
    colors = List(
        title=u"A tuple of color pair tuples for use in calendar display.")

    cal_colors = Dict(
            title=u"Calendar Colors",
            key_type=TextLine(title=u"Symbolic parameter name"),
            value_type=List(),
            description=u"""
            A PersistentDict of {getPath(cal.__parent__): color_tuple}
            mappings.""")

    def makeCompositeCalendar(start, end):
        """Return the composite calendar for this person.

        start, end are dates denoting the period we are interested in.

        Returns a calendar that contains all events from every group
        that is related to this calendar as URICalendarProvider.

        All recurrent events are already expanded in the returned calendar.
        """
