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
Unit tests for the schooltool.infofacets module.

$Id$
"""
import unittest
from zope.interface.verify import verifyObject


class TestDynamicFacetField(unittest.TestCase):
    def test(self):
        from schooltool.infofacets import DynamicFacetField
        from schooltool.interfaces import IDynamicSchemaField
        field = DynamicFacetField('telephone','Phone')
        verifyObject(IDynamicSchemaField, field)


class TestDynamicFacet(unittest.TestCase):

    def test(self):
        from schooltool.infofacets import DynamicFacet
        from schooltool.interfaces import IDynamicFacet

        dif = DynamicFacet()
        verifyObject(IDynamicFacet, dif)

    def test_fields(self):
        from schooltool.infofacets import DynamicFacet
        dif = DynamicFacet()
        dif.addField('jid','Jabber ID','string')


class TestPersonInfoFacet(unittest.TestCase):

    def test(self):
        from schooltool.infofacets import PersonInfoFacet
        from schooltool.interfaces import IPersonInfoFacet

        pif = PersonInfoFacet()
        verifyObject(IPersonInfoFacet, pif)

    def test_name(self):
        from schooltool.model import Person
        from schooltool.component import FacetManager

        person = Person("Steve Alexander")
        facet = FacetManager(person).facetByName("person_info")

        facet.first_name = "John"
        self.assertEqual(facet.first_name, "John")
        self.assertEqual(person.title, "John")

        facet.last_name = "Smith"
        self.assertEqual(facet.last_name, "Smith")
        self.assertEqual(person.title, "John Smith")

        facet.first_name = ""
        self.assertEqual(person.title, "Smith")

        facet.last_name = ""
        self.assertEqual(person.title, "Smith")


class TestAddressInfoFacet(unittest.TestCase):

    def test(self):
        from schooltool.infofacets import AddressInfoFacet
        from schooltool.interfaces import IAddressInfoFacet

        aif = AddressInfoFacet()
        verifyObject(IAddressInfoFacet, aif)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDynamicFacetField))
    suite.addTest(unittest.makeSuite(TestDynamicFacet))
    suite.addTest(unittest.makeSuite(TestPersonInfoFacet))
    suite.addTest(unittest.makeSuite(TestAddressInfoFacet))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
