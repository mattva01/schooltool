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
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject, verifyClass
from schooltool.interfaces import ISpecificURI, IRelatable, ILink, IUnlinkHook
from schooltool.interfaces import ILinkSet, IPlaceholder
from schooltool.component import inspectSpecificURI
from schooltool.tests.helpers import sorted
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin, EqualsSortedMixin
from schooltool.tests.utils import RegistriesSetupMixin

class URITutor(ISpecificURI):
    """http://schooltool.org/ns/tutor"""

class URIRegClass(ISpecificURI):
    """http://schooltool.org/ns/regclass"""

class URIClassTutor(ISpecificURI):
    """http://schooltool.org/ns/classtutor"""

class URICommand(ISpecificURI):
    """http://army.gov/ns/command"""

class URISuperior(ISpecificURI):
    """http://army.gov/ns/superior"""

class URIReport(ISpecificURI):
    """http://army.gov/ns/report"""

class Relatable(LocatableEventTargetMixin):
    implements(IRelatable)

    def __init__(self, parent=None, name='does not matter'):
        LocatableEventTargetMixin.__init__(self, parent, name)
        self.__links__ = Set()

class TestRelationship(EventServiceTestMixin, unittest.TestCase):
    """Conceptual relationships are really represented by three
    closely bound objects -- two links and a median relationship
    object.  This test tests the whole construct.
    """

    def setUp(self):
        from schooltool.relationship import _LinkRelationship
        from schooltool.relationship import Link
        self.setUpEventService()
        self.klass = Relatable(self.serviceManager)
        self.tutor = Relatable(self.serviceManager)
        self.lklass = Link(self.klass, URITutor)
        self.ltutor = Link(self.tutor, URIRegClass)
        self.rel = _LinkRelationship(URIClassTutor, "Tutor of a class",
                                     self.ltutor, self.lklass)

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

        self.assertEquals(self.rel.title, "Tutor of a class")
        self.assertEquals(self.lklass.title, "Tutor of a class")
        self.assertEquals(self.ltutor.title, "Tutor of a class")
        self.assertEquals(self.lklass.role, URITutor)
        self.assertEquals(self.ltutor.role, URIRegClass)
        self.assert_(self.ltutor.traverse() is self.klass)
        self.assert_(self.lklass.traverse() is self.tutor)
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
        self.assert_(self.ltutor.traverse() is self.klass)
        self.assert_(self.lklass.traverse() is self.tutor)
        self.assert_(self.ltutor.__parent__ is self.tutor)
        self.assert_(self.lklass.__parent__ is self.klass)

        self.assert_(tutor_callback.callable_link is self.ltutor)
        self.assert_(tutor_callback.notify_link is None)
        self.assertEquals(len(self.ltutor.callbacks), 0)

        self.assert_(klass_callback.callable_link is None)
        self.assert_(klass_callback.notify_link is self.lklass)
        self.assertEquals(len(self.lklass.callbacks), 0)

        self.assertEquals(len(self.eventService.events), 1)
        e = self.eventService.events[0]
        self.assert_(IRelationshipRemovedEvent.isImplementedBy(e))
        self.assert_(URIClassTutor.isImplementedBy(e))
        self.assert_(self.ltutor in e.links)
        self.assert_(self.lklass in e.links)
        self.assertEquals(self.klass.events, [e])
        self.assertEquals(self.tutor.events, [e])


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
        self.assertRaises(TypeError, RelationshipSchema, "foo",
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

        title1, doc = inspectSpecificURI(URICommand)
        schema1 = RelationshipSchema(URICommand,
                                    superior=URISuperior, report=URIReport)
        title2 = "optional title"
        schema2 = RelationshipSchema(URICommand, title2,
                                    superior=URISuperior, report=URIReport)

        for title, schema in (title1, schema1), (title2, schema2):
            self.assert_(schema.type is URICommand)
            self.assertEqual(schema.title, title)

            superior = Relatable(self.serviceManager)
            report = Relatable(self.serviceManager)
            links = schema(superior=superior, report=report)

            link_to_superior = links.pop('superior')
            link_to_report = links.pop('report')
            self.assertEqual(links, {})

            verifyObject(ILink, link_to_superior)
            self.assert_(link_to_superior.role is URISuperior)
            self.assert_(link_to_superior.__parent__ is report)
            self.assert_(link_to_superior.traverse() is superior)

            verifyObject(ILink, link_to_report)
            self.assert_(link_to_report.role is URIReport)
            self.assert_(link_to_report.__parent__ is superior)
            self.assert_(link_to_report.traverse() is report)


class TestEvents(unittest.TestCase):

    def test_relationship_events(self):
        from schooltool.relationship import RelationshipAddedEvent
        from schooltool.relationship import RelationshipRemovedEvent
        from schooltool.interfaces import IRelationshipAddedEvent
        from schooltool.interfaces import IRelationshipRemovedEvent
        links = (object(), object())
        e = RelationshipAddedEvent(links)
        verifyObject(IRelationshipAddedEvent, e)
        self.assert_(e.links is links)

        e = RelationshipRemovedEvent(links)
        verifyObject(IRelationshipRemovedEvent, e)
        self.assert_(e.links is links)


class TestRelate(EventServiceTestMixin, unittest.TestCase):

    def check_one_event_received(self, receivers):
        self.assertEquals(len(self.eventService.events), 1)
        e = self.eventService.events[0]
        for target in receivers:
            self.assertEquals(len(target.events), 1)
            self.assert_(target.events[0] is e)
        return e

    def test_relate(self):
        from schooltool.relationship import relate
        self.doChecks(relate)

    def test_defaultRelate(self):
        from schooltool.relationship import defaultRelate
        from schooltool.interfaces import IRelationshipAddedEvent

        a, b, links  = self.doChecks(defaultRelate)

        e = self.check_one_event_received([a, b])
        self.assert_(IRelationshipAddedEvent.isImplementedBy(e))
        self.assert_(URICommand.isImplementedBy(e))
        self.assert_(e.links is links)

    def doChecks(self, relate):
        title = 'a title'
        a, role_a = Relatable(self.serviceManager), URISuperior
        b, role_b = Relatable(self.serviceManager), URIReport
        links = relate(URICommand, (a, role_a), (b, role_b), title=title)

        self.assertEqual(len(links), 2)
        self.assertEquals(Set([l.traverse() for l in links]), Set([a, b]))
        self.assertEquals(Set([l.role for l in links]), Set([role_a, role_b]))
        self.assertEquals(links[0].title, title)
        self.assertEquals(links[1].title, title)
        self.assertEquals(links[0].reltype, URICommand)
        self.assertEquals(links[1].reltype, URICommand)

        linka, linkb = links
        self.assertEqual(len(a.__links__), 1)
        self.assertEqual(len(b.__links__), 1)
        self.assertEqual(list(a.__links__)[0], linka)
        self.assertEqual(list(b.__links__)[0], linkb)
        self.assertEqual(list(a.__links__)[0].traverse(), b)
        self.assertEqual(list(b.__links__)[0].traverse(), a)
        self.assertEqual(list(a.__links__)[0].role, role_b)
        self.assertEqual(list(b.__links__)[0].role, role_a)
        self.assertEqual(list(a.__links__)[0].title, title)
        self.assertEqual(list(b.__links__)[0].title, title)

        return a, b, links


class TestRelatableMixin(unittest.TestCase):

    def test(self):
        from schooltool.relationship import RelatableMixin, relate
        from schooltool.interfaces import IRelatable, IQueryLinks

        a = RelatableMixin()
        b = RelatableMixin()

        verifyObject(IQueryLinks, a)
        verifyObject(IRelatable, a)

        relate(URIClassTutor, (a, URIClassTutor), (b, URIRegClass))

        # no duplicate relationships
        self.assertRaises(ValueError,
            relate, URIClassTutor, (a, URIClassTutor), (b, URIRegClass))
        self.assertRaises(ValueError,
            relate, URIClassTutor, (b, URIRegClass), (a, URIClassTutor))

        self.assert_(a.listLinks(URIRegClass)[0].traverse() is b)
        self.assert_(b.listLinks(URIClassTutor)[0].traverse() is a)

    def test_listLinks(self):
        from schooltool.relationship import RelatableMixin
        a = RelatableMixin()

        class URIEmployee(ISpecificURI): "foo:employee"
        class URIJanitor(URIEmployee): "foo:janitor"
        class URIWindowWasher(URIJanitor): "foo:windowman"

        class LinkStub:
            def __init__(self, role):
                self.role = role

        j = LinkStub(URIJanitor)
        e = LinkStub(URIEmployee)

        a.__links__ = [e, j]

        self.assertEqual(a.listLinks(), [e, j])
        self.assertEqual(a.listLinks(URIEmployee), [e, j])
        self.assertEqual(a.listLinks(URIJanitor), [j])
        self.assertEqual(a.listLinks(URIWindowWasher), [])


class LinkStub:
    implements(ILink)

    def __init__(self, reltype, role, target):
        self.reltype = reltype
        self.role = role
        self._target = target

    def traverse(self):
        return self._target


class SimplePlaceholder:
    implements(IPlaceholder)

    replacedByLink = None

    def replacedBy(self, link):
        self.replacedByLink = link


class TestLinkSet(unittest.TestCase):

    def testInterface(self):
        from schooltool.relationship import LinkSet
        s = LinkSet()
        verifyObject(ILinkSet, s)

    def test(self):
        from persistence import Persistent
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

        self.assertRaises(ValueError, s.remove, equivalent_to_a)
        s.remove(a)
        self.assertRaises(ValueError, s.remove, a)
        self.assertEquals([b], list(s))

    def testPlaceholders(self):
        from persistence import Persistent
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
        from schooltool.interfaces import IRelationshipValencies
        from schooltool.interfaces import URIMembership, URIMember
        rvm = RelationshipValenciesMixin()
        self.assertEquals(len(rvm.getValencies()), 0)

        rvm._valencies.append((URIMembership, URIMember))

        self.assertEquals(list(rvm.getValencies()),
                          [(URIMembership, URIMember)])

    def test_getValencies_faceted(self):
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.interfaces import ISpecificURI
        from schooltool.interfaces import URIMembership, URIMember, IFacet
        from schooltool.component import FacetManager
        from schooltool.facet import FacetedMixin

        class MyValent(RelationshipValenciesMixin, FacetedMixin):
            def __init__(self):
                RelationshipValenciesMixin.__init__(self)
                FacetedMixin.__init__(self)

        class URIA(ISpecificURI): "uri:a"
        class URIB(ISpecificURI): "uri:b"
        class URIC(ISpecificURI): "uri:c"
        class URID(ISpecificURI): "uri:d"

        class Facet(RelationshipValenciesMixin):
            implements(IFacet)

        class SimpleFacet(Persistent):
            implements(IFacet)

        # A facet with valencies
        rvm = MyValent()
        facet = Facet()
        facet._valencies.append((URIA, URIB))
        FacetManager(rvm).setFacet(facet, self)

        rvm._valencies.append((URIMembership, URIMember))

        self.assertEqualsSorted(list(rvm.getValencies()),
                                [(URIMembership, URIMember), (URIA, URIB)])

        # A facet without valencies
        facet2 = SimpleFacet()
        FacetManager(rvm).setFacet(facet2, self)

        self.assertEqualsSorted(list(rvm.getValencies()),
                                [(URIMembership, URIMember), (URIA, URIB)])

        facet.active = False
        self.assertEqualsSorted(list(rvm.getValencies()),
                                [(URIMembership, URIMember)])


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
