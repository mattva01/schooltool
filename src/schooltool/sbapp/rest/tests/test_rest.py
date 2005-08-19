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
Unit tests for schooltool.sbapp.rest.

$Id$
"""
from StringIO import StringIO

from zope.testing import doctest
import unittest


def doctest_restSchoolBellSubscriber():
    """
    This event subscriber will mark the request with the
    ISchoolBellRequest interface once the SchoolTool application is
    traversed.  This interface will be used in order to override SB
    REST views.

        >>> from schooltool.sbapp.rest import restSchoolBellSubscriber
        >>> from schooltool.sbapp.rest import ISchoolBellRequest
        >>> from zope.app.publication.interfaces import BeforeTraverseEvent
        >>> from zope.publisher.http import HTTPRequest

    On an arbitrary object, the subscriber does nothing:

        >>> context = object()
        >>> request = HTTPRequest(StringIO(), StringIO(), {})
        >>> event = BeforeTraverseEvent(context, request)
        >>> restSchoolBellSubscriber(event)
        >>> ISchoolBellRequest.providedBy(request)
        False

    However, if the object is a SchoolToolApplication, the request is
    marked as an ISchoolBellRequest.

        >>> from schooltool.app.app import SchoolToolApplication
        >>> context = SchoolToolApplication()
        >>> event = BeforeTraverseEvent(context, request)
        >>> restSchoolBellSubscriber(event)
        >>> ISchoolBellRequest.providedBy(request)
        True

    Even if the object is a SchoolToolApplication, the request is
    unchanged if it is a browser request:

        >>> from zope.publisher.browser import TestRequest
        >>> context = SchoolToolApplication()
        >>> request = TestRequest()
        >>> event = BeforeTraverseEvent(context, request)
        >>> restSchoolBellSubscriber(event)
        >>> ISchoolBellRequest.providedBy(request)
        False

    """

def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
