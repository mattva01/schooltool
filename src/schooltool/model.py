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
"""

from zope.interface import implements
from schooltool.interfaces import IPerson, IGroup, IGroupMember

__metaclass__ = type


class Person:

    implements(IPerson)

    def __init__(self, name):
        self.name = name

    def groups(self):
        return ()


class Group:

    implements(IGroup)

    def __init__(self):
        self._next_key = 0
        self._members = {}

    def keys(self):
        return self._members.keys()

    def values(self):
        return self._members.values()

    def items(self):
        return self._members.items()

    def __getitem__(self, key):
        return self._members[key]

    def add(self, member):
        if not IGroupMember.isImplementedBy(member):
            raise TypeError("A member has to implement IGroupMember")
        key = self._next_key
        self._next_key += 1
        self._members[key] = member
        return key

    def __delitem__(self, key):
        del self._members[key]
