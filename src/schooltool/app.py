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
The SchoolTool application support objects.
"""

from persistence import Persistent
from persistence.dict import PersistentDict
from zope.interface import implements
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import ILocation
from schooltool.event import EventService
from schooltool.component import UtilityService
from schooltool.db import PersistentKeysSet
from schooltool.timetable import TimetableSchemaService, TimePeriodService

__metaclass__ = type


class Application(Persistent):
    """The application object.

    Services (as given by IServiceManager) are found by attribute.

    Root application objects are found by getRoots().

    Application object containers are found by __getitem__.
    """

    implements(IApplication)

    def __init__(self):
        self.eventService = EventService()
        self.utilityService = UtilityService()
        self.utilityService.__parent__ = self
        self.utilityService.__name__ = 'utils'
        self.timetableSchemaService = TimetableSchemaService()
        self.timetableSchemaService.__parent__ = self
        self.timetableSchemaService.__name__ = 'ttschemas'
        self.timePeriodService = TimePeriodService()
        self.timePeriodService.__parent__ = self
        self.timePeriodService.__name__ = 'time-periods'
        self._roots = PersistentKeysSet()
        self._appObjects = PersistentDict()

    def addRoot(self, root):
        """Internal api"""
        self._roots.add(root)

    def getRoots(self):
        """See IApplication"""
        return list(self._roots)

    def __setitem__(self, name, value):
        """Internal api"""
        if not ILocation.providedBy(value):
            raise TypeError("An application object must provide ILocatable")
        self._appObjects[name] = value
        value.__name__ = name
        value.__parent__ = self

    def __getitem__(self, name):
        """See IApplication"""
        return self._appObjects[name]

    def traverse(self, name):
        """See ITraversable"""
        if name == 'utils':
            return self.utilityService
        elif name == 'ttschemas':
            return self.timetableSchemaService
        elif name == 'time-periods':
            return self.timePeriodService
        return self[name]

    def keys(self):
        """See IApplication"""
        return self._appObjects.keys()


class ApplicationObjectContainer(Persistent):

    implements(IApplicationObjectContainer)

    __parent__ = None
    __name__ = None

    def __init__(self, factory):
        self._factory = factory
        self._contents = PersistentDict()
        self._nextid = 1

    def __getitem__(self, name):
        return self._contents[name]

    traverse = __getitem__

    def _newName(self):
        thisid = self._nextid
        self._nextid += 1
        return '%06i' % thisid

    def new(self, __name__=None, **kw):
        name = __name__
        if name is None:
            name = self._newName()
            while name in self._contents:
                name = self._newName()
        elif name in self._contents:
            raise KeyError(name)
        obj = self._factory(**kw)
        self._contents[name] = obj
        obj.__name__ = name
        obj.__parent__ = self
        return obj

    def __delitem__(self, name):
        obj = self._contents[name]
        if obj.__parent__ is self:
            obj.__parent__ = None
            obj.__name__ = None
        del self._contents[name]

    def keys(self):
        return self._contents.keys()

    def itervalues(self):
        return self._contents.itervalues()

