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
Unit tests for schooltool.browser.applog

$Id$
"""

import unittest
from StringIO import StringIO

from schooltool.browser.tests import RequestStub, setPath

__metaclass__ = type


class ApplicationStub:
    pass


class SiteStub:
    applog_path = 'anywhere'


class TestAppLog(unittest.TestCase):

    def setUp(self):
        from schooltool.browser.applog import ApplicationLogView
        app = ApplicationStub()
        setPath(app, '/')
        self.view = ApplicationLogView(app)
        self.view.authorization = lambda x, y: True
        self.view.openLog = lambda fn: StringIO("defaced\nby\nevil\nhackers")

    def test(self):
        request = RequestStub()
        request.site = SiteStub()

        contents = self.view.render(request)
        self.assert_("Application log" in contents)
        self.assert_("defaced" in contents)
        self.assert_("hackers" in contents)

    def test_page(self):
        request = RequestStub(args={'page': '2'})
        request.site = SiteStub()

        self.view.pagesize = 2
        contents = self.view.render(request)
        self.assert_("Application log" in contents)
        self.assert_("defaced" not in contents)
        self.assert_("hackers" in contents)

    def test_page_invalid(self):
        request = RequestStub(args={'page': 'b0rk'})
        request.site = SiteStub()

        self.view.pagesize = 2
        contents = self.view.render(request)
        self.assert_("Application log" in contents)
        self.assert_("defaced" not in contents)
        self.assert_("hackers" not in contents)
        self.assert_("Invalid value for 'page' parameter" in contents)

    def test_filter_str(self):
        request = RequestStub(args={'filter': 'vi'})
        request.site = SiteStub()

        contents = self.view.render(request)
        self.assert_("Application log" in contents)
        self.assert_("defaced" not in contents)
        self.assert_("evil" in contents)
        self.assert_("hackers" not in contents)

    def test_prev_filter_str(self):
        request = RequestStub(args={'page': '1',
                                    'prev_filter': 'vi',
                                    'filter': 'e'})
        request.site = SiteStub()

        self.view.pagesize = 1
        contents = self.view.render(request)
        self.assert_("Application log" in contents)
        self.assert_("defaced" not in contents)
        self.assert_("evil" not in contents)
        self.assert_("hackers" in contents)

    def test_nextPageURL(self):
        request = RequestStub(args={'page':'1'})
        request.site = SiteStub()
        self.view.pagesize = 1

        contents = self.view.render(request)
        self.view.request = request
        url = self.view.nextPageURL()
        self.assertEquals(url, 'http://localhost:7001/applog?page=2')

    def test_nextPageURL_last(self):
        request = RequestStub(args={'page':'-1'})
        request.site = SiteStub()

        contents = self.view.render(request)
        self.view.request = request
        url = self.view.nextPageURL()
        self.assertEquals(url, None)

    def test_prevPageURL(self):
        request = RequestStub(args={'page':'3'})
        request.site = SiteStub()
        self.view.pagesize = 1

        contents = self.view.render(request)
        self.view.request = request
        url = self.view.prevPageURL()
        self.assertEquals(url, 'http://localhost:7001/applog?page=2')

    def test_prevPageURL_first(self):
        request = RequestStub(args={'page':'1'})
        request.site = SiteStub()

        contents = self.view.render(request)
        self.view.request = request
        url = self.view.prevPageURL()
        self.assertEquals(url, None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppLog))
    return suite


if __name__ == '__main__':
    unittest.main()
