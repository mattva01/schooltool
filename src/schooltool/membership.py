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
SchoolTool groups and members

$Id: model.py 153 2003-10-16 12:33:50Z mg $
"""

from sets import Set
from zope.interface import implements, moduleProvides
from persistence import Persistent
from zodb.btrees.IOBTree import IOBTree
from schooltool.interfaces import IQueryLinks, IGroupMember, IGroup
from schooltool.interfaces import ISpecificURI, IRemovableLink
from schooltool.interfaces import URIMembership, URIGroup, URIMember
from schooltool.interfaces import IMembershipEvent
from schooltool.interfaces import IMemberAddedEvent
from schooltool.interfaces import IMemberRemovedEvent
from schooltool.interfaces import IModuleSetup
from schooltool.db import PersistentKeysDict
from schooltool.relationship import RelationshipSchema, RelationshipEvent
from schooltool import relationship
from schooltool.component import registerRelationship

moduleProvides(IModuleSetup)

__metaclass__ = type


class MemberMixin(Persistent):
    """A mixin providing the IGroupMember interface.

    Also, it implements ILocation by setting the first group the
    member is added to as a parent, and clearing it if the member is
    removed from it.
    """

    implements(IGroupMember)

    def __init__(self):
        self._groups = PersistentKeysDict()
        self.__name__ = None
        self.__parent__ = None

    def groups(self):
        """See IGroupMember"""
        return self._groups.keys()

    def notifyAdded(self, group, name):
        """See IGroupMember"""
        self._groups[group] = name
        if self.__parent__ is None:
            self.__parent__ = group
            self.__name__ = str(name)

    def notifyRemoved(self, group):
        """See IGroupMember"""
        del self._groups[group]
        if group == self.__parent__:
            self.__parent__ = None
            self.__name__ = None


class GroupMixin(Persistent):
    """This class is a mixin which makes things a group"""

    def __init__(self):
        self._next_key = 0
        self._members = IOBTree()

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
            raise TypeError("Members must implement IGroupMember")
        key = self._next_key
        self._next_key += 1
        self._members[key] = member
        self._addhook(member)
        member.notifyAdded(self, key)
        # XXX this should send events as well
        return key

    def __delitem__(self, key):
        """See IGroup"""
        member = self._members[key]
        self._deletehook(member)
        del self._members[key]
        member.notifyRemoved(self)
        # XXX this should send event and call unlink notifications as well

    # Hooks for use by mixers-in

    def _addhook(self, member):
        pass

    def _deletehook(self, member):
        pass


Membership = RelationshipSchema(URIMembership,
                                group=URIGroup, member=URIMember)

def checkForCycles(group, potential_member):
    """Raises ValueError if adding potential_member would create a
    cycle in membership relationships.
    """
    for a, b in (group, potential_member), (potential_member, group):
        seen = Set()
        last = Set()
        last.add(a)
        while last:
            if b in last:
                raise ValueError('Group %r is a transitive member of %r' %
                                 (a, b))
            seen |= last
            new_last = Set()
            for obj in last:
                if IQueryLinks.isImplementedBy(obj):
                    links = obj.listLinks(URIGroup)
                    new_last |= Set([link.traverse() for link in links])
            new_last.difference_update(seen)
            last = new_last

class MembershipEvent(RelationshipEvent):

    implements(IMembershipEvent, URIMembership)

    def __init__(self, links):
        RelationshipEvent.__init__(self, links)
        self.member = None
        self.group = None
        for link in links:
            if link.role.extends(URIMember, False):
                if self.member is not None:
                    raise TypeError("only one URIMember must be present"
                                    " among links", links)
                self.member = link.traverse()
            if link.role.extends(URIGroup, False):
                if self.group is not None:
                    raise TypeError("only one URIGroup must be present"
                                    " among links", links)
                self.group = link.traverse()
        if self.member is None or self.group is None:
            raise TypeError("both URIGroup and URIMember must be present"
                            " among links", links)


class MemberAddedEvent(MembershipEvent):
    implements(IMemberAddedEvent)


class MemberRemovedEvent(MembershipEvent):
    implements(IMemberRemovedEvent)

def membershipRelate(relationship_type, (a, role_a), (b, role_b), title=None):
    """See IRelationshipFactory"""

    checkForCycles(a, b)
    links = relationship.relate(relationship_type,
                                (a, role_a), (b, role_b), title)
    event = MemberAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def setUp():
    """Register the URIMembership relationship handler."""
    registerRelationship(URIMembership, membershipRelate)

