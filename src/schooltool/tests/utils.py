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

import sys
import unittest
from pprint import pformat
from zope.interface import implements
from schooltool.interfaces import ILocation, IContainmentRoot
from schooltool.interfaces import IServiceManager, IEventTarget
from schooltool.tests.helpers import normalize_xml, diff

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


class ServiceManager:
    implements(IContainmentRoot, IServiceManager, IEventTarget)

    def __init__(self):
        self.eventService = self
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
        self.serviceManager = ServiceManager()
        self.eventService = self.serviceManager.eventService

    def checkOneEventReceived(self, receivers=()):
        """Check that exactly one event was received by the event service.

        Returns that one event.

        Also check that all receivers have received the event and only
        that one event (this only works if receivers are stubs that collect
        received events in their events attribute).
        """
        self.assertEquals(len(self.eventService.events), 1)
        e = self.eventService.events[0]
        for receiver in receivers:
            self.assertEquals(len(receiver.events), 1)
            self.assert_(receiver.events[0] is e)
        return e


class RegistriesSetupMixin:
    """Mixin for substituting temporary global registries."""

    def setUpRegistries(self):
        from schooltool import component, rest, uris, timetable
        self.old_relationship_registry = component.relationship_registry
        self.old_view_registry = component.view_registry
        self.old_class_view_registry = component.class_view_registry
        self.old_facet_factory_registry = component.facet_factory_registry
        self.old_uri_registry = uris._uri_registry
        self.old_timetable_model_registry = component.timetable_model_registry
        component.resetRelationshipRegistry()
        component.resetViewRegistry()
        component.resetFacetFactoryRegistry()
        component.resetTimetableModelRegistry()
        uris.resetURIRegistry()
        uris.setUp()
        rest.setUp()
        timetable.setUp()

    def tearDownRegistries(self):
        from schooltool import component, uris
        component.relationship_registry = self.old_relationship_registry
        component.view_registry = self.old_view_registry
        component.class_view_registry = self.old_class_view_registry
        component.facet_factory_registry = self.old_facet_factory_registry
        component.timetable_model_registry = self.old_timetable_model_registry
        uris._uri_registry = self.old_uri_registry

    setUp = setUpRegistries
    tearDown = tearDownRegistries


class EqualsSortedMixin:
    """Mixin that adds a helper method for comparing lists ignoring order."""

    def assertEqualsSorted(self, a, b):
        x = list(a)
        y = list(b)
        x.sort()
        y.sort()
        self.assertEquals(x, y)

    assertEqualSorted = assertEqualsSorted


class NiceDiffsMixin:
    """Mixin that changes assertEquals to show a unified diff of pretty-printed
    values.
    """

    def assertEquals(self, results, expected, msg=None):
        if msg is None:
            if (isinstance(expected, basestring)
                and isinstance(results, basestring)):
                msg = "\n" + diff(expected, results)
            else:
                msg = "\n" + diff(pformat(expected), pformat(results))
        unittest.TestCase.assertEquals(self, results, expected, msg)

    assertEqual = assertEquals


class XMLCompareMixin:

    def assertEqualsXML(self, result, expected, recursively_sort=()):
        """Assert that two XML documents are equivalent.

        If recursively_sort is given, it is a sequence of tags that
        will have test:sort="recursively" appended to their attribute lists
        in 'result' text.  See the docstring for normalize_xml for more
        information about this attribute.
        """
        result = normalize_xml(result, recursively_sort=recursively_sort)
        expected = normalize_xml(expected, recursively_sort=recursively_sort)
        self.assertEquals(result, expected, "\n" + diff(expected, result))

    assertEqualXML = assertEqualsXML


class QuietLibxml2Mixin:
    """Text mixin that disables libxml2 error reporting.

    Sadly the API of libxml2 does not allow us to restore the error reporting
    function in tearDown.  <Insert derogatory comments here>
    """

    def setUpLibxml2(self):
        import libxml2
        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def tearDownLibxml2(self):
        import libxml2
        # It's not possible to restore the error handler that was installed
        # before (libxml2 API limitation), so we set up a generic one that
        # prints everything to stdout.
        def on_error_callback(ctx, msg):
            sys.stderr.write(msg)
        libxml2.registerErrorHandler(on_error_callback, None)
