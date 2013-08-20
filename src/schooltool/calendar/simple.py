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
Simple calendar events and calendars.
"""

import datetime
import random
import itertools
import email.Utils

from pytz import utc
from zope.interface import implements

from schooltool.calendar.interfaces import ICalendar, ICalendarEvent
from schooltool.calendar.mixins import CalendarEventMixin, CalendarMixin


class SimpleCalendarEvent(CalendarEventMixin):
    """A simple implementation of ICalendarEvent.

        >>> from datetime import datetime, timedelta
        >>> from zope.interface.verify import verifyObject
        >>> e = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                         timedelta(minutes=15),
        ...                         'Work on schooltool.calendar.simple')
        >>> verifyObject(ICalendarEvent, e)
        True

    If you do not specify a unique ID, a random one is generated

        >>> e.unique_id is not None
        True

    Additional iCal information is also supported

        >>> e2 = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                         timedelta(minutes=15),
        ...                         'Work on schooltool.calendar.simple',
        ...                         description="Python for fun and profit",
        ...                         location="Mt. Vernon Stable",
        ...                         recurrence='FakeRecurrance')
        >>> e2.description
        'Python for fun and profit'
        >>> e2.location
        'Mt. Vernon Stable'
        >>> e2.recurrence
        'FakeRecurrance'

    We're going to store all datetime objects in UTC

        >>> e2.dtstart.tzname()
        'UTC'

    """

    implements(ICalendarEvent)

    # Events in older versions had no allday events so this attribute
    # must be initialized in here
    allday = False

    def __init__(self, dtstart, duration, title, description=None,
                 location=None, unique_id=None, recurrence=None, allday=False):
        assert title is not None, 'title is required'

        if dtstart.tzname() not in (None, 'UTC'):
            raise ValueError, 'Can not store non UTC time info'
        self.dtstart = dtstart.replace(tzinfo=utc)

        self.duration = duration
        self.title = title
        self.description = description
        self.location = location
        self.recurrence = recurrence
        self.allday = allday
        self.unique_id = unique_id
        if not self.unique_id:
            self.unique_id = new_unique_id()


class ImmutableCalendar(CalendarMixin):
    """A simple read-only calendar.

        >>> from datetime import datetime, timedelta
        >>> from zope.interface.verify import verifyObject
        >>> e = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                         timedelta(minutes=15),
        ...                         'Work on schooltool.calendar.simple')
        >>> calendar = ImmutableCalendar([e])
        >>> verifyObject(ICalendar, calendar)
        True

        >>> [e.title for e in calendar]
        ['Work on schooltool.calendar.simple']

        >>> len(calendar)
        1

    """

    implements(ICalendar)

    def __init__(self, events=()):
        self._events = tuple(events)

    def __iter__(self):
        return iter(self._events)

    def __len__(self):
        return len(self._events)


def combine_calendars(*calendars):
    r"""Combine events from several calendars into one read-only calendar.

    Suppose you have several calendars with events

        >>> from datetime import datetime, timedelta
        >>> from schooltool.calendar.simple import SimpleCalendarEvent
        >>> e1 = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                          timedelta(minutes=15),
        ...                          'Work on schooltool.calendar.simple')
        >>> calendar1 = ImmutableCalendar([e1])
        >>> e2 = SimpleCalendarEvent(datetime(2005, 2, 2, 20, 28),
        ...                          timedelta(minutes=10),
        ...                          'Write a test for combine_calendars')
        >>> calendar2 = ImmutableCalendar([e2])

    You can combine them

        >>> calendar = combine_calendars(calendar1, calendar2)
        >>> titles = [e.title for e in calendar]
        >>> titles.sort()
        >>> print '\n'.join(titles)
        Work on schooltool.calendar.simple
        Write a test for combine_calendars

    This calendar is read-only

        >>> from schooltool.calendar.interfaces import IEditCalendar
        >>> IEditCalendar.providedBy(calendar)
        False

        >>> from schooltool.calendar.interfaces import ICalendar
        >>> ICalendar.providedBy(calendar)
        True

    """
    return ImmutableCalendar(itertools.chain(*calendars))


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
    more_uniqueness = '%d.%d' % (datetime.datetime.utcnow().microsecond,
                                 random.randrange(10 ** 6, 10 ** 7))
    # generate an rfc-822 style id and strip angle brackets
    unique_id = email.Utils.make_msgid(more_uniqueness)[1:-1]
    return unique_id

