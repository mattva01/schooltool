#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
SchoolTool calendaring stuff.

$Id$
"""

import datetime
import calendar
import email.Utils
from sets import Set
from zope.interface import implements
from persistent import Persistent
from persistent.list import PersistentList
from schooltool.auth import ACL
from schooltool.component import getRelatedObjects
from schooltool.interfaces import ISchooldayModel, ISchooldayModelWrite
from schooltool.interfaces import ILocation, IDateRange
from schooltool.interfaces import ICalendar, ICalendarWrite, ICalendarEvent
from schooltool.interfaces import ICalendarOwner, IExpandedCalendarEvent
from schooltool.interfaces import IACLCalendar
from schooltool.interfaces import ViewPermission
from schooltool.interfaces import ModifyPermission, AddPermission
from schooltool.interfaces import Unchanged
from schooltool.interfaces import IRecurrenceRule
from schooltool.interfaces import IDailyRecurrenceRule, IYearlyRecurrenceRule
from schooltool.interfaces import IWeeklyRecurrenceRule, IMonthlyRecurrenceRule
from schooltool.uris import URICalendarProvider
from icalendar import ical_weekdays, ical_date, ical_date_time

__metaclass__ = type


#
# Date ranges and schoolday models
#

class DateRange:

    implements(IDateRange)

    def __init__(self, first, last):
        self.first = first
        self.last = last
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))

    def __iter__(self):
        date = self.first
        while date <= self.last:
            yield date
            date += datetime.date.resolution

    def __len__(self):
        return (self.last - self.first).days + 1

    def __contains__(self, date):
        return self.first <= date <= self.last


class SchooldayModel(DateRange, Persistent):

    implements(ISchooldayModel, ISchooldayModelWrite, ILocation)

    def __init__(self, first, last):
        DateRange.__init__(self, first, last)
        self._schooldays = Set()
        self.__parent__ = None
        self.__name__ = None

    def _validate(self, date):
        if not date in self:
            raise ValueError("Date %r not in period [%r, %r]" %
                             (date, self.first, self.last))

    def isSchoolday(self, date):
        self._validate(date)
        if date in self._schooldays:
            return True
        return False

    def add(self, date):
        self._validate(date)
        self._schooldays.add(date)
        self._schooldays = self._schooldays  # persistence

    def remove(self, date):
        self._validate(date)
        self._schooldays.remove(date)
        self._schooldays = self._schooldays  # persistence

    def addWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays and self.isSchoolday(date):
                self.remove(date)

    def toggleWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                if self.isSchoolday(date):
                    self.remove(date)
                else:
                    self.add(date)

    def reset(self, first, last):
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))
        self.first = first
        self.last = last
        self._schooldays.clear()


#
# Calendaring
#

class Calendar(Persistent):

    implements(ICalendar, ICalendarWrite, ILocation)

    def __init__(self):
        self.events = Set()
        self.__name__ = None
        self.__parent__ = None

    def __iter__(self):
        return iter(self.events)

    def find(self, unique_id):
        # We could speed it up by building and maintaining index
        for event in self:
            if event.unique_id == unique_id:
                return event
        raise KeyError(unique_id)

    def byDate(self, date):
        cal = Calendar()
        for event in self:
            event_start = event.dtstart.date()
            event_end = (event.dtstart + event.duration).date()
            if event_start <= date <= event_end:
                cal.addEvent(event)
        return cal

    def expand(self, first, last):
        cal = Calendar()
        for event in self:
            if event.recurrence is not None:
                starttime = event.dtstart.time()
                for recdate in event.recurrence.apply(event, last):
                    if first <= recdate <= last:
                        start = datetime.datetime.combine(recdate, starttime)
                        new = event.replace(dtstart=start)
                        cal.addEvent(ExpandedCalendarEvent.duplicate(new))
            else:
                event_start = event.dtstart.date()
                event_end = (event.dtstart + event.duration).date()
                if (first <= event_start <= last or
                    event_start <= first <= event_end):
                    cal.addEvent(ExpandedCalendarEvent.duplicate(event))
        return cal

    def addEvent(self, event):
        self.events.add(event)
        self.events = self.events  # make persistence work

    def _removeEvent(self, event):
        self.events.remove(event)
        self.events = self.events  # make persistence work

    def removeEvent(self, event):
        self._removeEvent(event)
        # In SchoolTool resource booking works as follows:
        #   1. A CalendarEvent is created with owner == the user who booked
        #      the resource and context == the resource.
        #   2. That event is added to both the owner's calendar and the
        #   resource's calendar.
        # When that event is removed from either the owner's or the resource's
        # calendar, it should be removed from the other one as well.
        owner_calendar = event.owner is not None and event.owner.calendar
        context_calendar = event.context is not None and event.context.calendar
        if self is owner_calendar or self is context_calendar:
            if owner_calendar is not None and owner_calendar is not self:
                owner_calendar._removeEvent(event)
            if context_calendar is not None and context_calendar is not self:
                context_calendar._removeEvent(event)

    def update(self, calendar):
        for event in calendar:
            self.events.add(event)
        self.events = self.events  # make persistence work

    def clear(self):
        self.events.clear()
        self.events = self.events  # make persistence work


class CalendarEvent(Persistent):

    implements(ICalendarEvent)

    unique_id = property(lambda self: self._unique_id)
    dtstart = property(lambda self: self._dtstart)
    duration = property(lambda self: self._duration)
    title = property(lambda self: self._title)
    owner = property(lambda self: self._owner)
    context = property(lambda self: self._context)
    location = property(lambda self: self._location)
    recurrence = property(lambda self: self._recurrence)
    privacy = property(lambda self: self._privacy)
    _privacy = "public"

    def __init__(self, dtstart, duration, title, owner=None, context=None,
                 location=None, unique_id=None, recurrence=None,
                 privacy="public"):
        self._dtstart = dtstart
        self._duration = duration
        self._title = title
        self._owner = owner
        self._context = context
        self._location = location
        self._recurrence = recurrence
        if not privacy in ('private', 'public', 'hidden'):
             raise ValueError("privacy must be one of 'private',"
                              " 'public', or 'hidden', got %r" % (privacy, ))
        self._privacy = privacy

        if unique_id is None:
            # & 0x7ffffff to avoid FutureWarnings with negative numbers
            nonnegative_hash = hash((self.dtstart, self.title, self.duration,
                                     self.owner, self.context,
                                     self.location)) & 0x7ffffff
            more_uniqueness = '%d.%08X' % (datetime.datetime.now().microsecond,
                                           nonnegative_hash)
            # generate an rfc-822 style id and strip angle brackets
            unique_id = email.Utils.make_msgid(more_uniqueness)[1:-1]
        self._unique_id = unique_id

    replace_kw = ('dtstart', 'duration', 'title','owner', 'context',
                  'location', 'unique_id', 'recurrence', 'privacy')

    def replace(self,  **kw):
        """Returns a copy of the event with some attrs changed.

        replace_kw is a list of keywords that are passed to the constructor.
        """

        for k in self.replace_kw:
            if k not in kw:
                kw[k] = getattr(self, k)

        dtstart = kw.pop('dtstart')
        duration = kw.pop('duration')
        title = kw.pop('title')
        return self.__class__(dtstart, duration, title, **kw)

    def _tupleForComparison(self):
        return (self.dtstart, self.title, self.duration, self.owner,
                self.context, self.location, self.unique_id,
                self.recurrence, self.privacy)

    def __eq__(self, other):
        if not isinstance(other, CalendarEvent):
            return False
        return self._tupleForComparison() == other._tupleForComparison()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self._tupleForComparison() < other._tupleForComparison()

    def __le__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self._tupleForComparison() <= other._tupleForComparison()

    def __gt__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self._tupleForComparison() > other._tupleForComparison()

    def __ge__(self, other):
        if not isinstance(other, CalendarEvent):
            raise TypeError('Cannot compare CalendarEvent with %r' % other)
        return self._tupleForComparison() >= other._tupleForComparison()

    def __hash__(self):
        # Technically speaking,
        #    return hash(self.unique_id)
        # should be enough, if the ID is really unique.
        return hash((self.dtstart, self.title, self.duration, self.owner,
                     self.context, self.location, self.unique_id,
                     self.recurrence, self.privacy))

    def __repr__(self):
        return ("%s%r"
                % (self.__class__.__name__,
                   (self.dtstart, self.duration, self.title, self.owner,
                    self.context, self.location, self.unique_id,
                    self.recurrence, self.privacy), ))

    def hasOccurrences(self):
        if self.recurrence is None:
            # No recurrence rule implies one and only one occurrence
            return True
        if self.recurrence.until is None and self.recurrence.count is None:
            # Events that repeat forever always have occurrences because
            # there is a finite number of exceptions.
            return True
        try:
            self.recurrence.apply(self).next()
        except StopIteration:
            # No occurrences
            return False
        else:
            # At least ne occurrence exists
            return True


class ExpandedCalendarEvent(CalendarEvent):
    """Event in an expanded calendar

    Can be either a real event or a recurrence of some other event.  If it
    is a recurrence, the dtstart attribute will be different from the original
    event.
    """

    implements(IExpandedCalendarEvent)

    def duplicate(cls, ev):
        """Create an expanded event which is equal to the event passed."""
        return cls(ev.dtstart, ev.duration, ev.title, owner=ev.owner,
                   context=ev.context, location=ev.location,
                   unique_id=ev.unique_id, recurrence=ev.recurrence,
                   privacy=ev.privacy)

    duplicate = classmethod(duplicate)


class ACLCalendar(Calendar):

    implements(IACLCalendar)

    def __init__(self):
        self.acl = ACL()
        self.acl.__parent__ = self
        self.acl.__name__ = 'acl'
        Calendar.__init__(self)


class CalendarOwnerMixin(Persistent):

    implements(ICalendarOwner)

    def __init__(self):
        self.calendar = ACLCalendar()
        self.calendar.__parent__ = self
        self.calendar.__name__ = 'calendar'

    def makeCompositeCalendar(self):
        result = Calendar()
        result.__parent__ = self
        result.__name__ = 'composite-calendar'
        for group in getRelatedObjects(self, URICalendarProvider):
            result.update(group.calendar)
        # TODO: Mark the resulting events as coming from a composite calendar.
        return result

    def addSelfToCalACL(self):
        self.calendar.acl.add((self, ViewPermission))
        self.calendar.acl.add((self, AddPermission))
        self.calendar.acl.add((self, ModifyPermission))


class RecurrenceRule:

    implements(IRecurrenceRule)

    interval = property(lambda self: self._interval)
    count = property(lambda self: self._count)
    until = property(lambda self: self._until)
    exceptions = property(lambda self: self._exceptions)

    # A string that represents the recurrence frequency in iCalendar.
    # Must be overridden by subclasses.
    ical_freq = None

    def __init__(self, interval=1, count=None, until=None, exceptions=()):
        self._interval = interval
        self._count = count
        self._until = until
        self._exceptions = tuple(exceptions)
        self._validate()

    def _validate(self):
        if self.count is not None and self.until is not None:
            raise ValueError("count and until cannot be both set (%s, %s)"
                             % (self.count, self.until))
        if not self.interval >= 1:
            raise ValueError("interval must be a positive integer (got %r)"
                             % (self.interval, ))
        for ex in self.exceptions:
            if not isinstance(ex, datetime.date):
                raise ValueError("Exceptions must be a sequence of"
                                 " datetime.dates (got %r in exceptions)"
                                 % (ex, ))

    def replace(self, interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged):
        if interval is Unchanged:
            interval = self.interval
        if count is Unchanged:
            count = self.count
        if until is Unchanged:
            until = self.until
        if exceptions is Unchanged:
            exceptions = self.exceptions
        return self.__class__(interval, count, until, exceptions)

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (self.__class__.__name__, self.interval,
                                       self.count, self.until,
                                       self.exceptions)

    def _tupleForComparison(self):
        return (self.__class__.__name__, self.interval, self.count,
                self.until, tuple(self.exceptions))

    def __eq__(self, other):
        """See if self == other."""
        if isinstance(other, RecurrenceRule):
            return self._tupleForComparison() == other._tupleForComparison()
        else:
            return False

    def __ne__(self, other):
        """See if self != other."""
        return not self == other

    def __hash__(self):
        """Return the hash value of this recurrence rule.

        It is guaranteed that if recurrence rules compare equal, hash will
        return the same value.
        """
        return hash(self._tupleForComparison())

    def apply(self, event, enddate=None):
        """Generator that generates dates of recurrences"""
        cur = event.dtstart.date()
        count = 0
        while True:
            if ((enddate and cur > enddate) or
                (self.count is not None and count >= self.count) or
                (self.until and cur > self.until)):
                break
            if cur not in self.exceptions:
                yield cur
            count += 1
            cur = self._nextRecurrence(cur)

    def _nextRecurrence(self, date):
        """Add the basic step of recurrence to the date."""
        return date + self.interval * date.resolution

    def iCalRepresentation(self, dtstart):
        """See IRecurrenceRule"""
        assert self.ical_freq, 'RecurrenceRule.ical_freq must be overridden'

        if self.count:
            args = 'COUNT=%d;' % self.count
        elif self.until:
            args = 'UNTIL=%s;' % ical_date_time(self.until)
        else:
            args = ''
        extra_args = self._iCalArgs(dtstart)
        if extra_args is not None:
            args += extra_args + ';'

        result = ['RRULE:FREQ=%s;%sINTERVAL=%d'
                  % (self.ical_freq, args, self.interval)]

        if self.exceptions:
            # Exceptions should include the exact time portion as well
            # (this was implemented in revision 1860), however,
            # Mozilla Calendar refuses to work with such exceptions.
            dates = ','.join([ical_date(d) for d in self.exceptions])
            result.append('EXDATE;VALUE=DATE:' + dates)
        return result

    def _iCalArgs(self, dtstart):
        """Return extra iCal arguments as a string.

        Should be overridden by child classes that have specific arguments.
        The returned string must not include the semicolon separator.
        If None is returned, no arguments are inserted.
        """
        pass


class DailyRecurrenceRule(RecurrenceRule):
    """Daily recurrence rule.

    Immutable hashable object.
    """
    implements(IDailyRecurrenceRule)

    ical_freq = 'DAILY'


class YearlyRecurrenceRule(RecurrenceRule):
    """Yearly recurrence rule.

    Immutable hashable object.
    """
    implements(IYearlyRecurrenceRule)

    ical_freq = 'YEARLY'

    def _nextRecurrence(self, date):
        """Adds the basic step of recurrence to the date"""
        nextyear = date.year + self.interval
        return date.replace(year=nextyear)

    def _iCalArgs(self, dtstart):
        """Return iCalendar parameters specific to monthly reccurence."""
        # XXX KOrganizer wants explicit BYMONTH and BYMONTHDAY arguments.
        #     Maybe it is a good idea to add them for the sake of explicitness.
        pass


class WeeklyRecurrenceRule(RecurrenceRule):
    """Weekly recurrence rule."""

    implements(IWeeklyRecurrenceRule)

    weekdays = property(lambda self: self._weekdays)

    ical_freq = 'WEEKLY'

    def __init__(self, interval=1, count=None, until=None, exceptions=(),
                 weekdays=()):
        self._interval = interval
        self._count = count
        self._until = until
        self._exceptions = tuple(exceptions)
        self._weekdays = tuple(weekdays)
        self._validate()

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r)' % (
            self.__class__.__name__, self.interval,
            self.count, self.until, self.exceptions, self.weekdays)

    def _validate(self):
        RecurrenceRule._validate(self)
        for dow in self.weekdays:
            if not isinstance(dow, int) or not 0 <= dow <= 6:
                raise ValueError("Day of week must be an integer 0..6 (got %r)"
                                 % (dow, ))

    def replace(self, interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged, monthly=Unchanged):
        if interval is Unchanged:
            interval = self.interval
        if count is Unchanged:
            count = self.count
        if until is Unchanged:
            until = self.until
        if exceptions is Unchanged:
            exceptions = self.exceptions
        if weekdays is Unchanged:
            weekdays = self.weekdays
        return self.__class__(interval, count, until, exceptions, weekdays)

    def _tupleForComparison(self):
        return (self.__class__.__name__, self.interval, self.count,
                self.until, self.exceptions, self.weekdays)

    def apply(self, event, enddate=None):
        """Generate dates of recurrences."""
        cur = start = event.dtstart.date()
        count = 0
        weekdays = Set(self.weekdays)
        weekdays.add(event.dtstart.weekday())
        while True:
            if ((enddate and cur > enddate) or
                (self.count is not None and count >= self.count) or
                (self.until and cur > self.until)):
                break
            # Check that this is the correct week and
            # the desired weekday
            if (weekspan(start, cur) % self.interval == 0 and
                cur.weekday() in weekdays):
                if cur not in self.exceptions:
                    yield cur
                count += 1
            cur = self._nextRecurrence(cur)

    def _nextRecurrence(self, date):
        """Add the basic step of recurrence to the date."""
        return date + date.resolution

    def _iCalArgs(self, dtstart):
        """Return iCalendar parameters specific to monthly reccurence."""
        if self.weekdays:
            return 'BYDAY=' + ','.join([ical_weekdays[weekday]
                                        for weekday in self.weekdays])


class MonthlyRecurrenceRule(RecurrenceRule):
    """Monthly recurrence rule.

    Immutable hashable object.
    """
    implements(IMonthlyRecurrenceRule)

    monthly = property(lambda self: self._monthly)

    ical_freq = 'MONTHLY'

    def __init__(self, interval=1, count=None, until=None, exceptions=(),
                 monthly="monthday"):
        self._interval = interval
        self._count = count
        self._until = until
        self._exceptions = tuple(exceptions)
        self._monthly = monthly
        self._validate()

    def __repr__(self):
        return '%s(%r, %r, %r, %r, %r)' % (
            self.__class__.__name__, self.interval,
            self.count, self.until, self.exceptions, self.monthly)

    def _validate(self):
        RecurrenceRule._validate(self)
        if self.monthly not in ("monthday", "weekday", "lastweekday"):
            raise ValueError("monthly must be one of 'monthday', 'weekday',"
                             " 'lastweekday'. Got %r" % (self.monthly, ))

    def replace(self, interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged, monthly=Unchanged):
        if interval is Unchanged:
            interval = self.interval
        if count is Unchanged:
            count = self.count
        if until is Unchanged:
            until = self.until
        if exceptions is Unchanged:
            exceptions = tuple(self.exceptions)
        if monthly is Unchanged:
            monthly = self.monthly
        return self.__class__(interval, count, until, exceptions, monthly)

    def _tupleForComparison(self):
        return (self.__class__.__name__, self.interval, self.count,
                self.until, self.exceptions, self.monthly)

    def _nextRecurrence(self, date):
        """Add basic step of recurrence to the date."""
        year = date.year
        month = date.month
        while True:
            year, month = divmod(year * 12 + month - 1 + self.interval, 12)
            month += 1 # convert 0..11 to 1..12
            try:
                return date.replace(year=year, month=month)
            except ValueError:
                continue

    def apply(self, event, enddate=None):
        if self.monthly == 'monthday':
            for date in  RecurrenceRule.apply(self, event, enddate):
                yield date
        elif self.monthly == 'weekday':
            for date in self._applyWeekday(event, enddate):
                yield date
        elif self.monthly == 'lastweekday':
            for date in self._applyLastWeekday(event, enddate):
                yield date

    def _applyWeekday(self, event, enddate=None):
        """Generator that generates dates of recurrences."""
        cur = start = event.dtstart.date()
        count = 0
        year = start.year
        month = start.month
        weekday = start.weekday()
        index = start.day / 7 + 1

        while True:
            cur = monthindex(year, month, index, weekday)
            if ((enddate and cur > enddate) or
                (self.count is not None and count >= self.count) or
                (self.until and cur > self.until)):
                break
            if cur not in self.exceptions:
                yield cur
            count += 1
            # Next month, please.
            year, month = divmod(year * 12 + month + self.interval - 1, 12)
            month += 1

    def _applyLastWeekday(self, event, enddate=None):
        """Generator that generates dates of recurrences."""
        cur = start = event.dtstart.date()
        count = 0
        year = start.year
        month = start.month
        weekday = start.weekday()
        daysinmonth = calendar.monthrange(year, month)[1]
        index = (start.day - daysinmonth - 1) / 7

        while True:
            cur = monthindex(year, month, index, weekday)
            if ((enddate and cur > enddate) or
                (self.count is not None and count >= self.count) or
                (self.until and cur > self.until)):
                break
            if cur not in self.exceptions:
                yield cur
            count += 1
            # Next month, please.
            year, month = divmod(year * 12 + month + self.interval - 1, 12)
            month += 1

    def _iCalArgs(self, dtstart):
        """Return iCalendar parameters specific to monthly reccurence."""
        if self.monthly == 'monthday':
            return 'BYMONTHDAY=%d' % dtstart.day
        elif self.monthly == 'weekday':
            week = dtstart.day / 7 + 1
            return 'BYDAY=%d%s' % (week, ical_weekdays[dtstart.weekday()])
        elif self.monthly == 'lastweekday':
            return 'BYDAY=-1%s' % ical_weekdays[dtstart.weekday()]
        else:
            raise NotImplementedError(self.monthly)



def weekspan(first, second):
    """Returns the distance in weeks between dates.

    For days in the same ISO week, the result is 0.
    For days in adjacent weeks, it is 1, etc.
    """
    firstmonday = first - datetime.timedelta(first.weekday())
    secondmonday = second - datetime.timedelta(second.weekday())
    return (secondmonday - firstmonday).days / 7


def monthindex(year, month, index, weekday):
    """Returns the index-th weekday of the month in a year.

    May return a date beyond month if index is too big.
    """
    # make corrections for the negative index
    # if index is negative, we're really interested in the next month's
    # first weekday, minus n weeks
    if index < 0:
        yeardelta, month = divmod(month, 12)
        year += yeardelta
        month += 1
        index += 1

    # find first weekday
    for day in range(1, 8):
        if datetime.date(year, month, day).weekday() == weekday:
            break

    # calculate the timedelta to the index-th
    shift = (index - 1) * datetime.timedelta(7)

    # return the result
    return datetime.date(year, month, day) + shift
