#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for schooltool.views.applog

$Id$
"""

import unittest
from StringIO import StringIO
from schooltool.views.tests import RequestStub

__metaclass__ = type


class TestApplicationLogView(unittest.TestCase):

    def setUp(self):
        from schooltool.views.applog import ApplicationLogView
        self.view = ApplicationLogView(None)
        self.view.authorization = lambda ctx, rq: True
        self.view.openLog = lambda f: StringIO('y00 h4v3 b33n 0wn3d')
        self.request = RequestStub()
        class SiteStub:
            applog_path = 'whatever'
        self.request.site = SiteStub()

    def test(self):
        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'], "text/plain")
        self.assertEquals(result, 'y00 h4v3 b33n 0wn3d')

        self.request.site.applog_path = None
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

    def testFilter(self):
        self.view.openLog = lambda f: StringIO("cut\nfit\ndog\nbit\nkite")
        self.request.args.update({'filter': ['i']})

        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'], "text/plain")
        self.assertEquals(result, 'fit\nbit\nkite')

    def testPaging(self):
        self.view.openLog = lambda f: StringIO("cut\nfit\ndog\nbit\nkite\n")
        self.request.args.update({'filter': [''],
                                  'pagesize': ["2"], 'page': ["-1"]})

        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'], "text/plain")
        self.assertEquals(self.request.headers['x-page'], "3")
        self.assertEquals(self.request.headers['x-total-pages'], "3")
        self.assertEquals(result, 'kite\n')

    def test_getPageRange(self):
        self.assertEquals(self.view.getPageRange(1, 10, 100), (0, 10))
        self.assertEquals(self.view.getPageRange(2, 10, 100), (10, 20))

        # If the last page is incomplete, slice does the right thing
        self.assertEquals(self.view.getPageRange(2, 10, 12), (10, 20))

        # Negative indices mean counting from the end
        self.assertEquals(self.view.getPageRange(-1, 10, 12), (10, 20))
        self.assertEquals(self.view.getPageRange(-2, 10, 12), (0, 10))

        # Out of range gets the last page
        self.assertEquals(self.view.getPageRange(3, 10, 12), (10, 20))
        self.assertEquals(self.view.getPageRange(-3, 10, 12), (0, 10))

    def testErrorZero(self):
        self.request.args.update({'filter': [''],
                                  'pagesize': ["0"], 'page': ["1"]})
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

    def testErrorNonInt(self):
        self.request.args.update({'pagesize': ["1"], 'page': ["one"]})
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplicationLogView))
    return suite

if __name__ == '__main__':
    unittest.main()

