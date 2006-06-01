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

from zope.interface import Interface, implements
from zope.testing import doctest
from zope.app.testing import setup, ztapi
from zope.app import zapi
from zope.traversing.interfaces import TraversalError
from zope.component.interfaces import ComponentLookupError
from zope.app.security.interfaces import IAuthentication
from zope.app.container.contained import ObjectAddedEvent

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.testing.setup import setUpLocalGrants
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

    def tearDown(self):
        setup.placefulTearDown()

    def test(self):
        from schooltool.app.security import authSetUpSubscriber
        self.assertRaises(ComponentLookupError, self.app.getSiteManager)
        event = ObjectAddedEvent(self.app)
        authSetUpSubscriber(self.app, event)
        auth = zapi.traverse(self.app, '++etc++site/default/SchoolToolAuth')
        auth1 = zapi.getUtility(IAuthentication, context=self.app)
        self.assert_(auth is auth1)

        # If we fire the event again, it does not fail.  Such events
        # are fired when the object is copied and pasted.
        authSetUpSubscriber(self.app, event)


def doctest_ConfigurableCrowd():
    """Tests for ConfigurableCrowd.

    Some setup:

        >>> class CustomisationsStub(object):
        ...     implements(IAccessControlCustomisations)
        ...     def get(self, key):
        ...         print 'Getting %s' % key
        ...         return True

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication)
        ...     def __conform__(self, iface):
        ...         if iface == IAccessControlCustomisations:
        ...             return CustomisationsStub()

        >>> from zope.component import provideAdapter
        >>> provideAdapter(lambda context: AppStub(),
        ...                adapts=[None],
        ...                provides=ISchoolToolApplication)

        >>> from schooltool.app.security import ConfigurableCrowd

    Off we go:

        >>> crowd = ConfigurableCrowd(object())
        >>> crowd.setting_key = 'key'
        >>> crowd.contains(object())
        Getting key
        True

    """


def doctest_CalendarViewersCrowd():
    """Tests for CalendarViewersCrowd.

        >>> setup.placelessSetUp()

        >>> class CalendarStub:
        ...     def __init__(self, parent):
        ...         self.__parent__ = parent

        >>> from schooltool.app.security import CalendarViewersCrowd
        >>> crowd = CalendarViewersCrowd(CalendarStub(None))

    First, fire a blank (no adapters registered):

        >>> crowd.contains(object())
        False

    OK, let's try with an adaptable object now:

        >>> from schooltool.app.interfaces import ICalendarParentCrowd

        >>> class ParentCrowdStub(object):
        ...     implements(ICalendarParentCrowd)
        ...     def __init__(self, context):
        ...         print 'Getting adapter for %s' % context
        ...     def contains(self, principal):
        ...         print 'Checking %s' % principal
        ...         return True

        >>> class IOwner(Interface):
        ...     pass

        >>> class OwnerStub(object):
        ...     implements(IOwner)

        >>> from zope.component import provideAdapter
        >>> provideAdapter(ParentCrowdStub, adapts=[IOwner],
        ...                provides=ICalendarParentCrowd,
        ...                name='schooltool.view')

    Let's try now with the adapter:

        >>> crowd = CalendarViewersCrowd(CalendarStub(OwnerStub()))
        >>> crowd.contains('some principal')
        Getting adapter for <...OwnerStub ...>
        Checking some principal
        True

    We're done.

        >>> setup.placefulTearDown()

    """


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestAuthSetUpSubscriber),
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
        doctest.DocFileSuite('../security.txt', optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
