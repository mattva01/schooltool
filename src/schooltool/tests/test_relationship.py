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
Unit tests for the relationships.

$Id$
"""

from sets import Set
import unittest

from persistent import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject, verifyClass
from zope.app.traversing.api import getPath

from schooltool.interfaces import IRelatable, ILink, IUnlinkHook
from schooltool.interfaces import ILinkSet, IPlaceholder
from schooltool.interfaces import IURIObject
from schooltool.uris import URIObject
from schooltool.tests.helpers import sorted
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin, EqualsSortedMixin
from schooltool.tests.utils import RegistriesSetupMixin, TraversableRoot
from schooltool.tests.utils import LocationStub


URITutor = URIObject("http://schooltool.org/ns/tutor")
URIRegClass = URIObject("http://schooltool.org/ns/regclass")
URIClassTutor = URIObject("http://schooltool.org/ns/classtutor")
URICommand = URIObject("http://army.gov/ns/command")
URISuperior = URIObject("http://army.gov/ns/superior")
URIReport = URIObject("http://army.gov/ns/report")


class Relatable(LocatableEventTargetMixin, Persistent):
    implements(IRelatable)

    def __init__(self, parent=None, name='does not matter'):
        from schooltool.relationship import LinkSet
        LocatableEventTargetMixin.__init__(self, parent, name)
        Persistent.__init__(self)
        self.__links__ = LinkSet(self)


class LinkStub(Persistent):
    implements(ILink)

    def __init__(self, reltype=None, role=None, target=None, title=None):
        self.reltype = reltype
        self.role = role
        self.target = target
        self.title = title
        self.__name__ = None


class TestRelationship(EventServiceTestMixin, RegistriesSetupMixin,
                       unittest.TestCase):
    """Conceptual relationships are really represented by three
    closely bound objects -- two links and a median relationship
    object.  This test tests the whole construct.
    """

    def setUp(self):
        from schooltool.relationship import _LinkRelationship, Link
        self.setUpEventService()
        self.setUpRegistries()

        self.klass = Relatable(self.serviceManager)
        self.tutor = Relatable(self.serviceManager)
        self.klass.title = '5C'
        self.tutor.title = 'John Jones'
        self.lklass = Link(self.klass, URITutor)
        self.ltutor = Link(self.tutor, URIRegClass)
        self.rel = _LinkRelationship(URIClassTutor, self.ltutor, self.lklass)

    def tearDown(self):
        self.tearDownRegistries()

    def test_interface(self):
        from schooltool.interfaces import IRemovableLink
        verifyObject(IRemovableLink, self.lklass)
        verifyObject(IRemovableLink, self.ltutor)

    def testLinkChecksURIs(self):
        from schooltool.relationship import Link
        self.assertRaises(TypeError, Link, Relatable(), "my tutor")

    def testLinkChecksParent(self):
        from schooltool.relationship import Link
        self.assertRaises(TypeError, Link, object(), URITutor)

    def test(self):
        from schooltool.interfaces import IRelationshipRemovedEvent

        self.assertEquals(self.lklass.title, "John Jones")
        self.assertEquals(self.ltutor.title, "5C")
        self.assertEquals(self.lklass.role, URITutor)
        self.assertEquals(self.ltutor.role, URIRegClass)
        self.assert_(self.ltutor.target is self.klass)
        self.assert_(self.lklass.target is self.tutor)
        self.assertEquals(list(self.klass.__links__), [self.lklass])
        self.assertEquals(list(self.tutor.__links__), [self.ltutor])

        class Callback:
            implements(IUnlinkHook)
            notify_link = None
            callable_link = None

            def notifyUnlinked(self, link):
                self.notify_link = link

            def callableCallback(self, link):
                self.callable_link = link

        self.assertRaises(TypeError, self.ltutor.registerUnlinkCallback,
                          object())

        tutor_callback = Callback()
        self.ltutor.registerUnlinkCallback(tutor_callback.callableCallback)
        klass_callback = Callback()
        self.lklass.registerUnlinkCallback(klass_callback)

        self.ltutor.unlink()

        self.assertEquals(list(self.klass.__links__), [])
        self.assertEquals(list(self.tutor.__links__), [])
        self.assert_(self.ltutor.target is self.klass)
        self.assert_(self.lklass.target is self.tutor)
        self.assert_(self.ltutor.source is self.tutor)
        self.assert_(self.lklass.source is self.klass)
        self.assert_(self.ltutor.__parent__ is None)
        self.assert_(self.lklass.__parent__ is None)

        self.assert_(tutor_callback.callable_link is self.ltutor)
        self.assert_(tutor_callback.notify_link is None)
        self.assertEquals(len(self.ltutor.callbacks), 0)

        self.assert_(klass_callback.callable_link is None)
        self.assert_(klass_callback.notify_link is self.lklass)
        self.assertEquals(len(self.lklass.callbacks), 0)

        self.assertEquals(len(self.eventService.events), 1)
        e = self.eventService.events[0]
        self.assert_(IRelationshipRemovedEvent.providedBy(e))
        self.assert_(self.ltutor in e.links)
        self.assert_(self.lklass in e.links)
        self.assertEquals(self.klass.events, [e])
        self.assertEquals(self.tutor.events, [e])

    def test_getPath(self):
        from schooltool.relationship import RelatableMixin

        root = TraversableRoot()
        parent = RelatableMixin()
        parent.__name__ = 'obj'
        parent.__parent__ = root

        link = LinkStub(role=URISuperior, reltype=URICommand,
                        target=LinkStub())
        parent.__links__.add(link)
        self.assertEqual(getPath(link), '/obj/relationships/0001')

        bystander = LocationStub('0000', parent)
        self.assertEqual(getPath(bystander), '/obj/0000')


class TestRelationshipSchema(EventServiceTestMixin, RegistriesSetupMixin,
                             unittest.TestCase):

    def setUp(self):
        self.setUpEventService()
        self.setUpRegistries()

    def tearDown(self):
        self.tearDownRegistries()

    def test_interfaces(self):
        from schooltool.relationship import RelationshipSchema
        from schooltool.interfaces import IRelationshipSchema
        verifyClass(IRelationshipSchema, RelationshipSchema)
        # verifyObject is buggy. It treats a class's __call__ as its __call__
        # IYSWIM
        ##verifyObject(IRelationshipSchemaFactory, RelationshipSchema)

    def testBadConstructor(self):
        from schooltool.relationship import RelationshipSchema
        self.assertRaises(TypeError, RelationshipSchema,
                          URICommand, '13', '14',
                          superior=URISuperior, report=URIReport)
        self.assertRaises(TypeError, RelationshipSchema,
                          URICommand, foo=URIReport,
                          superior=URISuperior, report=URIReport)
        self.assertRaises(TypeError, RelationshipSchema,
                          URICommand, report=URIReport)
        self.assertRaises(TypeError, RelationshipSchema,
                          report=URIReport, superior=URISuperior)

    def testBadCreateRelationship(self):
        from schooltool.relationship import RelationshipSchema
        schema = RelationshipSchema(URICommand,
                                    superior=URISuperior, report=URIReport)
        self.assertRaises(TypeError, schema)
        self.assertRaises(TypeError, schema, Relatable(), Relatable())
        self.assertRaises(TypeError, schema,
                          superior=Relatable(), bar=Relatable())
        self.assertRaises(TypeError, schema, foo=Relatable(),
                          superior=Relatable(), report=Relatable())

    def test(self):
        from schooltool.relationship import RelationshipSchema
        from schooltool import relationship
        relationship.setUp()

        verifyObject(IURIObject, URICommand)
        schema = RelationshipSchema(URICommand,
                                    superior=URISuperior, report=URIReport)

        self.assert_(schema.type is URICommand)

        superior = Relatable(self.serviceManager)
        report = Relatable(self.serviceManager)
        superior.title = 'superior'
        report.title = 'report'
        links = schema(superior=superior, report=report)

        link_to_superior = links.pop('superior')
        link_to_report = links.pop('report')
        self.assertEqual(links, {})

        verifyObject(ILink, link_to_superior)
        self.assert_(link_to_superior.role is URISuperior)
        self.assert_(link_to_superior.source is report)
        self.assert_(link_to_superior.target is superior)

        verifyObject(ILink, link_to_report)
        self.assert_(link_to_report.role is URIReport)
        self.assert_(link_to_report.source is superior)
        self.assert_(link_to_report.target is report)


class TestEvents(unittest.TestCase):

    def test_relationship_events(self):
        from schooltool.relationship import RelationshipAddedEvent
        from schooltool.relationship import RelationshipRemovedEvent
        from schooltool.interfaces import IRelationshipAddedEvent
        from schooltool.interfaces import IRelationshipRemovedEvent
        links = (LinkStub(role=URIReport, target=object()),
                 LinkStub(role=URISuperior, target=object()))
        e = RelationshipAddedEvent(links)
        verifyObject(IRelationshipAddedEvent, e)
        self.assert_(e.links is links)
        self.assert_('RelationshipAddedEvent' in str(e))

        e = RelationshipRemovedEvent(links)
        verifyObject(IRelationshipRemovedEvent, e)
        self.assert_(e.links is links)
        self.assert_('RelationshipRemovedEvent' in str(e))


class TestRelate(EventServiceTestMixin, unittest.TestCase):

    def setUp(self):
        self.setUpEventService()

    def test_relate(self):
        from schooltool.relationship import relate
        self.doChecks(relate)

    def test_defaultRelate(self):
        from schooltool.relationship import defaultRelate
        from schooltool.interfaces import IRelationshipAddedEvent

        a, b, links  = self.doChecks(defaultRelate)

        e = self.checkOneEventReceived([a, b])
        self.assert_(IRelationshipAddedEvent.providedBy(e))
        self.assert_(e.links is links)

    def doChecks(self, relate):
        a, role_a = Relatable(self.serviceManager), URISuperior
        b, role_b = Relatable(self.serviceManager), URIReport
        links = relate(URICommand, (a, role_a), (b, role_b))

        self.assertEqual(len(links), 2)
        self.assertEquals(Set([l.target for l in links]), Set([a, b]))
        self.assertEquals(Set([l.role for l in links]), Set([role_a, role_b]))
        self.assertEquals(links[0].reltype, URICommand)
        self.assertEquals(links[1].reltype, URICommand)

        linka, linkb = links
        self.assertEqual(len(list(a.__links__)), 1)
        self.assertEqual(len(list(b.__links__)), 1)
        self.assertEqual(list(a.__links__)[0], linka)
        self.assertEqual(list(b.__links__)[0], linkb)
        self.assertEqual(list(a.__links__)[0].target, b)
        self.assertEqual(list(b.__links__)[0].target, a)
        self.assertEqual(list(a.__links__)[0].role, role_b)
        self.assertEqual(list(b.__links__)[0].role, role_a)

        return a, b, links


class TestRelatableMixin(unittest.TestCase):

    def test(self):
        from schooltool.relationship import RelatableMixin, relate
        from schooltool.interfaces import IRelatable, IQueryLinks

        a = RelatableMixin()
        b = RelatableMixin()

        verifyObject(IQueryLinks, a)
        verifyObject(IRelatable, a)

        la ,lb = relate(URIClassTutor, (a, URIClassTutor), (b, URIRegClass))

        # no duplicate relationships
        self.assertRaises(ValueError,
            relate, URIClassTutor, (a, URIClassTutor), (b, URIRegClass))
        self.assertRaises(ValueError,
            relate, URIClassTutor, (b, URIRegClass), (a, URIClassTutor))

        self.assert_(a.listLinks(URIRegClass)[0].target is b)
        self.assert_(b.listLinks(URIClassTutor)[0].target is a)

        self.assert_(a.getLink(la.__name__) is la)
        self.assert_(b.getLink(lb.__name__) is lb)

    def test_listLinks(self):
        from schooltool.relationship import RelatableMixin
        a = RelatableMixin()

        URIEmployee = URIObject("foo:employee")
        URIJanitor = URIObject("foo:janitor")
        URIWindowWasher = URIObject("foo:windowman")

        j = LinkStub(role=URIJanitor)
        e = LinkStub(role=URIEmployee)

        a.__links__ = [e, j]

        self.assertEqual(a.listLinks(), [e, j])
        self.assertEqual(a.listLinks(URIEmployee), [e])
        self.assertEqual(a.listLinks(URIJanitor), [j])
        self.assertEqual(a.listLinks(URIWindowWasher), [])


class SimplePlaceholder:
    implements(IPlaceholder)

    replacedByLink = None

    __name__ = None

    def replacedBy(self, link):
        self.replacedByLink = link


class TestLinkSet(unittest.TestCase):

    def testInterface(self):
        from schooltool.relationship import LinkSet
        s = LinkSet()
        verifyObject(ILinkSet, s)

    def test(self):
        from schooltool.relationship import LinkSet
        s = LinkSet()
        reltype_a = object()
        role_a = object()
        target_a = Persistent()
        a = LinkStub(reltype_a, role_a, target_a)
        equivalent_to_a = LinkStub(reltype_a, role_a, target_a)
        b = LinkStub(object(), object(), Persistent())
        self.assertRaises(TypeError, s.add, object())
        s.add(a)
        s.add(b)
        self.assertRaises(ValueError, s.add, a)
        self.assertEquals(sorted([a, b]), sorted(s))
        self.assert_(a.__name__ is not None)
        self.assert_(b.__name__ is not None)
        self.assert_(a.__parent__ is s)
        self.assert_(b.__parent__ is s)
        self.assert_(s.getLink(a.__name__) is a)
        self.assert_(s.getLink(b.__name__) is b)

        self.assertRaises(ValueError, s.remove, equivalent_to_a)
        s.remove(a)
        self.assertRaises(ValueError, s.remove, a)
        self.assertEquals([b], list(s))

    def testPlaceholders(self):
        from schooltool.relationship import LinkSet
        s = LinkSet()
        link = LinkStub(object(), object(), Persistent())
        placeholder = SimplePlaceholder()
        self.assertRaises(TypeError, s.addPlaceholder, link, object())
        self.assertRaises(TypeError, s.addPlaceholder, object(), placeholder)
        self.assertRaises(ValueError, s.remove, placeholder)
        s.addPlaceholder(link, placeholder)
        # __iter__ should only iterate over links, not placeholders
        self.assertEqual(list(iter(s)), [])
        self.assertEqual(list(s.iterPlaceholders()), [placeholder])
        s.remove(placeholder)
        placeholder.__name__ = None
        self.assertEqual(list(s.iterPlaceholders()), [])

        # test that placeholder.replaced(link) is called
        s.addPlaceholder(link, placeholder)
        self.assertEqual(placeholder.replacedByLink, None)
        s.add(link)
        self.assertEqual(placeholder.replacedByLink, link)
        self.assertRaises(ValueError, s.addPlaceholder, link, placeholder)


class TestRelationshipValenciesMixin(unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.interfaces import IRelationshipValencies
        rvm = RelationshipValenciesMixin()
        verifyObject(IRelationshipValencies, rvm)

    def test_getValencies(self):
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.relationship import Valency
        from schooltool.uris import URIMembership, URIMember, URIGroup
        from schooltool.interfaces import ISchemaInvocation

        rvm = RelationshipValenciesMixin()
        self.assertEquals(len(rvm.getValencies()), 0)

        class SchemaStub:
            def __init__(self, type, **roles):
                self.type = type
                self.roles = roles

        schema = SchemaStub(URIMembership, a=URIMember, b=URIGroup)
        rvm.valencies = Valency(schema, 'a')
        result = rvm.getValencies()
        self.assertEquals(list(result), [(URIMembership, URIMember)])
        invocation = result[URIMembership, URIMember]
        verifyObject(ISchemaInvocation, invocation)
        self.assertEquals(invocation.this, 'a')
        self.assertEquals(invocation.other, 'b')
        self.assertEquals(invocation.schema, schema)

    def test_getValencies_faceted(self):
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.uris import URIObject
        from schooltool.uris import URIMembership, URIMember, URIGroup
        from schooltool.interfaces import IFacet
        from schooltool.relationship import Valency
        from schooltool.component import FacetManager
        from schooltool.facet import FacetedMixin

        class MyValent(RelationshipValenciesMixin, FacetedMixin):
            def __init__(self):
                RelationshipValenciesMixin.__init__(self)
                FacetedMixin.__init__(self)

        URIA = URIObject("uri:a")
        URIB = URIObject("uri:b")
        URIC = URIObject("uri:c")
        URID = URIObject("uri:d")

        class FacetStub(RelationshipValenciesMixin):
            implements(IFacet)
            __parent__ = None
            __name__ = None

        class SimpleFacetStub(Persistent):
            implements(IFacet)
            __parent__ = None
            __name__ = None

        class SchemaStub:
            def __init__(self, type, **roles):
                self.type = type
                self.roles = roles

        # A facet with valencies
        rvm = MyValent()
        facet = FacetStub()
        schema = SchemaStub(URIA, c=URIB, d=URIC)
        facet.valencies = Valency(schema, 'c')
        FacetManager(rvm).setFacet(facet, self)

        schema1 = SchemaStub(URIMembership, member=URIMember, group=URIGroup)
        rvm.valencies = Valency(schema1, 'member')

        self.assertEqualsSorted(list(rvm.getValencies()),
                                [(URIMembership, URIMember), (URIA, URIB)])

        # A facet without valencies
        facet2 = SimpleFacetStub()
        FacetManager(rvm).setFacet(facet2, self)

        self.assertEqualsSorted(list(rvm.getValencies()),
                                [(URIMembership, URIMember), (URIA, URIB)])

        facet.active = False
        self.assertEqualsSorted(list(rvm.getValencies()),
                                [(URIMembership, URIMember)])

    def test_getValencies_conflict(self):
        from schooltool.facet import FacetMixin, FacetedMixin, membersGetFacet
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.component import FacetManager

        class FooFacet(FacetMixin):
            pass

        class FooGroupFacet(FacetMixin, RelationshipValenciesMixin):
            membersGetFacet(FooFacet)

        class BarFacet(FacetMixin):
            pass

        class BarGroupFacet(FacetMixin, RelationshipValenciesMixin):
            membersGetFacet(BarFacet)

        class FacetedRelatableStub(FacetedMixin, RelationshipValenciesMixin):
            def __init__(self):
                FacetedMixin.__init__(self)
                RelationshipValenciesMixin.__init__(self)

        obj = FacetedRelatableStub()
        fm = FacetManager(obj)
        fm.setFacet(FooGroupFacet())
        obj.getValencies()
        fm.setFacet(BarGroupFacet())
        self.assertRaises(TypeError, obj.getValencies)

    def test__valency2invocation(self):
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.uris import URIMembership, URIMember, URIGroup
        from schooltool.relationship import Valency

        class SchemaStub:
            def __init__(self, type, **roles):
                self.type = type
                self.roles = roles

        schema = SchemaStub(URIMembership, member=URIMember, group=URIGroup)
        valency = Valency(schema, 'member')
        r = RelationshipValenciesMixin()
        self.assertEqual(r._valency2invocation(valency).keys(),
                         [(URIMembership, URIMember)])
        valency = Valency(schema, 'bad')
        self.assertRaises(ValueError, r._valency2invocation, valency)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationship))
    suite.addTest(unittest.makeSuite(TestRelationshipSchema))
    suite.addTest(unittest.makeSuite(TestEvents))
    suite.addTest(unittest.makeSuite(TestRelate))
    suite.addTest(unittest.makeSuite(TestRelatableMixin))
    suite.addTest(unittest.makeSuite(TestLinkSet))
    suite.addTest(unittest.makeSuite(TestRelationshipValenciesMixin))
    return suite
