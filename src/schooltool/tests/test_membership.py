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
Unit tests for schooltool.membership

$Id: test_model.py 153 2003-10-16 12:33:50Z mg $
"""

import unittest
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember, IFaceted, IQueryLinks
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.utils import RelationshipTestMixin
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.test_relationship import Relatable
from schooltool.relationship import RelatableMixin

__metaclass__ = type

class P(Persistent):
    pass

class BasicRelatable(Relatable, RelatableMixin):
    pass

class MemberStub(BasicRelatable):
    implements(IGroupMember, IFaceted)

    def __init__(self, parent=None, name='does not matter'):
        BasicRelatable.__init__(self, parent, name)
        self.__facets__ = {}
        self.added = None
        self.removed = None

    def notifyAdded(self, group, name):
        self.added = group
        if self not in group.values():
            raise AssertionError("notifyAdded called too early")

    def notifyRemoved(self, group):
        self.removed = group
        if self in group.values():
            raise AssertionError("notifyRemoved called too early")


class GroupStub(BasicRelatable):
    deleted = None

    def __delitem__(self, key):
        self.deleted = key

    def add(self, value):
        return "name"



class TestURIs(unittest.TestCase):

    def testURIGroup(self):
        from schooltool.interfaces import URIGroup
        from schooltool.component import inspectSpecificURI
        inspectSpecificURI(URIGroup)

    def testURIMember(self):
        from schooltool.interfaces import URIMember
        from schooltool.component import inspectSpecificURI
        inspectSpecificURI(URIMember)


class TestMemberMixin(unittest.TestCase):

    def test_notifyAdded(self):
        from schooltool.membership import MemberMixin
        member = MemberMixin()
        group = P()
        member.notifyAdded(group, 1)
        self.assertEqual(list(member.groups()), [group])
        self.assertEqual(member.__parent__, group)
        self.assertEqual(member.__name__, '1')
        member.notifyAdded(P(), '2')
        self.assertEqual(member.__parent__, group)
        self.assertEqual(member.__name__, '1')

    def test_notifyRemoved(self):
        from schooltool.membership import MemberMixin
        member = MemberMixin()
        group = object()
        other = object()
        for parent in (group, other):
            member.__parent__ = parent
            member.__name__ = 'spam'
            member._groups = {group: '1'}
            member.notifyRemoved(group)
            self.assertEqual(list(member.groups()), [])
            self.assertRaises(KeyError, member.notifyRemoved, group)
            if parent == group:
                self.assertEqual(member.__parent__, None)
                self.assertEqual(member.__name__, None)
            else:
                self.assertEqual(member.__parent__, other)
                self.assertEqual(member.__name__, 'spam')


class TestGroupMixin(unittest.TestCase):

    def test_add(self):
        from schooltool.membership import GroupMixin
        group = GroupMixin()
        member = MemberStub()
        key = group.add(member)
        self.assertEqual(member, group[key])
        self.assertEqual(member.added, group)
        self.assertRaises(TypeError, group.add, "not a member")

    def test_remove(self):
        from schooltool.membership import GroupMixin
        group = GroupMixin()
        member = MemberStub()
        key = group.add(member)
        del group[key]
        self.assertRaises(KeyError, group.__getitem__, key)
        self.assertRaises(KeyError, group.__delitem__, key)
        self.assertEqual(member.removed, group)

    def test_items(self):
        from schooltool.membership import GroupMixin
        group = GroupMixin()
        self.assertEquals(list(group.keys()), [])
        self.assertEquals(list(group.values()), [])
        self.assertEquals(list(group.items()), [])
        member = MemberStub()
        key = group.add(member)
        self.assertEquals(list(group.keys()), [key])
        self.assertEquals(list(group.values()), [member])
        self.assertEquals(list(group.items()), [(key, member)])


class TestMembershipRelationship(RelationshipTestMixin, EventServiceTestMixin,
                                 unittest.TestCase):

    def test(self):
        from schooltool.component import registerRelationship
        from schooltool.membership import Membership
        from schooltool.interfaces import URIMembership, URIGroup, URIMember

        cookie = object()
        def handler(reltype, (a, role_of_a), (b, role_of_b), title=None):
            self.assert_(reltype is URIMembership)
            self.assert_((m, URIMember) in [(a, role_of_a), (b, role_of_b)])
            self.assert_((g, URIGroup) in [(a, role_of_a), (b, role_of_b)])
            self.assertEquals(title, "http://schooltool.org/ns/membership")
            return (cookie, cookie)

        registerRelationship(URIMembership, handler)

        g, m = GroupStub(), MemberStub()
        result = Membership(group=g, member=m)
        self.assert_(result['group'] is cookie, "our handler wasn't called")

    def testInterfaces(self):
        from schooltool.component import registerRelationship
        from schooltool.membership import Membership
        from schooltool.interfaces import URIMembership, URIGroup, URIMember
        from schooltool.interfaces import IRelationshipSchema
        verifyObject(IRelationshipSchema, Membership)

class TestCyclicConstraint(RelationshipTestMixin, EventServiceTestMixin,
                           unittest.TestCase):

    def testCyclicMembership(self):
        self.setUpEventService()
        # Not bothering to register a relationship especially for membership.
        # Standard relationships will do.
        from schooltool.membership import Membership, checkForCycles
        from schooltool.component import registerRelationship
        from schooltool.interfaces import ISpecificURI
        from schooltool.relationship import defaultRelate
        registerRelationship(ISpecificURI, defaultRelate)
        Relatable = lambda: BasicRelatable(self.serviceManager)
        g = Relatable()

        # Test a cycle of a group with itself.
        self.assertRaises(ValueError, checkForCycles, g, g)

        # Test a two-group cycle.
        g1 = Relatable()
        g2 = Relatable()
        checkForCycles(g1, g2)
        checkForCycles(g2, g1)
        links = Membership(group=g1, member=g2)
        self.assertEquals(links['member'].traverse(), g2)
        self.assertEquals(links['group'].traverse(), g1)
        self.assertRaises(ValueError, checkForCycles, g2, g1)
        self.assertRaises(ValueError, checkForCycles, g1, g2)


class TestEvents(unittest.TestCase):

    def test_membership_events(self):
        from schooltool.membership import MemberAddedEvent
        from schooltool.membership import MemberRemovedEvent
        from schooltool.interfaces import IMemberAddedEvent
        from schooltool.interfaces import IMemberRemovedEvent
        from schooltool.interfaces import URIGroup, URIMember
        from schooltool.interfaces import ISpecificURI

        class URIUnrelated(ISpecificURI):
            """http://ns.example.org/role/unrelated"""

        class LinkStub:
            def __init__(self, friend, role):
                self._friend = friend
                self.role = role
            def traverse(self):
                return self._friend

        group, member = object(), object()
        links = (LinkStub(group, URIGroup), LinkStub(member, URIMember))

        e = MemberAddedEvent(links)
        verifyObject(IMemberAddedEvent, e)
        self.assert_(e.links is links)
        self.assert_(e.member is member)
        self.assert_(e.group is group)

        links = (LinkStub(member, URIMember), LinkStub(group, URIGroup))
        e = MemberRemovedEvent(links)
        verifyObject(IMemberRemovedEvent, e)
        self.assert_(e.links is links)
        self.assert_(e.member is member)
        self.assert_(e.group is group)

        links = (LinkStub(member, URIMember), LinkStub(group, URIUnrelated))
        self.assertRaises(TypeError, MemberAddedEvent, links)

        links = (LinkStub(member, URIGroup), LinkStub(group, URIUnrelated))
        self.assertRaises(TypeError, MemberAddedEvent, links)

        links = (LinkStub(member, URIGroup), LinkStub(group, URIMember),
                 LinkStub(object(), URIMember))
        self.assertRaises(TypeError, MemberAddedEvent, links)

        links = (LinkStub(member, URIGroup), LinkStub(group, URIMember),
                 LinkStub(object(), URIGroup))
        self.assertRaises(TypeError, MemberAddedEvent, links)


class TestMembershipRelate(RelationshipTestMixin, EventServiceTestMixin,
                           unittest.TestCase):

    def test_membershipRelate(self):
        self.setUpEventService()

        from schooltool import membership
        membership.setUp()
        Relatable = lambda: BasicRelatable(self.serviceManager)
        g = Relatable()

        # Test a cycle of a group with itself.
        self.assertRaises(ValueError, membership.Membership,
                          group=g, member=g)

        # Test a two-group cycle.
        g1 = Relatable()
        g2 = Relatable()
        links = membership.Membership(group=g1, member=g2)
        self.assertEquals(links['member'].traverse(), g2)
        self.assertEquals(links['group'].traverse(), g1)
        for events in g1.events, g2.events:
            self.assertEquals(len(events), 1)
            self.assertEquals(type(events[0]), membership.MemberAddedEvent)
        self.assertRaises(ValueError, membership.Membership,
                          group=g2, member=g1)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGroupMixin))
    suite.addTest(unittest.makeSuite(TestMembershipRelationship))
    suite.addTest(unittest.makeSuite(TestMemberMixin))
    suite.addTest(unittest.makeSuite(TestURIs))
    suite.addTest(unittest.makeSuite(TestCyclicConstraint))
    suite.addTest(unittest.makeSuite(TestEvents))
    suite.addTest(unittest.makeSuite(TestMembershipRelate))
    return suite

if __name__ == '__main__':
    unittest.main()
