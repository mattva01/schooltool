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
import UserDict
import logging
from zope.interface import implements, directlyProvidedBy, directlyProvides
from schooltool.interfaces import IPerson, IGroup, IGroupMember, IRootGroup
from schooltool.interfaces import IMarkingGroup, IFaceted
from persistence import Persistent
from persistence.list import PersistentList
from persistence.dict import PersistentDict
from zodb.btrees.OOBTree import OOSet
from zodb.btrees.IOBTree import IOBTree

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
        self.__facets__ = PersistentDict()


class Person(Persistent, GroupMember, FacetedMixin):

    implements(IPerson)

    def __init__(self, name):
        Persistent.__init__(self)
        GroupMember.__init__(self)
        FacetedMixin.__init__(self)
        self.name = name


class Group(Persistent, GroupMember, FacetedMixin):

    implements(IGroup, IGroupMember)

    def __init__(self, name):
        Persistent.__init__(self)
        GroupMember.__init__(self)
        FacetedMixin.__init__(self)
        self._next_key = 0
        self._members = IOBTree()
        self.name = name

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
        member.notifyAdd(self, key)
        return key

    def __delitem__(self, key):
        """See IGroup"""
        self._members[key].notifyRemove(self)
        del self._members[key]


class RootGroup(Group):
    """A persistent application root object"""
    implements(IRootGroup)

class MarkingGroup(Group):
    """A group which sets a marker interface on its members."""

    implements(IMarkingGroup)

    def __init__(self, name, marker):
        self.marker = marker
        super(MarkingGroup, self).__init__(name)

    def add(self, member):
        if self.marker.isImplementedBy(member):
            logging.warning("%s already implements %s" % (member, self.marker))
        directlyProvides(member, directlyProvidedBy(member), self.marker)
        return super(MarkingGroup, self).add(member)

    def __delitem__(self, key):
        member = self[key]
        directlyProvides(member, directlyProvidedBy(member) - self.marker)
        if self.marker.isImplementedBy(member):
            logging.warning("%s still implements %s" % (member, self.marker))
        super(MarkingGroup, self).__delitem__(key)

class PersistentListSet(Persistent):
    """A set implemented with a PersistentList as a backend storage.

    This approach is not most efficient, but avoids the need of having
    a total ordering needed to employ OOSets
    (http://zope.org/Wikis/ZODB/FrontPage/guide/node6.html) or
    constant hashes (memory addresses) used for normal dicts.
    """

    def __init__(self):
        self._data = PersistentList()

    def add(self, item):
        if item not in self._data:
            self._data.append(item)

    def __iter__(self):
        return iter(self._data)

    def remove(self, item):
        self._data.remove(item)

class PersistentKeysDict(Persistent, UserDict.DictMixin):
    """A PersistentDict which uses persistent objects as keys by
    relying on their _p_oids.

    If an object used as a key does not yet have a _p_oid, it is added
    to self._p_jar and assigned a _p_oid.  Thus, PersistentKeysDict()
    has to be added to the ZODB connection before being used.
    """

    def __init__(self):
        # XXX: probably getting a connection or a persistent object
        # here is a good idea. Let's see how it gets used...
        self._data = PersistentDict()

    def __setitem__(self, key, value):
        """Adds a value to the dict.

        If a key object does not yet have _p_oid, it is added to the
        current connection (self._p_jar).
        """
        self.checkJar()
        self.checkKey(key)
        if key._p_oid is None:
            self._p_jar.add(key)
        self._data[key._p_oid] = value

    def __getitem__(self, key):
        self.checkKey(key)
        return self._data[key._p_oid]

    def __delitem__(self, key):
        self.checkKey(key)
        del self._data[key._p_oid]

    def keys(self):
        self.checkJar()
        result = []
        for oid in self._data:
            result.append(self._p_jar.get(oid))
        # XXX returning a lazy sequence is one optimization we might make
        return result

    def __contains__(self, key):
        self.checkKey(key)
        return  key._p_oid in self._data

    def __iter__(self):
        self.checkJar()
        for oid in self._data:
            yield self._p_jar.get(oid)

    def __len__(self):
        return len(self._data)

    def checkJar(self):
        if  self._p_jar is None:
            raise TypeError("PersistentKeyDict %r must be added "
                            "to the connection before being used" % (self, ))

    def checkKey(self, key):
        if not hasattr(key, '_p_oid'):
            raise TypeError("the key must be persistent (got %r)" % (key, ))
