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
Unit tests for schooltool.security

$Id$
"""

import unittest
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.tests.utils import AppSetupMixin, RegistriesSetupMixin


__metaclass__ = type


class TestSecurity(AppSetupMixin, unittest.TestCase):

    def test_interface(self):
        from schooltool.security import SecurityPolicy
        from schooltool.security import ISecurityPolicy
        verifyObject(ISecurityPolicy, SecurityPolicy(self.person))

    def test_canBook(self):
        from schooltool.security import SecurityPolicy
        from schooltool.interfaces import AddPermission, ModifyPermission
        from schooltool.interfaces import ViewPermission

        # The manager can book anything
        policy =  SecurityPolicy(self.manager)
        self.assertEquals(policy.canBook(self.person2, self.location), True)

        # The user has to have the add permission for both the resource's
        # and the owner's calendar.
        user = self.person
        owner = self.person2
        policy =  SecurityPolicy(user)
        self.assertEquals(policy.canBook(owner, self.location), False)

        self.location.calendar.acl.add((user, AddPermission))
        self.assertEquals(policy.canBook(owner, self.location), False)

        self.person2.calendar.acl.add((user, AddPermission))
        self.assertEquals(policy.canBook(owner, self.location), True)

        self.location.calendar.acl.remove((user, AddPermission))
        self.assertEquals(policy.canBook(owner, self.location), False)

    def test_canModifyBooking(self):
        from schooltool.security import SecurityPolicy
        from schooltool.interfaces import AddPermission, ModifyPermission
        from schooltool.interfaces import ViewPermission

        # The manager can modify anything
        policy =  SecurityPolicy(self.manager)
        self.assertEquals(policy.canModifyBooking(self.person2, self.location),
                          True)

        # The user has to have the modify permission for both the resource's
        # and the owner's calendar.
        user = self.person
        owner = self.person2
        policy =  SecurityPolicy(user)
        self.assertEquals(policy.canModifyBooking(owner, self.location), False)

        self.location.calendar.acl.add((user, ModifyPermission))
        self.assertEquals(policy.canModifyBooking(owner, self.location), False)

        self.person2.calendar.acl.add((user, ModifyPermission))
        self.assertEquals(policy.canModifyBooking(owner, self.location), True)

        self.location.calendar.acl.remove((user, ModifyPermission))
        self.assertEquals(policy.canModifyBooking(owner, self.location), False)


class TestHelpers(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        import schooltool.membership
        from schooltool.membership import Membership
        from schooltool.model import Person, Group
        from schooltool.app import Application, ApplicationObjectContainer
        self.setUpRegistries()
        schooltool.membership.setUp()

        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)

        self.teachers_group = app['groups'].new('teachers')
        self.managers_group = app['groups'].new('managers')

        self.simpleuser = app['persons'].new('simpleuser')
        self.otheruser = app['persons'].new('otheruser')
        self.teacher = app['persons'].new('teacher')
        self.manager = app['persons'].new('manager')

        Membership(group=self.teachers_group, member=self.teacher)
        Membership(group=self.managers_group, member=self.manager)

    def test_isManager(self):
        from schooltool.rest.auth import isManager
        self.assertEquals(isManager(None), False)
        self.assertEquals(isManager(self.simpleuser), False)
        self.assertEquals(isManager(self.teacher), False)
        self.assertEquals(isManager(self.manager), True)

    def test_isTeacher(self):
        from schooltool.rest.auth import isTeacher
        self.assertEquals(isTeacher(None), False)
        self.assertEquals(isTeacher(self.simpleuser), False)
        self.assertEquals(isTeacher(self.teacher), True)
        self.assertEquals(isTeacher(self.manager), True)

    def test_getOwner(self):
        from schooltool.rest.auth import getOwner
        from schooltool.interfaces import ILocation, IApplicationObject

        class ObjectStub:
            implements(ILocation)

            def __init__(self, parent, name='foo'):
                self.__parent__ = parent
                self.__name__ = name

        class PersonStub(ObjectStub):
            implements(IApplicationObject)

        a = ObjectStub(None)
        b = PersonStub(a)
        c = ObjectStub(b)

        self.assertEquals(getOwner(None), None)
        self.assertEquals(getOwner(a), None)
        self.assertEquals(getOwner(b), b)
        self.assertEquals(getOwner(c), b)
        self.assertEquals(getOwner('foo'), None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSecurity))
    suite.addTest(unittest.makeSuite(TestHelpers))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
