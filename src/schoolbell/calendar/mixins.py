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
Mixins for implementing calendars.

$Id$
"""

import datetime
from zope.interface import implements
from schoolbell.calendar.interfaces import IExpandedCalendarEvent


class CalendarMixin(object):
    """Mixin for implementing ICalendar methods.

    You do not have to use this mixin, however it might make implementation
    easier, albeit potentially slower.

    A class that uses this mixin must already implement ICalendar.__iter__.

        >>> from schoolbell.calendar.interfaces import ICalendar
        >>> from zope.interface import implements
        >>> class MyCalendar(CalendarMixin):
        ...     implements(ICalendar)
        ...     def __iter__(self):
        ...         return iter([])
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(ICalendar, MyCalendar())
        True

    """

    def __len__(self):
        """Return the number of events in this calendar.

        This implementation just returns len(list(self)), which is not very
        efficient.

            >>> class MyCalendar(CalendarMixin):
            ...     def __iter__(self):
            ...         return iter(['event' for n in range(3)])

            >>> cal = MyCalendar()
            >>> len(cal)
            3

        """
        return len(list(self))

    def find(self, unique_id):
        """Find a calendar event with a given UID.

        This particular implementation simply performs a linear search by
        iterating over all events and looking at their UIDs.

            >>> from schoolbell.calendar.interfaces import ICalendar
            >>> from zope.interface import implements

            >>> class Event(object):
            ...     def __init__(self, uid):
            ...         self.unique_id = uid

            >>> class MyCalendar(CalendarMixin):
            ...     implements(ICalendar)
            ...     def __iter__(self):
            ...         return iter([Event(uid) for uid in 'a', 'b'])
            >>> cal = MyCalendar()

            >>> cal.find('a').unique_id
            'a'
            >>> cal.find('b').unique_id
            'b'
            >>> cal.find('c')
            Traceback (most recent call last):
              ...
            KeyError: 'c'

        """
        for event in self:
            if event.unique_id == unique_id:
                return event
        raise KeyError(unique_id)

    def expand(self, first, last):
        """Return an iterator over all expanded events in a given time period.

        See ICalendar for more details.
        """
        zero = datetime.timedelta(0)
        epsilon = datetime.timedelta.resolution
        for event in self:
            if event.recurrence is not None:
                starttime = event.dtstart.time()
                for recdate in event.recurrence.apply(event, last.date()):
                    dtstart = datetime.datetime.combine(recdate, starttime)
                    dtend = dtstart + event.duration
                    if event.duration == zero: # corner case: zero-length event
                        dtend += epsilon       # treat it as a very short event
                    if dtend > first and dtstart < last:
                        yield ExpandedCalendarEvent(event, dtstart=dtstart)
            else:
                dtstart = event.dtstart
                dtend = dtstart + event.duration
                if event.duration == zero: # corner case: zero-length event
                    dtend += epsilon       # treat it as a very short event
                if dtend > first and dtstart < last:
                    yield event


class EditableCalendarMixin(object):
    """Mixin for implementing some IEditCalendar methods.

    This mixin implements `clear` by using `removeEvent`.

        >>> class Event(object):
        ...     def __init__(self, uid):
        ...         self.unique_id = uid

        >>> class SampleCalendar(EditableCalendarMixin):
        ...     def __init__(self):
        ...         self._events = {}
        ...     def __iter__(self):
        ...         return self._events.itervalues()
        ...     def addEvent(self, event):
        ...         self._events[event.unique_id] = event
        ...     def removeEvent(self, event):
        ...         del self._events[event.unique_id]

        >>> cal = SampleCalendar()
        >>> cal.addEvent(Event('a'))
        >>> cal.addEvent(Event('b'))
        >>> cal.addEvent(Event('c'))
        >>> len(list(cal))
        3

        >>> cal.clear()
        >>> list(cal)
        []

    """

    def clear(self):
        """Remove all events from the calendar."""
        for event in list(self):
            self.removeEvent(event)


class CalendarEventMixin(object):
    """Mixin for implementing ICalendarEvent comparison methods.

    Calendar events are equal iff all their attributes are equal.  We can get a
    list of those attributes easily because ICalendarEvent is a schema.

        >>> from schoolbell.calendar.interfaces import ICalendarEvent
        >>> from zope.schema import getFieldNames
        >>> all_attrs = getFieldNames(ICalendarEvent)
        >>> 'unique_id' in all_attrs
        True
        >>> '__eq__' not in all_attrs
        True

    We will create a bunch of Event objects that differ in exactly one
    attribute and compare them.

        >>> class Event(CalendarEventMixin):
        ...     def __init__(self, **kw):
        ...         for attr in all_attrs:
        ...             setattr(self, attr, '%s_default_value' % attr)
        ...         for attr, value in kw.items():
        ...             setattr(self, attr, value)

        >>> e1 = Event()
        >>> for attr in all_attrs:
        ...     e2 = Event()
        ...     setattr(e2, attr, 'some other value')
        ...     assert e1 != e2, 'change in %s was not noticed' % attr

    If you have two events with the same values in all ICalendarEvent
    attributes, they are equal

        >>> e1 = Event()
        >>> e2 = Event()
        >>> e1 == e2
        True

    even if they have extra attributes

        >>> e1 = Event()
        >>> e1.annotation = 'a'
        >>> e2 = Event()
        >>> e2.annotation = 'b'
        >>> e1 == e2
        True

    Events are ordered by their date and time, title and, finally, UID (to
    break any ties and provide a stable consistent ordering).

        >>> from datetime import datetime

        >>> e1 = Event(dtstart=datetime(2004, 12, 15))
        >>> e2 = Event(dtstart=datetime(2004, 12, 16))
        >>> e1 < e2
        True

        >>> e1 = Event(dtstart=datetime(2004, 12, 15), title="A")
        >>> e2 = Event(dtstart=datetime(2004, 12, 15), title="B")
        >>> e1 < e2
        True

        >>> e1 = Event(dtstart=datetime(2004, 12, 1), title="A", unique_id="X")
        >>> e2 = Event(dtstart=datetime(2004, 12, 1), title="A", unique_id="Y")
        >>> e1 < e2
        True

    """

    def __eq__(self, other):
        """Check whether two calendar events are equal."""
        return (self.unique_id, self.dtstart, self.duration, self.title,
                self.description, self.location, self.recurrence) \
               == (other.unique_id, other.dtstart, other.duration, other.title,
                   other.description, other.location, other.recurrence)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return (self.dtstart, self.title, self.unique_id) \
               < (other.dtstart, other.title, other.unique_id)

    def __gt__(self, other):
        return (self.dtstart, self.title, self.unique_id) \
               > (other.dtstart, other.title, other.unique_id)

    def __le__(self, other):
        return (self.dtstart, self.title, self.unique_id) \
               <= (other.dtstart, other.title, other.unique_id)

    def __ge__(self, other):
        return (self.dtstart, self.title, self.unique_id) \
               >= (other.dtstart, other.title, other.unique_id)

    def hasOccurrences(self):
        """Check whether the event has any occurrences."""
        if self.recurrence is None:
            # No recurrence rule implies one and only one occurrence.
            return True
        if self.recurrence.until is None and self.recurrence.count is None:
            # Events that repeat forever always have occurrences.  There is a
            # finite number of exceptions, so they cannon cover an infinite
            # numer of recurrences.
            return True
        try:
            self.recurrence.apply(self).next()
        except StopIteration:
            # No occurrences.
            return False
        else:
            # At least one occurrence exists.
            return True

    def replace(self, **kw):
        r"""Return a copy of this event with some attributes replaced.

            >>> from schoolbell.calendar.interfaces import ICalendarEvent
            >>> from zope.schema import getFieldNames
            >>> all_attrs = getFieldNames(ICalendarEvent)
            >>> class Event(CalendarEventMixin):
            ...     def __init__(self, **kw):
            ...         for attr in all_attrs:
            ...             setattr(self, attr, '%s_default_value' % attr)
            ...         for attr, value in kw.items():
            ...             setattr(self, attr, value)

            >>> from datetime import datetime, timedelta
            >>> e1 = Event(dtstart=datetime(2004, 12, 15, 18, 57),
            ...            duration=timedelta(minutes=15),
            ...            title='Work on schoolbell.calendar.simple',
            ...            location=None)

            >>> e2 = e1.replace(location=u'Matar\u00f3')
            >>> e2 == e1
            False
            >>> e2.title == e1.title
            True
            >>> e2.location
            u'Matar\xf3'

            >>> e3 = e2.replace(location=None)
            >>> e3 == e1
            True

        """
        # The import is here to avoid cyclic dependencies
        from schoolbell.calendar.simple import SimpleCalendarEvent
        for attr in ['dtstart', 'duration', 'title', 'description', 'location',
                     'unique_id', 'recurrence']:
            kw.setdefault(attr, getattr(self, attr))
        # We explicitly return SimpleCalendarEvent instead of using
        # self.__class__ here because self.class might be unsuitable.  E.g.
        # if we have a calendar event class that inherits from SQLObject,
        # instantiating new instances will implicitly create new rows in
        # a relational database table.
        return SimpleCalendarEvent(**kw)


class ExpandedCalendarEvent(CalendarEventMixin):
    """A single occurrence of a recurring calendar event.

    When creating an expanded event, you must specify the original recurrent
    event.

        >>> from schoolbell.calendar.simple import SimpleCalendarEvent
        >>> from schoolbell.calendar.recurrent import DailyRecurrenceRule
        >>> dtstart = datetime.datetime(2005, 2, 10, 1, 2)
        >>> duration = datetime.timedelta(hours=3)
        >>> recurrence = DailyRecurrenceRule()
        >>> original = SimpleCalendarEvent(dtstart, duration, "An event",
        ...                                description="Some description",
        ...                                unique_id="some unique id",
        ...                                location="Out in the open",
        ...                                recurrence=recurrence)

        >>> dtstart2 = datetime.datetime(2005, 2, 11, 1, 2)
        >>> evt = ExpandedCalendarEvent(original, dtstart2)

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IExpandedCalendarEvent, evt)
        True

    The start date of the event will be the specified one:

        >>> evt.dtstart
        datetime.datetime(2005, 2, 11, 1, 2)

    Other attributes will be the same as in the original event:

        >>> evt.duration
        datetime.timedelta(0, 10800)

        >>> evt.title
        'An event'

        >>> evt.description
        'Some description'

        >>> evt.location
        'Out in the open'

        >>> evt.recurrence
        DailyRecurrenceRule(1, None, None, ())

    Attribute values may not be modified:

        >>> evt.dtstart = 'b0rk'
        Traceback (most recent call last):
        ...
        AttributeError: can't set attribute

        >>> evt.location = 'b0rk'
        Traceback (most recent call last):
        ...
        AttributeError: can't set attribute

    """

    implements(IExpandedCalendarEvent)

    def __init__(self, event, dtstart):
        self.__dict__["original"] = event
        self.__dict__["dtstart"] = dtstart

    def __getattr__(self, name):
        return getattr(self.original, name)

    def __setattr__(self, name, value):
        raise AttributeError("can't set attribute")
