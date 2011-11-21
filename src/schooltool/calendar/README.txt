SchoolTool calendaring library
==============================

schooltool.calendar is a calendaring library for Zope 3.


Features
--------

- It can parse and generate iCalendar files.  Only a subset of the iCalendar
  spec is supported, however it is a sensible subset that should be enough for
  interoperation with desktop calendaring applications like Apple's iCal,
  Mozilla Calendar, Evolution, and KOrganizer.

- It is storage independent -- your application could store the calendar in
  ZODB, in a relational database, or elsewhere, as long as the storage
  component provides the necessary interface.

- You can display several calendars in a single view by using calendar
  composition.

- It supports recurring events (daily, weekly, monthly and yearly).

Things that are not currently supported:

- Timezone handling (UTC times are converted into server's local time in the
  iCalendar parser, but that's all).

- All-day events (that is, events that only specify the date but not the time).

- Informing the user when uploaded iCalendar files use features that are not
  supported by SchoolTool.


Modules
-------

At the moment ``schooltool.calendar`` contains building blocks for calendaring
in your own application.

``schooltool.calendar.interfaces``
    defines interfaces for calendars and calendar events.

``schooltool.calendar.simple``
    defines simple calendar and calendar event classes.

    They are not tied into any particular storage system, so if you want to
    store your calendars in the ZODB or in a relational database, you will
    want to write your own.

    TODO: there should be a standard Persistent calendar class in this package.

``schooltool.calendar.mixins``
    defines mixins that make implementation of your own calendar and event classes easier.

``schooltool.calendar.icalendar``
    lets you parse and generate iCalendar (`RFC 2445`_) files.

``schooltool.calendar.browser``
    defines some browser views for calendars.

``schooltool.calendar.recurrent``
    defines some recurrence rules that let you describe events recurring daily,
    weekly, monthly or yearly.

``schooltool.calendar.utils``
    contains a number of small standalone utility functions for manipulating dates and times.


Calendars
---------

A calendar is a set of events.  A calendar event has a date and time, a
duration, a title, and a bunch of other (optional) attributes like location
or description.  Here's a sample calendar event:

    >>> from pytz import utc
    >>> from datetime import datetime, timedelta
    >>> from schooltool.calendar.simple import SimpleCalendarEvent
    >>> appointment = SimpleCalendarEvent(datetime(2004, 12, 28, 13, 40,
    ...                                            tzinfo=utc),
    ...                                   timedelta(hours=1),
    ...                                   'Dentist')

Calendar events are described by the ICalendarEvent interface.

    >>> from schooltool.calendar.interfaces import ICalendarEvent
    >>> ICalendarEvent.providedBy(appointment)
    True

Here's another calendar event.  It repeats every week:

    >>> from schooltool.calendar.recurrent import WeeklyRecurrenceRule
    >>> meeting = SimpleCalendarEvent(datetime(2005, 2, 7, 18, 0, tzinfo=utc),
    ...                               timedelta(hours=1),
    ...                               'IRC meeting',
    ...                               location='#schooltool',
    ...                               recurrence=WeeklyRecurrenceRule())

A calendar is a set of events.  Some calendars are read-only, while others
are editable.  Here's a simple read-only calendar that contains two events:

    >>> from schooltool.calendar.simple import ImmutableCalendar
    >>> calendar = ImmutableCalendar([meeting, appointment])
    >>> len(calendar)
    2

You can iterate over calendars to get all events in unspecified order.  You
can then sort the events by date.  Let us define a simple function for
listing calendar events sorted by date::

    >>> def print_cal(calendar):
    ...     events = list(calendar)
    ...     events.sort()
    ...     for event in events:
    ...         print event.dtstart.strftime('%Y-%m-%d'), event.title

    >>> print_cal(calendar)
    2004-12-28 Dentist
    2005-02-07 IRC meeting

Note that, although IRC meeting repeats weekly, it was printed only once.
If you want to see all occurrences of repeating calendar events, you can
call calendar.expand.  Since some events may repeat indefinitely, expand
takes two datetime arguments and limits returned events to the specified
datetime range.

    >>> print_cal(calendar.expand(datetime(2005, 2, 1, tzinfo=utc),
    ...                           datetime(2005, 3, 1, tzinfo=utc)))
    2005-02-07 IRC meeting
    2005-02-14 IRC meeting
    2005-02-21 IRC meeting
    2005-02-28 IRC meeting


Storage of calendars
--------------------

SchoolTool was designed to allow flexibility in calendar storage: calendars
may be stored in the ZODB, in a relational database, as iCalendar files on
disk, or computed on the fly from some other data source.

To achieve this, ``schooltool.calendar`` defines interfaces for calendars
(``ICalendar`` and ``IEditCalendar``) and calendar events (``ICalendarEvent``) and relies
on objects implementing those interfaces.

You can define your own calendar and calendar event classes.  There are
mixins (``CalendarMixin``, ``EditableCalendarMixin``, ``CalendarEventMixin``) defined
in ``schooltool.calendar.mixins`` that you can use (if you want to) to implement
some of calendar/calendar event operations.

There are some simple implementations of calendars and calendar events in
``schooltool.calendar.simple``: ``SimpleCalendarEvent`` and
``ImmutableCalendar``. They are particularly useful for calendars that are
generated on the fly. For example, suppose we have a list of deadlines for a
project:;

    >>> deadlines = [('2005-02-28', 'Feature freeze'),
    ...              ('2005-03-05', 'Release candidate 1'),
    ...              ('2005-03-15', 'Release')]

We can generate a calendar like this::

    >>> from schooltool.calendar.simple import ImmutableCalendar
    >>> from schooltool.calendar.simple import SimpleCalendarEvent
    >>> from schooltool.calendar.utils import parse_datetimetz
    >>> from datetime import timedelta

    >>> deadline_calendar = ImmutableCalendar([
    ...         SimpleCalendarEvent(parse_datetimetz(date + ' 00:00:00Z'),
    ...                             timedelta(hours=1),
    ...                             deadline)
    ...         for date, deadline in deadlines])

    >>> print_cal(deadline_calendar)
    2005-02-28 Feature freeze
    2005-03-05 Release candidate 1
    2005-03-15 Release

Note that every event will get a new randomly generated `unique_id` attribute.
If you want to publish a computed calendar as an iCalendar file, you might
want to generate deterministic unique IDs and explicitly pass them to
``SimpleCalendarEvent``'s constructor.


iCalendar
---------

iCalendar (defined in `RFC 2445`_) is a popular calendar representation
format.

.. _`RFC 2445`: http://www.ietf.org/rfc/rfc2445.txt

There is a sample iCalendar file (created with Evolution) in
``schooltool.calendar.tests``

    >>> import os, schooltool.calendar
    >>> filename = os.path.join(os.path.dirname(schooltool.calendar.__file__),
    ...                         'tests', 'sample.ics')

You can read an iCalendar file event by event:

    >>> from schooltool.calendar.icalendar import read_icalendar
    >>> print_cal(read_icalendar(open(filename)))
    2005-02-09 SchoollTool 0.9 release
    2005-02-09 SchoolTool release party!
    2005-02-14 #schooltool meeting

Note that read_icalendar returns an iterator, and not a calendar.  If you want
a calendar object, you can create one as follows:

    >>> from schooltool.calendar.simple import ImmutableCalendar
    >>> sample_calendar = ImmutableCalendar(read_icalendar(open(filename)))
    >>> len(sample_calendar)
    3

You can create an iCalendar file from a SchoolTool calendar.

    >>> from schooltool.calendar.icalendar import convert_calendar_to_ical
    >>> lines = convert_calendar_to_ical(sample_calendar)
    >>> print "\n".join(lines)                          # doctest: +ELLIPSIS
    BEGIN:VCALENDAR
    VERSION:2.0
    PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
    BEGIN:VEVENT
    UID:20050211T140836Z-19135-1013-8968-3@muskatas
    ...
    DTSTART:20050209T183000Z
    DURATION:PT3H
    DTSTAMP:...
    END:VEVENT
    END:VCALENDAR

iCalendar spec mandates lines (including the last one) are terminated by CR LF
characters, so you should use something like

    >>> output_as_string = "\r\n".join(lines + [''])

TODO: this is inconvenient.  ``"".join(lines)`` should return a valid iCalendar
stream.  ``fileobject.writelines(lines)`` should just work.  Although there
are other complications with automatic LF -> CRLF transformations when
file objects are opened in text mode.

iCalendar is a large specification, and ``schooltool.calendar`` supports only a
subset of it.  This subset should be enough to interoperate with most open
source calendaring software, but you should keep in mind that reading an
iCalendar file into SchoolTool objects and writing it back is a lossy
transformation.


Calendar composition
--------------------

It is often useful to display several calendars at the same time.  Rather
than iterating over a number of calendars, you may want to construct a single
calendar that contains all the events from those other calendars:

    >>> from schooltool.calendar.simple import combine_calendars
    >>> cal = combine_calendars(deadline_calendar, sample_calendar)
    >>> len(cal) == len(deadline_calendar) + len(sample_calendar)
    True
    >>> print_cal(cal)
    2005-02-09 SchoollTool 0.9 release
    2005-02-09 SchoolTool release party!
    2005-02-14 #schooltool meeting
    2005-02-28 Feature freeze
    2005-03-05 Release candidate 1
    2005-03-15 Release

TODO: when we display a combined calendar, we often want to know where each
event came from.


Recurring events
----------------

Recurring events are calendar events with a defined recurrence rule.  An
example of a recurrence rule that says "this event repeats 5 times on every
third day" is

    >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
    >>> rule = DailyRecurrenceRule(count=5, interval=3)

Currently there are four kinds of recurrence rules defined in
``schooltool.calendar.recurrent``:

- daily recurrences (e.g. "every second day")
- weekly recurrences (e.g. "every week on Monday through Friday")
- monthly recurrences (e.g. "every second Tuesday of a month" or
  "15th of every second month")
- yearly (e.g. "January 29th every year")

All recurrence rules share some common attributes:

`interval`
  to express "every third week" you would create a ``WeeklyRecurrenceRule``
  with an interval of 3.  An interval of 1 means simply "every".
  Intervals lower than 1 are not allowed.

`count` and `until`
  you can limit the number of occurrences by specifying
  an explicit count (e.g. "every second year during the next 10 years" would
  be expressed as ``YearlyRecurrenceRule(interval=2, count=5)``), or by
  specifying the date of the last occurrence (e.g. "every third day until
  August 15th" would be expressed as ``DailyRecurrenceRule(interval=3,
  until=datetime.date(2005, 8, 15))``).  If neither `count` not `until` are
  specified, the rule repeats forever.

`exceptions`
  you can say "repeat every Monday except on February 21" as
  ``WeeklyRecurrenceRule(weekdays=calendar.MONDAY, exceptions=[date(2005, 2, 21)])``.

Weekly recurrence rules let you specify a set of weekdays that the event
occurs on.  E.g. "every second weekend" can be expressed as
``WeeklyRecurrenceRule(interval=2, weekdays=[calendar.SATURDAY, calendar.SUNDAY])``.

Monthly recurrence rules also let you choose one of three variants:

- same day of month (e.g. an event that occurrs on January 29 and has
  a ``MonthlyRecurrenceRule(monthly='monthday')`` will recur on the 29th of
  every month (except Februrary on non-leap years).

- same day of week (e.g. "2nd Tuesday of a month" can be expressed as
  a ``MonthlyRecurrenceRule(monthly='weekday')``, if the recurrence rule is
  assigned to an event that happens on the 2nd Tuesday of some month.

- same day of week, but counting from the end of the month, e.g. "2nd last
  Wednesday of a month" -- ``MonthlyRecurrenceRule(monthly='lastweekday')``.

Here's how you create recurring events:

    >>> from schooltool.calendar.recurrent import YearlyRecurrenceRule
    >>> event = SimpleCalendarEvent(datetime(2005, 1, 29, 12, tzinfo=utc),
    ...                             timedelta(hours=1),
    ...                             'My birthday',
    ...                             recurrence=YearlyRecurrenceRule())

Here's how you can get all recurrence dates of an event:

    >>> iterator = event.recurrence.apply(event)
    >>> iterator.next()
    datetime.date(2005, 1, 29)
    >>> iterator.next()
    datetime.date(2006, 1, 29)
    >>> iterator.next()
    datetime.date(2007, 1, 29)

Usually you will use ``ICalendar.expand``.

    >>> cal = ImmutableCalendar([event])
    >>> print_cal(cal.expand(datetime(2003, 1, 1, tzinfo=utc),
    ...                      datetime(2009, 1, 1, tzinfo=utc)))
    2005-01-29 My birthday
    2006-01-29 My birthday
    2007-01-29 My birthday
    2008-01-29 My birthday

Sometimes a recurrence rule may exclude even the original occurrence:

    >>> from datetime import date
    >>> empty_event = SimpleCalendarEvent(datetime(2005, 2, 3, 12, tzinfo=utc),
    ...                     timedelta(hours=1), 'Copious free time',
    ...                     recurrence=YearlyRecurrenceRule(
    ...                                     until=date(2005, 1, 1)))
    >>> list(empty_event.recurrence.apply(event))
    []

You can check if an even is "empty" by calling ``event.hasOccurrences()``:

    >>> event.hasOccurrences()
    True
    >>> empty_event.hasOccurrences()
    False


Utilities
---------

``schooltool.calendar.utils`` contains a number of small standalone functions
for parsing and manipulating dates::

    >>> from schooltool.calendar.utils import parse_date, parse_datetime
    >>> from schooltool.calendar.utils import parse_datetimetz
    >>> parse_date('2004-02-11')
    datetime.date(2004, 2, 11)
    >>> parse_datetime('2004-02-11 15:35:44')
    datetime.datetime(2004, 2, 11, 15, 35, 44)
    >>> parse_datetimetz('2004-02-11 15:35:44Z')
    datetime.datetime(2004, 2, 11, 15, 35, 44, tzinfo=<UTC>)

    >>> from datetime import date
    >>> from schooltool.calendar.utils import prev_month, next_month
    >>> prev_month(date(2004, 2, 11))
    datetime.date(2004, 1, 1)
    >>> next_month(date(2004, 2, 11))
    datetime.date(2004, 3, 1)

    >>> from calendar import SUNDAY
    >>> from schooltool.calendar.utils import week_start
    >>> week_start(date(2004, 2, 11)).strftime('%a, %b %d %Y')
    'Mon, Feb 09 2004'
    >>> week_start(date(2004, 2, 11), SUNDAY).strftime('%a, %b %d %Y')
    'Sun, Feb 08 2004'

    >>> from schooltool.calendar.utils import weeknum_bounds
    >>> s, e = [d.strftime('%a, %b %d') for d in weeknum_bounds(2005, 1)]
    >>> print 'Week 1 of 2005 started on %s and ended on %s.' % (s, e)
    Week 1 of 2005 started on Mon, Jan 03 and ended on Sun, Jan 09.

    >>> from schooltool.calendar.utils import check_weeknum
    >>> if check_weeknum(2004, 53):
    ...     print "There was a 53-th week in 2004"
    There was a 53-th week in 2004
    >>> if not check_weeknum(2005, 53):
    ...     print "There is no week 53 in 2005"
    There is no week 53 in 2005
