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
Unit tests for schoolbell.app.app.

$Id$
"""

import unittest
from datetime import date, datetime, timedelta

from zope.testing import doctest
from zope.interface.verify import verifyObject


def doctest_CalendarEvent():
    r"""Tests for CalendarEvent.

    CalendarEvents are almost like SimpleCalendarEvents, the main difference
    is that CalendarEvents are mutable and IContained.

        >>> from schoolbell.app.cal import CalendarEvent, Calendar

        >>> event = CalendarEvent(datetime(2005, 2, 7, 16, 24),
        ...                       timedelta(hours=3),
        ...                       "A sample event",
        ...                       unique_id="*the* event")

    The event implements IContainedCalendarEvent:

        >>> from schoolbell.app.interfaces import IContainedCalendarEvent
        >>> verifyObject(IContainedCalendarEvent, event)
        True

    It has a name, which is equal to its unique id, and can have a parent:

        >>> event.__name__
        '*the* event'
        >>> event.__parent__ is None
        True

    The calendar in which the event resides is referenced in __parent__,
    but you should just use adaptation to ICalendar:

        >>> event.__parent__ = object()

        >>> from schoolbell.calendar.interfaces import ICalendar
        >>> ICalendar(event) is event.__parent__
        True

    As CalendarEvents are mutable, you can modify attributes at will:

        >>> event.dtend = timedelta(hours=1)
        >>> event.dtend
        datetime.timedelta(0, 3600)

    It is very unwise to touch the __name__ or unique_id of events.
    TODO: enforce this restriction.

    """


def doctest_Calendar():
    r"""Tests for Calendar.

    Let's create a Calendar:

        >>> from schoolbell.app.cal import Calendar
        >>> cal = Calendar()
        >>> cal.__name__
        'calendar'

    The calendar should be an ILocation and it should implement IEditCalendar.

        >>> from schoolbell.calendar.interfaces import IEditCalendar
        >>> from zope.app.location.interfaces import ILocation
        >>> verifyObject(IEditCalendar, cal)
        True
        >>> verifyObject(ILocation, cal)
        True

    A quick look at the empty calendar:

        >>> len(cal)
        0
        >>> list(cal)
        []

    We can add events by using addEvent():

        >>> from schoolbell.app.cal import CalendarEvent
        >>> event = CalendarEvent(None, None, 'Example 1')

        >>> cal.addEvent(event)
        >>> len(cal)
        1
        >>> list(cal) == [event]
        True

        >>> event.__parent__ is cal
        True

    Added events acquire a parent:

        >>> event.__parent__ is cal
        True

    You should not try to add the same event to a different calendar:

        >>> cal2 = Calendar()
        >>> cal2.addEvent(event)
        Traceback (most recent call last):
        ...
        AssertionError: Event already belongs to a calendar

    Let's add a few more events:

        >>> event2 = CalendarEvent(None, None, 'Example 2')
        >>> cal.addEvent(event2)
        >>> event3 = CalendarEvent(None, None, 'Example 3')
        >>> cal.addEvent(event3)

    You can't, however, add multiple events with the same unique_id

        >>> event3a = CalendarEvent(None, None, 'Example 3',
        ...                         unique_id=event3.unique_id)
        >>> cal.addEvent(event3a)
        Traceback (most recent call last):
          ...
        ValueError: an event with this unique_id already exists

    You can iterate through a calendar:

        >>> len(cal)
        3
        >>> titles = [ev.title for ev in cal]
        >>> titles.sort()
        >>> titles
        ['Example 1', 'Example 2', 'Example 3']

    Events can be retrieved by their unique id through find():

        >>> cal.find(event2.unique_id) == event2
        True

        >>> cal.find('nonexistent')
        Traceback (most recent call last):
        ...
        KeyError: 'nonexistent'

    All events can be removed from a calendar by using clear():

        >>> cal.clear()
        >>> list(cal)
        []

    By the way, you can specify the calendar's owner in the constructor:

        >>> parent = object()
        >>> cal2 = Calendar(parent)
        >>> cal2.__parent__ is parent
        True

    We will trust that `expand` inherited from CalendarMixin has been unit
    tested.
    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
