SchoolBell calendaring library
==============================

schoolbell.calendar is a calendaring library for Zope 3.


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


Quick overview
--------------

At the moment schoolbell.calendar contains building blocks for calendaring
in your own application.


Calendars
---------

A calendar is a set of events.  A calendar event has a date and time, a
duration, a title, and a bunch of other (optional) attributes like location
or description.  Here's a sample calendar event:

    >>> from datetime import datetime, timedelta
    >>> from schoolbell.calendar.simple import SimpleCalendarEvent
    >>> appointment = SimpleCalendarEvent(datetime(2004, 12, 28, 13, 40),
    ...                                   timedelta(hours=1),
    ...                                   'Dentist')

Calendar events are described by the ICalendarEvent interface.

    >>> from schoolbell.calendar.interfaces import ICalendarEvent
    >>> ICalendarEvent.providedBy(appointment)
    True

SimpleCalendarEvent is but one of classes that implement ICalendarEvent,
see the section on calendar storage below.


Storage of calendars
--------------------

SchoolBell was designed to allow flexibility in calendar storage: calendars
may be stored in the ZODB, in a relational database, as iCalendar files on
disk, or computed on the fly from some other data source.

To achieve this, schoolbell.calendar defines interfaces for calendars
(ICalendar and IEditCalendar) and calendar events (ICalendarEvent) and relies
on objects implementing those interfaces.

You can define your own calendar and calendar event classes.  There are
mixins (CalendarMixin, EditableCalendarMixin, CalendarEventMixin) defined
in schoolbell.calendar.mixins that you can use (if you want to) to implement
some of calendar/calendar event operations.

There are some simple implementations of calendars and calendar events in
schoolbell.calendar.simple: SimpleCalendarEvent and ImmutableCalendar.
They are particularly useful for calendars that are generated on the fly.
For example, suppose we have a list of (fictious) deadlines for a project:

    >>> deadlines = [('2005-02-28', 'Feature freeze'),
    ...              ('2005-03-05', 'Release candidate 1'),
    ...              ('2005-03-15', 'Release')]

We can generate a calendar like this

    >>> from schoolbell.calendar.simple import ImmutableCalendar
    >>> from schoolbell.calendar.simple import SimpleCalendarEvent
    >>> from schoolbell.calendar.utils import parse_datetime
    >>> from datetime import timedelta
    >>> deadline_calendar = ImmutableCalendar([
    ...         SimpleCalendarEvent(parse_datetime(date + ' 00:00:00'),
    ...                             timedelta(hours=1),
    ...                             deadline)
    ...         for date, deadline in deadlines])

(Note that every event will get a new randomly generated unique_id attribute.
If you want to publish a computed calendar as an iCalendar file, you might
want to generate deterministic unique IDs and explicitly pass them to
SimpleCalendarEvent's constructor.)

    >>> for event in deadline_calendar:
    ...     print event.dtstart.strftime('%Y-%m-%d'), event.title
    2005-02-28 Feature freeze
    2005-03-05 Release candidate 1
    2005-03-15 Release


iCalendar
---------

iCalendar (defined in `RFC 2445`__) is a popular calendar representation
format.

  __ http://www.ietf.org/rfc/rfc2445.txt

There is a sample iCalendar file (created with Ximian Evolution) in
schoolbell.calendar.tests

    >>> import os, schoolbell.calendar
    >>> filename = os.path.join(os.path.dirname(schoolbell.calendar.__file__),
    ...                         'tests', 'sample.ics')

You can read an iCalendar file event by event:

    >>> from schoolbell.calendar.icalendar import read_icalendar
    >>> for event in read_icalendar(open(filename)):
    ...     print event.dtstart.strftime('%Y-%m-%d'), event.title
    2005-02-14 #schooltool meeting
    2005-02-09 SchoollTool 0.9 release
    2005-02-09 SchoolTool release party!

You can easily construct a SchoolBell calendar from an iCalendar file

    >>> from schoolbell.calendar.simple import ImmutableCalendar
    >>> calendar = ImmutableCalendar(read_icalendar(open(filename)))
    >>> len(calendar)
    3

You can create an iCalendar file from a SchoolBell calendar.

    >>> from schoolbell.calendar.icalendar import convert_calendar_to_ical
    >>> lines = convert_calendar_to_ical(calendar)
    >>> print "\n".join(lines)                          # doctest: +ELLIPSIS
    BEGIN:VCALENDAR
    VERSION:2.0
    PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN
    BEGIN:VEVENT
    UID:20050211T140836Z-19135-1013-8968-3@muskatas
    ...
    DTSTART:20050209T203000
    DURATION:PT3H
    DTSTAMP:...
    END:VEVENT
    END:VCALENDAR

iCalendar spec mandates lines (including the last one) are terminated by CR LF
characters, so you should use something like

    >>> output_as_string = "\r\n".join(lines + [''])

iCalendar is a large specification, and schoolbell.calendar supports only a
subset of it.  This subset should be enough to interoperate with most open
source calendaring software, but you should keep in mind that reading an
iCalendar file into SchoolBell objects and writing it back is a lossy
transformation.


Calendar composition
--------------------

It is often useful to display several calendars at the same time.  Rather
than iterating over a number of calendars, you may want to construct a single
calendar that contains all the events from those other calendars:

    >>> from schoolbell.calendar.simple import combine_calendars
    >>> cal = combine_calendars(deadline_calendar, calendar)
    >>> len(cal) == len(deadline_calendar) + len(calendar)
    True
    >>> for event in cal:
    ...     print event.dtstart.strftime('%Y-%m-%d'), event.title
    2005-02-28 Feature freeze
    2005-03-05 Release candidate 1
    2005-03-15 Release
    2005-02-14 #schooltool meeting
    2005-02-09 SchoollTool 0.9 release
    2005-02-09 SchoolTool release party!


Utilities
---------

schoolbell.calendar.utils contains a number of small standalone functions
for parsing and manipulating dates.

    >>> from schoolbell.calendar.utils import parse_date, parse_datetime
    >>> parse_date('2004-02-11')
    datetime.date(2004, 2, 11)
    >>> parse_datetime('2004-02-11 15:35:44')
    datetime.datetime(2004, 2, 11, 15, 35, 44)

    >>> from datetime import date
    >>> from schoolbell.calendar.utils import prev_month, next_month
    >>> prev_month(date(2004, 2, 11))
    datetime.date(2004, 1, 1)
    >>> next_month(date(2004, 2, 11))
    datetime.date(2004, 3, 1)

    >>> from calendar import SUNDAY
    >>> from schoolbell.calendar.utils import week_start
    >>> week_start(date(2004, 2, 11)).strftime('%a, %b %e %Y')
    'Mon, Feb  9 2004'
    >>> week_start(date(2004, 2, 11), SUNDAY).strftime('%a, %b %e %Y')
    'Sun, Feb  8 2004'

    >>> from schoolbell.calendar.utils import weeknum_bounds
    >>> s, e = [d.strftime('%a, %b %e') for d in weeknum_bounds(2005, 1)]
    >>> print 'Week 1 of 2005 started on %s and ended on %s.' % (s, e)
    Week 1 of 2005 started on Mon, Jan  3 and ended on Sun, Jan  9.

    >>> from schoolbell.calendar.utils import check_weeknum
    >>> if check_weeknum(2004, 53):
    ...     print "There was a 53-th week in 2004"
    There was a 53-th week in 2004
    >>> if not check_weeknum(2005, 53):
    ...     print "There is no week 53 in 2005"
    There is no week 53 in 2005


Future goals
------------

- Timezones
- All day events
- Ready to use calendar as a Zope 3 content component, with browser views
