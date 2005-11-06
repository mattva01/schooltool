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
Tests for infrastructure of restive views.

$Id$
"""
import unittest
from StringIO import StringIO

from zope.interface import Interface, implements
from zope.app.testing.placelesssetup import PlacelessSetup
from zope.app.testing import ztapi
from zope.app.publication.http import HTTPPublication
from zope.publisher.http import HTTPRequest


class Test(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.__env =  {
            'SERVER_URL':         'http://127.0.0.1',
            'HTTP_HOST':          '127.0.0.1',
            'CONTENT_LENGTH':     '0',
            'GATEWAY_INTERFACE':  'TestFooInterface/1.0',
            }

    def test_http(self):
        from schooltool.app.rest import RestPublicationRequestFactory

        factory = RestPublicationRequestFactory(None)
        for method in ('HEAD', 'PUT', 'POST', 'DELETE',
                       'head', 'put', 'post', 'delete',
                       'whatnot'):
            self.__env['REQUEST_METHOD'] = method
            request = factory(StringIO(''), self.__env)
            self.assertEqual(request.__class__, HTTPRequest)
            self.assertEqual(request.publication.__class__, HTTPPublication)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test),
        ))

if __name__=='__main__':
    unittest.main(defaultTest='test_suite')
