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
"""

import unittest
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember

__metaclass__ = type

class MemberStub:
    implements(IGroupMember)

class TestPerson(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IPerson
        from schooltool.model import Person
        person = Person('John Smith')
        verifyObject(IPerson, person)


class TestGroup(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup
        from schooltool.model import Group
        group = Group()
        verifyObject(IGroup, group)

    def test_add(self):
        from schooltool.model import Group
        group = Group()
        member = MemberStub()
        key = group.add(member)
        self.assertEqual(member, group[key])
        self.assertRaises(TypeError, group.add, "not a member")

    def test_remove(self):
        from schooltool.model import Group
        group = Group()
        member = MemberStub()
        key = group.add(member)
        del group[key]
        self.assertRaises(KeyError, group.__getitem__, key)
        self.assertRaises(KeyError, group.__delitem__, key)

    def test_items(self):
        from schooltool.model import Group
        group = Group()
        self.assertEquals(group.keys(), [])
        self.assertEquals(group.values(), [])
        self.assertEquals(group.items(), [])
        member = MemberStub()
        key = group.add(member)
        self.assertEquals(group.keys(), [key])
        self.assertEquals(group.values(), [member])
        self.assertEquals(group.items(), [(key, member)])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    return suite

if __name__ == '__main__':
    unittest.main()
