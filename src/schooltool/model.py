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
from persistence import Persistent
from zodb.btrees.IOBTree import IOBTree
from schooltool.interfaces import IFaceted, IEventConfigurable, IQueryLinks
from schooltool.interfaces import IPerson, IGroup, IGroupMember, IRootGroup
from schooltool.interfaces import ISpecificURI, URIGroup, URIMember
from schooltool.component import queryFacet, setFacet, getFacetItems
from schooltool.db import PersistentKeysSet, PersistentKeysDict, HookablePJar
from schooltool.event import EventTargetMixin, EventService

__metaclass__ = type


class GroupLink:
    __slots__ = '_group'

    def __init__(self, group):
        self._group = group

    def traverse(self):
        return self._group

    role = URIGroup
    title = "Membership"


class MemberLink:
    __slots__ = '_member'

    def __init__(self, member):
        self._member = member

    def traverse(self):
        return self._member

    role = URIMember
    title = "Membership"


# A hook for tests
_setFactory = PersistentKeysSet

class GroupMember(Persistent):
    """A mixin providing the IGroupMember interface.

    Also, it implements ILocation by setting the first group the
    member is added to as a parent, and clearing it if the member is
    removed from it.
    """

    implements(IGroupMember, IQueryLinks)

    def __init__(self):
        self._groups = _setFactory()
        self.__name__ = None
        self.__parent__ = None

    def groups(self):
        """See IGroupMember"""
        return self._groups

    def notifyAdd(self, group, name):
        """See IGroupMember"""
        self._groups.add(group)
        if self.__parent__ is None:
            self.__parent__ = group
            self.__name__ = str(name)

    def notifyRemove(self, group):
        """See IGroupMember"""
        self._groups.remove(group)
        if group == self.__parent__:
            self.__parent__ = None
            self.__name__ = None

    def listLinks(self, role=ISpecificURI):
        if URIGroup.extends(role, False):
            return [GroupLink(group) for group in self.groups()]
        else:
            return []

    def setDataManager(self, datamanager):
        # Can be in the process of being unghostified, need to be careful.
        if hasattr(self, '_groups'):
            datamanager.add(self._groups)

    _p_jar = HookablePJar(setDataManager)


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


class Person(GroupMember, FacetedEventTargetMixin):

    implements(IPerson)

    def __init__(self, name):
        Persistent.__init__(self)
        GroupMember.__init__(self)
        FacetedEventTargetMixin.__init__(self)
        self.name = name


class Group(GroupMember, FacetedEventTargetMixin):

    implements(IGroup, IGroupMember)

    def __init__(self, name, facetFactory=None):
        Persistent.__init__(self)
        GroupMember.__init__(self)
        FacetedEventTargetMixin.__init__(self)
        self._next_key = 0
        self._members = IOBTree()
        self.name = name
        self.facetFactory = facetFactory

    def keys(self):
        """See IGroup"""
        return self._members.keys()

    def values(self):
        """See IGroup"""
        return self._members.values()

    def items(self):
        """See IGroup"""
        return self._members.items()

    def __getitem__(self, key):
        """See IGroup"""
        return self._members[key]

    def add(self, member):
        """See IGroup"""
        if not IGroupMember.isImplementedBy(member):
            raise TypeError("A member has to implement IGroupMember")
        if self._p_jar is not None:
            self._p_jar.add(member)
        key = self._next_key
        self._next_key += 1
        self._members[key] = member
        if self.facetFactory is not None:
            facet = queryFacet(member, self)
            if facet is None:
                facet = self.facetFactory(member)
                setFacet(member, self, facet)
            facet.active = True
        member.notifyAdd(self, key)
        return key

    def __delitem__(self, key):
        """See IGroup"""
        member = self._members[key]
        member.notifyRemove(self)
        facet = queryFacet(member, self)
        if facet is not None:
            facet.active = False
        del self._members[key]

    def listLinks(self, role=ISpecificURI):
        links = GroupMember.listLinks(self, role)
        if URIMember.extends(role, False):
            links += [MemberLink(member) for member in self.values()]
        return links


class RootGroup(Group):
    """A persistent application root object"""

    implements(IRootGroup)

    def __init__(self, name, facetFactory=None):
        Group.__init__(self, name, facetFactory)
        self.eventService = EventService()

