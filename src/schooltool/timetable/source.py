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
from zope.component import adapts, subscribers

from schooltool.timetable.interfaces import IHaveTimetables
from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.timetable.interfaces import ITimetableSource, ITimetables
from schooltool.relationship import getRelatedObjects
from schooltool.app.membership import URIGroup
from schooltool.app.relationships import URISection
from schooltool.timetable.interfaces import IOwnTimetables


class BaseRelationshipTimetableSource(object):
    """A timetable source for composing timetables over relationships.

    Subclasses must provide a role attribute, with a URI of the role
    of the related objects that will be added.
    """

    implements(ITimetableSource)
    adapts(IHaveTimetables)

    def __init__(self, context):
        self.context = context

    def getTimetableSourceObjects(self):
        """Recursivelly collects all the objects for timetables."""
        objects = getRelatedObjects(self.context, self.role)
        objs = []
        for obj in objects:
            for adapter in subscribers((obj, ), ITimetableSource):
                objs.extend(adapter.getTimetableSourceObjects())

        return list(set(objs))


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


class OwnedTimetableSource(object):
    "A subscription adapter that adds the timetable stored in annotations."
    adapts(IOwnTimetables)
    implements(ITimetableSource)

    def __init__(self, context):
        self.context = context

    def getTimetableSourceObjects(self):
        return [self.context]
