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
from schooltool.interfaces import IPerson, IGroup, IGroupMember
from persistence import Persistent
from zodb.btrees.OOBTree import OOSet
from zodb.btrees.IOBTree import IOBTree

__metaclass__ = type


class GroupMember:
    """A mixin providing the IGroupMember interface."""

    implements(IGroupMember)

    def __init__(self):
        self._groups = OOSet()

    def groups(self):
        """See IGroupMember"""
        return self._groups

    def notifyAdd(self, group):
        """See IGroupMember"""
        self._groups.insert(group)

    def notifyRemove(self, group):
        """See IGroupMember"""
        self._groups.remove(group)


class Person(Persistent, GroupMember):

    implements(IPerson)

    def __init__(self, name):
        self.name = name
        super(Person, self).__init__()


class Group(Persistent, GroupMember):

    implements(IGroup, IGroupMember)

    def __init__(self, name):
        self._next_key = 0
        self._members = IOBTree()
        self.name = name
        super(Group, self).__init__()

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
        member.notifyAdd(self)
        return key

    def __delitem__(self, key):
        """See IGroup"""
        self._members[key].notifyRemove(self)
        del self._members[key]

