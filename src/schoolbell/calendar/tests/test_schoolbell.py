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
Unit tests for schoolbell.calendar

$Id$
"""

import unittest
from zope.testing import doctest


def doctest_interfaces():
    """Look for syntax errors in interfaces.py

        >>> import schoolbell.calendar.interfaces

    """


def doctest_CalendarMixin_expand():
    """Tests for CalendarMixin.expand.

    Let's define a calendar that uses CalendarMixin and contains a fixed
    set of events

        >>> from datetime import datetime, timedelta
        >>> from schoolbell.calendar.mixins import CalendarMixin
        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> from schoolbell.calendar.recurrent import DailyRecurrenceRule
        >>> Event = SimpleCalendarEvent # shorter

        >>> class MyCalendar(CalendarMixin):
        ...     def __iter__(self):
        ...         return iter([Event(datetime(2004, 12, 14, 12, 30,tzinfo=utc),
        ...                            timedelta(hours=1), 'a'),
        ...                      Event(datetime(2004, 12, 15, 16, 30,tzinfo=utc),
        ...                            timedelta(hours=1), 'c'),
        ...                      Event(datetime(2004, 12, 15, 14, 30,tzinfo=utc),
        ...                            timedelta(hours=1), 'b'),
        ...                      Event(datetime(2004, 12, 16, 17, 30,tzinfo=utc),
        ...                            timedelta(hours=1), 'd'),
        ...                      Event(datetime(2005,  2,  3,  4,  5,tzinfo=utc),
        ...                            timedelta(hours=4), 'simple'),
        ...                      Event(datetime(2005,  2,  4,  4,  5,tzinfo=utc),
        ...                            timedelta(hours=4), 'recurring',
        ...                            recurrence=DailyRecurrenceRule()),
        ...                     ])

        >>> cal = MyCalendar()

    We will define a convenience function for showing all events returned
    by expand:

        >>> from pytz import timezone
        >>> utc = timezone('UTC')
        >>> def show(first, last):
        ...     first.replace(tzinfo=utc)
        ...     last.replace(tzinfo=utc)
        ...     events = list(cal.expand(first, last))
        ...     events.sort()
        ...     print '[%s]' % ', '.join([e.title for e in events])

        >>> def show_long(first, last):
        ...     first.replace(tzinfo=utc)
        ...     last.replace(tzinfo=utc)
        ...     events = list(cal.expand(first, last))
        ...     events.sort()
        ...     for e in events:
        ...         print e.dtstart.strftime('%Y-%m-%d'), e.title

    Events that fall inside the interval

        >>> show(datetime(2004, 12, 1, tzinfo=utc), datetime(2004, 12, 31,tzinfo=utc))
        [a, b, c, d]

        >>> show(datetime(2004, 12, 15), datetime(2004, 12, 16))
        [b, c]

    Events that fall partially in the interval

        >>> show(datetime(2004, 12, 15, 17, 0),
        ...      datetime(2004, 12, 16, 18, 0))
        [c, d]

    Corner cases: if event.dtstart + event.duration == last, or
    event.dtstart == first, the event is not included.

        >>> show(datetime(2004, 12, 15, 15, 30),
        ...      datetime(2004, 12, 15, 16, 30))
        []

    Recurring events:

        >>> show_long(datetime(2005, 2, 2), datetime(2005, 2, 5))
        2005-02-03 simple
        2005-02-04 recurring

        >>> show_long(datetime(2005, 2, 2), datetime(2005, 2, 6))
        2005-02-03 simple
        2005-02-04 recurring
        2005-02-05 recurring

        >>> show_long(datetime(2005, 2, 10), datetime(2005, 2, 13))
        2005-02-10 recurring
        2005-02-11 recurring
        2005-02-12 recurring

    Recurring events are replaced by proxy objects

        >>> from schoolbell.calendar.interfaces import IExpandedCalendarEvent
        >>> events = list(cal.expand(datetime(2005, 2, 2),
        ...                          datetime(2005, 2, 6)))
        >>> events.sort()
        >>> [IExpandedCalendarEvent.providedBy(e) for e in events]
        [False, True, True]
        >>> events[1].original is events[2].original
        True

    """


def doctest_CalendarMixin_expand_at_midnight():
    """Regression tests for CalendarMixin.expand.

    Bug: an event that occurs at midnight and is 0 minutes long gets lost.

        >>> from datetime import datetime, timedelta
        >>> from schoolbell.calendar.mixins import CalendarMixin
        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> from schoolbell.calendar.recurrent import DailyRecurrenceRule
        >>> e1 = SimpleCalendarEvent(datetime(2005, 3, 2, 0, 0), timedelta(0),
        ...                          "Corner case")
        >>> e2 = SimpleCalendarEvent(datetime(2005, 3, 4, 0, 0), timedelta(0),
        ...                          "Recurring case",
        ...                          recurrence=DailyRecurrenceRule())

        >>> class MyCalendar(CalendarMixin):
        ...     def __iter__(self):
        ...         return iter([e1, e2])
        >>> cal = MyCalendar()

        >>> [e.title
        ...  for e in cal.expand(datetime(2005, 3, 2), datetime(2005, 3, 3))]
        ['Corner case']

        >>> [e.title
        ...  for e in cal.expand(datetime(2005, 3, 1), datetime(2005, 3, 2))]
        []

        >>> [e.title
        ...  for e in cal.expand(datetime(2005, 3, 4), datetime(2005, 3, 5))]
        ['Recurring case']

        >>> [e.title
        ...  for e in cal.expand(datetime(2005, 3, 3), datetime(2005, 3, 4))]
        []

    """


def doctest_CalendarEventMixin_hasOccurrences():
    """Tests for CalendarEventMixin.hasOccurrences.

    We will use SimpleCalendarEvent which is a trivial subclass of
    CalendarEventMixin

        >>> from datetime import date, datetime, timedelta
        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> from schoolbell.calendar.recurrent import DailyRecurrenceRule

    A simple event always has occurrences.

        >>> e1 = SimpleCalendarEvent(datetime(2004, 11, 25, 12, 0),
        ...                          timedelta(minutes=10), 'whatever')
        >>> e1.hasOccurrences()
        True

    A forever-repeating event always has occurrences.

        >>> e2 = SimpleCalendarEvent(datetime(2004, 11, 25, 12, 0),
        ...                          timedelta(minutes=10), 'whatever',
        ...                          recurrence=DailyRecurrenceRule())
        >>> e2.hasOccurrences()
        True

    Here's an event without occurrences:

        >>> e3 = SimpleCalendarEvent(datetime(2004, 11, 25, 12, 0),
        ...                          timedelta(minutes=10), 'whatever',
        ...                          recurrence=DailyRecurrenceRule(
        ...                              count=3,
        ...                              exceptions=[date(2004, 11, 25),
        ...                                          date(2004, 11, 26),
        ...                                          date(2004, 11, 27)]))
        >>> e3.hasOccurrences()
        False

    However remove one exception, and it becomes an occurrence:

        >>> e4 = SimpleCalendarEvent(datetime(2004, 11, 25, 12, 0),
        ...                          timedelta(minutes=10), 'whatever',
        ...                          recurrence=DailyRecurrenceRule(
        ...                              count=3,
        ...                              exceptions=[date(2004, 11, 25),
        ...                                          date(2004, 11, 27)]))
        >>> e4.hasOccurrences()
        True

    """

def doctest_CalendarEventMixin_replace():
    """Make sure CalendarEventMixin.replace does not forget any attributes.

        >>> from schoolbell.calendar.interfaces import ICalendarEvent
        >>> from zope.schema import getFieldNames
        >>> all_attrs = getFieldNames(ICalendarEvent)

    We will use SimpleCalendarEvent which is a trivial subclass of
    CalendarEventMixin

        >>> from datetime import datetime, timedelta
        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> e1 = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                          timedelta(minutes=15),
        ...                          'Work on schoolbell.calendar.simple')

        # XXX Need a better test for this.  event.dtstart should always be a
        # datetime object not a string
        #>>> for attr in all_attrs:
        #...     e2 = e1.replace(**{attr: 'new value'})
        #...     assert getattr(e2, attr) == 'new value', attr
        #...     assert e2 != e1, attr
        #...     assert e2.replace(**{attr: getattr(e1, attr)}) == e1, attr

    """


def doctest_weeknum_bounds():
    """Unit test for schoolbell.calendar.utils.weeknum_bounds.

    Check that weeknum_bounds is the reverse of datetime.isocalendar().

        >>> from datetime import date
        >>> from schoolbell.calendar.utils import weeknum_bounds
        >>> d = date(2000, 1, 1)
        >>> while d < date(2010, 1, 1):
        ...     year, weeknum, weekday = d.isocalendar()
        ...     l, h = weeknum_bounds(year, weeknum)
        ...     assert l <= d <= h
        ...     d += d.resolution

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(doctest.DocFileSuite('../README.txt'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.mixins'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.simple'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.recurrent'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.utils'))
    suite.addTest(doctest.DocTestSuite('schoolbell.calendar.browser',
                        optionflags=doctest.ELLIPSIS | doctest.REPORT_UDIFF))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
