#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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

import os
import sets
import sys
import time
import unittest
import zope.event
from pprint import pformat
from zope.interface import implements, directlyProvides
from schooltool.interfaces import ILocation, IContainmentRoot, ITraversable
from schooltool.interfaces import IServiceManager, IEventTarget
from schooltool.tests.helpers import normalize_xml, diff
from zope.testing.cleanup import CleanUp

__metaclass__ = type


class _Anything:
    """An object that is equal to any other object."""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return 'Anything'

Anything = _Anything()


class TraversableStub:

    implements(ITraversable)

    def __init__(self, **kw):
        self.children = kw

    def traverse(self, name, path=None):
        return self.children[name]


class LocationStub(object):
    implements(ILocation)

    def __init__(self, name=None, parent=None):
        self.__name__ = name
        self.__parent__ = parent


class TraversableRoot(TraversableStub):

    implements(IContainmentRoot)


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


def setPath(obj, path, root=None):
    """Trick getPath(obj) into returning path."""
    assert path.startswith('/')
    obj.__name__ = path[1:]
    if root is None:
        directlyProvides(obj, ILocation)
        obj.__parent__ = TraversableRoot()
    else:
        assert IContainmentRoot.providedBy(root)
        obj.__parent__ = root


class ServiceManager:
    implements(IContainmentRoot, IServiceManager, IEventTarget)

    def __init__(self):
        self.eventService = self
        self.events = []
        self.targets = []

    def register(self, target):
        self.targets.append(target)

    def notify(self, event):
        zope.event.notify(event)
        self.events.append(event)
        for target in self.targets:
            event.dispatch(target)

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


class RegistriesCleanupMixin:
    """Saves the values of registries in setUp and restores them in tearDown.

    Only Zope Component Architecture is reset with the CleanUp facility.
    """

    def saveRegistries(self):
        from schooltool import component
        self.old_view_registry = component.view_registry
        self.old_class_view_registry = component.class_view_registry
        component.resetViewRegistry()
        CleanUp().cleanUp()

    def restoreRegistries(self):
        from schooltool import component
        component.view_registry = self.old_view_registry
        component.class_view_registry = self.old_class_view_registry
        CleanUp().cleanUp()

    setUp = saveRegistries
    tearDown = restoreRegistries


class RegistriesSetupMixin(RegistriesCleanupMixin):
    """Mixin for substituting temporary global registries."""

    def setUpRegistries(self):
        from schooltool import component, rest, uris, timetable, booking
        self.saveRegistries()
        component.setUp()
        uris.setUp()
        rest.setUp()
        timetable.setUp()
        booking.setUp()

    def tearDownRegistries(self):
        self.restoreRegistries()

    setUp = setUpRegistries
    tearDown = tearDownRegistries


class AppSetupMixin(RegistriesSetupMixin):
    """Mixin that creates a sample application structure for tests.

    The application (self.app) contains five containers:

      groups
        root        (self.root)
        locations   (self.locations)
        managers    (self.managers)
        teachers    (self.teachers)
        pupils      (self.pupils)
      persons
        johndoe     (self.person)
        nothohn     (self.person2)
        manager     (self.manager)
        teacher     (self.teacher)
      resources
        resource    (self.resource)
        location    (self.location)
        location2   (self.location2)
      notes
        note        (self.note1)
        note2       (self.note2)
      residences
        residence     (self.residence1)
        residence     (self.residence2)

    """

    def setUpSampleApp(self):
        from schooltool.model import Group, Person, Resource, Note, Residence
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        self.app = app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        app['notes'] = ApplicationObjectContainer(Note)
        app['residences'] = ApplicationObjectContainer(Residence)
        self.root = app['groups'].new("root", title="root")
        self.locations = app['groups'].new("locations", title="Locations")
        self.managers = app['groups'].new("managers", title="Managers")
        self.teachers = app['groups'].new("teachers", title="Teachers")
        self.pupils = app['groups'].new("pupils", title="Pupils")
        self.person = app['persons'].new("johndoe", title="John Doe")
        self.person2 = app['persons'].new("notjohn", title="Not John Doe")
        self.manager = app['persons'].new("manager", title="Manager")
        self.teacher = app['persons'].new("teacher", title="Prof. Bar")
        self.resource = app['resources'].new("resource", title="Kitchen sink")
        self.location = app['resources'].new("location", title="Inside")
        self.location2 = app['resources'].new("location2", title="Outside")
        self.note1 = app['notes'].new("note1", title="Note 1 Title",
                body="Note 1 Body")
        self.note2 = app['notes'].new("note2", title="Note 2",
                body="Note 2 Body")
        self.residence1 = app['residences'].new(title="Home Residence")

        Membership(group=self.root, member=self.person)
        Membership(group=self.root, member=self.teachers)
        Membership(group=self.root, member=self.managers)
        Membership(group=self.managers, member=self.manager)
        Membership(group=self.teachers, member=self.teacher)
        Membership(group=self.locations, member=self.location)
        Membership(group=self.locations, member=self.location2)

    setUp = setUpSampleApp

    # tearDown is inherited from the RegistriesSetupMixin.


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
            elif (isinstance(expected, sets.Set)
                and isinstance(results, sets.Set)):
                msg = "\n" + diff(pformat_set(expected), pformat_set(results))
            else:
                msg = "\n" + diff(pformat(expected), pformat(results))
        unittest.TestCase.assertEquals(self, results, expected, msg)

    assertEqual = assertEquals


def pformat_set(s):
    """Pretty-print a Set."""
    items = list(s)
    items.sort()
    return 'sets.Set(%s)' % pformat(items)


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


class TimezoneTestMixin:
    """A mixin for tests that fiddle with timezones."""

    def setUp(self):
        self.have_tzset = hasattr(time, 'tzset')
        self.touched_tz = False
        self.old_tz = os.getenv('TZ')

    def tearDown(self):
        if self.touched_tz:
            self.setTZ(self.old_tz)

    def setTZ(self, tz):
        self.touched_tz = True
        if tz is None:
            os.unsetenv('TZ')
        else:
            os.putenv('TZ', tz)
        time.tzset()


class LinkStub:

    def __init__(self, friend):
        self._friend = friend

    def traverse(self):
        return self._friend


class SchoolToolSetup(RegistriesSetupMixin, unittest.TestCase):
    """A base class for SchoolTool tests that need components to be set up.

    This is here mainly to save typing.  In the future it is possible that
    we will use PlacelessSetup from Zope3 instead of this class.
    """
