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
import sha
from zope.interface import implements
from schooltool.interfaces import IPerson, IGroup, IResource
from schooltool.interfaces import IAbsenceComment
from schooltool.interfaces import IApplicationObject
from schooltool.interfaces import Everybody, ViewPermission
from schooltool.relationship import RelationshipValenciesMixin, Valency
from schooltool.facet import FacetedEventTargetMixin
from schooltool.membership import Membership
from schooltool.db import PersistentKeysSetWithNames
from schooltool.cal import CalendarOwnerMixin
from schooltool.timetable import TimetabledMixin
from schooltool.absence import Absence
from schooltool.component import getPath, FacetManager
from schooltool.infofacets import PersonInfoFacet
from schooltool.auth import ACL

__metaclass__ = type


class ApplicationObjectMixin(FacetedEventTargetMixin,
                             RelationshipValenciesMixin,
                             CalendarOwnerMixin, TimetabledMixin):

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
        first = datetime.datetime.combine(first, datetime.time(0))
        last = datetime.datetime.combine(last, datetime.time(0)) + one_day
        intset = IntervalSet(first, last)

        for a, b in unavailable_hours:
            date = first
            while date < last:
                intset.remove(date + a, date + b)
                date += one_day

        for event in self.calendar:
            intset.remove(event.dtstart, event.dtstart + event.duration)

        for event in self.makeCalendar():
            intset.remove(event.dtstart, event.dtstart + event.duration)

        return [(start, end - start) for start, end in intset
                                     if end >= start + min_duration]

    def getRelativePath(self, obj):
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)

    def __repr__(self):
        return "<%s object %s at 0x%x>" % (self.__class__.__name__,
                                           self.title, id(self))

    def __hash__(self):
        try:
            return hash((self.__class__.__name__, getPath(self)))
        except (ValueError, TypeError), e:
            raise TypeError("%r cannot be hashed because it doesn't "
                            "have a path: %s" % (self, e))


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


class Group(ApplicationObjectMixin):

    implements(IGroup)

    def __init__(self, title=None):
        ApplicationObjectMixin.__init__(self, title)
        self.valencies = Valency(Membership, 'group')
        self.acl.add((Everybody, ViewPermission))


class Resource(ApplicationObjectMixin):

    implements(IResource)


class IntervalSet:
    """An ordered set of disjoint intervals [a, b).

    a and b can be numbers or something more exotic like datetime objects.

    >>> i = IntervalSet(0, 10)
    >>> list(i)
    [(0, 10)]
    >>> i.remove(5, 6)
    >>> list(i)
    [(0, 5), (6, 10)]
    >>> i.remove(7, 4)
    >>> list(i)
    [(0, 5), (6, 10)]
    >>> i.remove(-1, 1)
    >>> list(i)
    [(1, 5), (6, 10)]
    >>> i.remove(9, 11)
    >>> list(i)
    [(1, 5), (6, 9)]
    >>> i.remove(4, 7)
    >>> list(i)
    [(1, 4), (7, 9)]
    >>> i.remove(11, 12)
    >>> list(i)
    [(1, 4), (7, 9)]
    >>> i.remove(1, 4)
    >>> list(i)
    [(7, 9)]
    >>> list(IntervalSet(0, 0))
    []
    >>> list(IntervalSet(1, 0))
    []
    """

    def __init__(self, start, end):
        """Create an interval set containing one interval [start, end)."""
        self._intervals = []
        if start < end:
            self._intervals.append((start, end))

    def remove(self, start, end):
        """Remove interval [start, end) from the set.

        Does nothing if start >= end
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
