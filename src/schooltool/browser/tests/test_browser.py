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
        return View(None)

    def createConcreteView(self):
        from schooltool.browser import View
        from schooltool.browser.auth import PublicAccess

        class ConcreteView(View):
            authorization = PublicAccess

            def do_GET(self, request):
                request.setHeader('Content-Type', 'text/plain')
                return "text"

        return ConcreteView(None)

    def test_POST(self):
        view = self.createView()
        view.do_GET = lambda request: 'Something'
        request = RequestStub(method='POST')
        result = view.do_POST(request)
        self.assertEquals(result, 'Something')

    def test_render_no_auth(self):
        view = self.createConcreteView()
        request = RequestStub()
        result = view.render(request)
        self.assert_(request.authenticated_user is None)

    def test_render_auth(self):
        from schooltool.browser.auth import globalTicketService
        from schooltool.interfaces import AuthenticationError
        view = self.createConcreteView()
        ticket = globalTicketService.newTicket(('username', 'password'))
        user = object()

        request = RequestStub(cookies={'auth': ticket})
        def authenticate(username, password):
            if username == 'username' and password == 'password':
                request.authenticated_user = user
            else:
                request.authenticated_user = None
                raise AuthenticationError
        request.authenticate = authenticate

        result = view.render(request)
        self.assert_(request.authenticated_user is user)

    def test_render_bad_auth(self):
        from schooltool.browser.auth import globalTicketService
        from schooltool.interfaces import AuthenticationError
        view = self.createConcreteView()
        ticket = globalTicketService.newTicket(('username', 'password'))
        user = object()

        request = RequestStub(cookies={'auth': ticket})
        def authenticate(username, password):
            if username == 'username' and password == 'new':
                request.authenticated_user = user
            else:
                request.authenticated_user = None
                raise AuthenticationError
        request.authenticate = authenticate

        result = view.render(request)
        self.assert_(request.authenticated_user is None)

    def test_render_password_changed(self):
        view = self.createConcreteView()

        request = RequestStub(cookies={'auth': 'faketicket'})
        def authenticate(username, password):
            request.authenticated_user = None
            raise AuthenticationError
        request.authenticate = authenticate

        result = view.render(request)
        self.assert_(request.authenticated_user is None)

    def test_unauthorized(self):
        from schooltool.browser import View
        view = View(None)
        request = RequestStub('/path')
        result = view.unauthorized(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/?expired=1&url=/path')
        self.assert_('www-authenticate' not in request.headers)

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

    def test_redirect_not_absolute(self):
        view = self.createView()
        request = RequestStub()
        result = view.redirect('/sublocation', request)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/sublocation')
        self.assertEquals(request.headers['content-type'],
                          'text/html; charset=UTF-8')
        self.assert_('http://localhost:7001/sublocation' in result)

    def test_redirect_no_slash(self):
        view = self.createView()
        request = RequestStub()
        result = view.redirect('sublocation', request)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/sublocation')
        self.assertEquals(request.headers['content-type'],
                          'text/html; charset=UTF-8')
        self.assert_('http://localhost:7001/sublocation' in result)

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
