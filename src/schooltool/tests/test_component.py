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
Unit tests for schooltool.component

$Id$
"""

import unittest
from sets import Set
from zope.interface import Interface, implements, directlyProvides
from zope.interface.verify import verifyObject
from schooltool.uris import ISpecificURI
from schooltool.interfaces import IFacet, IFaceted, IFacetAPI, IFacetManager
from schooltool.interfaces import IUtility, IUtilityService
from schooltool.interfaces import IServiceAPI, IServiceManager
from schooltool.interfaces import IContainmentAPI, IContainmentRoot, ILocation
from schooltool.interfaces import ITraversable, IMultiContainer
from schooltool.interfaces import IRelationshipAPI, IRelatable, IQueryLinks
from schooltool.interfaces import IViewAPI
from schooltool.interfaces import ComponentLookupError
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import EqualsSortedMixin
from schooltool.db import PersistentKeysSetWithNames

__metaclass__ = type


class I1(Interface):

    def foo():
        pass


class I2(Interface):
    pass


class C1:
    implements(I1)

    def __init__(self, context):
        self.context = context

    def foo(self):
        return "foo"


class LocationStub:
    implements(ILocation)

    def __init__(self, parent, name):
        self.__parent__ = parent
        self.__name__ = name

    def __repr__(self):
        return "LocationStub(%r, %r)" % (self.__parent__, self.__name__)


class MulticontainerStub(LocationStub):
    implements(IMultiContainer)

    def getRelativePath(self, obj):
        return 'magic/' + obj.__name__


class TraversableStub:
    implements(ITraversable)

    def __init__(self):
        self.children = {}

    def traverse(self, name):
        return self.children[name]


class TestCanonicalPath(unittest.TestCase):

    def test_api(self):
        from schooltool import component
        verifyObject(IContainmentAPI, component)

    def buildTree(self):
        a = LocationStub(None, 'root')
        directlyProvides(a, IContainmentRoot)
        b = LocationStub(a, 'foo')
        c = LocationStub(b, 'bar')
        d = MulticontainerStub(b, 'baz')
        e = LocationStub(d, 'quux')
        return a, b, c, d, e

    def test_getPath(self):
        from schooltool.component import getPath

        x = LocationStub(None, 'root')
        self.assertRaises(TypeError, getPath, x)
        self.assertRaises(TypeError, getPath, object())

        a, b, c, d, e = self.buildTree()
        self.assertEqual(getPath(a), '/')
        self.assertEqual(getPath(b), '/foo')
        self.assertEqual(getPath(c), '/foo/bar')
        self.assertEqual(getPath(d), '/foo/baz')
        self.assertEqual(getPath(e), '/foo/baz/magic/quux')

    def test_getRoot(self):
        from schooltool.component import getRoot

        x = LocationStub(None, 'root')
        self.assertRaises(TypeError, getRoot, x)
        self.assertRaises(TypeError, getRoot, object())

        a, b, c, d, e = self.buildTree()
        self.assertEqual(getRoot(a), a)
        self.assertEqual(getRoot(b), a)
        self.assertEqual(getRoot(c), a)

    def test_traverse(self):
        from schooltool.component import traverse

        x = LocationStub(None, 'root')
        y = object()

        a, b, c, d, e = self.buildTree()
        for path in ('', '.', './', './.', './/'):
            self.assertEqual(traverse(x, path), x)
            self.assertEqual(traverse(y, path), y)
            self.assertEqual(traverse(a, path), a)
            self.assertEqual(traverse(b, path), b)
            self.assertEqual(traverse(c, path), c)
        for path in ('/', '//', '/..', '/.', '../.././/../..'):
            self.assertRaises(TypeError, traverse, x, path)
            self.assertRaises(TypeError, traverse, y, path)
            self.assertEqual(traverse(a, path), a)
            self.assertEqual(traverse(b, path), a)
            self.assertEqual(traverse(c, path), a)
        u = TraversableStub()
        v = TraversableStub()
        u.children['v'] = v
        for path in ('v', './v', 'v/', 'v/.', 'v//'):
            self.assertEqual(traverse(u, 'v'), v)
        self.assertRaises(TypeError, traverse, u, '..')
        self.assertRaises(TypeError, traverse, u, '/')
        self.assertRaises(TypeError, traverse, x, 'y')
        self.assertRaises(KeyError, traverse, u, 'y')


class TestFacetManager(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):

        class Stub:
            implements(IFaceted)
            __facets__ = PersistentKeysSetWithNames()
            __facets__._data = {}

        class FacetStub:
            implements(IFacet)
            active = False
            owner = None
            __name__ = None
            __parent__ = None

        self.ob = Stub()
        self.facet = FacetStub()
        self.facetclass = FacetStub

    def test(self):
        from schooltool.component import FacetManager
        fm = FacetManager(self.ob)
        verifyObject(IFacetManager, fm)
        self.assertRaises(TypeError, FacetManager, object())

    def test_setFacet_removeFacet(self):
        from schooltool.component import FacetManager
        owner_marker = object()
        self.facet.owner = owner_marker
        self.assertRaises(TypeError, FacetManager, object())
        fm = FacetManager(self.ob)
        self.assertRaises(TypeError, fm.setFacet, object())
        fm.setFacet(self.facet)
        self.assert_(self.facet.owner is owner_marker)
        self.assert_(self.facet.__parent__ is self.ob)
        self.assert_(self.facet.active)
        self.assert_(self.facet in self.ob.__facets__)
        fm.removeFacet(self.facet)
        self.assert_(self.facet not in self.ob.__facets__)
        self.assert_(not self.facet.active)
        self.assert_(self.facet.__parent__ is None)

        owner = object()

        # We get a ValueError here because the facet has a __name__ already.
        self.assertRaises(ValueError, fm.setFacet, self.facet, owner=owner)
        self.facet.__name__ = None
        fm.setFacet(self.facet, owner=owner)
        self.assert_(self.facet.owner is owner)

    def testFacetNames(self):
        # On setting a facet, the facet is given a __name__ that is unique
        # within its parent's __facets__ collection.
        # We could use an oid, but that would be too long.
        from schooltool.component import FacetManager
        fm = FacetManager(self.ob)
        facet1 = self.facetclass()
        facet2 = self.facetclass()
        facet3 = self.facetclass()

        self.assertEquals(facet1.__name__, None)
        fm.setFacet(facet1)
        self.assertNotEquals(facet1.__name__, None)
        self.assertEquals(fm.facetByName(facet1.__name__), facet1)

        self.assertEquals(facet2.__name__, None)
        fm.setFacet(facet2)
        self.assertNotEquals(facet2.__name__, None)
        self.assertNotEquals(facet2.__name__, facet1.__name__)

    def test_setFacet_with_a_name(self):
        from schooltool.component import FacetManager
        fm = FacetManager(self.ob)
        facet1 = self.facetclass()
        fm.setFacet(facet1, name='facetname')
        self.assertEquals(facet1.__name__, 'facetname')

        facet2 = self.facetclass()
        self.assertRaises(ValueError, fm.setFacet, facet2, name='facetname')
        self.assert_(facet2.__name__ is None)
        self.assert_(facet2.__parent__ is None)

    def test_iterFacets(self):
        from schooltool.component import FacetManager
        self.ob.__facets__.add(self.facet)
        self.assertEqual(list(FacetManager(self.ob).iterFacets()),
                         [self.facet])

    def test_facetsByOwner(self):
        from schooltool.component import FacetManager
        owner_marker = object()
        fm = FacetManager(self.ob)
        self.assertEqual(list(fm.facetsByOwner(owner_marker)), [])
        facet1 = self.facetclass()
        facet1.owner = owner_marker
        facet2 = self.facetclass()
        facet3 = self.facetclass()
        facet3.owner = owner_marker
        fm.setFacet(facet1)
        fm.setFacet(facet2)
        fm.setFacet(facet3)
        self.assertEqualSorted(list(fm.facetsByOwner(owner_marker)),
                               [facet1, facet3])


class TestFacetFunctions(unittest.TestCase):

    def test_api(self):
        from schooltool import component
        verifyObject(IFacetAPI, component)

    def test_iterFacetFactories(self):
        from schooltool.component import iterFacetFactories
        from schooltool.component import registerFacetFactory
        from schooltool.component import resetFacetFactoryRegistry
        from schooltool.component import getFacetFactory
        from schooltool.facet import FacetFactory
        name = "some facet"
        title = "some title"
        factory = FacetFactory(object, name, title)
        self.assertEqual(len(list(iterFacetFactories())), 0)
        self.assertRaises(TypeError, registerFacetFactory, object)
        self.assertRaises(KeyError, getFacetFactory, name)
        registerFacetFactory(factory)
        self.assertEqual(list(iterFacetFactories()), [factory])
        self.assertEqual(getFacetFactory(name), factory)
        registerFacetFactory(factory)  # no-op, already registered
        factory2 = FacetFactory(lambda: None, name, "another title")
        self.assertRaises(ValueError, registerFacetFactory, factory2)
        self.assertEqual(list(iterFacetFactories()), [factory])
        resetFacetFactoryRegistry()
        self.assertEqual(len(list(iterFacetFactories())), 0)


class TestServiceAPI(unittest.TestCase):

    def test_api(self):
        from schooltool import component
        verifyObject(IServiceAPI, component)

    def setUpTree(self):

        class RootStub:
            implements(IServiceManager)
            eventService = object()
            utilityService = object()
            timetableSchemaService = object()
            timePeriodService = object()

        class ObjectStub:
            implements(ILocation)

            def __init__(self, parent, name='foo'):
                self.__parent__ = parent
                self.__name__ = name

        self.root = RootStub()
        self.a = ObjectStub(self.root)
        self.b = ObjectStub(self.a)
        self.cloud = ObjectStub(None)

    def doTestService(self, callable, intended_result):
        self.assertEquals(callable(self.root), intended_result)
        self.assertEquals(callable(self.a), intended_result)
        self.assertEquals(callable(self.b), intended_result)
        self.assertRaises(ComponentLookupError, callable, self.cloud)
        self.assertRaises(ComponentLookupError, callable, None)

    def test__getServiceManager(self):
        from schooltool.component import _getServiceManager
        self.setUpTree()
        self.doTestService(_getServiceManager, self.root)

    def test_getEventService(self):
        from schooltool.component import getEventService
        self.setUpTree()
        self.doTestService(getEventService, self.root.eventService)

    def test_getUtilityService(self):
        from schooltool.component import getUtilityService
        self.setUpTree()
        self.doTestService(getUtilityService, self.root.utilityService)

    def test_getTimetableSchemaService(self):
        from schooltool.component import getTimetableSchemaService
        self.setUpTree()
        self.doTestService(getTimetableSchemaService,
                           self.root.timetableSchemaService)

    def test_getTimePeriodService(self):
        from schooltool.component import getTimePeriodService
        self.setUpTree()
        self.doTestService(getTimePeriodService, self.root.timePeriodService)


class Relatable(LocatableEventTargetMixin):
    implements(IRelatable, IQueryLinks)

    def __init__(self, parent, name='does not matter'):
        LocatableEventTargetMixin.__init__(self, parent, name)
        self.__links__ = Set()

    def listLinks(self, role):
        return [link for link in self.__links__
                     if link.role.extends(role, False)]


class URISuperior(ISpecificURI):
    """http://army.gov/ns/superior"""


class URICommand(ISpecificURI):
    """http://army.gov/ns/command"""


class URIReport(ISpecificURI):
    """http://army.gov/ns/report"""


class TestRelationships(EventServiceTestMixin, RegistriesSetupMixin,
                        unittest.TestCase):

    def setUp(self):
        import schooltool.relationship
        self.setUpRegistries()
        schooltool.relationship.setUp()
        self.setUpEventService()

    def test_api(self):
        from schooltool import component
        verifyObject(IRelationshipAPI, component)

    def tearDown(self):
        self.tearDownRegistries()

    def test_getRelatedObjects(self):
        from schooltool.component import getRelatedObjects, relate
        officer = Relatable(self.serviceManager)
        soldier = Relatable(self.serviceManager)
        self.assertEqual(list(getRelatedObjects(officer, URIReport)), [])

        relate(URICommand, (officer, URISuperior), (soldier, URIReport))
        self.assertEqual(list(getRelatedObjects(officer, URIReport)),
                         [soldier])
        self.assertEqual(list(getRelatedObjects(officer, URISuperior)), [])

    def test_relate_and_registry(self):
        from schooltool.component import registerRelationship
        from schooltool.component import resetRelationshipRegistry
        from schooltool.component import getRelationshipHandlerFor
        from schooltool.component import relate

        class URISomething(ISpecificURI):
            """http://ns.example.com/something"""

        def stub(*args, **kw):
            return ('stub', args, kw)

        def stub2(*args, **kw):
            return ('stub2', args, kw)

        resetRelationshipRegistry()
        self.assertRaises(ComponentLookupError,
                          getRelationshipHandlerFor, ISpecificURI)
        self.assertRaises(ComponentLookupError,
                          getRelationshipHandlerFor, URISomething)

        registerRelationship(ISpecificURI, stub)
        self.assertEquals(getRelationshipHandlerFor(ISpecificURI), stub)
        self.assertEquals(getRelationshipHandlerFor(URISomething), stub)

        registerRelationship(URISomething, stub2)
        self.assertEquals(getRelationshipHandlerFor(ISpecificURI), stub)
        self.assertEquals(getRelationshipHandlerFor(URISomething), stub2)

        # Idempotent
        self.assertRaises(ValueError,
                          registerRelationship, ISpecificURI, stub2)
        registerRelationship(ISpecificURI, stub)

        m, g = object(), object()
        args = (URISomething, (m, URISomething), (g, URISomething))
        self.assertEquals(relate(*args), ('stub2', args, {}))
        title = 'foo'
        args = (ISpecificURI, (m, URISomething), (g, URISomething))
        self.assertEquals(relate(*args), ('stub', args, {}))


class TestViewRegistry(RegistriesSetupMixin, unittest.TestCase):

    def testApi(self):
        from schooltool import component

        verifyObject(IViewAPI, component)

    def test(self):
        from schooltool.component import getView, ComponentLookupError
        from schooltool.model import Person, Group
        from schooltool.app import ApplicationObjectContainer, Application
        from schooltool.rest.model import GroupView, PersonView
        from schooltool.rest.app import ApplicationView
        from schooltool.rest.app import ApplicationObjectContainerView

        self.assert_(getView(Person(":)")).__class__ is PersonView)
        self.assert_(getView(Group(":)")).__class__ is GroupView)
        self.assert_(getView(Application()).__class__ is ApplicationView)
        self.assert_(getView(ApplicationObjectContainer(Group)).__class__ is
                     ApplicationObjectContainerView)

        self.assertRaises(ComponentLookupError, getView, object())

    def testViewRegistry(self):
        from schooltool.component import registerView, getView
        from schooltool.component import registerViewForClass

        class SomeView:
            def __init__(self, context):
                self.context = context

        class ClassView:
            def __init__(self, context):
                self.context = context

        class I1(Interface): pass
        class C1: implements(I1)
        class C2: pass

        registerView(I1, SomeView)
        self.assert_(getView(C1()).__class__ is SomeView)

        # Repeated declarations are OK
        registerView(I1, SomeView)

        registerViewForClass(C2, ClassView)
        registerViewForClass(C1, ClassView)
        self.assert_(getView(C2()).__class__ is ClassView)
        self.assert_(getView(C1()).__class__ is ClassView)


class Utility:

    implements(IUtility)

    __name__ = None
    __parent__ = None

    def __init__(self, title):
        self.title = title


class TestUtilityService(unittest.TestCase):

    def test(self):
        from schooltool.component import UtilityService
        u = UtilityService()
        verifyObject(IUtilityService, u)
        foo = Utility('foo utility')
        self.assertRaises(KeyError, u.__getitem__, 'foo')
        u['foo'] = foo
        self.assert_(u['foo'] is foo)
        self.assert_(foo.__parent__ is u)
        self.assertEquals(foo.__name__, 'foo')
        self.assertEqual(u.values(), [foo])

    def testParentAlreadySet(self):
        from schooltool.component import UtilityService
        u = UtilityService()
        foo = Utility('foo utility')
        parent = object()
        foo.__parent__ = parent
        foo.__name__ = None
        self.assertRaises(ValueError, u.__setitem__, 'foo', foo)
        self.assertRaises(KeyError, u.__getitem__, 'foo')
        self.assert_(foo.__parent__ is parent)
        self.assert_(foo.__name__ is None)


class TestTimetableModelRegistry(RegistriesSetupMixin, unittest.TestCase):

    def test_interface(self):
        from schooltool.interfaces import ITimetableModelRegistry
        from schooltool import component
        verifyObject(ITimetableModelRegistry, component)

    def test(self):
        from schooltool.component import getTimetableModel
        from schooltool.component import registerTimetableModel
        from schooltool.component import listTimetableModels
        from schooltool.component import resetTimetableModelRegistry
        from schooltool.interfaces import ITimetableModel

        resetTimetableModelRegistry()
        self.assertEqual(listTimetableModels(), [])

        class TMStub:
            implements(ITimetableModel)

        registerTimetableModel("Foo.Bar.Baz", TMStub)
        registerTimetableModel("Foo.Bar.Baz", TMStub)
        self.assertEqual(listTimetableModels(), ["Foo.Bar.Baz"])
        self.assertRaises(ValueError, registerTimetableModel,
                          "Foo.Bar.Baz", object)
        self.assertEqual(getTimetableModel("Foo.Bar.Baz"), TMStub)
        registerTimetableModel("Moo.Spoo", TMStub)
        self.assertEqual(Set(listTimetableModels()),
                         Set(["Foo.Bar.Baz", "Moo.Spoo"]))
        self.assertEqual(getTimetableModel("Moo.Spoo"), TMStub)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCanonicalPath))
    suite.addTest(unittest.makeSuite(TestFacetManager))
    suite.addTest(unittest.makeSuite(TestFacetFunctions))
    suite.addTest(unittest.makeSuite(TestServiceAPI))
    suite.addTest(unittest.makeSuite(TestRelationships))
    suite.addTest(unittest.makeSuite(TestViewRegistry))
    suite.addTest(unittest.makeSuite(TestUtilityService))
    suite.addTest(unittest.makeSuite(TestTimetableModelRegistry))
    return suite

if __name__ == '__main__':
    unittest.main()
