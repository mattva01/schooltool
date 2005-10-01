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
Tests for scholltool.app.rest.acl

$Id$
"""

import unittest
from StringIO import StringIO

from zope.publisher.browser import TestRequest
from zope.app.testing import setup, ztapi

from schooltool.app.rest.testing import XMLCompareMixin
from schooltool.testing import setup as sbsetup


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
        from schooltool.relationship.tests import setUpRelationships
        setUpRelationships()

        # SchoolToolApplication
        self.app = sbsetup.setupSchoolToolSite()

        from schooltool.person.person import Person
        self.person = self.app['persons']['joe'] = Person('joe')
        self.app['persons']['ann'] = Person('ann')

        from schooltool.group.group import Group
        self.app['groups']['admins'] = Group('Admins')

        self.registerSpecialGroups()

        # Set some permissions
        from zope.app.securitypolicy.interfaces import \
             IPrincipalPermissionManager

        perms = IPrincipalPermissionManager(self.person)
        perms.grantPermissionToPrincipal('schooltool.edit', 'sb.person.joe')
        perms.grantPermissionToPrincipal('schooltool.view',
                                         'zope.unauthenticated')

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

    def test_GET(self):
        from schooltool.app.rest.acl import ACLView, ACLAdapter
        view = ACLView(ACLAdapter(self.person), TestRequest())

        # Let's limit the list of permissions so the output is shorter
        view.permissions = [('schooltool.view', 'View'),
                            ('schooltool.edit', 'Edit')]

        result = view.GET()
        expected = """
            <acl xmlns="http://schooltool.org/ns/model/0.1">
              <principal id="zope.authenticated">
                 <permission id="schooltool.view"/>
                 <permission id="schooltool.edit"/>
              </principal>
              <principal id="zope.unauthenticated">
                 <permission id="schooltool.view" setting="on"/>
                 <permission id="schooltool.edit"/>
              </principal>
              <principal id="sb.group.admins">
                <permission id="schooltool.view"/>
                <permission id="schooltool.edit"/>
              </principal>
              <principal id="sb.person.ann">
                <permission id="schooltool.view"/>
                <permission id="schooltool.edit"/>
              </principal>
              <principal id="sb.person.joe">
                <permission id="schooltool.view"/>
                <permission id="schooltool.edit" setting="on"/>
              </principal>
            </acl>
            """
        self.assertEqualsXML(result, expected)

    def test_POST(self):
        from schooltool.app.rest.acl import ACLView, ACLAdapter
        from zope.app.securitypolicy.interfaces import \
             IPrincipalPermissionManager

        # We need to test these cases:
        # 1. The principal had a permission and it was posted -- do nothing
        # 2. The principal had a permission but it was not posted -- unset
        # 3. The principal did not have a permission and it was posted --
        #    grant
        # 4. The principal did not have a permission and it was not posted --
        #    no change
        # 5. The principal had some permissions, but was not mentioned --
        #    no change

        # These have to do with inheriting permissions:

        # 6. Permission granted on parent but unchecked on context -- deny
        # 7. Permission granted on parent and granted on context -- unset
        # 8. Permission unset on parent and unset on context -- see 2, 4.

        perms = IPrincipalPermissionManager(self.person)
        grant = perms.grantPermissionToPrincipal
        grant('schooltool.edit', 'sb.person.joe')
        grant('schooltool.view', 'zope.unauthenticated')
        grant('schooltool.view', 'sb.group.admins')

        parentperms = IPrincipalPermissionManager(self.person.__parent__)
        pgrant = parentperms.grantPermissionToPrincipal
        pgrant('schooltool.edit', 'sb.person.joe')
        pgrant('schooltool.edit', 'sb.person.ann')

        body = """
            <acl xmlns="http://schooltool.org/ns/model/0.1">

              <principal id="zope.unauthenticated">
                <!-- 1. no change -->
                <permission id="schooltool.view" setting="on"/>
                <!-- 4. schooltool.edit remains unset -->
              </principal>

              <principal id="sb.person.joe">
                <!-- 2. remove schooltool.view -->
                <!-- 6. deny inherited schooltool.edit -->
              </principal>

              <principal id="sb.person.ann">
                <!-- 3. add schooltool.view -->
                <permission id="schooltool.view" setting="on"/>
                <!-- 7. unset inherited schooltool.edit -->
                <permission id="schooltool.edit" setting="on"/>
              </principal>

              <!--   5. sb.groups.admins is not mentioned -->
            </acl>
        """
        view = ACLView(ACLAdapter(self.person), TestRequest(StringIO(body)))

        # Let's limit the list of permissions so the output is shorter
        view.permissions = [('schooltool.view', 'View'),
                            ('schooltool.edit', 'Edit')]

        view.POST()

        result = view.GET()
        expected = """
            <acl xmlns="http://schooltool.org/ns/model/0.1">
              <principal id="zope.authenticated">
                 <permission id="schooltool.view"/>
                 <permission id="schooltool.edit"/>
              </principal>
              <principal id="zope.unauthenticated">
                 <permission id="schooltool.view" setting="on"/>
                 <permission id="schooltool.edit"/>
              </principal>
              <principal id="sb.group.admins">
                <permission id="schooltool.view" setting="on"/>
                <permission id="schooltool.edit"/>
              </principal>
              <principal id="sb.person.ann">
                <permission id="schooltool.view" setting="on"/>
                <permission id="schooltool.edit"  setting="on"/>
              </principal>
              <principal id="sb.person.joe">
                <permission id="schooltool.view"/>
                <permission id="schooltool.edit"/>
              </principal>
            </acl>
            """
        self.assertEqualsXML(result, expected)

        # Check cases 6 and 7
        from zope.app.security.settings import Deny, Unset
        self.assertEqual(perms.getSetting('schooltool.edit', 'sb.person.ann'),
                         Unset)
        self.assertEqual(perms.getSetting('schooltool.edit', 'sb.person.joe'),
                         Deny)

    def test_parseData(self):
        from schooltool.app.rest.acl import ACLView, ACLAdapter
        body = """
            <acl xmlns="http://schooltool.org/ns/model/0.1">
              <principal id="sb.person.ann">
                <permission id="schooltool.view" setting="on"/>
              </principal>
              <principal id="sb.person.joe">
                <permission id="schooltool.view" setting="on"/>
                <permission id="schooltool.edit" setting="on"/>
                <permission id="schooltool.create" setting="on"/>
                <permission id="schooltool.addEvents"/>
              </principal>
            </acl>
        """
        view = ACLView(ACLAdapter(self.person), TestRequest())

        data = view.parseData(body)
        self.assertEquals(data, {'sb.person.ann': ['schooltool.view'],
                                 'sb.person.joe': ['schooltool.view',
                                                   'schooltool.edit',
                                                   'schooltool.create']})

    def test_parseData_errors(self):
        from schooltool.app.rest.acl import ACLView, ACLAdapter
        from schooltool.app.rest.errors import RestError
        view = ACLView(ACLAdapter(self.person), TestRequest())

        body = """<acl xmlns="http://schooltool.org/ns/model/0.1">
                   <principal id="zope.anonymous">
                     <permission id="schooltool.view" setting="on"/>
                   </principal>
                  </acl>"""
        self.assertRaises(RestError, view.parseData, body)

        body = """<acl xmlns="http://schooltool.org/ns/model/0.1">
                   <principal id="sb.person.joe">
                     <permission id="zope.ManageContent" setting="on"/>
                   </principal>
                  </acl>"""
        self.assertRaises(RestError, view.parseData, body)


def test_suite():
    suite = unittest.TestSuite([
        unittest.makeSuite(TestAclView)
        ])
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
