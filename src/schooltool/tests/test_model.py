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
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember, IFacet, IFaceted
from schooltool.interfaces import IEventConfigurable
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.utils import EventServiceTestMixin

__metaclass__ = type

class P(Persistent):
    pass

class MemberStub(LocatableEventTargetMixin):
    implements(IGroupMember, IFaceted)

    def __init__(self, parent=None, name='does not matter'):
        LocatableEventTargetMixin.__init__(self, parent, name)
        self.__facets__ = {}
        self.added = None
        self.removed = None

    def notifyAdd(self, group, name):
        self.added = group

    def notifyRemove(self, group):
        self.removed = group

class GroupStub(LocatableEventTargetMixin):
    deleted = None

    def __delitem__(self, key):
        self.deleted = key

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


class TestGroup(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup, IEventTarget
        from schooltool.model import Group
        group = Group("root")
        verifyObject(IGroup, group)
        verifyObject(IGroupMember, group)
        verifyObject(IFaceted, group)
        verifyObject(IEventTarget, group)
        verifyObject(IEventConfigurable, group)

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

    def testQueryLinks(self):
        from schooltool.model import Group
        from schooltool.interfaces import IQueryLinks, URIGroup, URIMember
        from schooltool.interfaces import ISpecificURI
        group = Group("group")
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

        class URIFoo(URIMember):
            "http://example.com/ns/foo"

        for role in (URIGroup, URIFoo):
            links = group.listLinks(role)
            self.assertEqual(links, [], str(role))

        root = Group("root")
        root.add(group)

        links = group.listLinks()
        self.assertEqual(len(links), 2)

        links = group.listLinks(URIMember)
        self.assertEqual(len(links), 1)

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
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    suite.addTest(unittest.makeSuite(TestFacetedEventTargetMixin))
    return suite

if __name__ == '__main__':
    unittest.main()
