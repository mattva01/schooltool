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
SchoolTool organisational model.

$Id$
"""

import datetime
import sets
import sha

from zope.interface import implements
from schooltool.interfaces import IPerson, IGroup, IResource
from schooltool.interfaces import INote, IAddress
from schooltool.interfaces import IAbsenceComment
from schooltool.interfaces import IApplicationObject
from schooltool.interfaces import Everybody, ViewPermission
from schooltool.relationship import RelationshipValenciesMixin, Valency
from schooltool.facet import FacetedEventTargetMixin
from schooltool.event import EventTargetMixin
from schooltool.membership import Membership
from schooltool.db import PersistentKeysSetWithNames
from schooltool.cal import CalendarOwnerMixin
from schooltool.timetable import TimetabledMixin
from schooltool.timetable import getPeriodsForDay
from schooltool.absence import Absence
from schooltool.component import FacetManager, getRelatedObjects
from schooltool.component import getDynamicFacetSchemaService
from schooltool.infofacets import PersonInfoFacet, AddressInfoFacet
from schooltool.infofacets import DynamicFacet
from schooltool.auth import ACL
from schooltool.uris import URICurrentlyResides, URICurrentResidence
from schooltool.uris import URINotandum

__metaclass__ = type


class ApplicationObjectMixin(FacetedEventTargetMixin,
                             RelationshipValenciesMixin,
                             CalendarOwnerMixin, TimetabledMixin):
    """Mixin that implements IApplicationObject.

    One important note: do not change __name__ after the object is
    in use (meaning that it may be added to a dict or a set somewhere).
    Changing __name__ changes the object's hash value, and can result
    in unpleasantness.
    """

    implements(IApplicationObject)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        CalendarOwnerMixin.__init__(self)
        TimetabledMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None

        self.acl = ACL()
        self.acl.__name__ = 'acl'
        self.acl.__parent__ = self

    def getFreeIntervals(self, first, last, time_periods, min_duration):
        """See IAvailabilitySearch"""

        # Day time is expressed as a timedelta from midnight because
        # you cannot perform arithmetic with datetime.time objects
        unavailable_hours = IntervalSet(datetime.timedelta(hours=0),
                                        datetime.timedelta(hours=24))
        for start_time, duration in time_periods:
            start = datetime.timedelta(hours=start_time.hour,
                                       minutes=start_time.minute)
            unavailable_hours.remove(start, start + duration)

        one_day = datetime.timedelta(days=1)
        dtfirst = datetime.datetime.combine(first, datetime.time(0))
        dtlast = datetime.datetime.combine(last, datetime.time(0)) + one_day
        intset = self._availabilityMap(dtfirst, dtlast)

        for a, b in unavailable_hours:
            date = dtfirst
            while date < dtlast:
                intset.remove(date + a, date + b)
                date += one_day

        return [(start, end - start) for start, end in intset
                                     if end >= start + min_duration]

    def _availabilityMap(self, dtfirst, dtlast):
        """Return an IntervalSet for time intervals when the object is free."""
        intset = IntervalSet(dtfirst, dtlast)
        for event in self.calendar.expand(dtfirst, dtlast):
            intset.remove(event.dtstart, event.dtstart + event.duration)
        for event in self.makeTimetableCalendar():
            intset.remove(event.dtstart, event.dtstart + event.duration)
        return intset

    def getFreePeriods(self, first, last, timetable_periods):
        """See IAvailabilitySearch"""
        return list(self._getFreePeriods(first, last, timetable_periods))

    def _getFreePeriods(self, first, last, timetable_periods):
        # The following code is inefficient:
        #  - SequentialDaysTimetableModel needs to iterate from the
        #    beginning of the semester (or whatever) to day, thus leading
        #    to quadratic behaviour.
        #  - There are repeated lookups of the time-related services within
        #    getPeriodsForDay.
        # Fix this if profiling indicates _getFreePeriods takes too long in
        # real life.
        one_day = datetime.timedelta(days=1)
        dtfirst = datetime.datetime.combine(first, datetime.time(0))
        dtlast = datetime.datetime.combine(last, datetime.time(0)) + one_day
        available = self._availabilityMap(dtfirst, dtlast)
        timetable_periods = sets.Set(timetable_periods)
        day = first
        while day <= last:
            for period in getPeriodsForDay(day, self):
                if period.title in timetable_periods:
                    dtstart = datetime.datetime.combine(day, period.tstart)
                    if available.contains(dtstart, dtstart + period.duration):
                        yield (dtstart, period.duration, period.title)
            day += one_day

    def getRelativePath(self, obj):
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)

    def __repr__(self):
        return "<%s object %s at 0x%x>" % (self.__class__.__name__,
                                           self.title, id(self))

    def __hash__(self):
        if self.__name__ is None:
            raise TypeError("%r cannot be hashed because it doesn't "
                            "have a name" % self)
        return hash((self.__class__.__name__, self.__name__))


class Person(ApplicationObjectMixin):

    implements(IPerson)

    def _getName(self):
        return self.__name__

    username = property(_getName)

    def __init__(self, title=None):
        ApplicationObjectMixin.__init__(self, title)
        self.valencies = Valency(Membership, 'member')
        self._absences = PersistentKeysSetWithNames()
        self._current_absence = None
        self._pwhash = None
        first_name = last_name = None
        facet = PersonInfoFacet()
        FacetManager(self).setFacet(facet, self, "person_info")
        self.addSelfToCalACL()

    def iterAbsences(self):
        return iter(self._absences)

    def getAbsence(self, key):
        return self._absences.valueForName(key)

    def getCurrentAbsence(self):
        return self._current_absence

    def reportAbsence(self, comment):
        if not IAbsenceComment.providedBy(comment):
            raise TypeError("comment is not IAbsenceComment", comment)
        absence = self.getCurrentAbsence()
        if absence is None:
            absence = Absence(self)
            absence.__parent__ = self
            self._absences.add(absence)
            self._current_absence = absence
        absence.addComment(comment)
        return absence

    def getRelativePath(self, obj):
        if obj in self._absences:
            return 'absences/%s' % obj.__name__
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)

    def setPassword(self, password):
        if password is None:
            self._pwhash = None
        else:
            self._pwhash = sha.sha(password).digest()

    def checkPassword(self, password):
        if self._pwhash is None or password is None:
            return False
        else:
            return sha.sha(password).digest() == self._pwhash

    def hasPassword(self):
        return self._pwhash is not None
    
    def getAddresses(self):
        return getRelatedObjects(self, URICurrentResidence)

    def getDynamicFacets(self):
        service = getDynamicFacetSchemaService(self)
        facets = FacetManager(self).iterFacets()
        return [facet for facet in facets if facet in service.keys()]



class Group(ApplicationObjectMixin):

    implements(IGroup)

    def __init__(self, title=None):
        ApplicationObjectMixin.__init__(self, title)
        self.valencies = Valency(Membership, 'group')
        self.acl.add((Everybody, ViewPermission))


class Resource(ApplicationObjectMixin):

    implements(IResource)


class Note(RelationshipValenciesMixin, EventTargetMixin):

    implements(INote)

    title = None
    body = None
    owner = None
    created = None

    def __init__(self, title, body=None, owner=None):
        RelationshipValenciesMixin.__init__(self)
        EventTargetMixin.__init__(self)
        self.title = title
        self.body = body
        self.owner = owner
        self.__name__ = None
        self.__parent__ = None
        self.created = datetime.datetime.today()

    def getRelated(self):
        return getRelatedObjects(self, URINotandum)


class Address(FacetedEventTargetMixin, RelationshipValenciesMixin):

    implements(IAddress)

    title = None
    country = None

    def __init__(self, title=None, country=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        self.title = title
        self.country = country
        facet = AddressInfoFacet()
        FacetManager(self).setFacet(facet, self, "address_info")
        self.__name__ = None
        self.__parent__ = None

    def getPeople(self):
        return getRelatedObjects(self, URICurrentlyResides)

    def info(self):
        return FacetManager(self).facetByName('address_info')


class IntervalSet:
    """An ordered set of disjoint intervals [a, b).

    a and b can be numbers or something more exotic like datetime objects.

    First let us create a function to nicely print interval sets

        >>> def p(intset):
        ...     print ' '.join(['[%s, %s)' % pair for pair in intset])
        ...

    Initially the set contains exactly one interval.

        >>> i = IntervalSet(0, 10)
        >>> p(i)
        [0, 10)

    You can remove an interval from the set.

        >>> i.remove(5, 6)
        >>> p(i)
        [0, 5) [6, 10)

    Intervals [a, b) where a >= b, are empty, thus trying to remove them
    is a NOP.

        >>> i.remove(7, 4)
        >>> p(i)
        [0, 5) [6, 10)

    You can check whether a given interval is a subset of the union of all
    intervals in the set:

        >>> i.contains(1, 2)
        True
        >>> i.contains(5, 6)
        False
        >>> i.contains(4, 6)
        False
        >>> i.contains(5, 7)
        False

    Empty intervals are always a subset.

        >>> i.contains(20, 20)
        True

    The interval you want to remove does not necessarily have to be within the
    set.

        >>> i.remove(-1, 1)
        >>> p(i)
        [1, 5) [6, 10)

        >>> i.remove(9, 11)
        >>> p(i)
        [1, 5) [6, 9)

        >>> i.remove(4, 7)
        >>> p(i)
        [1, 4) [7, 9)

        >>> i.remove(11, 12)
        >>> p(i)
        [1, 4) [7, 9)

        >>> i.remove(1, 4)
        >>> p(i)
        [7, 9)

    """

    def __init__(self, start, end):
        """Create an interval set containing one interval [start, end).

        If start >= end, the set is empty.

            >>> list(IntervalSet(0, 0))
            []
            >>> list(IntervalSet(1, 0))
            []

        """
        self._intervals = []
        if start < end:
            self._intervals.append((start, end))

    def remove(self, start, end):
        """Remove interval [start, end) from the set.

        Does nothing if start >= end.
        """
        if start >= end:
            return
        res = []
        for istart, iend in self._intervals:
            a, b = istart, min(iend, start)
            if a < b:
                res.append((a, b))
            c, d = max(end, istart), iend
            if c < d:
                res.append((c, d))
            # Both invariants (see __iter__'s docstring) are maintained.
            # The first one is checked explicitly above (a < b, c < d).
            # The second one (b < c) is true because
            #   b = min(start, x) <= start < end <= max(end, y) = c
            # for any values of x and y.
        self._intervals = res

    def __iter__(self):
        """Iterate over all intervals in the set.

        For every interval [a, b) the following is true: a < b

        For every pair of adjacent intervals [a, b) and [c, d) the following
        is true: b < c
        """
        return iter(self._intervals)

    def contains(self, a, b):
        """Is [a, b) within the union of all intervals in this set?"""
        if a >= b:
            return True # empty set is always a subset
        for c, d in self:
            if c <= a <= b <= d:
                return True
            if c > a:
                return False # optimization: c will never become <= a
        return False

