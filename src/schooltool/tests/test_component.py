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
from persistent import Persistent
from zope.interface import Interface, implements
from zope.interface import directlyProvides, classProvides
from zope.interface.verify import verifyObject
from zope.component.exceptions import ComponentLookupError, Invalid
from schooltool.uris import URIObject
from schooltool.interfaces import IFacet, IFaceted, IFacetAPI, IFacetManager
from schooltool.interfaces import IUtility, IUtilityService, IViewAPI
from schooltool.interfaces import IServiceAPI, IServiceManager
from schooltool.interfaces import IContainmentRoot, ILocation, ITraversable
from schooltool.interfaces import IRelationshipAPI, IRelatable, IQueryLinks
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.utils import RegistriesSetupMixin, RegistriesCleanupMixin
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


class TraversableStub:
    implements(ITraversable)

    def __init__(self):
        self.children = {}

    def traverse(self, name):
        return self.children[name]


class TestFacetManager(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from schooltool.db import PersistentKeysSetContainer

        class Stub:
            implements(IFaceted)

            def __init__(self):
                self.__facets__ = PersistentKeysSetContainer('facets', self)

        class FacetStub(Persistent):
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
        self.assert_(self.facet.__parent__ is self.ob.__facets__)
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


class TestFacetFunctions(RegistriesCleanupMixin, unittest.TestCase):

    def test_api(self):
        from schooltool import component
        verifyObject(IFacetAPI, component)

    def test_registerFacetFactory(self):
        from schooltool.component import registerFacetFactory
        from schooltool.component import setUp
        from schooltool.interfaces import IFacetFactory
        from zope.component import getUtility, getUtilitiesFor
        from schooltool.facet import FacetFactory
        setUp()
        name = "some facet"
        title = "some title"
        factory = FacetFactory(object, name, title)
        self.assertEqual(list(getUtilitiesFor(IFacetFactory)), [])
        self.assertRaises(TypeError, registerFacetFactory, object)
        self.assertRaises(KeyError, getUtility, IFacetFactory, name)
        registerFacetFactory(factory)
        self.assertEqual(list(getUtilitiesFor(IFacetFactory)),
                         [(name, factory)])
        self.assertEqual(getUtility(IFacetFactory, name), factory)
        registerFacetFactory(factory)  # no-op, already registered
        factory2 = FacetFactory(lambda: None, name, "another title")
        registerFacetFactory(factory2)
        self.assertEqual(list(getUtilitiesFor(IFacetFactory)),
                         [(name, factory2)])


class TestDynamicSchemaField(unittest.TestCase):

    def test(self):
        from schooltool.component import DynamicSchemaField
        from schooltool.interfaces import IDynamicSchemaField
        field = DynamicSchemaField('telephone', 'Phone')
        verifyObject(IDynamicSchemaField, field)


class TestDynamicSchema(unittest.TestCase):

    def test(self):
        from schooltool.component import DynamicSchema
        from schooltool.interfaces import IDynamicSchema
        schema = DynamicSchema()
        verifyObject(IDynamicSchema, schema)


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

    def test_getOptions(self):
        from schooltool.component import getOptions
        from schooltool.interfaces import IOptions

        x = LocationStub(None, 'root')
        self.assertRaises(TypeError, getOptions, x)
        self.assertRaises(TypeError, getOptions, object())

        a = LocationStub(None, 'foo')
        b = LocationStub(a, 'bar')
        c = LocationStub(b, 'baz')
        directlyProvides(a, IOptions)

        self.assertEqual(getOptions(a), a)
        self.assertEqual(getOptions(b), a)
        self.assertEqual(getOptions(c), a)


class Relatable(LocatableEventTargetMixin):
    implements(IRelatable, IQueryLinks)

    def __init__(self, parent, name='does not matter'):
        LocatableEventTargetMixin.__init__(self, parent, name)
        self.__links__ = Set()

    def listLinks(self, role):
        return [link for link in self.__links__
                     if role is None or role == link.role]


URISuperior = URIObject("http://army.gov/ns/superior")
URICommand = URIObject("http://army.gov/ns/command")
URIReport = URIObject("http://army.gov/ns/report")


class TestRelationships(EventServiceTestMixin, RegistriesCleanupMixin,
                        unittest.TestCase):

    def setUp(self):
        import schooltool.relationship
        import schooltool.component
        self.saveRegistries()
        schooltool.component.setUp()
        schooltool.relationship.setUp()
        self.setUpEventService()

    def test_api(self):
        from schooltool import component
        verifyObject(IRelationshipAPI, component)

    def tearDown(self):
        self.restoreRegistries()

    def test_getRelatedObjects(self):
        from schooltool.component import getRelatedObjects, relate
        officer = Relatable(self.serviceManager)
        soldier = Relatable(self.serviceManager)
        self.assertEqual(list(getRelatedObjects(officer, URIReport)), [])

        relate(URICommand, (officer, URISuperior), (soldier, URIReport))
        self.assertEqual(list(getRelatedObjects(officer, URIReport)),
                         [soldier])
        self.assertEqual(list(getRelatedObjects(officer, URISuperior)), [])


class TestRelationshipsNoSetup(EventServiceTestMixin, RegistriesCleanupMixin,
                               unittest.TestCase):

    def setUp(self):
        import schooltool.component
        self.saveRegistries()
        schooltool.component.setUp()
        self.setUpEventService()

    def test_relate_and_registry(self):
        from schooltool.component import registerRelationship
        from schooltool.component import getRelationshipHandlerFor
        from schooltool.component import relate, setUp

        URISomething = URIObject("http://ns.example.com/something")

        def stub(*args, **kw):
            return ('stub', args, kw)

        def stub2(*args, **kw):
            return ('stub2', args, kw)

        self.assertRaises(ComponentLookupError,
                          getRelationshipHandlerFor, None)
        self.assertRaises(ComponentLookupError,
                          getRelationshipHandlerFor, URISomething)

        registerRelationship(None, stub)
        self.assertEquals(getRelationshipHandlerFor(None), stub)
        self.assertEquals(getRelationshipHandlerFor(URISomething), stub)

        registerRelationship(URISomething, stub2)
        self.assertEquals(getRelationshipHandlerFor(None), stub)
        self.assertEquals(getRelationshipHandlerFor(URISomething), stub2)

        registerRelationship(None, stub)

        m, g = object(), object()
        args = (URISomething, (m, URISomething), (g, URISomething))
        self.assertEquals(relate(*args), ('stub2', args, {}))
        title = 'foo'
        args = (None, (m, URISomething), (g, URISomething))
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


class TestTimetableModelRegistry(RegistriesCleanupMixin, unittest.TestCase):

    def test_interface(self):
        from schooltool.interfaces import ITimetableModelRegistry
        from schooltool import component
        verifyObject(ITimetableModelRegistry, component)

    def test(self):
        from zope.component import getUtility, getUtilitiesFor
        from schooltool.component import registerTimetableModel, setUp
        from schooltool.interfaces import ITimetableModel
        from schooltool.interfaces import ITimetableModelFactory

        setUp()
        self.assertEqual(list(getUtilitiesFor(ITimetableModelFactory)), [])

        class TMStub:
            implements(ITimetableModel)
            classProvides(ITimetableModelFactory)

        registerTimetableModel("Foo.Bar.Baz", TMStub)
        registerTimetableModel("Foo.Bar.Baz", TMStub)
        self.assertEqual(list(getUtilitiesFor(ITimetableModelFactory)),
                         [("Foo.Bar.Baz", TMStub)])
        self.assertRaises(Invalid, registerTimetableModel,
                          "Foo.Bar.Baz", object)
        self.assertEqual(getUtility(ITimetableModelFactory, "Foo.Bar.Baz"),
                         TMStub)
        registerTimetableModel("Moo.Spoo", TMStub)
        self.assertEqual(Set(getUtilitiesFor(ITimetableModelFactory)),
                         Set([("Foo.Bar.Baz", TMStub), ("Moo.Spoo", TMStub)]))
        self.assertEqual(getUtility(ITimetableModelFactory, "Moo.Spoo"),
                         TMStub)


class TestComponentArchitecture(unittest.TestCase):

    def test(self):
        from zope.component import getService
        from zope.component.interfaces import IUtilityService
        from schooltool.component import setUp
        setUp()
        s = getService('Utilities')
        verifyObject(IUtilityService, s)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFacetManager))
    suite.addTest(unittest.makeSuite(TestFacetFunctions))
    suite.addTest(unittest.makeSuite(TestServiceAPI))
    suite.addTest(unittest.makeSuite(TestRelationships))
    suite.addTest(unittest.makeSuite(TestRelationshipsNoSetup))
    suite.addTest(unittest.makeSuite(TestViewRegistry))
    suite.addTest(unittest.makeSuite(TestUtilityService))
    suite.addTest(unittest.makeSuite(TestTimetableModelRegistry))
    suite.addTest(unittest.makeSuite(TestDynamicSchemaField))
    suite.addTest(unittest.makeSuite(TestDynamicSchema))
    suite.addTest(unittest.makeSuite(TestComponentArchitecture))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
