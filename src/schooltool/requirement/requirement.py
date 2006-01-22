#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
"""Requirement Implementation

$Id$
"""

__docformat__ = 'restructuredtext'

import BTrees.OOBTree
import persistent
import persistent.list
import zope.event
import zope.interface
import zope.app.container.ordered
import zope.app.container.contained
import zope.app.event.objectevent
from zope.app import annotation
from zope.app.publisher.browser import applySkin

from schooltool.requirement import interfaces


REQUIREMENT_KEY = "schooltool.requirement"


class InheritedRequirement(zope.app.container.contained.Contained):
    """A simple requirement wrapper to mark inheritance.

    However, once the inherited requirement is modified by adding a
    sub-requirement, the inherited requirement is converted to a real one.
    """
    zope.interface.implements(interfaces.IRequirement)

    def __init__(self, requirement, parent, name):
        self.original = requirement
        self.__parent__ = parent
        self.__name__ = name

    def __eq__(self, other):
        return cmp(self.original, other)

    def __repr__(self):
        return '%s(%r)' %(self.__class__.__name__, self.original)

    def __setitem__(self, key, value):
        req = self.original.__class__(self.original.title, self.original)
        self.__parent__[self.__name__] = req
        req[key] = value

    def __getattr__(self, name):
        return getattr(self.original, name)


def unwrapRequirement(requirement):
    """Remove all inherited requirement wrappers."""
    while isinstance(requirement, InheritedRequirement):
        requirement = requirement.original
    return requirement


class Requirement(persistent.Persistent,
                  zope.app.container.contained.Contained):
    """A persistent requirement using a BTree for sub-requirements"""
    zope.interface.implements(interfaces.IExtendedRequirement)

    def __init__(self, title, *bases):
        super(Requirement, self).__init__()
        # See interfaces.IRequirement
        self.title = title
        # See interfaces.IRequirement
        self.bases = persistent.list.PersistentList()
        # See interfaces.IExtendedRequirement
        self.subs = persistent.list.PersistentList()
        # Storage for contained requirements
        self._data = BTrees.OOBTree.OOBTree()
        # List of keys that describe the order of the contained requirements
        self._order = persistent.list.PersistentList()
        for base in bases:
            self.addBase(base)

    def collectKeys(self):
        """See interfaces.IExtendedRequirement"""
        keys = tuple(self._data.keys())
        for base in self.bases:
            keys += base.collectKeys()
        return keys

    def distributeKey(self, key):
        """See interfaces.IExtendedRequirement"""
        self._order.append(key)
        for sub in self.subs:
            sub.distributeKey(key)

    def undistributeKey(self, key):
        """See interfaces.IExtendedRequirement"""
        self._order.remove(key)
        for sub in self.subs:
            sub.undistributeKey(key)

    def addBase(self, base):
        """See interfaces.IRequirement"""
        if base in self.bases:
            return
        self.bases.append(base)
        base.subs.append(self)
        for name, value in self._data.items():
            if name in base:
                value.addBase(base[name])
        for name in base.keys():
            if name not in self._order:
                self.distributeKey(name)

    def removeBase(self, base):
        """See interfaces.IRequirement"""
        self.bases.remove(base)
        base.subs.remove(self)
        for name, value in self._data.items():
            if name in base:
                value.removeBase(base[name])

        collectedKeys = self.collectKeys()
        for name in self._order:
            if name not in collectedKeys:
                self.undistributeKey(name)

    def changePosition(self, name, pos):
        """See interfaces.IRequirement"""
        old_pos = self._order.index(name)
        self._order.remove(name)
        self._order.insert(pos, name)
        zope.app.container.contained.notifyContainerModified(self)

    def keys(self):
        """See interface `IReadContainer`"""
        return self._order

    def __iter__(self):
        """See interface `IReadContainer`"""
        return iter(self.keys())

    def __getitem__(self, key):
        """See interface `IReadContainer`"""
        try:
            return self._data[key]
        except KeyError:
            for base in self.bases:
                if key in base:
                    return InheritedRequirement(base[key], self, key)
        raise KeyError, key

    def get(self, key, default=None):
        """See interface `IReadContainer`"""
        try:
            return self[key]
        except KeyError:
            pass
        return default

    def values(self):
        """See interface `IReadContainer`"""
        return [value for key, value in self.items()]

    def __len__(self):
        """See interface `IReadContainer`"""
        return len(self.keys())

    def items(self):
        """See interface `IReadContainer`"""
        for key in self.keys():
            yield key, self[key]

    def __contains__(self, key):
        """See interface `IReadContainer`"""
        return key in self.keys()

    has_key = __contains__

    def __setitem__(self, key, object):
        """See interface `IWriteContainer`"""
        for base in self.bases:
            if key in base:
                object.addBase(base[key])

        # Now set the item
        object, event = zope.app.container.contained.containedEvent(
            object, self, key)
        self._data[key] = object
        if key not in self._order:
            self.distributeKey(key)
        # Notify all subs of the addition
        for sub in self.subs:
            if not key in sub._order:
                sub._order.append(key)
        if event:
            zope.event.notify(event)
            zope.app.event.objectevent.modified(self)

    def __delitem__(self, key):
        """See interface `IWriteContainer`"""
        zope.app.container.contained.uncontained(self._data[key], self, key)
        self._order.remove(key)
        del self._data[key]

    def updateOrder(self, order):
        """See zope.app.container.interfaces.IOrderedContainer"""
        if set(self._order) != set(order):
            raise ValueError("Incompatible key set.")

        self._order = persistent.list.PersistentList(order)
        zope.app.container.contained.notifyContainerModified(self)

    def __repr__(self):
        return '%s(%r)' %(self.__class__.__name__, self.title)


def getRequirement(context):
    """Adapt an ``IHaveRequirement`` object to ``IRequirement``."""
    annotations = annotation.interfaces.IAnnotations(context)
    try:
        return annotations[REQUIREMENT_KEY]
    except KeyError:
        ## TODO: support generic objects without titles
        requirement = Requirement(getattr(context, "title", None))
        annotations[REQUIREMENT_KEY] = requirement
        zope.app.container.contained.contained(
            requirement, context, u'++requirement++')
        return requirement
# Convention to make adapter introspectable
getRequirement.factory = Requirement


class requirementNamespace(object):
    """Used to traverse to the requirements of an object"""

    def __init__(self, ob, request=None):
        self.context = ob

    def traverse(self, name, ignore):
        reqs = interfaces.IRequirement(self.context)
        return reqs

