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
Unit tests for schooltool.app.security

$Id$
"""

import unittest
from pprint import pprint
from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.tests import setup, ztapi
from zope.app import zapi
from zope.app.traversing.interfaces import TraversalError
from zope.component.exceptions import ComponentLookupError
from zope.app.security.interfaces import IAuthentication
from zope.app.container.contained import ObjectAddedEvent

from schooltool.testing.setup import setupLocalGrants

from schooltool.testing import setup as sbsetup


class TestAuthSetUpSubscriber(unittest.TestCase):

    def setUp(self):
        from schooltool.app.app import SchoolToolApplication
        self.root = setup.placefulSetUp(True)
        self.app = SchoolToolApplication()
        self.root['frogpond'] = self.app

        # Authenticated group
        from zope.app.security.interfaces import IAuthenticatedGroup
        from zope.app.security.principalregistry import AuthenticatedGroup
        ztapi.provideUtility(IAuthenticatedGroup,
                             AuthenticatedGroup('zope.authenticated',
                                                'Authenticated users',
                                                ''))
        # Local permission grants for principals
        from zope.app.annotation.interfaces import IAnnotatable
        from zope.app.securitypolicy.interfaces import \
             IPrincipalPermissionManager
        from zope.app.securitypolicy.principalpermission import \
             AnnotationPrincipalPermissionManager
        setup.setUpAnnotations()
        ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
                             AnnotationPrincipalPermissionManager)

    def tearDown(self):
        setup.placefulTearDown()

    def test(self):
        from schooltool.app.security import authSetUpSubscriber
        self.assertRaises(ComponentLookupError, self.app.getSiteManager)
        event = ObjectAddedEvent(self.app)
        authSetUpSubscriber(event)
        auth = zapi.traverse(self.app, '++etc++site/default/SchoolToolAuth')
        auth1 = zapi.getUtility(IAuthentication, context=self.app)
        self.assert_(auth is auth1)

        from zope.app.securitypolicy.interfaces import \
             IPrincipalPermissionManager
        from zope.app.security.settings import Allow
        perms = IPrincipalPermissionManager(self.app)
        self.assert_(('schooltool.view', Allow) in
                     perms.getPermissionsForPrincipal('zope.authenticated'))

        # If we fire the event again, it does not fail.  Such events
        # are fired when the object is copied and pasted.
        authSetUpSubscriber(event)

    def test_other_object(self):
        from schooltool.app.security import authSetUpSubscriber
        event = ObjectAddedEvent(self.root)
        authSetUpSubscriber(event)
        self.assertRaises(TraversalError, zapi.traverse,
                          self.root, '++etc++site/default/SchoolToolAuth')

    def test_other_event(self):
        from schooltool.app.security import authSetUpSubscriber
        class SomeEvent:
            object = self.app
        authSetUpSubscriber(SomeEvent())
        self.assertRaises(ComponentLookupError, self.app.getSiteManager)
        self.assertRaises(TraversalError, zapi.traverse,
                          self.app, '++etc++site/default/SchoolToolAuth')


def doctest_applicationCalendarPermissionsSubscriber():
    r"""
    Set up:

        >>> from schooltool.app.security import \
        ...      applicationCalendarPermissionsSubscriber
        >>> root = setup.placefulSetUp(True)
        >>> sbsetup.setupCalendaring()
        >>> setupLocalGrants()
        >>> st = sbsetup.createSchoolToolApplication()

        >>> root['sb'] = st

        >>> from zope.app.security.interfaces import IUnauthenticatedGroup
        >>> from zope.app.security.principalregistry import UnauthenticatedGroup
        >>> ztapi.provideUtility(IUnauthenticatedGroup,
        ...                      UnauthenticatedGroup('zope.unauthenticated',
        ...                                         'Unauthenticated users',
        ...                                         ''))

        >>> from zope.app.security.interfaces import IAuthenticatedGroup
        >>> from zope.app.security.principalregistry import AuthenticatedGroup
        >>> ztapi.provideUtility(IAuthenticatedGroup,
        ...                      AuthenticatedGroup('zope.authenticated',
        ...                                         'Authenticated users',
        ...                                         ''))

        >>> from zope.app.annotation.interfaces import IAnnotatable
        >>> from zope.app.securitypolicy.interfaces import \
        ...      IPrincipalPermissionManager
        >>> from zope.app.securitypolicy.principalpermission import \
        ...      AnnotationPrincipalPermissionManager
        >>> setup.setUpAnnotations()
        >>> ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
        ...                      AnnotationPrincipalPermissionManager)

    Call our subscriber:

        >>> applicationCalendarPermissionsSubscriber(ObjectAddedEvent(st))

    Check that unauthenticated has only viewCalendar permission on st.calendar:

        >>> from zope.app.securitypolicy.interfaces import \
        ...         IPrincipalPermissionManager
        >>> unauthenticated = zapi.queryUtility(IUnauthenticatedGroup)

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> map = IPrincipalPermissionManager(ISchoolToolCalendar(st))
        >>> print map.getPermissionsForPrincipal(unauthenticated.id)
        [('schooltool.viewCalendar', PermissionSetting: Allow)]

    And has no permissions on the app itself:

        >>> map = IPrincipalPermissionManager(st)
        >>> print map.getPermissionsForPrincipal(unauthenticated.id)
        []

    Check that no permissions are set if the object added is not an app.

        >>> from schooltool.person.person import Person
        >>> person = Person('james')
        >>> root['sb']['persons']['james'] = person
        >>> applicationCalendarPermissionsSubscriber(
        ...     ObjectAddedEvent(person))
        >>> map = IPrincipalPermissionManager(ISchoolToolCalendar(person))
        >>> map.getPermissionsForPrincipal(unauthenticated.id)
        []

    Authenticated users should be allowed to see the application calendar too:

        >>> authenticated = zapi.queryUtility(IAuthenticatedGroup)

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> map = IPrincipalPermissionManager(ISchoolToolCalendar(st))
        >>> print map.getPermissionsForPrincipal(authenticated.id)
        [('schooltool.viewCalendar', PermissionSetting: Allow)]

    Clean up:

        >>> setup.placefulTearDown()
    """


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestAuthSetUpSubscriber),
        doctest.DocTestSuite(),
        doctest.DocFileSuite('../security.txt', optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
