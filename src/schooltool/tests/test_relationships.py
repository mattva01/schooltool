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

class URITutor(ISpecificURI):
    """http://schooltool.org/ns/tutor"""

class URIRegClass(ISpecificURI):
    """http://schooltool.org/ns/regclass"""

class URICommand(ISpecificURI):
    """http://army.gov/ns/command"""

class URISuperior(ISpecificURI):
    """http://army.gov/ns/superior"""

class URIReport(ISpecificURI):
    """http://army.gov/ns/report"""

class Relatable:
    implements(IRelatable)
    def __init__(self):
        self.__links__ = Set()

class TestRelationship(unittest.TestCase):
    """Conceptual relationships are really represented by three
    closely bound objects -- two links and a median relationship
    object.  This test tests the whole construct.
    """
    def setUp(self):
        from schooltool.relationships import _LinkRelationship
        from schooltool.relationships import Link
        self.klass = Relatable()
        self.tutor = Relatable()
        self.lklass = Link(self.klass, URITutor)
        self.ltutor = Link(self.tutor, URIRegClass)
        self.rel = _LinkRelationship("Tutor of a class",
                                     self.ltutor, self.lklass)

    def test_interface(self):
        from schooltool.interfaces import IRemovableLink
        verifyObject(IRemovableLink, self.lklass)
        verifyObject(IRemovableLink, self.ltutor)

    def testLinkChecksURIs(self):
        from schooltool.relationships import Link
        self.assertRaises(TypeError, Link, Relatable(), "my tutor")

    def testLinkChecksParent(self):
        from schooltool.relationships import Link
        self.assertRaises(TypeError, Link, object(), URITutor)

    def test(self):
        from schooltool.relationships import Link
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

    def test_relate(self):
        from schooltool.relationships import relate
        officer = Relatable()
        soldier = Relatable()

        links = relate("Command",
                       (officer, URISuperior),
                       (soldier, URIReport))
        self.assertEqual(len(links), 2)
        linka, linkb = links
        for a, b, role, alink in ((officer, soldier, URIReport, linka),
                                  (soldier, officer, URISuperior, linkb)):
            self.assertEqual(len(a.__links__), 1)
            link = list(a.__links__)[0]
            self.assert_(link is alink)
            self.assert_(link.traverse() is b)
            self.assert_(link.role is role)
            self.assertEqual(link.title, "Command")


class TestRelationshipSchema(unittest.TestCase):

    def test_interfaces(self):
        from schooltool.relationships import RelationshipSchema
        from schooltool.interfaces import IRelationshipSchemaFactory
        from schooltool.interfaces import IRelationshipSchema
        verifyClass(IRelationshipSchema, RelationshipSchema)
        # verifyObject is buggy. It treats a class's __call__ as its __call__
        # iyswim
        ##verifyObject(IRelationshipSchemaFactory, RelationshipSchema)

    def testBadConstructor(self):
        from schooltool.relationships import RelationshipSchema
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
        from schooltool.relationships import RelationshipSchema
        schema = RelationshipSchema(URICommand,
                                    superior=URISuperior, report=URIReport)
        self.assertRaises(TypeError, schema)
        self.assertRaises(TypeError, schema, Relatable(), Relatable())
        self.assertRaises(TypeError, schema,
                          superior=Relatable(), bar=Relatable())
        self.assertRaises(TypeError, schema, foo=Relatable(),
                          superior=Relatable(), report=Relatable())

    def test(self):
        from schooltool.relationships import RelationshipSchema

        title1, doc = inspectSpecificURI(URICommand)
        schema1 = RelationshipSchema(URICommand,
                                    superior=URISuperior, report=URIReport)
        title2 = "optional title"
        schema2 = RelationshipSchema(URICommand, title2,
                                    superior=URISuperior, report=URIReport)

        for title, schema in (title1, schema1), (title2, schema2):
            self.assert_(schema.type is URICommand)
            self.assertEqual(schema.title, title)

            superior = Relatable()
            report = Relatable()
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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationship))
    suite.addTest(unittest.makeSuite(TestRelationshipSchema))
    return suite
