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
from persistence import Persistent
from zope.interface import Interface, implements
from zope.interface import directlyProvidedBy, directlyProvides
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember, IFacet, IFaceted

__metaclass__ = type

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
    active = False

    def __init__(self, context):
        self.context = context


class TestPerson(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IPerson
        from schooltool.model import Person
        person = Person('John Smith')
        verifyObject(IPerson, person)


class TestGroupMember(unittest.TestCase):

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


class TestGroup(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup
        from schooltool.model import Group
        group = Group("root")
        verifyObject(IGroup, group)
        verifyObject(IGroupMember, group)

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
        from schooltool.adapters import getFacet
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


class TestRootGroup(unittest.TestCase):

    def test_interfaces(self):
        from schooltool.interfaces import IRootGroup
        from schooltool.model import RootGroup
        group = RootGroup("root")
        verifyObject(IRootGroup, group)


class TestPersistentListSet(unittest.TestCase):

    def test(self):
        from schooltool.model import PersistentListSet
        p = PersistentListSet()
        a, b = object(), object()
        p.add(a)
        self.assertEquals(list(p), [a])
        p.add(a)
        self.assertEquals(list(p), [a])
        p.add(b)
        self.assertEquals(list(p), [a, b])
        p.remove(a)
        self.assertEquals(list(p), [b])
        p.add(a)
        self.assertEquals(list(p), [b, a])


class P(Persistent):
    pass

class TestPersistentKeysDict(unittest.TestCase):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def test_setitem(self):
        from schooltool.model import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.assertRaises(TypeError, d.__setitem__, p, 1)
        self.datamgr.add(d)
        d[p] = 2
        self.assert_(p._p_oid)
        self.assertRaises(TypeError, d.__setitem__, ob, 1)

    def test_getitem(self):
        from schooltool.model import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.datamgr.add(d)
        d[p] = 2
        self.assertEqual(d[p], 2)
        self.assertRaises(TypeError, d.__getitem__, object())
        self.assertRaises(KeyError, d.__getitem__, P())

    def test_delitem(self):
        from schooltool.model import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.datamgr.add(d)
        d[p] = 2
        self.assertEqual(d[p], 2)
        del d[p]
        self.assertRaises(KeyError, d.__getitem__, p)
        self.assertRaises(KeyError, d.__delitem__, p)
        self.assertRaises(KeyError, d.__delitem__, P())
        self.assertRaises(TypeError, d.__delitem__, object())

    def test_keys_iter_len(self):
        from schooltool.model import PersistentKeysDict
        ob = object()
        p = P()
        p2 = P()
        d = PersistentKeysDict()
        self.assertRaises(TypeError, d.keys)
        self.assertRaises(TypeError, list, d)
        self.datamgr.add(d)
        d[p] = 2
        d[p2] = 3
        self.assertEqual(d.keys(), [p, p2])
        self.assertEqual(list(d), [p, p2])
        self.assertEqual(len(d), 2)

    def test_contains(self):
        from schooltool.model import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.datamgr.add(d)
        d[p] = 2
        self.assert_(p in d)
        self.assertRaises(TypeError, d.__contains__, object())
        self.assert_(P() not in d)


class TestFacetedMixin(unittest.TestCase):

    def test(self):
        from schooltool.model import FacetedMixin
        from schooltool.interfaces import IFaceted
        m = FacetedMixin()
        verifyObject(IFaceted, m)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestRootGroup))
    suite.addTest(unittest.makeSuite(TestGroupMember))
    suite.addTest(unittest.makeSuite(TestPersistentListSet))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDict))
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    return suite

if __name__ == '__main__':
    unittest.main()
