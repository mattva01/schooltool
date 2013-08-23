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
Mixins for implementing calendars.
"""

import datetime
from pytz import utc
from zope.interface import implements
from schooltool.calendar.interfaces import IExpandedCalendarEvent


class CalendarMixin(object):
    """Mixin for implementing ICalendar methods.

    You do not have to use this mixin, however, it might make implementation
    easier, albeit potentially slower.

    A class that uses this mixin must already implement ICalendar.__iter__.

        >>> from schooltool.calendar.interfaces import ICalendar
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

            >>> class MyCalendar(CalendarMixin):
            ...     def __iter__(self):
            ...         return iter(['event' for n in range(3)])

            >>> cal = MyCalendar()
            >>> len(cal)
            3

        """
        count = 0
        for i in self:
            count += 1
        return count

    def find(self, unique_id):
        """Find a calendar event with a given UID.

        This particular implementation simply performs a linear search by
        iterating over all events and looking at their UIDs.

            >>> from schooltool.calendar.interfaces import ICalendar
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
        assert first.tzname() is not None
        assert last.tzname() is not None

        for event in self:
            for recurrence in event.expand(first, last):
                yield recurrence


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

        >>> from schooltool.calendar.interfaces import ICalendarEvent
        >>> from zope.schema import getFieldNames
        >>> all_attrs = getFieldNames(ICalendarEvent)
        >>> 'unique_id' in all_attrs
        True
        >>> 'allday' in all_attrs
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
                self.description, self.location, self.recurrence, self.allday)\
               == (other.unique_id, other.dtstart, other.duration, other.title,
                   other.description, other.location, other.recurrence,
                   other.allday)

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

    def expand(self, first, last):
        """Return an iterator over all expanded events in a given time period.

        See ICalendarEvent for more details.
        """
        zero = datetime.timedelta(0)
        epsilon = datetime.timedelta.resolution
        if self.recurrence is not None:
            # XXX mg: doesn't dtstart.time() already return UTC time?
            naivetime = self.dtstart.time()
            starttime = naivetime.replace(tzinfo=utc)
            # XXX mg: I have a bad feeling about taking just the date part and
            #         discarding the time and timezone.  It should at least
            #         convert the dates to UTC!
            for recdate in self.recurrence.apply(self, first.date(),
                                                 last.date()):
                dtstart = datetime.datetime.combine(recdate, starttime)
                dtend = dtstart + self.duration
                if self.duration == zero: # corner case: zero-length self
                    dtend += epsilon      # treat it as a very short self
                if dtend > first and dtstart < last:
                    yield ExpandedCalendarEvent(self, dtstart=dtstart)
        else:
            dtstart = self.dtstart
            dtend = dtstart + self.duration
            if self.duration == zero: # corner case: zero-length self
                dtend += epsilon      # treat it as a very short self
            if dtend > first and dtstart < last:
                yield self


class ExpandedCalendarEvent(CalendarEventMixin):
    """A single occurrence of a recurring calendar event.

    When creating an expanded event, you must specify the original recurrent
    event.

        >>> from schooltool.calendar.simple import SimpleCalendarEvent
        >>> from schooltool.calendar.recurrent import DailyRecurrenceRule
        >>> dtstart = datetime.datetime(2005, 2, 10, 1, 2)
        >>> duration = datetime.timedelta(hours=3)
        >>> recurrence = DailyRecurrenceRule()
        >>> original = SimpleCalendarEvent(dtstart, duration, "An event",
        ...                                description="Some description",
        ...                                unique_id="some unique id",
        ...                                location="Out in the open",
        ...                                recurrence=recurrence)

        >>> dtstart2 = datetime.datetime(2005, 2, 11, 1, 2,tzinfo=utc)
        >>> dtstart2.date()
        datetime.date(2005, 2, 11)
        >>> dtstart2.time()
        datetime.time(1, 2)
        >>> dtstart2.tzname()
        'UTC'
        >>> evt = ExpandedCalendarEvent(original, dtstart2)

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IExpandedCalendarEvent, evt)
        True

    The start date of the event will be the specified one:

        >>> evt.dtstart.date()
        datetime.date(2005, 2, 11)
        >>> evt.dtstart.time()
        datetime.time(1, 2)
        >>> evt.dtstart.tzname()
        'UTC'

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
        if dtstart.tzname() not in (None, 'UTC'):
            raise ValueError, 'Can not store non UTC time info'
        self.__dict__["original"] = event
        self.__dict__["dtstart"] = dtstart.replace(tzinfo=utc)

    def __getattr__(self, name):
        return getattr(self.original, name)

    def __setattr__(self, name, value):
        raise AttributeError("can't set attribute")
