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

from zope.interface import implements
from schooltool.interfaces import IPerson, IGroup, IResource
from schooltool.interfaces import IAbsenceComment
from schooltool.relationship import RelationshipValenciesMixin, Valency
from schooltool.facet import FacetedEventTargetMixin
from schooltool.membership import Membership
from schooltool.db import PersistentKeysSetWithNames
from schooltool.cal import CalendarOwnerMixin
from schooltool.timetable import TimetabledMixin
from schooltool.absence import Absence

__metaclass__ = type


class ApplicationObjectMixin(FacetedEventTargetMixin,
                             RelationshipValenciesMixin,
                             CalendarOwnerMixin, TimetabledMixin):

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        CalendarOwnerMixin.__init__(self)
        TimetabledMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None

    def getRelativePath(self, obj):
        if obj in self.__facets__:
            return 'facets/%s' % obj.__name__
        return RelationshipValenciesMixin.getRelativePath(self, obj)

    def __repr__(self):
        return "<%s object %s at 0x%x>" % (self.__class__.__name__,
                                           self.title, id(self))


class Person(ApplicationObjectMixin):

    implements(IPerson)

    def __init__(self, title=None):
        ApplicationObjectMixin.__init__(self, title)
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


class Group(ApplicationObjectMixin):

    implements(IGroup)

    def __init__(self, title=None):
        ApplicationObjectMixin.__init__(self, title)
        self.valencies = Valency(Membership, 'group')


class Resource(ApplicationObjectMixin):

    implements(IResource)

