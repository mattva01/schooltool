"""
Simple calendar events and calendars.
"""

import datetime
import random
import email.Utils
from zope.interface import implements
from schoolbell.interfaces import ICalendar, ICalendarEvent
from schoolbell.mixins import CalendarEventMixin, CalendarMixin

__metaclass__ = type


class SimpleCalendarEvent(CalendarEventMixin):
    """A simple implementation of ICalendarEvent.

        >>> from datetime import datetime, timedelta
        >>> from zope.interface.verify import verifyObject
        >>> e = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                         timedelta(minutes=15),
        ...                         'Work on schoolbell.simple')
        >>> verifyObject(ICalendarEvent, e)
        True

    If you do not specify a unique ID, a random one is generated

        >>> e.unique_id is not None
        True

    """

    implements(ICalendarEvent)

    def __init__(self, dtstart, duration, title, location=None, unique_id=None,
                 recurrence=None):
        self.dtstart = dtstart
        self.duration = duration
        self.title = title
        self.location = location
        self.recurrence = recurrence
        self.unique_id = unique_id
        if not self.unique_id:
            self.unique_id = new_unique_id()


class ImmutableCalendar(CalendarMixin):
    """A simple read-only calendar.

        >>> from datetime import datetime, timedelta
        >>> from zope.interface.verify import verifyObject
        >>> e = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                         timedelta(minutes=15),
        ...                         'Work on schoolbell.simple')
        >>> calendar = ImmutableCalendar([e])
        >>> verifyObject(ICalendar, calendar)
        True

        >>> [e.title for e in calendar]
        ['Work on schoolbell.simple']

    """

    implements(ICalendar)

    def __init__(self, events=()):
        self._events = tuple(events)

    def __iter__(self):
        return iter(self._events)


def new_unique_id():
    """Generate a new unique ID for a calendar event.

    UID is randomly generated and follows RFC 822 addr-spec:

        >>> uid = new_unique_id()
        >>> '@' in uid
        True

    Note that it does not have the angle brackets

        >>> '<' not in uid
        True
        >>> '>' not in uid
        True

    """
    more_uniqueness = '%d.%d' % (datetime.datetime.now().microsecond,
                                 random.randrange(10 ** 6, 10 ** 7))
    # generate an rfc-822 style id and strip angle brackets
    unique_id = email.Utils.make_msgid(more_uniqueness)[1:-1]
    return unique_id

