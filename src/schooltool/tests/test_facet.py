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
from schooltool.interfaces import IFacet, IFaceted
from schooltool.interfaces import IEventConfigurable, ISpecificURI
from schooltool.interfaces import IFacetedRelationshipSchemaFactory
from schooltool.interfaces import IFacetedRelationshipSchema, IUnlinkHook
from schooltool.tests.utils import EqualsSortedMixin

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
        self.callbacks = Set()

    def traverse(self):
        return self.target

    def registerUnlinkCallback(self, callback):
        self.callbacks.add(callback)

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

        # Raises a TypeError because child is not IFaceted
        self.assertRaises(TypeError, f, parent=parent, child=child)

        from schooltool.facet import FacetedMixin
        from schooltool.component import iterFacets
        child = FacetedMixin()
        self.assertEqual(list(iterFacets(child)), [])
        links = f(parent=parent, child=child)
        self.assertEqual(len(links), 2)
        self.assertEqual(links['parent'].traverse(), parent)
        self.assertEqual(links['child'].traverse(), child)
        # Next, need to check a facet was added to child.
        facet_list = list(iterFacets(child))
        self.assertEqual(len(facet_list), 1)
        facet = facet_list[0]

        self.assert_(facet.active, 'facet.active')
        self.assertEqual(facet.__parent__, child)
        self.assertEqual(facet.owner, links['child'])

        # Check that the facet will get deactivated when the link is unlinked.
        self.assert_(links['child'].callbacks,
                     'callbacks were not registered for the child link')
        for callback in links['child'].callbacks:
            if IUnlinkHook.isImplementedBy(callback):
                callback.notifyUnlinked(links['child'])
            else:
                callback(links['child'])
        self.assert_(not facet.active, 'not facet.active')


class TestFacetDeactivation(unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.facet import facetDeactivator
        from schooltool.facet import FacetedMixin
        from schooltool.component import iterFacets, setFacet
        faceted = FacetedMixin()
        facet = FacetStub()
        another_facet = FacetStub()
        link = LinkStub(faceted)
        setFacet(faceted, facet, owner=link)
        setFacet(faceted, another_facet, owner=object())
        self.assertEqualSorted(list(iterFacets(faceted)),
                               [facet, another_facet])
        self.assert_(another_facet.active)
        self.assert_(facet.active)
        facetDeactivator(link)
        self.assert_(another_facet.active)
        self.assert_(not facet.active, 'not facet.active')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    suite.addTest(unittest.makeSuite(TestFacetedEventTargetMixin))
    suite.addTest(unittest.makeSuite(TestFacetedRelationshipSchema))
    suite.addTest(unittest.makeSuite(TestFacetDeactivation))
    return suite

if __name__ == '__main__':
    unittest.main()
