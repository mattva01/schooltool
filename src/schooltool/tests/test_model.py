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

__metaclass__ = type

class P(Persistent):
    pass

class MemberStub:
    implements(IGroupMember, IFaceted)

    def __init__(self):
        self.__facets__ = {}
        self.added = None
        self.removed = None

    def notifyAdded(self, group, name):
        self.added = group

    def notifyRemoved(self, group):
        self.removed = group

class GroupStub(Persistent):
    deleted = None

    def __delitem__(self, key):
        self.deleted = key

    def add(self, thing):
        self.added = thing
        thing.notifyAdded(self, 'foo')

class FacetStub:
    implements(IFacet)

    def __init__(self, context=None, active=False):
        self.context = context
        self.active = active


class TestPerson(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IPerson, IEventTarget, IRelatable
        from schooltool.model import Person
        person = Person('John Smith')
        verifyObject(IPerson, person)
        verifyObject(IEventTarget, person)
        verifyObject(IEventConfigurable, person)
        verifyObject(IRelatable, person)


class TestGroup(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup, IEventTarget, IRelatable
        from schooltool.model import Group
        group = Group("root")
        verifyObject(IGroup, group)
        verifyObject(IGroupMember, group)
        verifyObject(IFaceted, group)
        verifyObject(IEventTarget, group)
        verifyObject(IEventConfigurable, group)
        verifyObject(IRelatable, group)

    def test_add_group(self):
        from schooltool.model import Group
        group = Group("root")
        member = Group("people")
        key = group.add(member)
        self.assertEqual(member, group[key])
        self.assertEqual(list(member.groups()), [group])


class TestRootGroup(unittest.TestCase):

    def test_interfaces(self):
        from schooltool.interfaces import IRootGroup
        from schooltool.model import RootGroup
        group = RootGroup("root")
        verifyObject(IRootGroup, group)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestRootGroup))
    return suite

if __name__ == '__main__':
    unittest.main()
