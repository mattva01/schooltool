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
from schooltool.browser.tests import AppSetupMixin
from schooltool.browser.tests import RequestStub
from schooltool.browser.tests import LocatableStub


class TestBrowserAuthPolicies(AppSetupMixin, unittest.TestCase):

    # request.authenticated_user is None when the user is not logged in
    anonymous = None

    def createViewWithPolicy(self, policy):
        class ViewStub:
            authorize = policy
        return ViewStub()

    def assertAllows(self, policy, users, context=None):
        view = self.createViewWithPolicy(policy)
        for user in users:
            request = RequestStub(authenticated_user=user)
            self.assert_(view.authorize(context, request),
                         "%s should allow access for %r"
                         % (view.authorize.__name__, user))

    def assertDenies(self, policy, users, context=None):
        view = self.createViewWithPolicy(policy)
        for user in users:
            request = RequestStub(authenticated_user=user)
            self.assert_(not view.authorize(context, request),
                         "%s should deny access for %r"
                         % (view.authorize.__name__, user))

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
        context = LocatableStub()
        directlyProvides(context, ILocation)
        context.__parent__ = self.person
        self.assertDenies(PrivateAccess,
                          [self.anonymous, self.person2, self.teacher],
                          context)
        self.assertAllows(PrivateAccess, [self.person, self.manager],
                          context)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBrowserAuthPolicies))
    return suite


if __name__ == '__main__':
    unittest.main()
