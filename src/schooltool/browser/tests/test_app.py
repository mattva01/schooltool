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
from logging import INFO

from schooltool.interfaces import AuthenticationError
from schooltool.browser.tests import TraversalTestMixin, RequestStub, setPath
from schooltool.tests.utils import EqualsSortedMixin
from datetime import date, time, timedelta

__metaclass__ = type


class PersonStub:
    __name__ = 'manager'
    title = 'The Mgmt'


class TestAppView(unittest.TestCase, TraversalTestMixin):

    def createView(self):
        from schooltool.app import Application
        from schooltool.app import ApplicationObjectContainer
        from schooltool.model import Person, Group, Resource
        from schooltool.browser.app import RootView
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        app['groups'] = ApplicationObjectContainer(Group)
        app['resources'] = ApplicationObjectContainer(Resource)
        view = RootView(app)
        return view

    def createRequestWithAuthentication(self, *args, **kw):
        person = PersonStub()
        setPath(person, '/persons/manager')
        request = RequestStub(*args, **kw)
        def authenticate(username, password):
            if username == 'manager' and password == 'schooltool':
                request.authenticated_user = person
                request.user = username
            else:
                request.authenticated_user = None
                request.user = ''
                raise AuthenticationError
        request.authenticate = authenticate
        return request

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

    def test_render_forbidden(self):
        view = self.createView()
        request = RequestStub('/?forbidden=1', args={'forbidden': '1'})
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('expired' not in result)
        self.assert_('not allowed' in result)
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

    def test_render_already_logged_in(self):
        view = self.createView()
        request = RequestStub(authenticated_user='the_boss')
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/start')

    def test_post(self):
        from schooltool.component import getTicketService
        view = self.createView()
        request = self.createRequestWithAuthentication(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool'})
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/start')
        ticket = request._outgoing_cookies['auth']
        username, password = \
                  getTicketService(view.context).verifyTicket(ticket)
        self.assertEquals(username, 'manager')
        self.assertEquals(password, 'schooltool')

    def test_post_with_url(self):
        from schooltool.component import getTicketService
        view = self.createView()
        request = self.createRequestWithAuthentication(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool',
                                    'url': '/some/path'})
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/some/path')
        ticket = request._outgoing_cookies['auth']
        username, password = \
                  getTicketService(view.context).verifyTicket(ticket)
        self.assertEquals(username, 'manager')
        self.assertEquals(password, 'schooltool')

    def test_post_failed(self):
        view = self.createView()
        request = self.createRequestWithAuthentication(method='POST',
                              args={'username': 'manager',
                                    'password': '5ch001t001'})
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
        from schooltool.browser.app import ResourceContainerView
        from schooltool.browser.app import BusySearchView
        from schooltool.browser.applog import ApplicationLogView
        from schooltool.browser.timetable import TimetableSchemaWizard
        from schooltool.browser.timetable import TimetableSchemaServiceView
        from schooltool.browser.timetable import TimePeriodServiceView

        view = self.createView()
        app = view.context
        self.assertTraverses(view, 'logout', LogoutView, app)
        self.assertTraverses(view, 'applog', ApplicationLogView, app)
        self.assertTraverses(view, 'persons', PersonContainerView,
                             app['persons'])
        self.assertTraverses(view, 'groups', GroupContainerView, app['groups'])
        self.assertTraverses(view, 'resources', ResourceContainerView,
                             app['resources'])
        self.assertTraverses(view, 'busysearch', BusySearchView, app)
        self.assertTraverses(view, 'ttschemas', TimetableSchemaServiceView,
                             app.timetableSchemaService)
        self.assertTraverses(view, 'newttschema', TimetableSchemaWizard,
                             app.timetableSchemaService)
        self.assertTraverses(view, 'time-periods', TimePeriodServiceView,
                             app.timePeriodService)
        css = self.assertTraverses(view, 'schooltool.css', StaticFile)
        self.assertEquals(css.content_type, 'text/css')
        logo = self.assertTraverses(view, 'logo.png', StaticFile)
        self.assertEquals(logo.content_type, 'image/png')
        user = object()
        request = RequestStub(authenticated_user=user)
        self.assertTraverses(view, 'start', StartView, user, request=request)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestLogoutView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import LogoutView
        from schooltool.app import Application
        view = LogoutView(Application())
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')

    def test_render_with_auth(self):
        from schooltool.component import getTicketService
        from schooltool.interfaces import AuthenticationError
        view = self.createView()
        ticket = getTicketService(view.context).newTicket(('usr', 'pwd'))
        request = RequestStub(cookies={'auth': ticket})
        request.authenticate = lambda username, password: None
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/')
        self.assertRaises(AuthenticationError,
                          getTicketService(view.context).verifyTicket, ticket)


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


class TestPersonAddView(unittest.TestCase):

    def createView(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonAddView

        class PersonContainerStub:

            def __init__(self):
                self.persons = []

            def new(self, username, title):
                if username == 'conflict':
                    raise KeyError(username)
                elif username is None:
                    username = 'auto'
                person = Person(title=title)
                person.__name__ = username
                person.__parent__ = self
                self.persons.append(person)
                return person

        self.person_container = PersonContainerStub()
        setPath(self.person_container, '/persons')

        return PersonAddView(self.person_container)

    def test(self):
        view = self.createView()

        request = RequestStub()
        result = view.do_GET(request)
        self.assert_('Add person' in result)

        request = RequestStub(args={'username': 'newbie',
                                    'password': 'foo',
                                    'verify_password': 'foo'})
        result = view.do_POST(request)
        self.assertEquals(request.applog,
                          [(None, u'Object /persons/newbie of type'
                            ' Person created', INFO)])
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/newbie/edit.html')

        persons = self.person_container.persons
        self.assertEquals(len(persons), 1)
        self.assertEquals(persons[0].__name__, 'newbie')
        self.assertEquals(persons[0].title, 'newbie')

    def test_nousername(self):
        view = self.createView()
        request = RequestStub(args={'username': '',
                                    'password': 'foo',
                                    'verify_password': 'foo'})
        result = view.do_POST(request)
        self.assertEquals(request.applog,
                          [(None, u'Object /persons/auto of type'
                            ' Person created', INFO)])
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/auto/edit.html')

        persons = self.person_container.persons
        self.assertEquals(len(persons), 1)
        self.assertEquals(persons[0].__name__, 'auto')
        self.assertEquals(persons[0].title, 'auto')

    def test_errors_invalidnames(self):
        # We're not very i18n friendly by not allowing international
        # symbols in user names.
        for username in ('newbie \xc4\x85', 'new/bie', 'foo\000bar'):
            view = self.createView()
            request = RequestStub(args={'username': username,
                                        'password': 'bar',
                                        'verify_password': 'bar'})
            content = view.do_POST(request)
            self.assert_('Add person' in content)
            self.assert_('Invalid username' in content)

    def test_errors_badpass(self):
        view = self.createView()
        request = RequestStub(args={'username': 'badpass',
                                    'password': 'foo',
                                    'verify_password': 'bar'})
        content = view.do_POST(request)
        self.assert_('Add person' in content)
        self.assert_('Passwords do not match' in content)
        self.assert_('badpass' in content)

    def test_errors_conflict(self):
        view = self.createView()
        request = RequestStub(args={'username': 'conflict',
                                    'password': 'foo',
                                    'verify_password': 'foo'})
        content = view.do_POST(request)
        self.assert_('Add person' in content)
        self.assert_('Username already registered' in content)
        self.assert_('conflict' in content)


class TestObjectContainerView(unittest.TestCase, TraversalTestMixin):

    def setUp(self):
        from schooltool.browser.app import ObjectContainerView

        class ViewStub:

            def __init__(self, context):
                self.context = context

        class AddViewStub:

            def __init__(self, context):
                self.context = context

        # These can be overridden by subclasses.
        self.view = ObjectContainerView
        self.add_view = ViewStub
        self.obj_view = AddViewStub

    def createView(self):
        self.obj = object()
        self.context = {'obj': self.obj}
        view = self.view(self.context)
        view.add_view = self.add_view
        view.obj_view = self.obj_view
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 404)

    def test_traverse(self):
        view = self.createView()
        self.assertTraverses(view, 'obj', self.obj_view, self.obj)
        self.assertTraverses(view, 'add.html', self.add_view, self.context)
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestPersonContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import PersonContainerView, PersonAddView
        from schooltool.browser.model import PersonView
        TestObjectContainerView.setUp(self)
        self.view = PersonContainerView
        self.add_view = PersonAddView
        self.obj_view = PersonView


class TestGroupContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import GroupContainerView, GroupAddView
        from schooltool.browser.model import GroupView
        TestObjectContainerView.setUp(self)
        self.view = GroupContainerView
        self.add_view = GroupAddView
        self.obj_view = GroupView


class TestResourceContainerView(TestObjectContainerView):

    def setUp(self):
        from schooltool.browser.app import ResourceContainerView
        from schooltool.browser.app import ResourceAddView
        from schooltool.browser.model import ResourceView
        TestObjectContainerView.setUp(self)
        self.view = ResourceContainerView
        self.add_view = ResourceAddView
        self.obj_view = ResourceView


class TestObjectAddView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.app import ObjectAddView
        from schooltool.model import ApplicationObjectMixin

        class ObjContainerStub:

            def __init__(self):
                self.objs = []

            def new(self, name, title):
                if name == 'conflict':
                    raise KeyError(name)
                obj = ApplicationObjectMixin(title=title)
                if name is None:
                    name = "auto"
                obj.__name__ = name
                obj.__parent__ = self
                self.objs.append(obj)
                return obj

        self.container = ObjContainerStub()
        setPath(self.container, '/objects')
        return ObjectAddView(self.container)

    def test_GET(self):
        view = self.createView()
        request = RequestStub()
        content = view.do_GET(request)
        self.assert_('Add object' in content)

    def test_POST(self):
        view = self.createView()
        request = RequestStub(args={'name': 'newobj',
                                    'title': 'New \xc4\x85 stuff'})
        content = view.do_POST(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/objects/newobj/edit.html')
        self.assertEquals(request.applog,
                          [(None, u'Object /objects/newobj of type'
                            ' ApplicationObjectMixin created', INFO)])

        self.assertEquals(len(self.container.objs), 1)
        obj = self.container.objs[0]
        self.assertEquals(obj.__name__, 'newobj')
        self.assertEquals(obj.title, u'New \u0105 stuff')

    def test_POST_alt_redirect(self):
        view = self.createView()
        view.redirect_to_edit = False
        request = RequestStub(args={'name': 'newobj',
                                    'title': 'New \xc4\x85 stuff'})
        content = view.do_POST(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/objects/newobj')

    def test_POST_noname(self):
        view = self.createView()
        request = RequestStub(args={'name': '',
                                    'title': ''})
        content = view.do_POST(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/objects/auto/edit.html')
        self.assertEquals(request.applog,
                          [(None, u'Object /objects/auto of type'
                            ' ApplicationObjectMixin created', INFO)])

        self.assertEquals(len(self.container.objs), 1)
        obj = self.container.objs[0]
        self.assertEquals(obj.__name__, 'auto')
        self.assertEquals(obj.title, u'')

    def test_POST_errors(self):
        view = self.createView()
        request = RequestStub(args={'name': 'new/obj', 'title': 'abc'})
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])
        self.assert_('Add object' in content)
        self.assert_('Invalid name' in content)

    def test_POST_conflict(self):
        view = self.createView()
        request = RequestStub(args={'name': 'conflict', 'title': 'foofoobar'})
        content = view.do_POST(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog, [])
        self.assert_('Add object' in content)
        self.assert_('Name already taken' in content)
        self.assert_('conflict' in content)
        self.assert_('foofoobar' in content)


class TestGroupAddView(unittest.TestCase):

    def test(self):
        from schooltool.browser.app import GroupAddView
        view = GroupAddView({})
        self.assertEquals(view.title, "Add group")


class TestResourceAddView(unittest.TestCase):

    def test(self):
        from schooltool.browser.app import ResourceAddView
        view = ResourceAddView({})
        self.assertEquals(view.title, "Add resource")
        self.assertEquals(view.redirect_to_edit, False)


class TestBusySearchView(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from schooltool.model import Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.browser.app import BusySearchView
        app = Application()
        self.app = app
        r = app['resources'] = ApplicationObjectContainer(Resource)
        self.r1 = r.new('r1', title='Resource 1')
        self.r2 = r.new('r2', title='Resource 2')
        self.view = BusySearchView(app)

    def test_allResources(self):
        self.assertEqual(self.view.allResources(), [self.r1, self.r2])

    def test_update(self):
        self.view.request = RequestStub(args={'first': '2004-08-11',
                                              'last': '2004-08-11',
                                              'duration': '30',
                                              'hours': [13, 14]})
        result = self.view.update()
        assert result is None, result

        self.assertEquals(self.view.first, date(2004, 8, 11))
        self.assertEquals(self.view.last, date(2004, 8, 11))
        self.assertEquals(self.view.duration, timedelta(minutes=30))
        self.assertEquals(self.view.hours, [(time(13, 0), timedelta(hours=2))])
        self.assertEqualsSorted(self.view.resources, [self.r1, self.r2])

    def test_render(self):
        request = RequestStub(args={}, authenticated_user=self.r1)
        result = self.view.render(request)
        assert 'Resource 1' in result, result
        assert 'Search' in result

        request = RequestStub(args={'first': '2004-08-11',
                                    'last': '2004-08-11',
                                    'duration': '30',
                                    'hours': [13, 14]},
                              authenticated_user=self.r1)
        result = self.view.render(request)
        assert 'Resource 1' in result, result
        assert 'Search' in result
        assert 'Book' in result
        assert '2004-08-11 13:00' in result
        assert '2004-08-11 15:00' in result


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestLogoutView))
    suite.addTest(unittest.makeSuite(TestStartView))
    suite.addTest(unittest.makeSuite(TestPersonAddView))
    suite.addTest(unittest.makeSuite(TestObjectContainerView))
    suite.addTest(unittest.makeSuite(TestPersonContainerView))
    suite.addTest(unittest.makeSuite(TestGroupContainerView))
    suite.addTest(unittest.makeSuite(TestResourceContainerView))
    suite.addTest(unittest.makeSuite(TestObjectAddView))
    suite.addTest(unittest.makeSuite(TestGroupAddView))
    suite.addTest(unittest.makeSuite(TestResourceAddView))
    suite.addTest(unittest.makeSuite(TestBusySearchView))
    return suite


if __name__ == '__main__':
    unittest.main()
