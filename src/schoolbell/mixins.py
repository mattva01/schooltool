"""
Mixins for implementing calendars.
"""

__metaclass__ = type


class CalendarMixin:
    """Mixin for implementing ICalendar methods.

    You do not have to use this mixin, however it might make implementation
    easier, albeit potentially slower.

    A class that uses this mixin must already implement ICalendar.__iter__.

        >>> from schoolbell.interfaces import ICalendar
        >>> from zope.interface import implements
        >>> class MyCalendar(CalendarMixin):
        ...     implements(ICalendar)
        ...     def __iter__(self):
        ...         return iter([])
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(ICalendar, MyCalendar())
        True

    """

    def find(self, unique_id):
        """Find a calendar event with a given UID.

        This particular implementation simply performs a linear search by
        iterating over all events and looking at their UIDs.

            >>> from schoolbell.interfaces import ICalendar
            >>> from zope.interface import implements

            >>> class Event:
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

            >>> from datetime import datetime, timedelta
            >>> from schoolbell.interfaces import ICalendar
            >>> from zope.interface import implements

            >>> class Event:
            ...     def __init__(self, dtstart, duration, title):
            ...         self.dtstart = dtstart
            ...         self.duration = duration
            ...         self.title = title

            >>> class MyCalendar(CalendarMixin):
            ...     implements(ICalendar)
            ...     def __iter__(self):
            ...         return iter([Event(datetime(2004, 12, 14, 12, 30),
            ...                            timedelta(hours=1), 'a'),
            ...                      Event(datetime(2004, 12, 15, 16, 30),
            ...                            timedelta(hours=1), 'b'),
            ...                      Event(datetime(2004, 12, 15, 14, 30),
            ...                            timedelta(hours=1), 'c'),
            ...                      Event(datetime(2004, 12, 16, 17, 30),
            ...                            timedelta(hours=1), 'd'),
            ...                     ])
            >>> cal = MyCalendar()

        We will define a convenience function for showing all events returned
        by expand:

            >>> def show(first, last):
            ...     events = cal.expand(first, last)
            ...     print '[%s]' % ', '.join([e.title for e in events])

        Events that fall inside the interval

            >>> show(datetime(2004, 12, 1), datetime(2004, 12, 31))
            [a, b, c, d]

            >>> show(datetime(2004, 12, 15), datetime(2004, 12, 16))
            [b, c]

        Events that fall partially in the interval

            >>> show(datetime(2004, 12, 15, 17, 0),
            ...      datetime(2004, 12, 16, 18, 0))
            [b, d]

        Corner cases: if event.dtstart + event.duration == last, or
        event.dtstart == first, the event is not included.

            >>> show(datetime(2004, 12, 15, 15, 30),
            ...      datetime(2004, 12, 15, 16, 30))
            []

        TODO: recurring events

        """
        for event in self:
            # TODO: recurring events
            dtstart = event.dtstart
            dtend = dtstart + event.duration
            if dtend > first and dtstart < last:
                yield event


class EditableCalendarMixin:
    """Mixin for implementing some IEditCalendar methods.

    This mixin implements `clear` and `update` by using `addEvent` and
    `removeEvent`.

        >>> class Event:
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

        >>> cal2 = SampleCalendar()
        >>> cal2.update(cal)
        >>> len(list(cal2))
        3

        >>> cal.clear()
        >>> list(cal)
        []

    """

    def update(self, calendar):
        """Add all events from another calendar to this calendar."""
        for event in calendar:
            self.addEvent(event)

    def clear(self):
        """Remove all events from the calendar."""
        for event in list(self):
            self.removeEvent(event)


class CalendarEventMixin:
    """Mixin for implementing ICalendarEvent comparison methods.

    Calendar events are equal iff all their attributes are equal.  We can get a
    list of those attributes easily because ICalendarEvent is a schema.

        >>> from schoolbell.interfaces import ICalendarEvent
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
                self.location, self.recurrence) \
               == (other.unique_id, other.dtstart, other.duration, other.title,
                   other.location, other.recurrence)

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
        raise NotImplementedError # TODO

    def replace(self, **kw):
        r"""Return a copy of this event with some attributes replaced.

            >>> from schoolbell.interfaces import ICalendarEvent
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
            ...            title='Work on schoolbell.simple',
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
        from schoolbell.simple import SimpleCalendarEvent
        for attr in ['dtstart', 'duration', 'title', 'location', 'unique_id',
                     'recurrence']:
            kw.setdefault(attr, getattr(self, attr))
        return SimpleCalendarEvent(**kw)
