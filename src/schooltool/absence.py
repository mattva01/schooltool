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
SchoolTool absence tracking functionality.

$Id$
"""

from datetime import datetime
from persistent import Persistent
from zope.interface import implements, moduleProvides
from schooltool.interfaces import IEventTarget
from schooltool.interfaces import IAbsenceEvent, IAbsenceEndedEvent
from schooltool.interfaces import IAbsenceTracker, IAbsenceTrackerUtility
from schooltool.interfaces import IAbsenceTrackerFacet
from schooltool.interfaces import IAbsence, IAbsenceComment, Unchanged
from schooltool.interfaces import IModuleSetup
from schooltool.event import EventMixin, CallAction
from schooltool.component import registerFacetFactory
from schooltool.facet import FacetMixin, FacetFactory
from schooltool.db import PersistentKeysSet
from schooltool.translation import ugettext as _


__metaclass__ = type

moduleProvides(IModuleSetup)


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
        if not IAbsenceComment.providedBy(comment):
            raise TypeError("Comment is not IAbsenceComment", comment)
        if comment.__parent__ is not None:
            raise ValueError("Comment is already added to an absence", comment)
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
            if IEventTarget.providedBy(comment.absent_from):
                event.dispatch(comment.absent_from)
            if IAbsenceEndedEvent.providedBy(event):
                for comment in self.comments:
                    if IEventTarget.providedBy(comment.absent_from):
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
        if IAbsenceEvent.providedBy(event):
            self.absences.add(event.absence)
        if IAbsenceEndedEvent.providedBy(event):
            if event.absence in self.absences:
                self.absences.remove(event.absence)


class AbsenceTrackerUtility(AbsenceTrackerMixin):

    implements(IAbsenceTrackerUtility)

    __name__ = None
    __parent__ = None

    def __init__(self):
        AbsenceTrackerMixin.__init__(self)
        self.title = _("Absence Tracker")


class AbsenceTrackerFacet(AbsenceTrackerMixin, FacetMixin):

    implements(IAbsenceTrackerFacet)

    def __init__(self):
        AbsenceTrackerMixin.__init__(self)
        self.eventTable = (CallAction(self.notify), )


def setUp():
    """Register the AbsenceTrackerFacet factory."""
    registerFacetFactory(FacetFactory(AbsenceTrackerFacet,
        name='absence_tracker', title=_('Absence Tracker'),
        facet_name='absences'))
