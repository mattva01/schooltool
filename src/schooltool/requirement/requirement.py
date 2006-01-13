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

import persistent.list
import zope.event
import zope.interface
import zope.app.container.btree
import zope.app.container.contained
import zope.app.event.objectevent
from zope.app import annotation
from zope.app.publisher.browser import applySkin

from schooltool.requirement import interfaces


REQUIREMENT_KEY = "schooltool.requirement"


class InheritedRequirement(zope.app.container.contained.Contained):
    """XXX I want a docstring"""

    def __init__(self, requirement, parent, name):
        self.original = requirement
        self.__parent__ = parent
        self.__name__ = name

    def __repr__(self):
        return '%s(%r)' %(self.__class__.__name__, self.original)

    def __setitem__(self, key, value):
        req = self.original.__class__(self.original.title)
        self.__parent__[self.__name__] = req
        req[key] = value

    def __getattr__(self, name):
        return getattr(self.original, name)


class Requirement(zope.app.container.btree.BTreeContainer,
                  zope.app.container.contained.Contained):
    """XXX I want a docstring"""

    zope.interface.implements(interfaces.IRequirement)

    def __init__(self, title, *bases):
        self.title = title
        zope.app.container.btree.BTreeContainer.__init__(self)
        self.bases = persistent.list.PersistentList()
        for base in bases:
            self.addBase(base)

    def addBase(self, base):
        if base in self.bases:
            return
        self.bases.append(base)
        for name, value in super(Requirement, self).items():
            if name in base:
                value.addBase(base[name])

    def removeBase(self, base):
        self.bases.remove(base)
        for name, value in super(Requirement, self).items():
            if name in base:
                value.removeBase(base[name])

    def keys(self):
        """See interface `IReadContainer`"""
        keys = set()
        for requirement in self.bases + [super(Requirement, self)]:
            keys.update(set(requirement.keys()))
        return keys

    def __iter__(self):
        return iter(self.keys())

    def __getitem__(self, key):
        """See interface `IReadContainer`"""
        container = super(Requirement, self)
        try:
            return container.__getitem__(key)
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
        self._SampleContainer__data.__setitem__(key, object)
        if event:
            zope.event.notify(event)
            zope.app.event.objectevent.modified(self)

    def __delitem__(self, key):
        """See interface `IWriteContainer`"""
        container = super(Requirement, self)
        zope.app.container.contained.uncontained(
            container.__getitem__(key), self, key)
        container.__delitem__(key)

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

