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
import unittest
from zope.interface.verify import verifyObject

class TestRelationship(unittest.TestCase):
    """Conceptual relationships are really represented by three
    closely bound objects -- two links and a median relationship
    object.  This test tests the whole construct.
    """
    def setUp(self):
        from schooltool.relationships import Relationship
        from schooltool.relationships import Link
        self.klass = object()
        self.tutor = object()
        self.lklass = Link(self.klass, "my tutor")
        self.ltutor = Link(self.tutor, "my class")
        self.rel = Relationship("Tutor of a class", self.ltutor, self.lklass)

    def test_interface(self):
        from schooltool.interfaces import ILink
        verifyObject(ILink, self.lklass)
        verifyObject(ILink, self.ltutor)

    def test(self):
        from schooltool.relationships import Relationship
        from schooltool.relationships import Link
        self.assertEquals(self.rel.title, "Tutor of a class")
        self.assertEquals(self.lklass.title, "Tutor of a class")
        self.assertEquals(self.ltutor.title, "Tutor of a class")
        self.assertEquals(self.lklass.role, "my tutor")
        self.assertEquals(self.ltutor.role, "my class")
        self.assert_(self.ltutor.traverse() is self.klass)
        self.assert_(self.lklass.traverse() is self.tutor)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationship))
    return suite
