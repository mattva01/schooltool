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
Common utilities (stubs, mixins) for schooltool unit tests.

$Id$
"""

from zope.interface import implements
from schooltool.interfaces import ILocation, IEventTarget

__metaclass__ = type


class LocatableEventTargetMixin:
    """Object that is locatable and acts as an event target.

    All received events are stored in the events attribute.
    """

    implements(ILocation, IEventTarget)

    def __init__(self, parent=None, name='does not matter'):
        self.__parent__ = parent
        self.__name__ = name
        self.events = []

    def notify(self, e):
        self.events.append(e)


class EventServiceTestMixin:
    """Mixin for setting up an event service."""

    def setUpEventService(self):
        """Creates a service manager and an event service.

        The service manager (self.serviceManager) can be passed as the
        parent to LocatableEventTargetMixin stubs.  The event service
        (self.eventService) holds all received events in a list in its
        'events' attribute.
        """
        from schooltool.interfaces import IServiceManager, IEventTarget

        class ServiceManager:
            implements(IServiceManager, IEventTarget)
            def __init__(self):
                self.eventService = self
                self.events = []

            def notify(self, e):
                self.events.append(e)

        self.serviceManager = ServiceManager()
        self.eventService = self.serviceManager.eventService

    setUp = setUpEventService

