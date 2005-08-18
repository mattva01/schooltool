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
from zope.testing import doctest


def doctest_schoolBellTraverseSubscriber():
    """Tests for schoolBellTraverseSubscriber.

    We subscribe to Zope's BeforeTraverseEvent and apply the SchoolBell skin
    whenever an ISchoolToolApplication is traversed during URL traversal.

        >>> from zope.publisher.browser import TestRequest
        >>> from zope.app.publication.zopepublication import BeforeTraverseEvent
        >>> from schoolbell.app.browser.skin import schoolBellTraverseSubscriber
        >>> from schoolbell.app.browser.skin import ISchoolBellSkin
        >>> from schooltool.app.app import SchoolToolApplication

        >>> ob = SchoolToolApplication()
        >>> request = TestRequest()
        >>> ev = BeforeTraverseEvent(ob, request)
        >>> schoolBellTraverseSubscriber(ev)
        >>> ISchoolBellSkin.providedBy(request)
        True

    The skin is, obviously, not applied if you traverse some other object

        >>> ob = object()
        >>> request = TestRequest()
        >>> ev = BeforeTraverseEvent(ob, request)
        >>> schoolBellTraverseSubscriber(ev)
        >>> ISchoolBellSkin.providedBy(request)
        False

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
