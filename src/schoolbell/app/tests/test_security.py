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
Unit tests for schoolbell.app.security

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


class TestAuthSetUpSubscriber(unittest.TestCase):

    def setUp(self):
        from schoolbell.app.app import SchoolBellApplication
        self.root = setup.placefulSetUp(True)
        self.app = SchoolBellApplication()
        self.root['frogpond'] = self.app

    def tearDown(self):
        setup.placefulTearDown()

    def test(self):
        from schoolbell.app.security import authSetUpSubscriber
        self.assertRaises(ComponentLookupError, self.app.getSiteManager)
        event = ObjectAddedEvent(self.app)
        authSetUpSubscriber(event)
        auth = zapi.traverse(self.app, '++etc++site/default/SchoolBellAuth')
        auth1 = zapi.getUtility(IAuthentication, context=self.app)
        self.assert_(auth is auth1)

        # If we fire the event again, it does not fail.  Such events
        # are fired when the object is copied and pasted.
        authSetUpSubscriber(event)


    def test_other_object(self):
        from schoolbell.app.security import authSetUpSubscriber
        event = ObjectAddedEvent(self.root)
        authSetUpSubscriber(event)
        self.assertRaises(TraversalError, zapi.traverse,
                          self.root, '++etc++site/default/SchoolBellAuth')

    def test_other_event(self):
        from schoolbell.app.security import authSetUpSubscriber
        class SomeEvent:
            object = self.app
        authSetUpSubscriber(SomeEvent())
        self.assertRaises(ComponentLookupError, self.app.getSiteManager)
        self.assertRaises(TraversalError, zapi.traverse,
                          self.app, '++etc++site/default/SchoolBellAuth')


def setUpLocalGrants():
    """Set up annotations and AnnotatationPrincipalPermissionManager"""
    from zope.app.annotation.interfaces import IAnnotatable
    from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
    from zope.app.securitypolicy.principalpermission import \
         AnnotationPrincipalPermissionManager
    setup.setUpAnnotations()
    setup.setUpTraversal()
    ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
                         AnnotationPrincipalPermissionManager)


def doctest_personPermissionsSubscriber():
    r"""
    Set up:

        >>> from schoolbell.app.app import SchoolBellApplication, Person, Group
        >>> root = setup.placefulSetUp(True)
        >>> setUpLocalGrants()
        >>> root['sb'] = SchoolBellApplication()

        >>> person = Person('frog', title="Frog")
        >>> root['sb']['persons']['frog'] = person

    Call our subscriber:

        >>> from schoolbell.app.security import personPermissionsSubscriber
        >>> personPermissionsSubscriber(ObjectAddedEvent(person))

    Check that the person has the permissions on self:

        >>> from zope.app.securitypolicy.interfaces import \
        ...     IPrincipalPermissionManager
        >>> map = IPrincipalPermissionManager(person)
        >>> x = map.getPermissionsForPrincipal('sb.person.frog')
        >>> x.sort()
        >>> pprint(x)
        [('schoolbell.addEvent', PermissionSetting: Allow),
         ('schoolbell.controlAccess', PermissionSetting: Allow),
         ('schoolbell.edit', PermissionSetting: Allow),
         ('schoolbell.modifyEvent', PermissionSetting: Allow),
         ('schoolbell.view', PermissionSetting: Allow)]

    Check that no permissions are set if the object added is not a person:

        >>> group = Group('slackers')
        >>> root['sb']['groups']['slackers'] = group
        >>> personPermissionsSubscriber(ObjectAddedEvent(group))
        >>> map = IPrincipalPermissionManager(group)
        >>> map.getPermissionsForPrincipal('sb.group.slackers')
        []

    Clean up:

        >>> setup.placefulTearDown()
    """


def doctest_personPermissionsSubscriber():
    r"""
    Set up:

        >>> from schoolbell.app.app import SchoolBellApplication, Group, Person
        >>> root = setup.placefulSetUp(True)
        >>> setUpLocalGrants()
        >>> root['sb'] = SchoolBellApplication()

        >>> group = Group('slackers')
        >>> root['sb']['groups']['slackers'] = group

    Call our subscriber:

        >>> from schoolbell.app.security import groupPermissionsSubscriber
        >>> groupPermissionsSubscriber(ObjectAddedEvent(group))

    Check that the group has a view permission on self:

        >>> from zope.app.securitypolicy.interfaces import \
        ...     IPrincipalPermissionManager
        >>> map = IPrincipalPermissionManager(group)
        >>> map.getPermissionsForPrincipal('sb.group.slackers')
        [('schoolbell.view', PermissionSetting: Allow)]

    Check that no permissions are set if the object added is not a group:

        >>> person = Person('joe')
        >>> root['sb']['persons']['joe'] = person
        >>> groupPermissionsSubscriber(ObjectAddedEvent(person))
        >>> map = IPrincipalPermissionManager(person)
        >>> map.getPermissionsForPrincipal('sb.person.joe')
        []

    Clean up:

        >>> setup.placefulTearDown()
    """


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestAuthSetUpSubscriber),
        doctest.DocTestSuite()
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
