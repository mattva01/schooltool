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
    __metaclass__ = type

    implements(ILocation, IEventTarget)

    def __init__(self, parent=None, name='does not matter'):
        self.__parent__ = parent
        self.__name__ = name
        self.events = []

    def notify(self, e):
        self.events.append(e)

    def clearEvents(self):
        self.events = []


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

            def clearEvents(self):
                self.events = []

        self.serviceManager = ServiceManager()
        self.eventService = self.serviceManager.eventService

    setUp = setUpEventService

    def check_one_event_received(self, receivers=None):
        """Check that exactly one event was received by the event service.

        Returns that one event.

        Also check that all receivers have received the event and only
        that one event (this only works if receivers are stubs that collect
        received events in their events attribute).
        """
        self.assertEquals(len(self.eventService.events), 1)
        e = self.eventService.events[0]
        if receivers:
            for target in receivers:
                self.assertEquals(len(target.events), 1)
                self.assert_(target.events[0] is e)
        return e


class RegistriesSetupMixin:
    """Mixin for substituting a temporary relationship and view registry."""

    def setUpRegistries(self):
        from schooltool import component, views, interfaces
        self.old_relationship_registry = component.relationship_registry
        self.old_view_registry = component.view_registry
        self.old_class_view_registry = component.class_view_registry
        self.old_facet_factory_registry = component.facet_factory_registry
        self.old_uri_registry = component._uri_registry
        component.resetRelationshipRegistry()
        component.resetViewRegistry()
        component.resetFacetFactoryRegistry()
        component.resetURIRegistry()
        interfaces.setUp()
        views.setUp()

    def tearDownRegistries(self):
        from schooltool import component
        component.relationship_registry = self.old_relationship_registry
        component.view_registry = self.old_view_registry
        component.class_view_registry = self.old_class_view_registry
        component.facet_factory_registry = self.old_facet_factory_registry
        component._uri_registry = self.old_uri_registry

    setUp = setUpRegistries
    tearDown = tearDownRegistries


class EqualsSortedMixin:

    def assertEqualsSorted(self, a, b):
        x = a[:]
        y = b[:]
        x.sort()
        y.sort()
        self.assertEquals(x, y)

    assertEqualSorted = assertEqualsSorted
