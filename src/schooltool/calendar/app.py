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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool calendaring objects.
"""
import base64

from persistent.dict import PersistentDict
from persistent import Persistent
from zope.interface import implements, implementer
from zope.schema import getFieldNames
from zope.component import adapts, adapter
from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.container.contained import Contained
from zope.location.interfaces import ILocation

from schooltool.calendar.icalendar import read_icalendar
from schooltool.calendar.interfaces import ICalendar
from schooltool.calendar.interfaces import ICalendarEvent
from schooltool.calendar.interfaces import IExpandedCalendarEvent
from schooltool.calendar.mixins import CalendarMixin
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IWriteCalendar
from schooltool.app.interfaces import IHaveCalendar


CALENDAR_KEY = 'schooltool.app.calendar.Calendar'


class CalendarEvent(SimpleCalendarEvent, Persistent, Contained):
    """A persistent calendar event contained in a persistent calendar."""

    implements(ISchoolToolCalendarEvent, IAttributeAnnotatable)

    __parent__ = None

    resources = property(lambda self: self._resources)

    def __init__(self, *args, **kwargs):
        resources = kwargs.pop('resources', ())
        SimpleCalendarEvent.__init__(self, *args, **kwargs)
        self.__name__ = base64.encodestring(self.unique_id.encode('utf-8')).replace('\n', '')
        self._resources = ()
        for resource in resources:
            self.bookResource(resource)

    def __conform__(self, interface):
        if interface is ICalendar:
            return self.__parent__

    def bookResource(self, resource):
        calendar = ISchoolToolCalendar(resource)
        if resource in self.resources:
            raise ValueError('resource already booked')
        if calendar is self.__parent__:
            raise ValueError('cannot book itself')
        self._resources += (resource, )
        if self.__parent__ is not None:
            calendar.addEvent(self)

    def unbookResource(self, resource):
        if resource not in self.resources:
            raise ValueError('resource not booked')
        self._resources = tuple([r for r in self.resources
                                 if r is not resource])
        ISchoolToolCalendar(resource).removeEvent(self)

    @property
    def owner(self):
        if self.__parent__:
            return self.__parent__.__parent__
        else:
            return None


class Calendar(Persistent, CalendarMixin):
    """A persistent calendar."""

    # CalendarMixin is only used for the expand() method

    implements(ISchoolToolCalendar, IAttributeAnnotatable)

    __name__ = 'calendar'

    title = property(lambda self: self.__parent__.title)

    def __init__(self, owner):
        self.events = PersistentDict()
        self.__parent__ = owner

    def __iter__(self):
        return self.events.itervalues()

    def __len__(self):
        return len(self.events)

    def addEvent(self, event):
        assert ISchoolToolCalendarEvent.providedBy(event)
        if event.unique_id in self.events:
            raise ValueError('an event with this unique_id already exists')
        if event.__parent__ is None:
            for resource in event.resources:
                if ISchoolToolCalendar(resource) is self:
                    raise ValueError('cannot book itself')
            event.__parent__ = self
            for resource in event.resources:
                ISchoolToolCalendar(resource).addEvent(event)
        elif self.__parent__ not in event.resources:
            raise ValueError("Event already belongs to a calendar")
        self.events[event.unique_id] = event

    def removeEvent(self, event):
        if self.__parent__ in event.resources:
            event.unbookResource(self.__parent__)
        else:
            del self.events[event.unique_id]
            parent_calendar = event.__parent__
            if self is parent_calendar:
                for resource in event.resources:
                    event.unbookResource(resource)
                event.__parent__ = None

    def clear(self):
        # clear is not actually used anywhere in schooltool.app (except tests),
        # so it doesn't have to be efficient.
        for e in list(self):
            self.removeEvent(e)

    def find(self, unique_id):
        return self.events[unique_id]


def getCalendar(owner):
    """Adapt an ``IAnnotatable`` object to ``ISchoolToolCalendar``."""
    annotations = IAnnotations(owner)
    try:
        return annotations[CALENDAR_KEY]
    except KeyError:
        calendar = Calendar(owner)
        annotations[CALENDAR_KEY] = calendar
        return calendar
getCalendar.factory = Calendar # Convention to make adapter introspectable


class WriteCalendar(object):
    r"""An adapter that allows writing iCalendar data to a calendar.

        >>> calendar = Calendar(None)
        >>> adapter = WriteCalendar(calendar)
        >>> adapter.write('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... SUMMARY:LAN party
        ... DTSTART:20050226T160000
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''')
        >>> for e in calendar:
        ...     print e.dtstart.strftime('%Y-%m-%d %H:%M'), e.title
        2005-02-26 16:00 LAN party

    Supporting other charsets would be nice too:

        >>> calendar = Calendar(None)
        >>> adapter = WriteCalendar(calendar)
        >>> adapter.write('''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... SUMMARY:LAN party %s
        ... DTSTART:20050226T160000
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''' %  chr(163), charset='latin-1')
        >>> titles = [e.title for e in calendar]
        >>> titles[0]
        u'LAN party \xa3'

    """

    adapts(ISchoolToolCalendar)
    implements(IWriteCalendar)

    # Hook for unit tests.
    read_icalendar = staticmethod(read_icalendar)

    _event_attrs = getFieldNames(ICalendarEvent)

    def __init__(self, context, request=None):
        self.calendar = context

    def write(self, data, charset='UTF-8'):
        changes = {} # unique_id -> (old_event, new_event)
        for e in self.calendar:
            changes[e.unique_id] = (e, None)

        for event in self.read_icalendar(data, charset):
            old_event = changes.get(event.unique_id, (None, ))[0]
            changes[event.unique_id] = (old_event, event)

        for old_event, new_event in changes.itervalues():
            if old_event is None:
                # new_event is a SimpleCalendarEvent, we need a CalendarEvent
                kwargs = dict([(attr, getattr(new_event, attr))
                               for attr in self._event_attrs])
                self.calendar.addEvent(CalendarEvent(**kwargs))
            elif new_event is None:
                self.calendar.removeEvent(old_event)
            elif old_event != new_event:
                # modify in place
                for attr in self._event_attrs:
                    setattr(old_event, attr, getattr(new_event, attr))


def clearCalendarOnDeletion(event):
    """When you delete an object, it's calendar should be cleared

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.testing.setup import setUpCalendaring

        >>> setUp()
        >>> setUpCalendaring()

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schooltool.app.cal import clearCalendarOnDeletion
        >>> zope.event.subscribers.append(clearCalendarOnDeletion)

    We will need some object that implements IHaveCalendar for that:

        >>> from zope.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> from schooltool.person.person import Person
        >>> container = BTreeContainer()
        >>> container['petras'] = petras =  Person(username="Petras")
        >>> def clearCalendar():
        ...     print "Clearing calendar"
        >>> ISchoolToolCalendar(petras).clear = clearCalendar

    If we delete Petras his calendar should be cleared:

        >>> del container['petras']
        Clearing calendar

    Restore old subscribers:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """
    if IHaveCalendar.providedBy(event.object):
        ISchoolToolCalendar(event.object).clear()


@adapter(IExpandedCalendarEvent)
@implementer(ILocation)
def expandedEventLocation(event):
    original = event.__dict__['original']
    return ILocation(original)
