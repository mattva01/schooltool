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
from zope.interface.verify import verifyObject
from zope.app.tests import setup
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

def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestAuthSetUpSubscriber)
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
