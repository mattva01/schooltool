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
from zope.interface import implements, moduleProvides
from persistence import Persistent
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IPerson, IGroup, Unchanged
from schooltool.interfaces import IAbsence, IAbsenceComment
from schooltool.interfaces import IEventTarget
from schooltool.interfaces import IAbsenceEvent, IAbsenceEndedEvent
from schooltool.interfaces import IAbsenceTracker, IAbsenceTrackerUtility
from schooltool.interfaces import IAbsenceTrackerFacet
from schooltool.relationship import RelationshipValenciesMixin, Valency
from schooltool.facet import FacetedEventTargetMixin, FacetFactory
from schooltool.membership import Membership
from schooltool.db import PersistentKeysSetWithNames, PersistentKeysSet
from schooltool.event import EventMixin, CallAction
from schooltool.component import registerFacetFactory
from schooltool.cal import TimetabledMixin

__metaclass__ = type

moduleProvides(IModuleSetup)


class Person(FacetedEventTargetMixin, RelationshipValenciesMixin,
             TimetabledMixin):

    implements(IPerson)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        TimetabledMixin.__init__(self)
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

    def reportAbsence(self, comment):
        if not IAbsenceComment.isImplementedBy(comment):
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


class Group(FacetedEventTargetMixin, RelationshipValenciesMixin,
            TimetabledMixin):

    implements(IGroup)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        TimetabledMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None
        self.valencies = Valency(Membership, 'group')

    def getRelativePath(self, obj):
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)

    def __repr__(self):
        return "<Group object %s at 0x%x>" % (self.title, id(self))


class Absence(Persistent):

    implements(IAbsence)

    def __init__(self, person, expected_presence=None, ended=False,
                 resolved=False):
        self.person = person
        self.expected_presence = expected_presence
        self.ended = ended
        self.resolved = resolved
        self.comments = []
        self.__name__ = None
        self.__parent__ = None

    def addComment(self, comment):
        if not IAbsenceComment.isImplementedBy(comment):
            raise TypeError("comment is not IAbsenceComment", comment)
        if comment.__parent__ is not None:
            raise ValueError("comment is already added to an absence", comment)
        event = AbsenceEvent(self, comment)
        if comment.ended is not Unchanged:
            if self.ended and not comment.ended:
                if self.person.getCurrentAbsence() is not None:
                    raise ValueError("Cannot reopen an absence when another"
                                     " one is not ended", self, comment)
                self.person._current_absence = self
                self.resolved = False
            elif not self.ended and comment.ended:
                self.person._current_absence = None
                event = AbsenceEndedEvent(self, comment)
            self.ended = comment.ended
        if comment.resolved is not Unchanged:
            if not self.ended:
                raise ValueError("Cannot resolve an unended absence",
                                 self, comment)
            self.resolved = comment.resolved
        if comment.expected_presence is not Unchanged:
            self.expected_presence = comment.expected_presence
        comment.__parent__ = self
        self.comments.append(comment)
        self.comments = self.comments
        if event is not None:
            event.dispatch(self.person)
            if IEventTarget.isImplementedBy(comment.absent_from):
                event.dispatch(comment.absent_from)
            if IAbsenceEndedEvent.isImplementedBy(event):
                for comment in self.comments:
                    if IEventTarget.isImplementedBy(comment.absent_from):
                        event.dispatch(comment.absent_from)


class AbsenceComment:

    implements(IAbsenceComment)

    def __init__(self, reporter=None, text=None, dt=None, absent_from=None,
                 expected_presence=Unchanged, ended=Unchanged,
                 resolved=Unchanged):
        if dt is None:
            dt = datetime.utcnow()
        self.reporter = reporter
        self.text = text
        self.datetime = dt
        self.absent_from = absent_from
        self.expected_presence = expected_presence
        if ended is Unchanged:
            self.ended = Unchanged
        else:
            self.ended = bool(ended)
        if resolved is Unchanged:
            self.resolved = Unchanged
        else:
            self.resolved = bool(resolved)
        self.__parent__ = None


class AttendanceEvent(EventMixin):

    implements(IAbsenceEvent)

    def __init__(self, absence, comment):
        EventMixin.__init__(self)
        self.absence = absence
        self.comment = comment

    def __str__(self):
        return "<%s for %s>" % (self.__class__.__name__, self.absence)


class AbsenceEvent(AttendanceEvent):
    implements(IAbsenceEvent)


class AbsenceEndedEvent(AttendanceEvent):
    implements(IAbsenceEndedEvent)


class AbsenceTrackerMixin(Persistent):

    implements(IAbsenceTracker)

    def  __init__(self):
        self.absences = PersistentKeysSet()

    def notify(self, event):
        """See IEventTarget"""
        if IAbsenceEvent.isImplementedBy(event):
            self.absences.add(event.absence)
        if IAbsenceEndedEvent.isImplementedBy(event):
            if event.absence in self.absences:
                self.absences.remove(event.absence)


class AbsenceTrackerUtility(AbsenceTrackerMixin):

    implements(IAbsenceTrackerUtility)

    def __init__(self):
        AbsenceTrackerMixin.__init__(self)
        self.__parent__ = None
        self.__name__ = None
        self.title = "Absence Tracker"


class AbsenceTrackerFacet(AbsenceTrackerMixin):

    implements(IAbsenceTrackerFacet)

    def __init__(self):
        AbsenceTrackerMixin.__init__(self)
        self.__parent__ = None
        self.__name__ = None
        self.active = False
        self.owner = None
        self.eventTable = (CallAction(self.notify), )


def setUp():
    """Register the AbsenceTrackerFacet factory."""
    registerFacetFactory(FacetFactory(AbsenceTrackerFacet, 'absence_tracker',
                                      'Absence Tracker',
                                      facet_name='absences'))


