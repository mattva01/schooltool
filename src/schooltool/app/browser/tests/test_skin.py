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
Tests for schooltool.app.browser.skin.

$Id$
"""

import unittest
import pprint

from zope.interface import providedBy
from zope.testing import doctest
from zope.app.testing import setup
from zope.publisher.browser import TestRequest
from zope.app.publication.zopepublication import BeforeTraverseEvent

def doctest_CalendarEventViewletManager():
    """Tests for CalendarEventViewletManager.

        >>> from schooltool.app.browser.skin import CalendarEventViewletManager
        >>> from schooltool.app.browser.skin import ICalendarEventContext
        >>> viewletManager = CalendarEventViewletManager(None, None, None)
        >>> ICalendarEventContext.providedBy(viewletManager)
        True

    """

def doctest_schoolToolTraverseSubscriber():
    """Tests for schoolToolTraverseSubscriber.

    We subscribe to Zope's BeforeTraverseEvent and apply the SchoolTool skin
    whenever an ISchoolToolApplication is traversed during URL traversal.

        >>> from schooltool.app.browser.skin import schoolToolTraverseSubscriber
        >>> from schooltool.skin import ISchoolToolSkin
        >>> from schooltool.app.app import SchoolToolApplication

        >>> ob = SchoolToolApplication()
        >>> request = TestRequest()
        >>> ev = BeforeTraverseEvent(ob, request)
        >>> schoolToolTraverseSubscriber(ob, ev)
        >>> ISchoolToolSkin.providedBy(request)
        True
        >>> skin = list(providedBy(request).interfaces())[1]
        >>> skin
        <InterfaceClass schooltool.skin.skin.ISchoolToolSkin>
        >>> pprint.pprint(skin.getBases())
        (<InterfaceClass schooltool.skin.skin.ISchoolToolLayer>,
         <InterfaceClass zope.publisher.interfaces.browser.IDefaultBrowserLayer>)

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
