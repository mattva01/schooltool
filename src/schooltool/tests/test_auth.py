#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.auth

$Id$
"""

import unittest
from sets import Set

from zope.testing.doctestunit import DocTestSuite
from zope.interface.verify import verifyObject
from schooltool.tests.utils import AppSetupMixin

__metaclass__ = type


class TestACL(unittest.TestCase):

    def test(self):
        from schooltool.auth import ACL
        from schooltool.interfaces import IACL

        verifyObject(IACL, ACL())

    def setUp(self):
        from schooltool.auth import ACL
        from schooltool.model import Person
        self.acl = ACL()
        self.person = Person("Steve")
        self.person2 = Person("Mark")

    def test_add(self):
        from schooltool.interfaces import ViewPermission, AddPermission
        from schooltool.interfaces import ModifyPermission
        self.acl.add((self.person, ViewPermission))
        self.assertEquals(self.acl._data[(self.person, ViewPermission)], 1)
        self.assertEquals(len(self.acl._data), 1)
        self.acl.add((self.person2, ModifyPermission))
        self.acl.add((self.person2, AddPermission))
        self.acl.add((self.person2, AddPermission))
        self.assertEquals(len(self.acl._data), 3)
        assert (self.person2, ModifyPermission) in self.acl._data
        assert (self.person2, AddPermission) in self.acl._data
        assert (self.person, ViewPermission) in self.acl._data
        self.assertRaises(ValueError, self.acl.add, (self.person, "Delete"))

    def test_allows_contains(self):
        from schooltool.interfaces import ViewPermission, AddPermission
        from schooltool.interfaces import ModifyPermission, Everybody
        assert (self.person, ViewPermission) not in self.acl
        assert not self.acl.allows(self.person, ViewPermission)
        self.acl.add((self.person, ViewPermission))
        assert (self.person, ViewPermission) in self.acl
        assert self.acl.allows(self.person, ViewPermission)

        self.acl.add((self.person2, ModifyPermission))
        self.acl.add((self.person2, AddPermission))

        assert (self.person2, ModifyPermission) in self.acl
        assert self.acl.allows(self.person2, ModifyPermission)

        self.assertRaises(ValueError, self.acl.allows, self.person, "Delete")
        self.assertRaises(ValueError, self.acl.__contains__,
                          (self.person, "Delete"))

    def testEverybody(self):
        from schooltool.interfaces import ViewPermission
        from schooltool.interfaces import Everybody
        assert not self.acl.allows(self.person, ViewPermission)

        self.acl.add((Everybody, ViewPermission))

        assert self.acl.allows(self.person, ViewPermission)
        assert (self.person, ViewPermission) not in self.acl
        assert (Everybody, ViewPermission) in self.acl
        assert self.acl.allows(Everybody, ViewPermission)
        self.assertEquals(list(iter(self.acl)),
                          [(Everybody, ViewPermission)])

        self.acl.remove((Everybody, ViewPermission))

        assert (Everybody, ViewPermission) not in self.acl
        self.assertEquals(list(iter(self.acl)), [])
        assert not self.acl.allows(Everybody, ViewPermission)
        assert not self.acl.allows(None, ViewPermission)

    def test_iter(self):
        from schooltool.interfaces import ViewPermission
        self.assertEquals(list(self.acl), [])
        self.acl.add((self.person, ViewPermission))
        self.assertEquals(list(self.acl), [(self.person, ViewPermission)])

    def test_delitem(self):
        from schooltool.interfaces import ViewPermission
        self.acl.add((self.person, ViewPermission))
        assert (self.person, ViewPermission) in self.acl._data
        self.acl.remove((self.person, ViewPermission))
        assert (self.person, ViewPermission) not in self.acl._data
        self.assertRaises(ValueError, self.acl.remove, (self.person, "Delete"))
        self.assertRaises(KeyError, self.acl.remove,
                          (self.person, ViewPermission))


class TestHelpers(AppSetupMixin, unittest.TestCase):

    def test_getAcl(self):
        from schooltool.browser.auth import getACL
        from schooltool.component import FacetManager
        assert getACL(self.person) is self.person.acl
        assert getACL(FacetManager(self.person)) is self.person.acl
        assert getACL(self.person.calendar) is self.person.calendar.acl
        assert getACL(self.teachers) is self.teachers.acl

    def test_getAncestorGroups(self):
        from schooltool.browser.auth import getAncestorGroups
        from schooltool.interfaces import ViewPermission
        from schooltool.membership import Membership
        self.assertEquals(getAncestorGroups(self.teacher),
                          Set([self.teachers, self.root]))

        g1 = self.app['groups'].new('g1')
        g21 = self.app['groups'].new('g21')
        g22 = self.app['groups'].new('g22')
        g3 = self.app['groups'].new('g3')
        unrelated = self.app['groups'].new('unrelated')

        Membership(group=self.root, member=g1)
        Membership(group=g1, member=g21)
        Membership(group=g1, member=g22)
        Membership(group=g21, member=g3)
        Membership(group=g22, member=g3)
        Membership(group=g22, member=unrelated)

        self.assertEquals(getAncestorGroups(g3),
                          Set([self.root, g1, g21, g22]))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestACL))
    suite.addTest(unittest.makeSuite(TestHelpers))
    suite.addTest(DocTestSuite('schooltool.auth'))
    return suite


if __name__ == '__main__':
    unittest.main()
