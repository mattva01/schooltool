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
Timetable source adapters

$Id$
"""
from sets import Set
from zope.interface import implements

from schooltool.timetable.interfaces import ITimetableSource
from schoolbell.relationship import getRelatedObjects
from schoolbell.app.membership import URIGroup
from schooltool.relationships import URISection


class BaseRelationshipTimetableSource(object):
    """A timetable source for composing timetables over relationships.

    Subclasses must provide a role attribute, with a URI of the role
    of the related objects, timetables of which will be added.
    """

    implements(ITimetableSource)

    def __init__(self, context):
        self.context = context

    def getTimetable(self, term, schema):
        timetables = []
        for obj in getRelatedObjects(self.context, self.role):
            tt = obj.getCompositeTimetable(term, schema)
            if tt is not None:
                timetables.append(tt)

        if not timetables:
            return None

        result = timetables[0].cloneEmpty()
        for tt in timetables:
            result.update(tt)

        return result

    def listTimetables(self):
        keys = Set()
        for obj in getRelatedObjects(self.context, self.role):
            keys.update(obj.listCompositeTimetables())
        return keys


class MembershipTimetableSource(BaseRelationshipTimetableSource):
    """A subscription adapter that adds the group timetables to the members'
    composite timetables.
    """
    role = URIGroup


class InstructionTimetableSource(BaseRelationshipTimetableSource):
    """A subscription adapter that adds the section timetables to the teachers'
    composite timetables.
    """
    role = URISection
