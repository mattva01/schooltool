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
Unit tests for schooltool.facet

$Id$
"""

import unittest
from sets import Set
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject, verifyClass
from schooltool.interfaces import IGroupMember, IFacet, IFaceted
from schooltool.interfaces import IEventConfigurable, ISpecificURI
from schooltool.interfaces import IFacetedRelationshipSchemaFactory
from schooltool.interfaces import IFacetedRelationshipSchema

__metaclass__ = type

class FacetStub(Persistent):
    implements(IFacet)

    __parent__ = None
    owner = None
    active = False

class FacetWithEventsStub(FacetStub):
    implements(IEventConfigurable)

    def __init__(self, eventTable=None):
        if eventTable is None:
            eventTable = []
        self.eventTable = eventTable


class TestFacetedMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedMixin
        from schooltool.interfaces import IFaceted
        m = FacetedMixin()
        verifyObject(IFaceted, m)


class TestFacetedEventTargetMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedEventTargetMixin
        from schooltool.interfaces import IFaceted, IEventTarget
        from schooltool.interfaces import IEventConfigurable
        et = FacetedEventTargetMixin()
        verifyObject(IFaceted, et)
        verifyObject(IEventTarget, et)
        verifyObject(IEventConfigurable, et)

    def test_getEventTable(self):
        from schooltool.facet import FacetedEventTargetMixin
        from schooltool.component import setFacet
        et = FacetedEventTargetMixin()
        et.__facets__ = Set()
        et.eventTable.append(0)
        setFacet(et, FacetStub())
        f = FacetStub()
        setFacet(et, f)
        f.active = False
        f = FacetWithEventsStub(eventTable=[1])
        setFacet(et, f)
        f.active = False
        setFacet(et, FacetWithEventsStub(eventTable=[2]))
        self.assertEquals(et.getEventTable(), [0, 2])


class DummyRelationshipSchema:

    def __init__(self, title, type):
        self.title = title
        self.type = type

    def __call__(self, **parties):
        self.parties = parties
        d = {}
        for rolename, party in parties.iteritems():
            d[rolename] = LinkStub(party)
        return d

class LinkStub:

    def __init__(self, target):
        self.target = target

    def traverse(self):
        return self.target

class URIDummy(ISpecificURI): """http://example.com/ns/dummy"""

class TestFacetedRelationshipSchema(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedRelationshipSchema

        # verifyObject is buggy. It treats a class's __call__ as its __call__
        # IYSWIM
        ##f = FacetedRelationshipSchema(object())
        ##verifyObject(IFacetedRelationshipSchemaFactory, f)

        verifyClass(IFacetedRelationshipSchema, FacetedRelationshipSchema)
        childlink = LinkStub(object())
        schema = DummyRelationshipSchema('foo', URIDummy)
        f = FacetedRelationshipSchema(schema, child=FacetStub)
        verifyObject(IFacetedRelationshipSchema, f)

        self.assertEqual(f.title, schema.title)
        self.assertEqual(f.type, schema.type)

        parent = object()
        child = object()

        # raises a TypeError because child is not IFaceted
        self.assertRaises(TypeError, f, parent=parent, child=child)

        from schooltool.facet import FacetedMixin
        from schooltool.component import iterFacets
        child = FacetedMixin()
        self.assertEqual(list(iterFacets(child)), [])
        returned = f(parent=parent, child=child)
        self.assertEqual(len(returned), 2)
        self.assertEqual(returned['parent'].traverse(), parent)
        self.assertEqual(returned['child'].traverse(), child)
        # next, need to check a facet was added to child.
        facet_list = list(iterFacets(child))
        self.assertEqual(len(facet_list), 1)
        facet = facet_list[0]

        # These will fail until I've updated the facet API for ownership
        self.assert_(facet.active, 'facet.active')
        self.assertEqual(facet.__parent__, child)
        self.assertEqual(facet.owner, returned['child'])

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    suite.addTest(unittest.makeSuite(TestFacetedEventTargetMixin))
    suite.addTest(unittest.makeSuite(TestFacetedRelationshipSchema))
    return suite

if __name__ == '__main__':
    unittest.main()
