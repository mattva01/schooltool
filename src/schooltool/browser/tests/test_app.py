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
Unit tests for schooltool.browser.app

$Id$
"""

import unittest

from schooltool.interfaces import AuthenticationError
from schooltool.browser.tests import TraversalTestMixin, RequestStub, setPath


__metaclass__ = type


class PersonStub:
    __name__ = 'manager'
    title = 'The Mgmt'


class SiteStub:

    def authenticate(self, app, username, password):
        if username == 'manager' and password == 'schooltool':
            person = PersonStub()
            setPath(person, '/persons/manager')
            return person
        else:
            raise AuthenticationError()


class TestAppView(unittest.TestCase, TraversalTestMixin):

    def createView(self):
        from schooltool.app import Application
        from schooltool.app import ApplicationObjectContainer
        from schooltool.model import Person, Group
        from schooltool.browser.app import RootView
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        app['groups'] = ApplicationObjectContainer(Group)
        view = RootView(app)
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assert_('expired' not in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_render_expired(self):
        view = self.createView()
        request = RequestStub('/?expired=1', args={'expired': '1'})
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assert_('expired' in result)
        self.assert_('action="/"' in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_render_with_url(self):
        view = self.createView()
        request = RequestStub(args={'url': '/some/url'})
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assert_('expired' not in result)
        self.assert_('<input type="hidden" name="url" value="/some/url" />'
                     in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_post(self):
        from schooltool.browser.auth import globalTicketService
        view = self.createView()
        request = RequestStub(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool'})
        request.site = SiteStub()
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/start')
        ticket = request._outgoing_cookies['auth']
        username, password = globalTicketService.verifyTicket(ticket)
        self.assertEquals(username, 'manager')
        self.assertEquals(password, 'schooltool')

    def test_post_with_url(self):
        from schooltool.browser.auth import globalTicketService
        view = self.createView()
        request = RequestStub(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool',
                                    'url': '/some/path'})
        request.site = SiteStub()
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/some/path')
        ticket = request._outgoing_cookies['auth']
        username, password = globalTicketService.verifyTicket(ticket)
        self.assertEquals(username, 'manager')
        self.assertEquals(password, 'schooltool')

    def test_post_failed(self):
        view = self.createView()
        request = RequestStub(method='POST',
                              args={'username': 'manager',
                                    'password': '5ch001t001'})
        request.site = SiteStub()
        result = view.render(request)
        self.assert_('error' in result)
        self.assert_('Username' in result)
        self.assert_('manager' in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_traversal(self):
        from schooltool.browser import StaticFile
        from schooltool.browser.app import LogoutView
        from schooltool.browser.app import StartView
        from schooltool.browser.app import PersonContainerView
        from schooltool.browser.app import GroupContainerView
        view = self.createView()
        app = view.context
        self.assertTraverses(view, 'logout', LogoutView, app)
        self.assertTraverses(view, 'persons', PersonContainerView,
                             app['persons'])
        self.assertTraverses(view, 'groups', GroupContainerView, app['groups'])
        css = self.assertTraverses(view, 'schooltool.css', StaticFile)
        self.assertEquals(css.content_type, 'text/css')
        user = object()
        request = RequestStub(authenticated_user=user)
        self.assertTraverses(view, 'start', StartView, user, request=request)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestLogoutView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import LogoutView
        view = LogoutView(None)
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')

    def test_render_with_auth(self):
        from schooltool.interfaces import AuthenticationError
        from schooltool.browser.auth import globalTicketService
        view = self.createView()
        ticket = globalTicketService.newTicket(('usr', 'pwd'))
        request = RequestStub(cookies={'auth': ticket})
        request.authenticate = lambda username, password: None
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')
        self.assertRaises(AuthenticationError,
                          globalTicketService.verifyTicket, ticket)


class TestStartView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import StartView
        from schooltool.model import Person
        user = Person()
        setPath(user, '/persons/user')
        return StartView(user)

    def test(self):
        view = self.createView()
        request = RequestStub(authenticated_user=view.context)
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assertEquals(request.code, 200)


class TestPersonContainerView(unittest.TestCase, TraversalTestMixin):

    def createView(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonContainerView
        return PersonContainerView({'person': Person()})

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_traverse(self):
        from schooltool.browser.model import PersonView
        view = self.createView()
        person = view.context['person']
        self.assertTraverses(view, 'person', PersonView, person)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestGroupContainerView(unittest.TestCase, TraversalTestMixin):

    def createView(self):
        from schooltool.model import Group
        from schooltool.browser.app import GroupContainerView
        return GroupContainerView({'group': Group()})

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_traverse(self):
        from schooltool.browser.model import GroupView
        view = self.createView()
        group = view.context['group']
        self.assertTraverses(view, 'group', GroupView, group)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestLogoutView))
    suite.addTest(unittest.makeSuite(TestStartView))
    suite.addTest(unittest.makeSuite(TestPersonContainerView))
    suite.addTest(unittest.makeSuite(TestGroupContainerView))
    return suite


if __name__ == '__main__':
    unittest.main()
