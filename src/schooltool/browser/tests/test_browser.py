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

from twisted.python.failure import Failure
from zope.interface import directlyProvides
from schooltool.browser.tests import RequestStub
from schooltool.tests.utils import AppSetupMixin

__metaclass__ = type


class ApplicationStub:

    def __init__(self, ticketService):
        from schooltool.interfaces import IServiceManager
        directlyProvides(self, IServiceManager) # avoid global imports
        self.ticketService = ticketService


class TestBrowserRequest(unittest.TestCase):

    def createRequest(self):
        from schooltool.browser import BrowserRequest
        return BrowserRequest(None, True)

    def createRequestWithStubbedAuth(self, auth_cookie, user, ts):
        from schooltool.interfaces import AuthenticationError
        request = self.createRequest()
        request._ts = ts
        app = ApplicationStub(ts)
        request.getApplication = lambda: app
        def authenticate(username, password):
            if username == 'username' and password == 'password':
                request.authenticated_user = user
            else:
                request.authenticated_user = None
                raise AuthenticationError
        request.authenticate = authenticate
        request.getCookie = {'auth': auth_cookie}.get
        return request

    def test_maybeAuthenticate_no_auth(self):
        request = self.createRequest()
        request.maybeAuthenticate()
        self.assert_(request.authenticated_user is None)

    def test_maybeAuthenticate_auth(self):
        from schooltool.auth import TicketService
        ts = TicketService()
        ticket = ts.newTicket(('username', 'password'))
        user = object()
        request = self.createRequestWithStubbedAuth(ticket, user, ts)
        request.maybeAuthenticate()
        self.assert_(request.authenticated_user is user)

    def test_maybeAuthenticate_password_changed(self):
        from schooltool.auth import TicketService
        ts = TicketService()
        ticket = ts.newTicket(('username', 'oldpassword'))
        user = object()
        request = self.createRequestWithStubbedAuth(ticket, user, ts)
        request.maybeAuthenticate()
        self.assert_(request.authenticated_user is None)

    def test_maybeAuthenticate_bad_auth(self):
        from schooltool.auth import TicketService
        ts = TicketService()
        user = object()
        request = self.createRequestWithStubbedAuth('faketicket', user, ts)
        request.maybeAuthenticate()
        self.assert_(request.authenticated_user is None)

    def test_renderInternalError(self):
        rq = self.createRequest()
        # Request does this before calling renderInternalError:
        rq.setResponseCode(500)
        failure = Failure(AttributeError('foo'))
        result = rq.renderInternalError(failure)
        self.assert_(isinstance(result, str))
        self.assert_(rq.code, 500)
        self.assertEqual(rq.headers['content-type'],
                         'text/html; charset=UTF-8')


class TestView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def tearDown(self):
        self.tearDownRegistries()

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

    def test_unauthorized_expired(self):
        from schooltool.browser import View
        view = View(None)
        request = RequestStub('/path')
        result = view.unauthorized(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/?expired=1&url=/path')
        self.assert_('www-authenticate' not in request.headers)

    def test_unauthorized_forbidden(self):
        from schooltool.browser import View
        view = View(None)
        request = RequestStub('/path', authenticated_user='not None')
        result = view.unauthorized(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/?forbidden=1&url=/path')
        self.assert_('www-authenticate' not in request.headers)

    def test_getChild(self):
        view = self.createView()
        request = RequestStub('/path//with/multiple/slashes/')
        self.assert_(view.getChild('', request) is view)

    def test_getChild_not_found(self):
        from schooltool.browser import NotFoundView
        view = self.createView()
        request = RequestStub('/path')
        view2 = view.getChild('nosuchpage', request)
        self.assert_(isinstance(view2, NotFoundView))

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

    def test_isManager(self):
        view = self.createView()
        view.request = RequestStub()
        self.assert_(not view.isManager())
        view.request = RequestStub(authenticated_user=self.person)
        self.assert_(not view.isManager())
        view.request = RequestStub(authenticated_user=self.manager)
        self.assert_(view.isManager())

    def test_isManager(self):
        view = self.createView()
        view.request = RequestStub()
        self.assert_(not view.isTeacher())
        view.request = RequestStub(authenticated_user=self.person)
        self.assert_(not view.isTeacher())
        view.request = RequestStub(authenticated_user=self.teacher)
        self.assert_(view.isTeacher())
        view.request = RequestStub(authenticated_user=self.manager)
        self.assert_(view.isTeacher())


class TestStaticFile(unittest.TestCase):

    def test(self):
        from schooltool.browser import StaticFile
        view = StaticFile('tests/test_browser.py', 'text/plain')
        request = RequestStub()
        result = view.render(request)
        self.assert_(result.startswith('#'))
        self.assertEquals(request.headers['content-type'], 'text/plain')


class TestNotFound(unittest.TestCase):

    def test(self):
        from schooltool.browser import NotFoundView
        view = NotFoundView()
        request = RequestStub(uri='/path')
        result = view.render(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_("Not found: /path" in result)

    def test_notFoundPage(self):
        from schooltool.browser import notFoundPage
        request = RequestStub(uri='/path')
        result = notFoundPage(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assert_("Not found: /path" in result)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBrowserRequest))
    suite.addTest(unittest.makeSuite(TestView))
    suite.addTest(unittest.makeSuite(TestStaticFile))
    suite.addTest(unittest.makeSuite(TestNotFound))
    return suite


if __name__ == '__main__':
    unittest.main()
