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
Unit tests for schooltool.views

$Id$
"""

import unittest
import datetime
from zope.interface import Interface, implements
from StringIO import StringIO
from schooltool.tests.helpers import dedent, diff
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.interfaces import IUtility

__metaclass__ = type


class I1(Interface):
    pass

class C1:
    implements(I1)

class RequestStub:

    code = 200
    reason = 'OK'
    content = StringIO()

    def __init__(self, uri='', method='GET'):
        self.headers = {}
        self.uri = uri
        self.method = method

    def setHeader(self, header, value):
        self.headers[header] = value

    def setResponseCode(self, code, reason):
        self.code = code
        self.reason = reason


class Utility:

    implements(IUtility)

    __parent__ = None
    __name__ = None

    def __init__(self, title):
        self.title = title


class TestTemplate(unittest.TestCase):

    def test_call(self):
        from schooltool.views import Template
        templ = Template('sample.pt')
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assertEquals(request.headers['Content-Type'],
                     "text/html; charset=UTF-8")
        self.assertEquals(result, "code: 200\nfoo: Foo\nbar: Bar\n")

    def test_content_type(self):
        from schooltool.views import Template
        templ = Template('sample_xml.pt', content_type='text/plain')
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assertEquals(request.headers['Content-Type'],
                     "text/plain; charset=UTF-8")
        self.assertEquals(result, "code: 200\n")


class TestErrorViews(unittest.TestCase):

    def test_ErrorView(self):
        from schooltool.views import ErrorView
        view = ErrorView(747, "Not ready to take off")
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/html; charset=UTF-8")
        self.assertEquals(request.code, 747)
        self.assertEquals(request.reason, "Not ready to take off")
        self.assert_('<title>747 - Not ready to take off</title>' in result)
        self.assert_('<h1>747 - Not ready to take off</h1>' in result)

    def test_NotFoundView(self):
        from schooltool.views import NotFoundView
        view = NotFoundView(404, "No Boeing found")
        request = RequestStub(uri='/hangar')
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/html; charset=UTF-8")
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "No Boeing found")
        self.assert_('<title>404 - No Boeing found</title>' in result)
        self.assert_('<h1>404 - No Boeing found</h1>' in result)
        self.assert_('/hangar' in result)

    def test_errorPage(self):
        from schooltool.views import errorPage
        request = RequestStub()
        result = errorPage(request, 747, "Not ready to take off")
        self.assertEquals(request.code, 747)
        self.assertEquals(request.reason, "Not ready to take off")
        self.assert_('<title>747 - Not ready to take off</title>' in result)
        self.assert_('<h1>747 - Not ready to take off</h1>' in result)


class TestView(unittest.TestCase):

    def test_getChild(self):
        from schooltool.views import View, NotFoundView
        context = None
        request = RequestStub()
        view = View(context)
        self.assert_(view.getChild('', request) is view)
        result = view.getChild('anything', request)
        self.assert_(result.__class__ is NotFoundView)
        self.assert_(result.code == 404)

    def test_getChild_with_traverse(self):
        from schooltool.views import View, NotFoundView
        context = None
        request = RequestStub()
        view = View(context)
        frob = object()
        def _traverse(name, request):
            if name == 'frob':
                return frob
            raise KeyError(name)
        view._traverse = _traverse
        self.assert_(view.getChild('frob', request) is frob)
        result = view.getChild('not frob', request)
        self.assert_(result.__class__ is NotFoundView)
        self.assert_(result.code == 404)

    def test_getChild_with_exceptions(self):
        from schooltool.views import View, NotFoundView
        context = None
        request = RequestStub()
        view = View(context)
        frob = object()
        def _traverse(name, request):
            raise AssertionError('just testing')
        view._traverse = _traverse
        self.assertRaises(AssertionError, view.getChild, 'frob', request)

    def test_do_GET(self):
        from schooltool.views import View
        context = object()
        body = 'foo'
        view = View(context)

        class TemplateStub:

            def __init__(self, request, view, context, body):
                self.request = request
                self.view = view
                self.context = context
                self.body = body

            def __call__(self, request, view=None, context=None):
                assert request is self.request
                assert view is self.view
                assert context is self.context
                return self.body

        request = RequestStub()
        view.template = TemplateStub(request, view, context, body)
        self.assertEquals(view.render(request), body)

    def test_do_HEAD(self):
        from schooltool.views import View
        context = object()
        body = 'foo'
        view = View(context)

        class TemplateStub:

            def __init__(self, request, view, context, body):
                self.request = request
                self.view = view
                self.context = context
                self.body = body

            def __call__(self, request, view=None, context=None):
                assert request is self.request
                assert view is self.view
                assert context is self.context
                return self.body

        request = RequestStub(method='HEAD')
        view.template = TemplateStub(request, view, context, body)
        self.assertEquals(view.render(request), '')
        self.assertEquals(request.headers['Content-Length'], len(body))

    def test_render(self):
        from schooltool.views import View
        context = object()
        view = View(context)
        view.do_FOO = lambda request: "Foo"

        request = RequestStub(method='PUT')
        self.assertNotEquals(view.render(request), '')
        self.assertEquals(request.code, 405)
        self.assertEquals(request.reason, 'Method Not Allowed')
        self.assertEquals(request.headers['Allow'], 'FOO, GET, HEAD')

        request = RequestStub(method='FOO')
        self.assertEquals(view.render(request), 'Foo')
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, 'OK')


class TestGroupView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import GroupView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership 
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.per = app['persons'].new("p", title="p")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)

        self.view = GroupView(self.group)

    def tearDown(self):
        self.tearDownRegistries()

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/group/")
        request.method = "GET"
        request.path = '/group'
        result = self.view.render(request)
        expected = dedent("""
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>group</name>
            ---8<---
              <item xlink:type="simple" xlink:title="p"
                    xlink:href="%s"/>
            ---8<---
              <item xlink:type="simple" xlink:title="subgroup"
                    xlink:href="%s"/>
            ---8<---
            </group>
            """ % (getPath(self.per), getPath(self.sub)))
        for segment in expected.split("---8<---\n"):
            self.assert_(segment in result, segment)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")


class TestPersonView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import PersonView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership 
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.sub, member=self.per)

        self.view = PersonView(self.per)

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/group/")
        request.method = "GET"
        request.path = getPath(self.per)
        result = self.view.render(request)
        segments = dedent("""
            <person xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>Pete</name>
              <groups>
            ---8<---
                <item xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="group"/>
            ---8<---
                <item xlink:type="simple" xlink:href="/groups/subgroup"
                      xlink:title="subgroup"/>
            ---8<---
              </groups>
            </person>
            """).split("---8<---\n")

        for chunk in segments:
            self.assert_(chunk in result, chunk)

        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")


class TestAppView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import ApplicationView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership, views
        self.setUpRegistries()
        membership.setUp()
        views.setUp()
        self.app = Application()
        self.app['groups'] = ApplicationObjectContainer(Group)
        self.app['persons'] = ApplicationObjectContainer(Person)
        self.group = self.app['groups'].new("root", title="Root group")
        self.app.addRoot(self.group)

        self.app.utilityService["foo"] = Utility("Foo utility")

        self.view = ApplicationView(self.app)

    def tearDown(self):
        from schooltool.component import resetViewRegistry
        resetViewRegistry()
        RegistriesSetupMixin.tearDown(self)

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/")
        request.method = "GET"
        result = self.view.render(request)

        expected = dedent("""\
            <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
              <message>Welcome to the SchoolTool server</message>
              <roots>
                <root xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="Root group"/>
              </roots>
              <utilities>
                <utility xlink:type="simple" xlink:href="/utils/foo"
                         xlink:title="Foo utility"/>
              </utilities>
            </schooltool>
            """)

        self.assertEquals(result, expected, "\n" + diff(result, expected))

    def test__traverse(self):
        from schooltool.views import ApplicationObjectContainerView
        from schooltool.views import UtilityServiceView
        request = RequestStub("http://localhost/groups")
        request.method = "GET"
        view = self.view._traverse('groups', request)
        self.assert_(view.__class__ is ApplicationObjectContainerView)
        self.assertRaises(KeyError, view._traverse, 'froups', request)

        view = self.view._traverse('utils', request)
        self.assert_(view.__class__ is UtilityServiceView)


class TestAppObjContainerView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import ApplicationObjectContainerView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership, views
        self.setUpRegistries()
        membership.setUp()
        views.setUp()
        self.app = Application()
        self.app['groups'] = ApplicationObjectContainer(Group)
        self.app['persons'] = ApplicationObjectContainer(Person)
        self.group = self.app['groups'].new("root", title="Root group")
        self.app.addRoot(self.group)

        self.view = ApplicationObjectContainerView(self.app['groups'])

    def tearDown(self):
        from schooltool.component import resetViewRegistry
        resetViewRegistry()
        RegistriesSetupMixin.tearDown(self)

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/groups")
        request.method = "GET"
        result = self.view.render(request)

        expected = dedent("""\
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>groups</name>
              <items>
                <item xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="Root group"/>
              </items>
            </container>
            """)

        self.assertEquals(result, expected, "\n" + diff(result, expected))

    def test__traverse(self):
        from schooltool.views import GroupView
        request = RequestStub("http://localhost/groups/root")
        request.method = "GET"
        view = self.view._traverse('root', request)
        self.assert_(view.__class__ is GroupView)
        self.assertRaises(KeyError, view._traverse, 'moot', request)


class TestUtilityServiceView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import UtilityServiceView
        from schooltool.app import Application
        from schooltool import views
        self.setUpRegistries()
        views.setUp()
        self.app = Application()
        self.app.utilityService["foo"] = Utility("Foo utility")
        self.view = UtilityServiceView(self.app.utilityService)

    def tearDown(self):
        from schooltool.component import resetViewRegistry
        resetViewRegistry()
        RegistriesSetupMixin.tearDown(self)

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/groups")
        request.method = "GET"
        result = self.view.render(request)

        expected = dedent("""\
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>utils</name>
              <items>
                <item xlink:type="simple" xlink:href="/utils/foo"
                      xlink:title="Foo utility"/>
              </items>
            </container>
            """)

        self.assertEquals(result, expected, diff(result, expected))

    def test__traverse(self):
        from schooltool.views import UtilityView
        request = RequestStub("http://localhost/utils/foo")
        request.method = "GET"
        view = self.view._traverse('foo', request)
        self.assert_(view.__class__ is UtilityView)
        self.assertRaises(KeyError, view._traverse, 'moot', request)


class TestUtilityView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import UtilityView
        from schooltool.app import Application
        from schooltool import views
        self.setUpRegistries()
        views.setUp()
        self.app = Application()
        self.app.utilityService["foo"] = Utility("Foo utility")
        self.view = UtilityView(self.app.utilityService['foo'])

    def tearDown(self):
        from schooltool.component import resetViewRegistry
        resetViewRegistry()
        RegistriesSetupMixin.tearDown(self)

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/groups")
        request.method = "GET"
        result = self.view.render(request)

        expected = dedent("""\
            <utility>
              <name>foo</name>
            </utility>
            """)

        self.assertEquals(result, expected, diff(result, expected))


class TestEventLogView(unittest.TestCase):

    def test_empty(self):
        from schooltool.views import EventLogView

        class EventLogStub:
            received = []

        context = EventLogStub()
        view = EventLogView(context)
        request = RequestStub("http://localhost/foo/eventlog")
        result = view.render(request)
        expected = dedent("""
            <eventLog>
            </eventLog>
        """)
        self.assertEquals(result, expected, "\n" + diff(result, expected))

    def test_nonempty(self):
        from schooltool.views import EventLogView

        class EventLogStub:
            received = []

        class EventStub:
            def __str__(self):
                return "Fake event"
            def __repr__(self):
                return "EventStub()"

        context = EventLogStub()
        context.received = [(datetime.datetime(2003, 10, 01, 11, 12, 13),
                             EventStub())]
        view = EventLogView(context)
        request = RequestStub("http://localhost/foo/eventlog")
        result = view.render(request)
        expected = dedent("""
            <eventLog>
              <event ts="2003-10-01 11:12:13">Fake event</event>
            </eventLog>
        """)
        self.assertEquals(result, expected, "\n" + diff(result, expected))

    def test_clear(self):
        from schooltool.views import EventLogView

        class EventLogStub:
            received = []
            def clear(self):
                self.received = []

        class EventStub:
            pass

        context = EventLogStub()
        context.received = [(datetime.datetime(2003, 10, 01, 11, 12, 13),
                             EventStub())]
        view = EventLogView(context)
        request = RequestStub("http://localhost/foo/eventlog", "PUT")
        result = view.render(request)
        expected = "1 event cleared"
        self.assertEquals(result, expected, "\n" + diff(result, expected))

        result = view.render(request)
        expected = "0 events cleared"
        self.assertEquals(result, expected, "\n" + diff(result, expected))

        request = RequestStub("http://localhost/foo/eventlog", "PUT")
        request.content.write("something")
        request.content.seek(0)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason,
                "Only PUT with an empty body is defined for event logs")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTemplate))
    suite.addTest(unittest.makeSuite(TestErrorViews))
    suite.addTest(unittest.makeSuite(TestView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestAppObjContainerView))
    suite.addTest(unittest.makeSuite(TestUtilityServiceView))
    suite.addTest(unittest.makeSuite(TestUtilityView))
    suite.addTest(unittest.makeSuite(TestEventLogView))
    return suite

if __name__ == '__main__':
    unittest.main()
