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
Unit tests for schooltool.model

$Id$
"""

import unittest
from sets import Set
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember, IFacet, IFaceted
from schooltool.interfaces import IEventConfigurable

__metaclass__ = type

class MemberSetup:
    def setUp(self):
        import schooltool.model
        from schooltool.db import PersistentListSet
        self.__save = schooltool.model._setFactory
        # PersistentListSet is used so that the order of items in the sets
        # is preserved, so that we can compare output to a fixed string.
        # This is a stricter requirement than the actual contract.
        schooltool.model._setFactory = PersistentListSet

    def tearDown(self):
        import schooltool.model
        schooltool.model._setFactory = self.__save

class MemberStub:
    added = None
    removed = None
    implements(IGroupMember, IFaceted)
    def __init__(self):
        self.__facets__ = {}
    def notifyAdd(self, group, name):
        self.added = group
    def notifyRemove(self, group):
        self.removed = group

class FacetStub:
    implements(IFacet)

    def __init__(self, context=None, active=False):
        self.context = context
        self.active = active

class FacetWithEventsStub(FacetStub):
    implements(IEventConfigurable)

    def __init__(self, context=None, active=False, eventTable=None):
        FacetStub.__init__(self, context, active)
        if eventTable is None:
            eventTable = []
        self.eventTable = eventTable


class TestPerson(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IPerson, IEventTarget
        from schooltool.model import Person
        person = Person('John Smith')
        verifyObject(IPerson, person)
        verifyObject(IEventTarget, person)
        verifyObject(IEventConfigurable, person)


class TestURIs(unittest.TestCase):
    def testURIGroup(self):
        from schooltool.interfaces import URIGroup
        from schooltool.component import inspectSpecificURI
        inspectSpecificURI(URIGroup)

    def testURIMember(self):
        from schooltool.interfaces import URIMember
        from schooltool.component import inspectSpecificURI
        inspectSpecificURI(URIMember)


class TestGroupMember(MemberSetup, unittest.TestCase):

    def test_notifyAdd(self):
        from schooltool.model import GroupMember
        member = GroupMember()
        group = object()
        member.notifyAdd(group, 1)
        self.assertEqual(list(member.groups()), [group])
        self.assertEqual(member.__parent__, group)
        self.assertEqual(member.__name__, '1')
        member.notifyAdd(object(), '2')
        self.assertEqual(member.__parent__, group)
        self.assertEqual(member.__name__, '1')

    def test_notifyRemove(self):
        from schooltool.model import GroupMember
        member = GroupMember()
        group = object()
        other = object()
        for parent in (group, other):
            member.__parent__ = parent
            member.__name__ = 'spam'
            member._groups = Set([group])
            member.notifyRemove(group)
            self.assertEqual(list(member.groups()), [])
            self.assertRaises(KeyError, member.notifyRemove, group)
            if parent == group:
                self.assertEqual(member.__parent__, None)
                self.assertEqual(member.__name__, None)
            else:
                self.assertEqual(member.__parent__, other)
                self.assertEqual(member.__name__, 'spam')

    def testQueryLinks(self):
        from schooltool.model import GroupMember
        from schooltool.interfaces import IQueryLinks, URIGroup, URIMember
        from schooltool.interfaces import ISpecificURI
        member = GroupMember()
        verifyObject(IQueryLinks, member)
        self.assertEqual(member.listLinks(), [])
        group = object()
        member.notifyAdd(group, 1)

        for role in (URIGroup, ISpecificURI):
            links = member.listLinks(role)
            self.assertEqual(len(links), 1, str(role))
            self.assertEqual(links[0].role, URIGroup)
            self.assertEqual(links[0].title, "Membership")
            self.assert_(links[0].traverse() is group)

        class URIFoo(URIGroup): "http://example.com/ns/foo"

        for role in (URIMember, URIFoo):
            links = member.listLinks(role)
            self.assertEqual(links, [], str(role))


class TestGroup(MemberSetup, unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup, IEventTarget
        from schooltool.model import Group
        group = Group("root")
        verifyObject(IGroup, group)
        verifyObject(IGroupMember, group)
        verifyObject(IFaceted, group)
        verifyObject(IEventTarget, group)
        verifyObject(IEventConfigurable, group)

    def test_add(self):
        from schooltool.model import Group
        group = Group("root")
        member = MemberStub()
        key = group.add(member)
        self.assertEqual(member, group[key])
        self.assertEqual(member.added, group)
        self.assertRaises(TypeError, group.add, "not a member")

    def test_add_group(self):
        from schooltool.model import Group
        group = Group("root")
        member = Group("people")
        key = group.add(member)
        self.assertEqual(member, group[key])
        self.assertEqual(list(member.groups()), [group])

    def test_facet_management(self):
        from schooltool.model import Group
        from schooltool.component import getFacet
        group = Group("root", FacetStub)
        member = MemberStub()
        key = group.add(member)
        facet = getFacet(member, group)
        self.assertEquals(facet.context, member)
        self.assert_(facet.active)

        del group[key]
        self.assert_(getFacet(member, group) is facet)
        self.assert_(not facet.active)

        key = group.add(member)
        self.assert_(getFacet(member, group) is facet)
        self.assert_(facet.active)

    def test_remove(self):
        from schooltool.model import Group
        group = Group("root")
        member = MemberStub()
        key = group.add(member)
        del group[key]
        self.assertRaises(KeyError, group.__getitem__, key)
        self.assertRaises(KeyError, group.__delitem__, key)
        self.assertEqual(member.removed, group)

    def test_items(self):
        from schooltool.model import Group
        group = Group("root")
        self.assertEquals(list(group.keys()), [])
        self.assertEquals(list(group.values()), [])
        self.assertEquals(list(group.items()), [])
        member = MemberStub()
        key = group.add(member)
        self.assertEquals(list(group.keys()), [key])
        self.assertEquals(list(group.values()), [member])
        self.assertEquals(list(group.items()), [(key, member)])

    def testQueryLinks(self):
        from schooltool.model import Group
        from schooltool.interfaces import IQueryLinks, URIGroup, URIMember
        from schooltool.interfaces import ISpecificURI
        group = Group("foo")
        verifyObject(IQueryLinks, group)
        self.assertEqual(group.listLinks(), [])
        member = MemberStub()
        key = group.add(member)

        for role in (URIMember, ISpecificURI):
            links = group.listLinks(role)
            self.assertEqual(len(links), 1, str(role))
            self.assertEqual(links[0].role, URIMember)
            self.assertEqual(links[0].title, "Membership")
            self.assert_(links[0].traverse() is member)

        class URIFoo(URIMember): "http://example.com/ns/foo"

        for role in (URIGroup, URIFoo):
            links = group.listLinks(role)
            self.assertEqual(links, [], str(role))

        root = Group("root")
        root.add(group)

        links = group.listLinks()
        self.assertEqual(len(links), 2)

        links = group.listLinks(URIMember)
        self.assertEqual(len(links), 1)

        class URIFoo(URIMember): "http://example.com/ns/foo"

        links = group.listLinks(URIFoo)
        self.assertEqual(links, [])

        links = group.listLinks(URIGroup)
        self.assertEqual([link.traverse() for link in links], [root])
        self.assertEqual([link.role for link in links], [URIGroup])
        self.assertEqual([link.title for link in links], ["Membership"])


class TestRootGroup(unittest.TestCase):

    def test_interfaces(self):
        from schooltool.interfaces import IRootGroup
        from schooltool.model import RootGroup
        group = RootGroup("root")
        verifyObject(IRootGroup, group)


class TestFacetedMixin(unittest.TestCase):

    def test(self):
        from schooltool.model import FacetedMixin
        from schooltool.interfaces import IFaceted
        m = FacetedMixin()
        verifyObject(IFaceted, m)


class TestFacetedEventTargetMixin(unittest.TestCase):

    def test(self):
        from schooltool.model import FacetedEventTargetMixin
        from schooltool.interfaces import IFaceted, IEventTarget
        from schooltool.interfaces import IEventConfigurable
        et = FacetedEventTargetMixin()
        verifyObject(IFaceted, et)
        verifyObject(IEventTarget, et)
        verifyObject(IEventConfigurable, et)

    def test_getEventTable(self):
        from schooltool.model import FacetedEventTargetMixin
        from schooltool.component import setFacet
        et = FacetedEventTargetMixin()
        et.__facets__ = {} # use a simple dict instead of PersistentKeysDict
        et.eventTable.append(0)
        setFacet(et, 1, FacetStub())
        setFacet(et, 2, FacetStub(active=True))
        setFacet(et, 3, FacetWithEventsStub(eventTable=[1]))
        setFacet(et, 4, FacetWithEventsStub(active=True, eventTable=[2]))
        self.assertEquals(et.getEventTable(), [0, 2])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestRootGroup))
    suite.addTest(unittest.makeSuite(TestGroupMember))
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    suite.addTest(unittest.makeSuite(TestFacetedEventTargetMixin))
    suite.addTest(unittest.makeSuite(TestURIs))
    return suite

if __name__ == '__main__':
    unittest.main()
