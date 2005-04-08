#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Tests for schollbell.rest.acl

$Id$
"""

import unittest
from StringIO import StringIO
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.app.testing import setup, ztapi
from zope.app.traversing.interfaces import IContainmentRoot
from schoolbell.app.rest.tests.utils import XMLCompareMixin, QuietLibxml2Mixin
from schoolbell.app.rest.xmlparsing import XMLDocument, XMLParseError


class TestAclView(unittest.TestCase, XMLCompareMixin):

    def setUp(self):
        # Local grants:
        from zope.app.annotation.interfaces import IAnnotatable
        from zope.app.securitypolicy.interfaces import \
                                IPrincipalPermissionManager
        from zope.app.securitypolicy.principalpermission import \
                                AnnotationPrincipalPermissionManager
        setup.placefulSetUp()
        setup.setUpAnnotations()
        setup.setUpTraversal()
        ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
                             AnnotationPrincipalPermissionManager)

        # Security policy
        from zope.security.management import setSecurityPolicy
        from zope.app.securitypolicy.zopepolicy import ZopeSecurityPolicy
        setSecurityPolicy(ZopeSecurityPolicy)

        # Relationships
        from schoolbell.relationship.tests import setUpRelationships
        setUpRelationships()

        # SchoolBellApplication
        from schoolbell.app.rest.app import ApplicationView
        from schoolbell.app.app import SchoolBellApplication, Person, Group
        from schoolbell.app.security import setUpLocalAuth
        from zope.app.component.hooks import setSite
        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)
        setUpLocalAuth(self.app)
        setSite(self.app)

        self.person = self.app['persons']['joe'] = Person('joe')
        self.app['persons']['ann'] = Person('ann')
        self.app['groups']['admins'] = Group('Admins')

    def tearDown(self):
        setup.placefulTearDown()

    def registerSpecialGroups(self):
        """Register the authenticated and unauthenticated groups"""
        from zope.app.security.interfaces import IAuthentication
        from zope.app.security.interfaces import IAuthenticatedGroup
        from zope.app.security.interfaces import IUnauthenticatedGroup
        from zope.app.security.principalregistry import UnauthenticatedGroup
        from zope.app.security.principalregistry import AuthenticatedGroup
        unauthenticated = UnauthenticatedGroup('zope.unauthenticated',
                                               'Unauthenticated users',
                                               '')
        ztapi.provideUtility(IUnauthenticatedGroup, unauthenticated)
        authenticated = AuthenticatedGroup('zope.authenticated',
                                           'Authenticated users',
                                           '')
        ztapi.provideUtility(IAuthenticatedGroup, authenticated)

        from zope.app.security.principalregistry import principalRegistry
        ztapi.provideUtility(IAuthentication, principalRegistry)
        principalRegistry.registerGroup(unauthenticated)
        principalRegistry.registerGroup(authenticated)


    def test_render(self):
        from schoolbell.app.rest.acl import ACLView
        from zope.app.securitypolicy.interfaces import \
             IPrincipalPermissionManager

        perms = IPrincipalPermissionManager(self.person)
        perms.grantPermissionToPrincipal('schoolbell.edit', 'sb.person.joe')
        perms.grantPermissionToPrincipal('schoolbell.view',
                                         'zope.unauthenticated')
        self.registerSpecialGroups()

        view = ACLView(self.person, TestRequest())

        # Let's limit the list of permissions so the output is shorter
        view.permissions = [('schoolbell.view', 'View'),
                            ('schoolbell.edit', 'Edit')]

        result = view.GET()
        expected = """
            <acl xmlns="http://schooltool.org/ns/model/0.1">
              <principal id="zope.authenticated">
                 <permission id="schoolbell.view"/>
                 <permission id="schoolbell.edit"/>
              </principal>
              <principal id="zope.unauthenticated">
                 <permission id="schoolbell.view" setting="on"/>
                 <permission id="schoolbell.edit"/>
              </principal>
              <principal id="sb.group.admins">
                <permission id="schoolbell.view"/>
                <permission id="schoolbell.edit"/>
              </principal>
              <principal id="sb.person.ann">
                <permission id="schoolbell.view"/>
                <permission id="schoolbell.edit"/>
              </principal>
              <principal id="sb.person.joe">
                <permission id="schoolbell.view"/>
                <permission id="schoolbell.edit" setting="on"/>
              </principal>
            </acl>
            """
        self.assertEqualsXML(result, expected)


def test_suite():
    suite = unittest.TestSuite([
        unittest.makeSuite(TestAclView)
        ])
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
