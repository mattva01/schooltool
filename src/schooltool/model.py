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
from schooltool.interfaces import IFaceted, IEventConfigurable
from schooltool.interfaces import IPerson, IGroup, IRootGroup
from schooltool.interfaces import ISpecificURI
from schooltool.component import queryFacet, setFacet, getFacetItems
from schooltool.db import PersistentKeysDict
from schooltool.event import EventTargetMixin, EventService
from schooltool.membership import MemberMixin, GroupMixin
from schooltool.relationships import RelatableMixin

__metaclass__ = type


class FacetedMixin:

    implements(IFaceted)

    def __init__(self):
        self.__facets__ = PersistentKeysDict()


class FacetedEventTargetMixin(FacetedMixin, EventTargetMixin):

    def __init__(self):
        FacetedMixin.__init__(self)
        EventTargetMixin.__init__(self)

    def getEventTable(self):
        tables = [self.eventTable]
        for key, facet in getFacetItems(self):
            if facet.active and IEventConfigurable.isImplementedBy(facet):
                tables.append(facet.eventTable)
        return sum(tables, [])


class Person(MemberMixin, FacetedEventTargetMixin, RelatableMixin):

    implements(IPerson)

    def __init__(self, name):
        MemberMixin.__init__(self)
        FacetedEventTargetMixin.__init__(self)
        RelatableMixin.__init__(self)
        self.name = name

    def listLinks(self, role=ISpecificURI):
        links = MemberMixin.listLinks(self, role)
        links += RelatableMixin.listLinks(self, role)
        return links


class Group(GroupMixin, MemberMixin, FacetedEventTargetMixin, RelatableMixin):

    implements(IGroup)

    def __init__(self, name, facetFactory=None):
        GroupMixin.__init__(self)
        MemberMixin.__init__(self)
        FacetedEventTargetMixin.__init__(self)
        RelatableMixin.__init__(self)
        self.name = name
        self.facetFactory = facetFactory

    def _addhook(self, member):
        if self.facetFactory is not None:
            facet = queryFacet(member, self)
            if facet is None:
                facet = self.facetFactory(member)
                setFacet(member, self, facet)
            facet.active = True

    def _deletehook(self, member):
        facet = queryFacet(member, self)
        if facet is not None:
            facet.active = False

    def listLinks(self, role=ISpecificURI):
        links = MemberMixin.listLinks(self, role)
        links += GroupMixin.listLinks(self, role)
        links += RelatableMixin.listLinks(self, role)
        return links


class RootGroup(Group):
    """A persistent application root object"""

    implements(IRootGroup)

    def __init__(self, name, facetFactory=None):
        Group.__init__(self, name, facetFactory)
        self.eventService = EventService()

