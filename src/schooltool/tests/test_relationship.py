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
from zope.interface import implements
from zope.interface.verify import verifyObject, verifyClass
from schooltool.interfaces import ISpecificURI, IRelatable, ILink
from schooltool.component import inspectSpecificURI
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin

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
        from schooltool.relationship import Link
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
        self.ltutor.unlink()
        self.assertEquals(list(self.klass.__links__), [])
        self.assertEquals(list(self.tutor.__links__), [])
        self.assert_(self.ltutor.traverse() is self.klass)
        self.assert_(self.lklass.traverse() is self.tutor)
        self.assert_(self.ltutor.__parent__ is self.tutor)
        self.assert_(self.lklass.__parent__ is self.klass)
        self.assertEquals(len(self.eventService.events), 1)
        e = self.eventService.events[0]
        self.assert_(IRelationshipRemovedEvent.isImplementedBy(e))
        self.assert_(URIClassTutor.isImplementedBy(e))
        self.assert_(self.ltutor in e.links)
        self.assert_(self.lklass in e.links)
        self.assertEquals(self.klass.events, [e])
        self.assertEquals(self.tutor.events, [e])

    def test_registerUnlinkCallback(self):
        self.assertRaises(NotImplementedError,
                          self.ltutor.registerUnlinkCallback, None)


class TestRelationshipSchema(EventServiceTestMixin, unittest.TestCase):

    def test_interfaces(self):
        from schooltool.relationship import RelationshipSchema
        from schooltool.interfaces import IRelationshipSchemaFactory
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

            self.assertEqual(len(links), 2)
            link_to_superior = None
            link_to_report = None
            for link in links:
                verifyObject(ILink, link)
                if link.role is URISuperior:
                    link_to_superior = link
                elif link.role is URIReport:
                    link_to_report = link
                else:
                    raise AssertionError('link has bad role. %r, %r'
                                        % (link, link.role))

            self.assertNotEquals(link_to_superior, None)
            self.assert_(link_to_superior.__parent__ is report)
            self.assert_(link_to_superior.traverse() is superior)

            self.assertNotEquals(link_to_report, None)
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

    def test__relate(self):
        from schooltool.relationship import _relate
        self.doChecks(_relate)

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
        from schooltool.relationship import RelatableMixin, _relate
        from schooltool.interfaces import IRelatable, IQueryLinks

        a = RelatableMixin()
        b = RelatableMixin()

        verifyObject(IQueryLinks, a)
        verifyObject(IRelatable, a)

        _relate(URIClassTutor, (a, URIClassTutor), (b, URIRegClass))

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

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationship))
    suite.addTest(unittest.makeSuite(TestRelationshipSchema))
    suite.addTest(unittest.makeSuite(TestEvents))
    suite.addTest(unittest.makeSuite(TestRelate))
    suite.addTest(unittest.makeSuite(TestRelatableMixin))
    return suite
