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
from schooltool.interfaces import IFacet, IFaceted, IPlaceholder, ILink
from schooltool.interfaces import IFacetFactory
from schooltool.interfaces import IEventConfigurable
from schooltool.interfaces import IFacetedRelationshipSchema, IUnlinkHook
from schooltool.uris import ISpecificURI
from schooltool.tests.utils import EqualsSortedMixin

__metaclass__ = type


class FacetStub(Persistent):
    implements(IFacet)

    __parent__ = None
    __name__ = None
    owner = None
    active = False


class FacetWithEventsStub(FacetStub):
    implements(IEventConfigurable)

    def __init__(self, eventTable=None):
        if eventTable is None:
            eventTable = []
        self.eventTable = eventTable


class TestFacetMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetMixin
        facet = FacetMixin()
        verifyObject(IFacet, facet)


class TestFacetFactory(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetFactory
        result = object()
        factory = lambda: result
        ff = FacetFactory(factory, 'name', 'title')
        verifyObject(IFacetFactory, ff)
        self.assertEqual(ff.name, 'name')
        self.assertEqual(ff.title, 'title')
        self.assert_(ff(), result)

    def testNoTitle(self):
        from schooltool.facet import FacetFactory
        ff = FacetFactory(object, 'name')
        self.assertEqual(ff.name, 'name')
        self.assertEqual(ff.title, 'name')


class TestFacetedMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedMixin
        m = FacetedMixin()
        verifyObject(IFaceted, m)


class TestFacetedEventTargetMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedEventTargetMixin
        from schooltool.interfaces import IEventTarget
        from schooltool.interfaces import IEventConfigurable
        et = FacetedEventTargetMixin()
        verifyObject(IFaceted, et)
        verifyObject(IEventTarget, et)
        verifyObject(IEventConfigurable, et)

    def test_getEventTable(self):
        from schooltool.facet import FacetedEventTargetMixin
        from schooltool.component import FacetManager
        et = FacetedEventTargetMixin()
        et.eventTable.append(0)
        FacetManager(et).setFacet(FacetStub())
        f = FacetStub()
        FacetManager(et).setFacet(f)
        f.active = False
        f = FacetWithEventsStub(eventTable=[1])
        FacetManager(et).setFacet(f)
        f.active = False
        FacetManager(et).setFacet(FacetWithEventsStub(eventTable=[2]))
        self.assertEquals(et.getEventTable(), [0, 2])


class DummyRelationshipSchema:

    def __init__(self, type, **links_to_return):
        self.type = type
        self.links_to_return = links_to_return
        self.roles = {}

    def __call__(self, **parties):
        self.parties = parties
        d = {}
        for rolename, party in parties.iteritems():
            if rolename in self.links_to_return:
                d[rolename] = self.links_to_return[rolename]
            else:
                d[rolename] = LinkStub(party)
        return d


class URIDummy(ISpecificURI):
    """http://example.com/ns/dummy"""


class URIDummy2(ISpecificURI):
    """http://example.com/ns/dummy2"""


class LinkStub:
    implements(ILink)

    def __init__(self, target, reltype=URIDummy, role=URIDummy):
        self.target = target
        self.reltype = reltype
        self.role = role
        self.callbacks = Set()
        self.__name__ = None

    def traverse(self):
        return self.target

    def registerUnlinkCallback(self, callback):
        self.callbacks.add(callback)


class TestFacetedRelationshipSchema(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedRelationshipSchema, FacetFactory

        # verifyObject is buggy. It treats a class's __call__ as its __call__
        # IYSWIM
        ##f = FacetedRelationshipSchema(object())
        ##verifyObject(IFacetedRelationshipSchemaFactory, f)

        verifyClass(IFacetedRelationshipSchema, FacetedRelationshipSchema)
        schema = DummyRelationshipSchema(URIDummy)

        self.assertRaises(TypeError,
                          FacetedRelationshipSchema, schema, child=FacetStub)
        f = FacetedRelationshipSchema(schema,
                child=FacetFactory(FacetStub, 'FacetStub',
                                   facet_name='wonderfacet'))
        verifyObject(IFacetedRelationshipSchema, f)

        self.assertEqual(f.type, schema.type)

        parent = object()
        child = object()

        # Raises a TypeError because child is not IFaceted
        self.assertRaises(TypeError, f, parent=parent, child=child)

        from schooltool.facet import FacetedMixin
        from schooltool.component import FacetManager
        from schooltool.facet import FacetedMixin
        from schooltool.relationship import RelatableMixin

        class FacetedRelatableStub(FacetedMixin, RelatableMixin):
            def __init__(self):
                FacetedMixin.__init__(self)
                RelatableMixin.__init__(self)

        child = FacetedRelatableStub()
        self.assertEqual(list(FacetManager(child).iterFacets()), [])
        links = f(parent=parent, child=child)
        self.assertEqual(len(links), 2)
        self.assertEqual(links['parent'].traverse(), parent)
        self.assertEqual(links['child'].traverse(), child)
        # Next, need to check a facet was added to child.
        facet_list = list(FacetManager(child).iterFacets())
        self.assertEqual(len(facet_list), 1)
        facet = facet_list[0]

        self.assert_(facet.active, 'facet.active')
        self.assertEqual(facet.__parent__, child)
        self.assertEqual(facet.owner, links['child'])
        self.assertEqual(facet.__name__, 'wonderfacet')

        # Check that the facet will get deactivated when the link is unlinked.
        self.assert_(links['child'].callbacks,
                     'callbacks were not registered for the child link')
        for callback in links['child'].callbacks:
            if IUnlinkHook.providedBy(callback):
                callback.notifyUnlinked(links['child'])
            else:
                callback(links['child'])
        self.assert_(not facet.active, 'not facet.active')

    def testOwnedFacetsAlreadyPresent(self):
        from schooltool.facet import FacetedRelationshipSchema, FacetFactory


        from schooltool.facet import FacetedMixin
        from schooltool.component import FacetManager
        from schooltool.facet import FacetedMixin
        from schooltool.relationship import RelatableMixin

        class FacetedRelatableStub(FacetedMixin, RelatableMixin):
            def __init__(self):
                FacetedMixin.__init__(self)
                RelatableMixin.__init__(self)

        child = FacetedRelatableStub()
        facet = FacetStub()
        parent = Persistent()
        link = LinkStub(child)
        FacetManager(child).setFacet(facet, owner=link)
        facet.active = False
        schema = DummyRelationshipSchema(URIDummy, child=link)
        # We now have contrived a relationship schema that will return a
        # link for the 'child' rolename that is the owner of a facet in
        # child. The facet should remain, desipte making a faceted
        # relationship between parent and child.
        f = FacetedRelationshipSchema(schema,
                child=FacetFactory(FacetStub, 'FacetStub'))

        links = f(parent=parent, child=child)
        self.assertEqual(len(links), 2)
        self.assertEqual(links['parent'].traverse(), parent)
        self.assertEqual(links['child'].traverse(), child)
        # Next, need to check the existing facet on child was reused
        facet_list = list(FacetManager(child).iterFacets())
        self.assertEqual(len(facet_list), 1)
        self.assert_(facet is facet_list[0])

        self.assert_(facet.active, 'facet.active')
        self.assertEqual(facet.__parent__, child)
        self.assertEqual(facet.owner, links['child'])


class TestFacetDeactivation(unittest.TestCase, EqualsSortedMixin):

    def test_FacetOwnershipSetter(self):
        from schooltool.facet import FacetOwnershipSetter
        f = FacetOwnershipSetter()
        verifyObject(IPlaceholder, f)

    def test(self):
        from schooltool.component import FacetManager
        from schooltool.facet import facetDeactivator

        from schooltool.facet import FacetedMixin
        from schooltool.relationship import RelatableMixin

        class FacetedRelatableStub(FacetedMixin, RelatableMixin):
            def __init__(self):
                FacetedMixin.__init__(self)
                RelatableMixin.__init__(self)

        target = FacetedRelatableStub()
        facet = FacetStub()
        another_facet = FacetStub()
        link = LinkStub(target)
        FacetManager(target).setFacet(facet, owner=link)
        FacetManager(target).setFacet(another_facet, owner=object())
        self.assertEqualSorted(list(FacetManager(target).iterFacets()),
                               [facet, another_facet])
        self.assert_(another_facet.active)
        self.assert_(facet.active)
        facetDeactivator(link)
        self.assert_(another_facet.active)
        self.assert_(not facet.active, 'not facet.active')
        self.assert_(facet.owner is not link)
        self.assert_(facet.owner is not None)

        # This bit is white-box flavoured.
        linkset = target.__links__
        placeholders = list(linkset.iterPlaceholders())
        self.assertEqual(len(placeholders), 1)
        self.assert_(facet.owner is placeholders[0])

        # Back to our usual black-box style.
        link2 = LinkStub(target)
        linkset.add(link2)
        self.assert_(facet.owner is link2, 'facet.owner is link2')
        self.assert_(not facet.active, 'not facet.active')

        # Now, check that a link that has no facets will not be replaced
        # by a placeholder. After all, there's just no need for it.
        target = FacetedRelatableStub()
        link3 = LinkStub(target, URIDummy2)
        facetDeactivator(link3)
        linkset = target.__links__
        self.assertEqual(list(linkset.iterPlaceholders()), [])


class TestMembersGetFacet(unittest.TestCase):

    def test_simple(self):
        from schooltool.uris import URIMembership, URIGroup
        from schooltool.facet import membersGetFacet, FacetMixin
        from schooltool.facet import FacetedRelationshipSchema, FacetFactory
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.membership import Membership

        class SomeFacet(FacetMixin):
            pass

        class SomeClass(FacetMixin, RelationshipValenciesMixin):
            membersGetFacet(SomeFacet)

        self.assert_(hasattr(SomeClass, 'valencies'))
        valencies = SomeClass().getValencies()
        self.assert_((URIMembership, URIGroup) in valencies)
        valency = valencies[URIMembership, URIGroup]
        self.assert_(isinstance(valency.schema, FacetedRelationshipSchema))
        self.assert_(valency.schema._schema is Membership)
        factory = valency.schema._factories['member']
        self.assert_(isinstance(factory, FacetFactory))
        self.assert_(factory.factory is SomeFacet)
        self.assertEquals(factory.name, 'SomeFacet')
        self.assert_(factory.facet_name is None)

    def test_bells_and_whistles(self):
        from schooltool.uris import URIMembership, URIGroup
        from schooltool.facet import membersGetFacet, FacetMixin
        from schooltool.facet import FacetedRelationshipSchema, FacetFactory
        from schooltool.relationship import RelationshipValenciesMixin
        from schooltool.membership import Membership

        class SomeFacet(FacetMixin):
            pass

        class SomeClass(FacetMixin, RelationshipValenciesMixin):
            membersGetFacet(SomeFacet, facet_name='my_facet',
                            factory_name='some factory')

        self.assert_(hasattr(SomeClass, 'valencies'))
        valencies = SomeClass().getValencies()
        self.assert_((URIMembership, URIGroup) in valencies)
        valency = valencies[URIMembership, URIGroup]
        self.assert_(isinstance(valency.schema, FacetedRelationshipSchema))
        self.assert_(valency.schema._schema is Membership)
        factory = valency.schema._factories['member']
        self.assert_(isinstance(factory, FacetFactory))
        self.assert_(factory.factory is SomeFacet)
        self.assertEquals(factory.name, 'some factory')
        self.assertEquals(factory.facet_name, 'my_facet')

    def test_errors(self):
        from schooltool.facet import membersGetFacet, FacetMixin
        from schooltool.relationship import RelationshipValenciesMixin

        class SomeFacet(FacetMixin):
            pass

        def try_to_define_without_facetness():
            class SomeClass(RelationshipValenciesMixin):
                membersGetFacet(SomeFacet)

        def try_to_define_without_relationshipness():
            class SomeClass(FacetMixin):
                membersGetFacet(SomeFacet)

        self.assertRaises(TypeError, try_to_define_without_facetness)
        self.assertRaises(TypeError, try_to_define_without_relationshipness)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFacetMixin))
    suite.addTest(unittest.makeSuite(TestFacetFactory))
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    suite.addTest(unittest.makeSuite(TestFacetedEventTargetMixin))
    suite.addTest(unittest.makeSuite(TestFacetedRelationshipSchema))
    suite.addTest(unittest.makeSuite(TestFacetDeactivation))
    suite.addTest(unittest.makeSuite(TestMembersGetFacet))
    return suite

if __name__ == '__main__':
    unittest.main()
