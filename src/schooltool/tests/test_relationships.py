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
from zope.interface.verify import verifyObject
from schooltool.interfaces import ISpecificURI, IRelatable

class URITutor(ISpecificURI):
    """http://schooltool.org/ns/tutor"""

class URIRegClass(ISpecificURI):
    """http://schooltool.org/ns/regclass"""

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
        from schooltool.relationships import _Relationship
        from schooltool.relationships import Link
        self.klass = Relatable()
        self.tutor = Relatable()
        self.lklass = Link(self.klass, URITutor)
        self.ltutor = Link(self.tutor, URIRegClass)
        self.rel = _Relationship("Tutor of a class", self.ltutor, self.lklass)

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationship))
    return suite
