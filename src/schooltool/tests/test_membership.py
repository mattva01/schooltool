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

from persistent import Persistent
from zope.interface.verify import verifyObject
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.utils import AppSetupMixin
from schooltool.tests.test_relationship import Relatable
from schooltool.relationship import RelatableMixin

__metaclass__ = type


class P(Persistent):
    pass


class BasicRelatable(Relatable, RelatableMixin):
    pass


class TestURIs(unittest.TestCase):

    def testURIGroup(self):
        from schooltool.uris import URIGroup
        from schooltool.interfaces import IURIObject
        verifyObject(IURIObject, URIGroup)

    def testURIMember(self):
        from schooltool.uris import URIMember
        from schooltool.interfaces import IURIObject
        verifyObject(IURIObject, URIMember)


class TestMembershipRelationship(RegistriesSetupMixin, EventServiceTestMixin,
                                 unittest.TestCase):

    def test(self):
        from schooltool.component import registerRelationship
        from schooltool.membership import Membership
        from schooltool.uris import URIMembership, URIGroup, URIMember

        cookie = object()
        def handler(reltype, (a, role_of_a), (b, role_of_b), title=None):
            self.assert_(reltype is URIMembership)
            self.assert_((m, URIMember) in [(a, role_of_a), (b, role_of_b)])
            self.assert_((g, URIGroup) in [(a, role_of_a), (b, role_of_b)])
            return (cookie, cookie)

        registerRelationship(URIMembership, handler)

        g, m = BasicRelatable(), BasicRelatable()
        result = Membership(group=g, member=m)
        self.assert_(result['group'] is cookie, "our handler wasn't called")

    def testInterfaces(self):
        from schooltool.component import registerRelationship
        from schooltool.membership import Membership
        from schooltool.interfaces import IRelationshipSchema
        verifyObject(IRelationshipSchema, Membership)


class TestCyclicConstraint(RegistriesSetupMixin, EventServiceTestMixin,
                           unittest.TestCase):

    def testCyclicMembership(self):
        self.setUpEventService()
        # Not bothering to register a relationship especially for membership.
        # Standard relationships will do.
        from schooltool.membership import Membership, checkForPotentialCycles
        from schooltool.component import registerRelationship
        from schooltool.relationship import defaultRelate
        registerRelationship(None, defaultRelate)
        Relatable = lambda: BasicRelatable(self.serviceManager)
        g = Relatable()

        # Test a cycle of a group with itself.
        self.assertRaises(ValueError, checkForPotentialCycles, g, g)

        # Test a two-group cycle.
        #   g1
        #   +-g2
        g1 = Relatable()
        g2 = Relatable()
        checkForPotentialCycles(g1, g2)
        checkForPotentialCycles(g2, g1)
        links = Membership(group=g1, member=g2)
        self.assertEquals(links['member'].traverse(), g2)
        self.assertEquals(links['group'].traverse(), g1)
        self.assertRaises(ValueError, checkForPotentialCycles, g2, g1)
        checkForPotentialCycles(g1, g2)

        # Test a three-group cycle
        #   g1
        #   +-g2
        #     +-g3
        g1 = Relatable()
        g2 = Relatable()
        g3 = Relatable()
        Membership(group=g1, member=g2)
        Membership(group=g2, member=g3)
        self.assertRaises(ValueError, checkForPotentialCycles, g3, g1)
        checkForPotentialCycles(g1, g3)


class TestEvents(unittest.TestCase):

    def testMembershipEvents(self):
        from schooltool.membership import MemberAddedEvent
        from schooltool.membership import MemberRemovedEvent
        from schooltool.interfaces import IMemberAddedEvent
        from schooltool.interfaces import IMemberRemovedEvent
        from schooltool.uris import URIGroup, URIMember, URIObject

        URIUnrelated = URIObject("http://ns.example.org/role/unrelated")

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

    def testBeforeMembershipEvent(self):
        from schooltool.membership import BeforeMembershipEvent
        from schooltool.interfaces import IBeforeMembershipEvent
        group = Relatable()
        member = Relatable()

        event = BeforeMembershipEvent(group, member)
        verifyObject(IBeforeMembershipEvent, event)


class TestMembershipRelate(RegistriesSetupMixin, EventServiceTestMixin,
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
            self.assertEquals(len(events), 2)
            self.assertEquals(type(events[0]),
                              membership.BeforeMembershipEvent)
            self.assertEquals(type(events[1]), membership.MemberAddedEvent)

        # g2 is already a member of g1
        self.assertRaises(ValueError, membership.Membership,
                          group=g2, member=g1)

        # Test a three-group cycle
        g1 = Relatable()
        g2 = Relatable()
        g3 = Relatable()
        membership.Membership(group=g1, member=g2)
        membership.Membership(group=g2, member=g3)
        self.assertRaises(ValueError, membership.Membership,
                          group=g3, member=g1)

        # Check that event listeners can veto the membership by
        # responding to IBeforeMembershipEvent
        from schooltool.interfaces import IBeforeMembershipEvent
        class VetoCaster(BasicRelatable):
            def notify(self, event):
                if IBeforeMembershipEvent.providedBy(event):
                    raise ValueError("Veto!")

        vetoer = VetoCaster(self.serviceManager)
        self.assertRaises(ValueError, membership.Membership,
                          group=vetoer, member=g1)


class TestHelpers(AppSetupMixin, unittest.TestCase):

    def test(self):
        from schooltool.browser.timetable import memberOf
        self.assert_(memberOf(self.person, self.root))
        self.assert_(not memberOf(self.person, self.teachers))


class TestRestictedMembershipPolicy(AppSetupMixin, unittest.TestCase):

    def test(self):
        from schooltool.membership import Membership

        self.app.restrict_membership = True

        Group = self.app['groups'].new
        Person = self.app['persons'].new
        Resource = self.app['resources'].new

        parent2 = Group()
        group = Group()
        member1 = Person('member1')
        member2 = Person('member2')
        member3 = Person('member3')
        resource = Resource('rrr')

        # Can add groups with no worries
        Membership(group=self.root, member=group)
        Membership(group=self.root, member=parent2)
        Membership(group=parent2, member=group)
        Membership(group=parent2, member=Group())

        # Can add persons to root
        Membership(group=self.root, member=member1)
        Membership(group=self.root, member=member3)
        Membership(group=parent2, member=member3)

        # member1 is in root
        Membership(group=group, member=member1)

        # member3 is in parent2
        Membership(group=group, member=member3)

        # member2 is not in root or parent2
        self.assertRaises(ValueError, Membership, group=group, member=member2)

        Membership(group=self.root, member=member2)
        Membership(group=group, member=member2)

        # can add resources
        Membership(group=group, member=resource)

        # if the option if off, I can add whatever I may well please
        self.app.restrict_membership = False
        Membership(group=group, member=Person())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMembershipRelationship))
    suite.addTest(unittest.makeSuite(TestURIs))
    suite.addTest(unittest.makeSuite(TestCyclicConstraint))
    suite.addTest(unittest.makeSuite(TestEvents))
    suite.addTest(unittest.makeSuite(TestMembershipRelate))
    suite.addTest(unittest.makeSuite(TestHelpers))
    suite.addTest(unittest.makeSuite(TestRestictedMembershipPolicy))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
