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

from zope.interface import implements
from persistence import Persistent
from zodb.btrees.IOBTree import IOBTree
from schooltool.interfaces import IQueryLinks, IGroupMember, IGroup
from schooltool.interfaces import ISpecificURI, IRemovableLink
from schooltool.interfaces import URIMembership, URIGroup, URIMember
from schooltool.db import PersistentKeysDict
from schooltool.relationships import RelationshipSchema

__metaclass__ = type


class GroupLink:
    """An object that represents membership in a group as a link.

    IOW, this is a link from a member to a group.
    """

    implements(IRemovableLink)
    __slots__ = '_group', 'name', '__parent__'
    role = URIGroup
    title = "Membership"
    reltype = URIMembership

    def __init__(self, parent, group, name):
        """The arguments are the following:
             parent is the owner of this link (a group member)
             group is the group at the opposite end of the relationship
             name is the key of parent in the group
        """
        self._group = group
        self.name = name
        self.__parent__ = parent

    def traverse(self):
        """See ILink"""
        return self._group

    def unlink(self):
        """See IRemovableLink"""
        del self._group[self.name]
        from schooltool.event import MemberRemovedEvent
        otherlink = MemberLink(self._group, self.__parent__, self.name)
        event = MemberRemovedEvent((self, otherlink))
        event.dispatch(self.traverse())
        event.dispatch(otherlink.traverse())


class MemberLink:
    """An object that represents containment of a group member as a link."""

    implements(IRemovableLink)
    __slots__ = '_member', 'name', '__parent__'
    role = URIMember
    title = "Membership"
    reltype = URIMembership

    def __init__(self, parent, member, name):
        """The arguments are the following:
             parent is the owner of this link (a group)
             member is the object at the opposite end of the relationship
             name is the key of member in parent
        """
        self._member = member
        self.name = name
        self.__parent__ = parent

    def traverse(self):
        """See ILink"""
        return self._member

    def unlink(self):
        """See IRemovableLink"""
        del self.__parent__[self.name]
        from schooltool.event import MemberRemovedEvent
        otherlink = GroupLink(self._member, self.__parent__, self.name)
        event = MemberRemovedEvent((self, otherlink))
        event.dispatch(self.traverse())
        event.dispatch(otherlink.traverse())


class MemberMixin(Persistent):
    """A mixin providing the IGroupMember interface.

    Also, it implements ILocation by setting the first group the
    member is added to as a parent, and clearing it if the member is
    removed from it.
    """

    implements(IGroupMember, IQueryLinks)

    def __init__(self):
        self._groups = PersistentKeysDict()
        self.__name__ = None
        self.__parent__ = None

    def groups(self):
        """See IGroupMember"""
        return self._groups.keys()

    def notifyAdd(self, group, name):
        """See IGroupMember"""
        self._groups[group] = name
        if self.__parent__ is None:
            self.__parent__ = group
            self.__name__ = str(name)

    def notifyRemove(self, group):
        """See IGroupMember"""
        del self._groups[group]
        if group == self.__parent__:
            self.__parent__ = None
            self.__name__ = None

    def listLinks(self, role=ISpecificURI):
        if URIGroup.extends(role, False):
            return [GroupLink(self, group, name)
                    for group, name in self._groups.iteritems()]
        else:
            return []


class GroupMixin(Persistent):

    implements(IQueryLinks)

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
        ##if self._p_jar is not None:
        ##    self._p_jar.add(member)
        key = self._next_key
        self._next_key += 1
        self._members[key] = member
        self._addhook(member)
        member.notifyAdd(self, key)
        return key

    def __delitem__(self, key):
        """See IGroup"""
        member = self._members[key]
        member.notifyRemove(self)
        self._deletehook(member)
        del self._members[key]

    def listLinks(self, role=ISpecificURI):
        """See IQueryLinks"""
        if URIMember.extends(role, False):
            return [MemberLink(self, member, name)
                    for name, member in self.items()]
        else:
            return []

    # Hooks for use by mixers-in

    def _addhook(self, member):
        pass

    def _deletehook(self, member):
        pass


Membership = RelationshipSchema(URIMembership,
                                group=URIGroup, member=URIMember)

