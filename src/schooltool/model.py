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

from datetime import datetime
from zope.interface import implements
from persistence import Persistent
from schooltool.interfaces import IPerson, IGroup
from schooltool.interfaces import IAbsence, IAbsenceComment, IAbsenteeismEvent
from schooltool.relationship import RelationshipValenciesMixin, Valency
from schooltool.facet import FacetedEventTargetMixin
from schooltool.membership import Membership
from schooltool.db import PersistentKeysSetWithNames
from schooltool.event import EventMixin

__metaclass__ = type


class Person(FacetedEventTargetMixin, RelationshipValenciesMixin):

    implements(IPerson)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None
        self.valencies = Valency(Membership, 'member')
        self._absences = PersistentKeysSetWithNames()
        self._current_absence = None

    def iterAbsences(self):
        return iter(self._absences)

    def getAbsence(self, key):
        return self._absences.valueForName(key)

    def getCurrentAbsence(self):
        return self._current_absence

    def addAbsence(self, comment):
        absence = self.getCurrentAbsence()
        if absence is None:
            absence = Absence(self)
            absence.__parent__ = self
            absence.addComment(comment)
            self._absences.add(absence)
            self._current_absence = absence
        else:
            absence.addComment(comment)
        return absence

    def getRelativePath(self, obj):
        if obj in self._absences:
            return 'absences/%s' % obj.__name__
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)


class Group(FacetedEventTargetMixin, RelationshipValenciesMixin):

    implements(IGroup)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None
        self.valencies = Valency(Membership, 'group')

    def getRelativePath(self, obj):
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)


class Absence(Persistent):

    implements(IAbsence)

    def __init__(self, person, expected_presence=None, resolved=False):
        self.person = person
        self.expected_presence = expected_presence
        self.resolved = resolved
        self.comments = []
        self.__name__ = None
        self.__parent__ = None

    def addComment(self, comment):
        if not IAbsenceComment.isImplementedBy(comment):
            raise TypeError("comment is not IAbsenceComment", comment)
        if comment.resolution_change is not None:
            if self.resolved and not comment.resolution_change:
                if self.person.getCurrentAbsence() is not None:
                    raise ValueError("Cannot reopen an absence when another"
                                     " one is not resolved", self, comment)
                self.person._current_absence = self
            elif not self.resolved and comment.resolution_change:
                self.person._current_absence = None
            self.resolved = comment.resolution_change
        if comment.expected_presence_change is not None:
            self.expected_presence = comment.expected_presence_change
        self.comments.append(comment)
        self.comments = self.comments
        event = AbsenteeismEvent(self, comment)
        event.dispatch(self.person)


class AbsenceComment:

    implements(IAbsenceComment)

    def __init__(self, reporter, text, dt=None, absent_from=None,
                 expected_presence_change=None, resolution_change=None):
        if dt is None:
            dt = datetime.utcnow()
        self.reporter = reporter
        self.text = text
        self.datetime = dt
        self.absent_from = absent_from
        self.expected_presence_change = expected_presence_change
        self.resolution_change = resolution_change


class AbsenteeismEvent(EventMixin):

    implements(IAbsenteeismEvent)

    def __init__(self, absence, comment):
        EventMixin.__init__(self)
        self.absence = absence
        self.comment = comment

    def __str__(self):
        return "AbsenceEvent for %s" % self.absence

