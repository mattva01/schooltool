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

from zope.testing import doctest
from zope.interface.verify import verifyObject


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

        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> event = SimpleCalendarEvent(None, None, 'Example 1')

        >>> cal.addEvent(event)
        >>> len(cal)
        1
        >>> list(cal) == [event]
        True

    Let's add a few more events:

        >>> event2 = SimpleCalendarEvent(None, None, 'Example 2')
        >>> cal.addEvent(event2)
        >>> event3 = SimpleCalendarEvent(None, None, 'Example 3')
        >>> cal.addEvent(event3)

    You can't, however, add multiple events with the same unique_id

        >>> event3a = SimpleCalendarEvent(None, None, 'Example 3',
        ...                               unique_id=event3.unique_id)
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

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
