"""
Interface definitions for SchoolBell.

There are two interfaces for calendars: `ICalendar` for read-only calendars,
and `IEditCalendar` for read-write calendars.

Semantically calendars are unordered sets of events.  Events themselves
(`ICalendarEvent`) are immutable and comparable.  If you have an editable
calendar, and want to change an event in it, you need to create a new event
object and put it into the calendar:

    calendar.removeEvent(event)
    replacement_event = event.replace(title=u"New title", ...)
    calendar.addEvent(replacement_event)

Calendars have globally unique IDs.  If you are changing an event in the
fashion demonstrated above, you should preserve its unique_id attribute.

"""

from zope.interface import Interface
from zope.schema import TextLine, Int, Datetime, Date, List, Set, Choice
from zope.schema import Field, Object


class ICalendar(Interface):
    """Calendar.

    A calendar is a set of calendar events (see ICalendarEvent).  Recurring
    events are listed only once.
    """

    def __iter__():
        """Return an iterator over all events in this calendar.

        The order of events is not defined.
        """

    def find(unique_id):
        """Return an event with the given unique id.

        Raises a KeyError if there is no event with this id.
        """

    def expand(first, last):
        """Return an iterator over all expanded events in a given time period.

        "Expanding" here refers to expanding recurring events, that is,
        creating objects for all occurrences of recurring events.  If a
        recurring event has occurreces that overlap the specified time
        interval, every such occurrence is represented as a new calendar event
        with the `dtstart` attribute replaced with the date and time of that
        occurrence.  These events provide IExpandedCalendarEvent and have an
        additional attribute which points to the original event.

        `first` and `last` are datetime.datetimes and define a half-open
        time interval.

        The order of returned events is not defined.
        """


class IEditCalendar(ICalendar):
    """Editable calendar.

    Calendar events are read-only, so to change an event you need to remove
    the old event, and add a replacement event in the calendar.
    """

    def clear():
        """Remove all events."""

    def addEvent(event):
        """Add an event to the calendar.

        Raises ValueError if an event with the same unique_id already exists
        in the calendar.

        Returns the newly added event (which may be a copy of the argument,
        e.g. if the calendar needs its events to be instances of a particular
        class).

        It is perhaps not a good idea to add calendar events that have no
        occurrences into calendars (see ICalendarEvent.hasOccurrences), as they
        will be invisible in date-based of calendar views.

        Do not call addEvent while iterating over the calendar.
        """

    def removeEvent(event):
        """Remove event from the calendar.

        Raises ValueError if event is not present in the calendar.

        Do not call removeEvent while iterating over the calendar.
        """

    def update(calendar):
        """Add all events from another calendar.

            cal1.update(cal2)

        is equivalent to

            for event in cal2:
                cal1.addEvent(event)
        """


class IRecurrenceRule(Interface):
    """Base interface of the recurrence rules.

    Recurrence rules are stored as attributes of ICalendarEvent.  They
    are also immutable and comparable.  To modify the recurrence
    rule of an event, you need to create a new recurrence rule, and a new
    event:

        replacement_rule = event.recurrence.replace(count=3, until=None)
        replacement_event = event.replace(recurrence=replacement_rule)
        calendar.removeEvent(event)
        calendar.addEvent(replacement_event)

    """

    interval = Int(
        title=u"Interval",
        min=1,
        description=u"""
        Interval of recurrence (a positive integer).

        For example, to indicate that an event occurs every second day,
        you would create a DailyRecurrenceRule witl interval equal to 2.
        """)

    count = Int(
        title=u"Count",
        required=False,
        description=u"""
        Number of times the event is repeated.

        Can be None or an integer value.  If count is not None then
        until must be None.  If both count and until are None the
        event repeats forever.
        """)

    until = Date(
        title=u"Until",
        required=False,
        description=u"""
        The date of the last recurrence of the event.

        Can be None or a datetime.date instance.  If until is not None
        then count must be None.  If both count and until are None the
        event repeats forever.
        """)

    exceptions = List(
        title=u"Exceptions",
        value_type=Date(),
        description=u"""
        A list of days when this event does not occur.

        Values in this list must be instances of datetime.date.
        """)

    def replace(**kw):
        """Return a copy of this recurrence rule with new specified fields."""

    def __eq__(other):
        """See if self == other."""

    def __ne__(other):
        """See if self != other."""

    def apply(event, enddate=None):
       """Apply this rule to an event.

       This is a generator that returns the dates on which the event should
       recur.  Be careful when iterating over these dates -- rules that do not
       have either 'until' or 'count' attributes will go on forever.

       The optional enddate attribute can be used to set a range on the dates
       generated by this function (inclusive).
       """

    def iCalRepresentation(dtstart):
       """Return the rule in iCalendar format.

       Returns a list of strings.  XXX more details, please

       dtstart is a datetime representing the date that the recurring
       event starts on.
       """


class IDailyRecurrenceRule(IRecurrenceRule):
    """Daily recurrence."""


class IYearlyRecurrenceRule(IRecurrenceRule):
    """Yearly recurrence."""


class IWeeklyRecurrenceRule(IRecurrenceRule):
    """Weekly recurrence."""

    weekdays = Set(
        title=u"Weekdays",
        value_type=Int(min=0, max=6),
        description=u"""
        A set of weekdays when this event occurs.

        Weekdays are represented as integers from 0 (Monday) to 6 (Sunday).
        This is what the `calendar` and `datetime` modules use.

        The event repeats on the weekday of the first occurence even
        if that weekday is not in this set.
        """)


class IMonthlyRecurrenceRule(IRecurrenceRule):
    """Monthly recurrence."""

    monthly = Choice(
        title=u"Type",
        values=('monthday', 'weekday', 'lastweekday'),
        description=u"""
        Specification of a monthly occurence.

        Can be one of three values: 'monthday', 'weekday', 'lastweekday'.

        'monthday'    specifies that the event recurs on the same day of month
                      (e.g., 25th day of a month).

        'weekday'     specifies that the event recurs on the same week
                      within a month on the same weekday, indexed from the
                      first (e.g. 3rd Friday of a month).

        'lastweekday' specifies that the event recurs on the same week
                      within a month on the same weekday, indexed from the
                      end of month (e.g. 2nd last Friday of a month).
        """)


class ICalendarEvent(Interface):
    """A calendar event.

    Calendar events are immutable and comparable.

    Events are compared in chronological order, so lists of events can be
    sorted.  If two events start at the same time, they are ordered according
    to their titles.

    While `unique_id` is a globally unique ID of a calendar event, you can
    have several calendar event objects with the same value of `unique_id`,
    and they will not be equal if any their attributes are different.
    Semantically these objects are different versions of the same calendar
    event.

    If you need to modify a calendar event in a calendar, you should do
    the following:

        calendar.removeEvent(event)
        replacement_event = event.replace(title=u"New title", ...)
        calendar.addEvent(replacement_event)

    """

    unique_id = TextLine(
        title=u"UID",
        description=u"""
        A globally unique id for this calendar event.

        iCalendar (RFC 2445) recommeds using the RFC 822 addr-spec syntax
        for unique IDs.  Put the current timestamp and a random number
        on the left of the @ sign, and put the hostname on the right.
        """)

    dtstart = Datetime(
        title=u"Start",
        description=u"""
        Date and time when the event starts.
        """)

    duration = Field( # zope.schema does not have TimeInterval
        title=u"Duration",
        description=u"""
        The duration of the event (datetime.timedelta).

        You can compute the event end date/time by adding duration to dtstart.
        """)

    title = TextLine(
        title=u"Title",
        description=u"""The title of the event.""")

    location = TextLine(
        title=u"Location",
        required=False,
        description=u"""The location where this event takes place.""")

    recurrence = Object(
        title=u"Recurrence",
        schema=IRecurrenceRule,
        required=False,
        description=u"""
        The recurrence rule, if this is a recurring event, otherwise None.
        """)

    def replace(**kw):
        """Return a calendar event with new specified fields.

        This is useful for editing calendars.  For example, to change the
        title and location of an event in a calendar, you would do

            calendar.removeEvent(event)
            replacement_event = event.replace(title=u"New title",
                                              location=None)
            calendar.addEvent(replacement_event)

        """

    def __eq__(other):
        """See if self == other."""

    def __ne__(other):
        """See if self != other."""

    def __lt__(other):
        """See if self < other."""

    def __gt__(other):
        """See if self > other."""

    def __le__(other):
        """See if self <= other."""

    def __ge__(other):
        """See if self >= other."""

    def hasOccurrences():
        """Does the event have any occurrences?

        Normally all events have at least one occurrence.  However if you have
        a repeating event that repeats a finite number of times, and all those
        repetitions are listed as exceptions, then hasOccurrences() will return
        False.  There are other corner cases as well (e.g. a recurring event
        with until date that is earlier than dtstart).
        """


class IExpandedCalendarEvent(ICalendarEvent):
    """A single occurrence of a recurring calendar event.

    The original event is stored in the `original` attribute.  The `dtstart`
    attribute contains the date and time of this occurrence and may differ
    from the `dtstart` attribute of the original event.  All other attributes
    are the same.
    """

    dtstart = Datetime(
        title=u"Start",
        description=u"""
        Date and time when this occurrence of the event starts.
        """)

    original = Object(
        title=u"Original",
        schema=ICalendarEvent,
        description=u"""
        The recurring event that generated this occurrence.
        """)

    def replace(**kw):
        """Return a calendar event with new specified fields.

            expanded_event.replace(**kw)

        is (almost) equivalent to

            expanded_event.original.replace(**kw)

        In other words, the returned event will not provide
        IExpandedCalendarEvent and its dtstart attribute will be the date and
        time of the original event rather than this specific occurrence.
        """

