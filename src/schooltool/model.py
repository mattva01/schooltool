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

from sets import Set
from zope.interface import implements
from persistence import Persistent
from persistence.list import PersistentList
from zodb.btrees.IOBTree import IOBTree
from schooltool.interfaces import IFaceted
from schooltool.interfaces import IPerson, IGroup, IGroupMember, IRootGroup
from schooltool.interfaces import IEvent, IEventTarget, IEventConfigurable
from schooltool.interfaces import IEventAction, ILookupAction
from schooltool.interfaces import IRouteToMembersAction, IRouteToGroupsAction
from schooltool.adapters import queryFacet, setFacet, getFacetItems
from schooltool.db import PersistentListSet, PersistentKeysDict

__metaclass__ = type


class GroupMember:
    """A mixin providing the IGroupMember interface.

    Also, it implements ILocation by setting the first group the
    member is added to as a parent, and clearing it if the member is
    removed from it.
    """

    implements(IGroupMember)

    def __init__(self):
        self._groups = PersistentListSet()
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


class FacetedMixin:

    implements(IFaceted)

    def __init__(self):
        self.__facets__ = PersistentKeysDict()


class EventMixin:

    implements(IEvent)

    def __init__(self, context=None):
        self.context = context
        self.__seen = Set()

    def dispatch(self, target=None):
        if target is None:
            target = self.context
        if target not in self.__seen:
            self.__seen.add(target)
            target.handle(self)


class EventTargetMixin:

    implements(IEventTarget, IEventConfigurable)

    def __init__(self):
        self.eventTable = PersistentList()

    def getEventTable(self):
        # this method can be overriden in subclasses
        return self.eventTable

    def handle(self, event):
        for action in self.getEventTable():
            if action.eventType.isImplementedBy(event):
                action.handle(event, self)


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


class EventActionMixin:

    implements(IEventAction)

    def __init__(self, eventType):
        self.eventType = eventType

    def handle(self, event, target):
        raise NotImplementedError('Subclasses must override this method')


class LookupAction(EventActionMixin):

    implements(ILookupAction)

    def __init__(self, eventTable=None, eventType=IEvent):
        EventActionMixin.__init__(self, eventType)
        if eventTable is None:
            eventTable = PersistentList()
        self.eventTable = eventTable

    def handle(self, event, target):
        for action in self.eventTable:
            if action.eventType.isImplementedBy(event):
                action.handle(event, target)


class RouteToMembersAction(EventActionMixin):

    implements(IRouteToMembersAction)

    def handle(self, event, target):
        for member in target.values():
            event.dispatch(member)


class RouteToGroupsAction(EventActionMixin):

    implements(IRouteToGroupsAction)

    def handle(self, event, target):
        for group in target.groups():
            event.dispatch(group)


class Person(Persistent, GroupMember,  FacetedEventTargetMixin):

    implements(IPerson)

    def __init__(self, name):
        Persistent.__init__(self)
        GroupMember.__init__(self)
        FacetedEventTargetMixin.__init__(self)
        self.name = name


class Group(Persistent, GroupMember, FacetedEventTargetMixin):

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


class RootGroup(Group):
    """A persistent application root object"""
    implements(IRootGroup)
