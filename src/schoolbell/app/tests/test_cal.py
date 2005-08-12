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
from textwrap import dedent
from datetime import date, datetime, timedelta

from zope.testing import doctest
from zope.interface.verify import verifyObject


class ResourceStub(object):
    """Stub resource.

    For the purposes of resource booking, a resource is anything that
    has a 'calendar' attribute.
    """

    def __init__(self):
        from schoolbell.app.cal import Calendar
        self.calendar = Calendar(self)


def doctest_CalendarEvent():
    r"""Tests for CalendarEvent.

    CalendarEvents are almost like SimpleCalendarEvents, the main difference
    is that CalendarEvents are mutable and IContained.

        >>> from schoolbell.app.cal import CalendarEvent, Calendar

        >>> event = CalendarEvent(datetime(2005, 2, 7, 16, 24),
        ...                       timedelta(hours=3),
        ...                       "A sample event",
        ...                       unique_id="*the* event")

    The event implements ISchoolBellCalendarEvent:

        >>> from schoolbell.app.interfaces import ISchoolBellCalendarEvent
        >>> verifyObject(ISchoolBellCalendarEvent, event)
        True

    It has a name, which is equal to its unique id, and can have a parent:

        >>> event.__name__
        '*the* event'
        >>> event.__parent__ is None
        True

    The calendar in which the event resides is referenced in __parent__,
    but you should just use adaptation to ICalendar:

    XXX mg: I have second thoughts about using adaptation to navigate.

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


def doctest_CalendarEvent_resource_booking():
    """Resource booking tests for CalendarEvent.

    All calendar events have a `resources` argument, but initially it is empty.

        >>> from schoolbell.app.cal import Calendar, CalendarEvent
        >>> c = Calendar()
        >>> e = CalendarEvent(datetime(2005, 2, 28), None, '')
        >>> c.addEvent(e)
        >>> e.resources
        ()

    It is also read-only.

        >>> e.resources = []
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

    CalendarEvent.bookResource adds the resource to its resources list and
    adds the event into the resource's calendar.

        >>> r = ResourceStub()
        >>> e.bookResource(r)
        >>> e.resources
        (<...ResourceStub object at...>,)
        >>> e in r.calendar
        True

    CalendarEvent.unbookResource undoes this

        >>> e.unbookResource(r)
        >>> e.resources
        ()
        >>> e in r.calendar
        False

    When you create a CalendarEvent, you can pass a list of resources
    to the constructor.  This is equivalent to creating a CalendarEvent
    without the resources argument, and then subsequently calling bookResource
    for each resource.

        >>> a = ResourceStub()
        >>> b = ResourceStub()
        >>> e = CalendarEvent(datetime(2005, 2, 28), None, 'title', resources=[a, b])
        >>> c.addEvent(e)
        >>> a in e.resources and b in e.resources
        True
        >>> e in a.calendar and e in b.calendar
        True
        >>> e.__parent__ is c
        True

    You cannot book the same resource twice:

        >>> e.bookResource(a)
        Traceback (most recent call last):
          ...
        ValueError: resource already booked

    You cannot unbook a resource that is not booked

        >>> e.unbookResource(r)
        Traceback (most recent call last):
          ...
        ValueError: resource not booked

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
        >>> event = CalendarEvent(datetime(2005, 2, 28), None, 'Example 1')

        >>> cal.addEvent(event)
        >>> len(cal)
        1
        >>> list(cal) == [event]
        True

    Added events acquire a parent:

        >>> event.__parent__ is cal
        True

    You should not try to add the same event to a different calendar:

        >>> cal2 = Calendar()
        >>> cal2.addEvent(event)
        Traceback (most recent call last):
        ...
        ValueError: Event already belongs to a calendar

    There are exceptions to the previous rule: resource booking adds the same
    event to several calendars simultaneously.

    Let's add a few more events:

        >>> event2 = CalendarEvent(datetime(2005, 2, 28), None, 'Example 2')
        >>> cal.addEvent(event2)
        >>> event3 = CalendarEvent(datetime(2005, 2, 28), None, 'Example 3')
        >>> cal.addEvent(event3)

    You can't, however, add multiple events with the same unique_id

        >>> event3a = CalendarEvent(datetime(2005, 2, 28), None, 'Example 3',
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

    You can remove an event by calling removeEvent()

        >>> cal.removeEvent(event)

    When an event is removed, its __parent__ becomes None

        >>> event.__parent__ is None
        True

    All events can be removed from a calendar by using clear():

        >>> cal.clear()
        >>> list(cal)
        []

    It also clears __parent__ attributes

        >>> event3.__parent__ is None
        True

    By the way, you can specify the calendar's owner in the constructor:

        >>> class PersonStub:
        ...     title = 'A person'
        >>> parent = PersonStub()
        >>> cal2 = Calendar(parent)
        >>> cal2.__parent__ is parent
        True

    The calendar's `title` is its owner's title:

        >>> cal2.title
        'A person'

    We will trust that `expand` inherited from CalendarMixin has been unit
    tested.
    """


def doctest_Calendar_addEvent_resource_booking():
    """Tests for Calendar.addEvent.

    For the purposes of resource booking, a resource is anything that
    has a 'calendar' attribute.

        >>> resource = ResourceStub()

    When you add an event to a calendar, the calendar's addEvent sets the
    event's __parent__ to itself, or complains loudly if __parent__ already
    set.  Thus normally you cannot add the same calendar event into two
    different calendars.

        >>> from schoolbell.app.cal import Calendar, CalendarEvent
        >>> cal = Calendar()
        >>> e = CalendarEvent(datetime(2005, 2, 28), None, '')
        >>> cal.addEvent(e)
        >>> e.__parent__ is cal
        True

        >>> resource.calendar.addEvent(e)
        Traceback (most recent call last):
          ...
        ValueError: Event already belongs to a calendar

    However, there is an exception to the previous rule: you can add an event
    to a resource's calendar, if the resource is listed in event.resources.

        >>> e._resources = (resource, )
        >>> resource in e.resources
        True

        >>> resource.calendar.addEvent(e)
        >>> e in resource.calendar
        True

    Event's __parent__ is not changed in this case.

        >>> e.__parent__ is cal
        True

    """


def doctest_WriteCalendar():
    r"""Tests for WriteCalendar.

    WriteCalendar is an adapter for calendars into IWriteFile

        >>> from schoolbell.app.cal import Calendar, WriteCalendar
        >>> cal = Calendar()
        >>> writer = WriteCalendar(cal)

        >>> from schoolbell.app.interfaces import IWriteCalendar
        >>> verifyObject(IWriteCalendar, writer)
        True

    Let's check that WriteCalendar is hooked up to the iCalendar parser:

        >>> writer.write(dedent('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... METHOD:PUBLISH
        ... BEGIN:VEVENT
        ... UID:956630271
        ... SUMMARY:Christmas Day
        ... CLASS:PUBLIC
        ... DTSTART;VALUE=DATE:20030501
        ... DTEND;VALUE=DATE:20031226
        ... DTSTAMP:20020430T114937Z
        ... END:VEVENT
        ... END:VCALENDAR
        ... '''))

        >>> len(list(cal))
        1
        >>> event = cal.find('956630271')
        >>> event.title
        u'Christmas Day'

    As iCalendar is a bit unwieldy for testing, we will plant a hook:

        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> def event(unique_id, title, day=22, duration=3, **kwargs):
        ...     return SimpleCalendarEvent(title=title,
        ...                                dtstart=datetime(2005, 2, day),
        ...                                duration=duration,
        ...                                unique_id=unique_id)
        >>> evts = []
        >>> writer.read_icalendar = lambda ignored, ignored_too: evts

    OK, now we can do a trivial test with two events:

        >>> evts = [event('e1', 'Event I'), event('e2', 'Event II')]
        >>> writer.write(None)

        >>> len(list(cal))
        2
        >>> cal.find('e1').title
        'Event I'
        >>> cal.find('e2').title
        'Event II'

    """


def doctest_WriteCalendar_sophisticated():
    r"""Tests for WriteCalendar.

    We start with three calendar events.

        >>> from datetime import datetime, timedelta
        >>> from schoolbell.app.cal import Calendar, CalendarEvent
        >>> cal = Calendar()
        >>> event1 = CalendarEvent(title='Play Doom',
        ...                        dtstart=datetime(2005, 2, 28),
        ...                        duration=timedelta(hours=2),
        ...                        unique_id=u'id1')
        >>> cal.addEvent(event1)
        >>> event2 = CalendarEvent(title='Play chess',
        ...                        dtstart=datetime(2005, 3, 1),
        ...                        duration=timedelta(hours=2),
        ...                        unique_id=u'id2')
        >>> cal.addEvent(event2)
        >>> event3 = CalendarEvent(title='Sleep',
        ...                        dtstart=datetime(2005, 3, 2),
        ...                        duration=timedelta(hours=2),
        ...                        unique_id=u'id3')
        >>> cal.addEvent(event3)

    We will now upload a new calendar that does not change event1, removes
    event2, modifies event3 and adds a new event, event4.
    
        >>> from schoolbell.app.cal import WriteCalendar
        >>> writer = WriteCalendar(cal)
        >>> writer.write(dedent('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... BEGIN:VEVENT
        ... UID:id1
        ... SUMMARY:Play Doom
        ... DTSTART:20050228T000000
        ... DURATION:PT2H
        ... END:VEVENT
        ... BEGIN:VEVENT
        ... UID:id3
        ... SUMMARY:Sleep (zzz)
        ... DTSTART:20050302T000000
        ... DURATION:PT8H
        ... END:VEVENT
        ... BEGIN:VEVENT
        ... UID:id4
        ... SUMMARY:Wake up
        ... DTSTART:20050302T080000
        ... DURATION:PT0H
        ... END:VEVENT
        ... END:VCALENDAR
        ... '''))

    The calendar now contains three events -- event2 is gone, event4 has
    appeared.

        >>> ids = [e.unique_id for e in cal]
        >>> ids.sort()
        >>> ids
        [u'id1', u'id3', u'id4']

    event1 is unchanged, and, in fact, it is the same object

        >>> cal.find('id1') is event1
        True

    event3 was modified in place

        >>> cal.find('id3') is event3
        True
        >>> event3.duration == timedelta(hours=8)
        True

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schoolbell.app.cal',
                                     optionflags=doctest.ELLIPSIS),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
