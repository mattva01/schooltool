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

iCalendar is a large specification, and schoolbell.calendar supports only a
subset of it.  This subset should be enough to interoperate with most open
source calendaring software, but you should keep in mind that reading an
iCalendar file into SchoolBell objects and writing it back is a lossy
transformation.


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
