#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.browser

$Id$
"""

import unittest

from schooltool.browser.tests import RequestStub


class TestView(unittest.TestCase):

    def createView(self):
        from schooltool.browser import View
        view = View(None)
        return view

    def test_POST(self):
        view = self.createView()
        view.do_GET = lambda request: 'Something'
        request = RequestStub(method='POST')
        result = view.do_POST(request)
        self.assertEquals(result, 'Something')

    def test_authorization(self):
        view = self.createView()
        request = RequestStub(method='POST')
        self.assert_(view.authorization(view.context, request))

    def test_getChild(self):
        view = self.createView()
        request = RequestStub('/path//with/multiple/slashes/')
        self.assert_(view.getChild('', request) is view)

    def test_redirect(self):
        view = self.createView()
        request = RequestStub()
        result = view.redirect('http://example.com/', request)
        self.assertEquals(request.headers['location'], 'http://example.com/')
        self.assertEquals(request.headers['content-type'],
                          'text/html; charset=UTF-8')
        self.assert_('http://example.com/' in result)

    def test_macros(self):
        view = self.createView()
        self.assert_('page' in view.macros)


class TestStaticFile(unittest.TestCase):

    def test(self):
        from schooltool.browser import StaticFile
        view = StaticFile('tests/test_browser.py', 'text/plain')
        request = RequestStub()
        result = view.render(request)
        self.assert_(result.startswith('#'))
        self.assertEquals(request.headers['content-type'], 'text/plain')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestView))
    suite.addTest(unittest.makeSuite(TestStaticFile))
    return suite

if __name__ == '__main__':
    unittest.main()
