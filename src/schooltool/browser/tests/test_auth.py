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
Unit tests for schooltool.browser.auth

$Id$
"""

import unittest
from zope.interface import directlyProvides
from schooltool.browser.tests import RequestStub
from schooltool.browser.tests import LocationStub
from schooltool.tests.utils import AppSetupMixin


class AuthPolicyTestMixin(object):

    # request.authenticated_user is None when the user is not logged in
    anonymous = None

    def createViewWithPolicy(self, policy):
        class ViewStub:
            authorize = policy
        return ViewStub()

    def policyName(self, policy):
        if isinstance(policy, staticmethod):
            return self.createViewWithPolicy(policy).authorize.__name__
        else:
            return policy.__class__.__name__

    def assertAllows(self, policy, users, context=None):
        view = self.createViewWithPolicy(policy)
        name = self.policyName(policy)
        for user in users:
            request = RequestStub(authenticated_user=user)
            self.assert_(view.authorize(context, request),
                         "%s should allow access for %r" % (name, user))

    def assertDenies(self, policy, users, context=None):
        view = self.createViewWithPolicy(policy)
        name = self.policyName(policy)
        for user in users:
            request = RequestStub(authenticated_user=user)
            self.assert_(not view.authorize(context, request),
                         "%s should deny access for %r" % (name, user))


class TestBrowserAuthPolicies(AuthPolicyTestMixin, AppSetupMixin,
                              unittest.TestCase):

    def test_PublicAccess(self):
        from schooltool.browser.auth import PublicAccess
        self.assertAllows(PublicAccess,
                          [self.anonymous, self.person, self.person2,
                           self.teacher, self.manager])

    def test_AuthenticatedAccess(self):
        from schooltool.browser.auth import AuthenticatedAccess
        self.assertDenies(AuthenticatedAccess, [self.anonymous])
        self.assertAllows(AuthenticatedAccess,
                          [self.person, self.person2, self.teacher,
                           self.manager])

    def test_TeacherAccess(self):
        from schooltool.browser.auth import TeacherAccess
        self.assertDenies(TeacherAccess,
                          [self.anonymous, self.person, self.person2])
        self.assertAllows(TeacherAccess, [self.teacher, self.manager])

    def test_ManagerAccess(self):
        from schooltool.browser.auth import ManagerAccess
        self.assertDenies(ManagerAccess,
                          [self.anonymous, self.person, self.person2,
                           self.teacher])
        self.assertAllows(ManagerAccess, [self.manager])

    def test_PrivateAccess(self):
        from schooltool.interfaces import ILocation
        from schooltool.browser.auth import PrivateAccess
        context = LocationStub(None, self.person)
        self.assertDenies(PrivateAccess,
                          [self.anonymous, self.person2, self.teacher],
                          context)
        self.assertAllows(PrivateAccess, [self.person, self.manager],
                          context)


class TestACLAccess(AppSetupMixin, AuthPolicyTestMixin, unittest.TestCase):

    def test_defaults(self):
        from schooltool.browser.auth import ACLAccess
        from schooltool.interfaces import ViewPermission
        ViewAccess = ACLAccess(ViewPermission)
        self.assertAllows(ViewAccess, [self.person, self.manager],
                          self.person.calendar)
        self.assertDenies(ViewAccess,
                          [self.anonymous, self.person2, self.teacher],
                          self.person.calendar)

    def test(self):
        from schooltool.browser.auth import ACLAccess
        from schooltool.interfaces import ViewPermission
        ViewAccess = ACLAccess(ViewPermission)
        self.person.calendar.acl.add((self.teachers, ViewPermission))
        self.assertAllows(ViewAccess,
                          [self.person, self.manager, self.teacher],
                          self.person.calendar)
        self.assertDenies(ViewAccess,
                          [self.anonymous, self.person2],
                          self.person.calendar)

        self.person.calendar.acl.add((self.person2, ViewPermission))
        self.assertAllows(ViewAccess,
                          [self.person, self.manager,
                           self.teacher, self.person2],
                          self.person.calendar)
        self.assertDenies(ViewAccess, [self.anonymous],
                          self.person.calendar)

    def testGetAcl(self):
        from schooltool.browser.auth import ACLAccess
        from schooltool.interfaces import ViewPermission
        from schooltool.component import FacetManager
        ViewAccess = ACLAccess(ViewPermission)
        self.person.acl.add((self.teachers, ViewPermission))
        self.assertAllows(ViewAccess,
                          [self.manager, self.teacher],
                          FacetManager(self.person))
        self.assertDenies(ViewAccess,
                          [self.anonymous, self.person, self.person2],
                          FacetManager(self.person))
        self.person.acl.add((self.teachers, ViewPermission))

    def test_ACLFooAccess(self):
        from schooltool.browser.auth import ACLViewAccess
        from schooltool.browser.auth import ACLAddAccess
        from schooltool.browser.auth import ACLModifyAccess

        for access in (ACLModifyAccess, ACLAddAccess, ACLViewAccess):
            self.assertAllows(access,
                              [self.person, self.manager],
                              self.person.calendar)
            self.assertDenies(access,
                              [self.anonymous, self.person2, self.teacher],
                              self.person.calendar)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBrowserAuthPolicies))
    suite.addTest(unittest.makeSuite(TestACLAccess))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
