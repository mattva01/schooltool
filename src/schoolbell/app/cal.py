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
SchoolBell calendaring objects.

$Id$
"""

import datetime
from persistent.dict import PersistentDict
from persistent import Persistent
from zope.interface import implements
from zope.schema import getFieldNames
from zope.component import adapts
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container.contained import Contained
from zope.app.filerepresentation.interfaces import IWriteFile
from zope.app.location.interfaces import ILocation

from schoolbell.calendar.icalendar import read_icalendar
from schoolbell.calendar.interfaces import ICalendar
from schoolbell.calendar.interfaces import ICalendarEvent
from schoolbell.calendar.mixins import CalendarMixin
from schoolbell.calendar.simple import SimpleCalendarEvent
from schoolbell.app.interfaces import IContainedCalendarEvent
from schoolbell.app.interfaces import ISchoolBellCalendar


class CalendarEvent(SimpleCalendarEvent, Persistent, Contained):
    """A persistent calendar event contained in a persistent calendar."""

    implements(IContainedCalendarEvent)

    __parent__ = None

    def __init__(self, *args, **kwargs):
        SimpleCalendarEvent.__init__(self, *args, **kwargs)
        self.__name__ = self.unique_id

    def __conform__(self, interface):
        if interface is ICalendar:
            return self.__parent__


class Calendar(Persistent, CalendarMixin):
    """A persistent calendar."""

    # We use the expand() implementation from CalendarMixin

    implements(ISchoolBellCalendar, IAttributeAnnotatable)

    __name__ = 'calendar'

    def __init__(self, owner=None):
        self.events = PersistentDict()
        self.__parent__ = owner

    def __iter__(self):
        return self.events.itervalues()

    def __len__(self):
        return len(self.events)

    def addEvent(self, event):
        assert IContainedCalendarEvent.providedBy(event)
        assert event.__parent__ is None, "Event already belongs to a calendar"
        if event.unique_id in self.events:
            raise ValueError('an event with this unique_id already exists')
        self.events[event.unique_id] = event
        event.__parent__ = self

    def removeEvent(self, event):
        del self.events[event.unique_id]

    def clear(self):
        self.events.clear()

    def find(self, unique_id):
        return self.events[unique_id]


class WriteCalendar(object):
    """An adapter that allows writing iCalendar date to a calendar.

        >>> calendar = Calendar()
        >>> adapter = WriteCalendar(calendar)
        >>> adapter.write('''
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... SUMMARY:LAN party
        ... DTSTART:20050226T160000
        ... DURATION:P6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''')
        >>> for e in calendar:
        ...     print e.dtstart.strftime('%Y-%m-%d %H:%M'), e.title
        2005-02-26 16:00 LAN party

    """

    adapts(ISchoolBellCalendar)
    implements(IWriteFile)

    # Hook for unit tests.
    read_icalendar = staticmethod(read_icalendar)

    _event_attrs = getFieldNames(ICalendarEvent)

    def __init__(self, context):
        self.calendar = context

    def write(self, data):
        events = []
        for vevent in self.read_icalendar(data):
            kwargs = dict([(attr, getattr(vevent, attr))
                           for attr in self._event_attrs])
            events.append(CalendarEvent(**kwargs))
        self.calendar.clear()
        for e in events:
            self.calendar.addEvent(e)

