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
Tests for schoolbell.skin.

$Id$
"""
import unittest
from zope.publisher.browser import TestRequest


class TestSchoolBellSubscriber(unittest.TestCase):

    def test(self):
        from schoolbell.app.browser.skin import schoolBellTraverseSubscriber
        from schoolbell.app.browser.skin import ISchoolBellSkin
        from zope.app.publication.zopepublication import BeforeTraverseEvent
        from schoolbell.app.app import SchoolBellApplication
        from schoolbell.app.interfaces import ISchoolBellApplication

        # A non SchoolBellApplication is traversed
        ob = object()
        request = TestRequest()
        ev = BeforeTraverseEvent(ob, request)
        schoolBellTraverseSubscriber(ev)
        self.assert_(not ISchoolBellSkin.providedBy(request))

        # A SchoolBellApplication is traversed
        ob = SchoolBellApplication()
        request = TestRequest()
        ev = BeforeTraverseEvent(ob, request)
        schoolBellTraverseSubscriber(ev)
        self.assert_(ISchoolBellSkin.providedBy(request))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchoolBellSubscriber))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
