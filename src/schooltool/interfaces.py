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
SchoolTool package interfaces
"""

from zope.interface import Interface, Attribute


class IGroupRead(Interface):
    """A set of group members.

    All group members implement IGroupMember.
    """

    def __getitem__(key):
        """Returns a member with the given key.

        Raises a KeyError if there is no such member.
        """

    def keys():
        """Returns a sequence of member keys."""

    def values():
        """Returns a sequence of members."""

    def items():
        """Returns a sequence of (key, member) pairs."""


class IGroupWrite(Interface):
    """Modification access to a group."""

    def add(memeber):
        """Adds a new member to this group.

        Returns the key assigned to this member.
        """

    def __delitem__(key):
        """Removes a member from the group.

        Raises a KeyError if there is no such member.
        """


class IGroup(IGroupWrite, IGroupRead):
    __doc__ = IGroupRead.__doc__


class IGroupMember(Interface):

    def groups():
        """Returns a set for all groups this object is a member of."""

    def notifyAdd(group):
        """Notifies a member that it's added to a group."""

    def notifyRemove(group):
        """Notifies a member that it's removed from a group."""

class IPerson(IGroupMember):

    name = Attribute("Person's name")

