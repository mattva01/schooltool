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
import sets
from zope.interface import Interface, implements, directlyProvides
from StringIO import StringIO
from schooltool.tests.helpers import dedent, diff
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.interfaces import IUtility, IFacet, IContainmentRoot

__metaclass__ = type


class I1(Interface):
    pass


class C1:
    implements(I1)


class RequestStub:

    code = 200
    reason = 'OK'

    def __init__(self, uri='', method='GET', body=''):
        self.headers = {}
        self.uri = uri
        self.method = method
        self.path = ''
        self.content = StringIO(body)
        start = uri.find('/', uri.find('://')+3)
        if start >= 0:
            self.path = uri[start:]
        self._hostname = 'localhost'

    def getRequestHostname(self):
        return self._hostname

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


class FacetStub:
    implements(IFacet)

    def __init__(self, name=None, active=True, parent=None, owner=None):
        self.__name__ = name
        self.__parent__ = parent
        self.active = active
        self.owner = owner


class ContainmentRoot:
    implements(IContainmentRoot)


def setPath(obj, path):
    """Trick getPath(obj) into returning path"""
    assert path.startswith('/')
    obj.__name__ = path[1:]
    obj.__parent__ = ContainmentRoot()


class TestHelpers(unittest.TestCase):

    def test_absoluteURL(self):
        from schooltool.views import absoluteURL
        request = RequestStub("http://locahost/foo/bar")
        self.assertEquals(absoluteURL(request, '/moo/spoo'),
                          "http://localhost/moo/spoo")
        self.assertRaises(ValueError, absoluteURL, request, 'relative/path')


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
        request = RequestStub(uri='http://foo/')
        view = View(context)
        self.assert_(view.getChild('', request) is view)
        result = view.getChild('anything', request)
        self.assert_(result.__class__ is NotFoundView)
        self.assert_(result.code == 404)

        request = RequestStub(uri='http://foo/x')
        result = view.getChild('', request)
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
        from schooltool.views import View
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
        request = RequestStub("http://localhost/group/")
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
              <relationships xlink:type="simple"
                             xlink:title="Relationships"
                             xlink:href="p/relationships"/>
              <facets xlink:type="simple" xlink:title="Facets"
                      xlink:href="p/facets"/>
            </person>
            """).split("---8<---\n")

        for chunk in segments:
            self.assert_(chunk in result, chunk)

        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")


class TestApplicationObjectTraverserView(RegistriesSetupMixin,
                                         unittest.TestCase):

    def setUp(self):
        from schooltool.views import ApplicationObjectTraverserView
        from schooltool.model import Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        self.per = app['persons'].new("p", title="Pete")
        self.view = ApplicationObjectTraverserView(self.per)

    def test_traverse(self):
        from schooltool.views import RelationshipsView, FacetManagementView
        from schooltool.interfaces import IFacetManager

        request = RequestStub("http://localhost/people/p")
        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.isImplementedBy(result.context))

        self.assertRaises(KeyError, self.view._traverse, 'anything', request)


class TestAppView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import ApplicationView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
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
        request = RequestStub("http://localhost/")
        result = self.view.render(request)

        expected = dedent("""\
            <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
              <message>Welcome to the SchoolTool server</message>
              <roots>
                <root xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="Root group"/>
              </roots>
              <containers>
                <container xlink:type="simple" xlink:href="/persons"
                           xlink:title="persons"/>
                <container xlink:type="simple" xlink:href="/groups"
                           xlink:title="groups"/>
              </containers>
              <utilities>
                <utility xlink:type="simple" xlink:href="/utils/foo"
                         xlink:title="Foo utility"/>
              </utilities>
            </schooltool>
            """)

        self.assertEquals(result, expected, "\n" + diff(expected, result))

    def test__traverse(self):
        from schooltool.views import ApplicationObjectContainerView
        from schooltool.views import UtilityServiceView
        request = RequestStub("http://localhost/groups")
        view = self.view._traverse('groups', request)
        self.assert_(view.__class__ is ApplicationObjectContainerView)
        self.assertRaises(KeyError, self.view._traverse, 'froups', request)

        view = self.view._traverse('utils', request)
        self.assert_(view.__class__ is UtilityServiceView)


class TestAppObjContainerView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import ApplicationObjectContainerView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
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
        request = RequestStub("http://localhost/groups")
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

        self.assertEquals(result, expected, "\n" + diff(expected, result))

    def test_post(self, suffix="", method="POST", body=None, view=None):
        if view is None:
            view = self.view
        request = RequestStub("http://localhost/groups" + suffix,
                              method=method, body=body)
        result = view.render(request)
        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        location = request.headers['Location']
        base = "http://localhost/groups/"
        self.assert_(location.startswith(base))
        name = location[len(base):]
        self.assert_(name in self.app['groups'].keys())
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(location in result)
        return name

    def test_post_with_a_title(self):
        name = self.test_post(body='title="New Group"')
        self.assert_(self.app['groups'][name].title == 'New Group')

    def test_get_child(self, method="GET"):
        from schooltool.views import ApplicationObjectCreatorView
        view = ApplicationObjectCreatorView(self.app['groups'], 'foo')
        request = RequestStub("http://localhost/groups/foo", method=method)
        result = view.render(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")

    def test_delete_child(self):
        self.test_get_child(method="DELETE")

    def test_put_child(self):
        from schooltool.views import ApplicationObjectCreatorView
        view = ApplicationObjectCreatorView(self.app['groups'], 'foo')
        name = self.test_post(method="PUT", suffix="/foo", view=view)
        self.assertEquals(name, 'foo')

        view = ApplicationObjectCreatorView(self.app['groups'], 'bar')
        name = self.test_post(method="PUT", suffix="/bar", view=view,
                              body='title="Bar Bar"')
        self.assertEquals(name, 'bar')
        self.assert_(self.app['groups'][name].title == 'Bar Bar')

    def test__traverse(self):
        from schooltool.views import GroupView, ApplicationObjectCreatorView
        request = RequestStub("http://localhost/groups/root")
        view = self.view._traverse('root', request)
        self.assert_(view.__class__ is GroupView)
        view = self.view._traverse('newchild', request)
        self.assert_(view.__class__ is ApplicationObjectCreatorView)
        self.assertEquals(view.container, self.view.context)
        self.assertEquals(view.name, 'newchild')


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
        request = RequestStub("http://localhost/groups")
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

        self.assertEquals(result, expected, "\n" + diff(expected, result))

    def test__traverse(self):
        from schooltool.views import UtilityView
        request = RequestStub("http://localhost/utils/foo")
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
        self.tearDownRegistries()

    def test_render(self):
        request = RequestStub("http://localhost/groups")
        result = self.view.render(request)

        expected = dedent("""\
            <utility>
              <name>foo</name>
            </utility>
            """)

        self.assertEquals(result, expected, "\n" + diff(expected, result))


class TestFacetView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import FacetView
        from schooltool import views
        self.setUpRegistries()
        views.setUp()
        self.facet = FacetStub(name="001")
        self.view = FacetView(self.facet)

    def tearDown(self):
        self.tearDownRegistries()

    def test_render(self):
        request = RequestStub("http://localhost/some/object/facets/001")
        result = self.view.render(request)
        expected = dedent("""
            <facet active="active" owned="unowned">
              <class>FacetStub</class>
              <name>001</name>
            </facet>
            """)
        self.assertEquals(result, expected, "\n" + diff(expected, result))

        self.facet.active = False
        self.facet.owner = object()
        result = self.view.render(request)
        expected = dedent("""\
            <facet active="inactive" owned="owned">
              <class>FacetStub</class>
              <name>001</name>
            </facet>
            """)
        self.assertEquals(result, expected, "\n" + diff(expected, result))

    def test_delete_owned(self):
        request = RequestStub("http://localhost/some/object/facets/001",
                              method="DELETE")
        self.facet.owner = object()
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason,
                          "Owned facets may not be deleted manually")

    def test_delete_unowned(self):
        from schooltool.interfaces import IFaceted

        class FacetedStub:
            implements(IFaceted)

            def __init__(self, initial=[]):
                self.__facets__ = sets.Set(initial)

        self.facet.__parent__ = FacetedStub([self.facet])
        request = RequestStub("http://localhost/some/object/facets/001",
                              method="DELETE")
        result = self.view.render(request)
        expected = "Facet removed"
        self.assertEquals(result, expected, "\n" + diff(expected, result))


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
        self.assertEquals(result, expected, "\n" + diff(expected, result))

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
        self.assertEquals(result, expected, "\n" + diff(expected, result))

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
        self.assertEquals(result, expected, "\n" + diff(expected, result))

        result = view.render(request)
        expected = "0 events cleared"
        self.assertEquals(result, expected, "\n" + diff(expected, result))

        request = RequestStub("http://localhost/foo/eventlog", "PUT")
        request.content.write("something")
        request.content.seek(0)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason,
                "Only PUT with an empty body is defined for event logs")


class TestRelationshipsView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import RelationshipsView
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
        self.sub = app['groups'].new("sub", title="subgroup")
        self.new = app['groups'].new("new", title="New Group")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.sub, member=self.per)

        self.view = RelationshipsView(self.sub)

    def test_listLinks(self):
        from pprint import pformat
        request = RequestStub("http://localhost/groups/sub/relationships/")
        result = self.view.listLinks()
        self.assertEquals(len(result), 2)
        self.assert_({'traverse': '/persons/p',
                      'role': 'http://schooltool.org/ns/membership/member',
                      'type': 'http://schooltool.org/ns/membership',
                      'title': 'Pete',
                      'path': '/groups/sub/relationships/0002'}
                     in result, pformat(result))
        self.assert_({'traverse': '/groups/root',
                      'role': 'http://schooltool.org/ns/membership/group',
                      'type': 'http://schooltool.org/ns/membership',
                      'title': 'group',
                      'path': '/groups/sub/relationships/0001'}
                     in result, pformat(result))

    def test_getValencies(self):
        request = RequestStub("http://localhost/groups/sub/relationships/")
        result = self.view.getValencies()
        self.assertEquals(result,
                          [{'type':'http://schooltool.org/ns/membership',
                            'role':'http://schooltool.org/ns/membership/group'
                            }])

    def test_traverse(self):
        from schooltool.interfaces import ILink
        from schooltool.views import LinkView
        request = RequestStub("http://localhost/groups/sub/relationships/0001")
        result = self.view._traverse('0001', request)
        self.assert_(isinstance(result, LinkView), "is LinkView")
        self.assert_(ILink.isImplementedBy(result.context), "is ILink")

    def testGET(self):
        request = RequestStub("http://localhost/groups/sub/relationships/")
        result = self.view.render(request)
        self.assert_('<valencies>' in result)
        self.assert_('<existing>' in result)
        self.assert_(
            '<relationships xmlns:xlink="http://www.w3.org/1999/xlink">'
            in result)
        self.assert_(
            'xlink:role="http://schooltool.org/ns/membership/group"' in result)
        self.assert_(
            'xlink:role="http://schooltool.org/ns/membership/member"'
            in result)

    def testPOST(self):
        request = RequestStub("http://localhost/groups/sub/relationships/",
            method='POST',
            body='''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple"
                      xlink:role="http://schooltool.org/ns/membership/group"
                      xlink:arcrole="http://schooltool.org/ns/membership"
                      xlink:href="/groups/new"/>''')
        self.assertEquals(len(self.sub.listLinks()), 2)
        self.assert_(self.new not in
                     [l.traverse() for l in self.sub.listLinks()])
        result = self.view.render(request)
        self.assertEquals(request.code, 201)
        self.assertEquals(len(self.sub.listLinks()), 3)
        self.assert_(self.new in
                     [l.traverse() for l in self.sub.listLinks()])
        self.assertEquals(request.headers['Content-Type'],
                          "text/plain")
        location = "http://localhost/groups/sub/relationships/0003"
        self.assertEquals(request.headers['Location'], location)
        self.assert_(location in result)

    def testBadPOSTs(self):
        bad_requests = (
            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="BADPATH"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="BAD URI"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/nonexistent"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            />''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/member"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/root"/>''',
            )

        for body in bad_requests:
            request = RequestStub("http://localhost/groups/sub/relationships",
                                  method="POST", body=body)
            self.assertEquals(len(self.sub.listLinks()), 2)
            result = self.view.render(request)
            self.assertEquals(request.code, 400)
            self.assertEquals(request.headers['Content-Type'],
                              "text/plain")
            self.assertEquals(len(self.sub.listLinks()), 2)


class TestFacetManagementView(RegistriesSetupMixin, unittest.TestCase):

    def test_traverse(self):
        from schooltool.views import View, FacetManagementView
        from schooltool.interfaces import IFacet
        from schooltool.component import registerView

        class IFacetStub(IFacet):
            pass

        class FacetStub:
            implements(IFacetStub)

        class FacetManagerStub:
            def __init__(self):
                self.facets = {}

            def facetByName(self, name):
                return self.facets[name]

        registerView(IFacetStub, View)

        context = FacetManagerStub()
        facet = FacetStub()
        context.facets['foo'] = facet
        view = FacetManagementView(context)
        request = RequestStub()
        self.assertRaises(KeyError, view._traverse, 'bar', request)
        child = view._traverse('foo', request)
        self.assertEquals(child.context, facet)

    def test_get(self):
        from schooltool.views import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        from schooltool.debug import EventLogFacet, setUp
        from schooltool.interfaces import IContainmentRoot
        setUp() # register a facet factory

        request = RequestStub("http://localhost/person/facets")
        facetable = Person()
        owner = Person()
        setPath(facetable, '/person')
        context = FacetManager(facetable)
        facet = EventLogFacet()
        context.setFacet(facet)
        facet.active = False
        context.setFacet(EventLogFacet(), owner=owner)
        view = FacetManagementView(context)
        result = view.render(request)
        expected = dedent("""
            <facets xmlns:xlink="http://www.w3.org/1999/xlink">
            ---8<---
              <facet xlink:type="simple" active="inactive"
                     xlink:title="001" class="EventLogFacet"
                     owned="unowned" xlink:href="/person/facets/001"/>
            ---8<---
              <facet xlink:type="simple" active="active"
                     xlink:title="002" class="EventLogFacet"
                     owned="owned" xlink:href="/person/facets/002"/>
            ---8<---
              <facetFactory name="eventlog" title="Event Log Factory"/>
            ---8<---
            </facets>
            """)
        for segment in expected.split("---8<---\n"):
            self.assert_(segment in result,
                         "\n-- segment\n%s\n-- not in\n%s" % (segment, result))
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

    def test_post(self):
        from schooltool.views import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        from schooltool.debug import EventLogFacet, setUp
        setUp() # register a facet factory

        request = RequestStub("http://localhost/group/facets",
                              method="POST",
                              body="<facet factory=\"eventlog\"/>")
        facetable = Person()
        context = FacetManager(facetable)
        view = FacetManagementView(context)
        result = view.render(request)
        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        self.assertEquals(request.headers['Location'],
                          "http://localhost/group/facets/001")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_("http://localhost/group/facets/001" in result)
        self.assertEquals(len(list(context.iterFacets())), 1)
        facet = context.facetByName('001')
        self.assert_(facet.__class__ is EventLogFacet)

    def test_post_errors(self):
        from schooltool.views import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        facetable = Person()
        context = FacetManager(facetable)
        view = FacetManagementView(context)
        for body in ("", "foo", "facet factory=\"nosuchfactory\""):
            request = RequestStub("http://localhost/group/facets",
                                  method="POST",
                                  body=body)
            result = view.render(request)
            self.assertEquals(request.code, 400,
                              "%s != 400 for %s" % (request.code, body))
            self.assertEquals(request.headers['Content-Type'], "text/plain")


class TestXMLPseudoParser(unittest.TestCase):

    def test_extractKeyword(self):
        from schooltool.views import XMLPseudoParser
        text = '''This is not even XML, it\'s just some random text.
               xlink:type="simple"
               xlink:title="http://schooltool.org/ns/membership"
               xlink:arcrole="http://schooltool.org/ns/membership"
               xlink:role="http://schooltool.org/ns/membership/group"
               xlink:href="/groups/new"
               '''
        extr = XMLPseudoParser().extractKeyword
        self.assertEquals(extr(text, 'type'), 'simple')
        self.assertEquals(extr(text, 'xlink:role'),
                          'http://schooltool.org/ns/membership/group')
        self.assertEquals(extr(text, 'role'),
                          'http://schooltool.org/ns/membership/group')
        self.assertEquals(extr(text, 'xlink:arcrole'),
                          'http://schooltool.org/ns/membership')
        self.assertEquals(extr(text, 'href'),
                          '/groups/new')
        self.assertRaises(KeyError, extr, text, 'shmoo')


class TestLinkView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views import LinkView
        from schooltool.model import Group
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="Subordinate Group")

        links = Membership(group=self.group, member=self.sub)

        self.link = links['member']
        self.view = LinkView(self.link)

    def testGET(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost%s" % getPath(self.link))
        result = self.view.render(request)
        expected = dedent("""\
        <relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple"
                      xlink:role="http://schooltool.org/ns/membership/member"
                      xlink:title="Subordinate Group"
                      xlink:arcrole="http://schooltool.org/ns/membership"
                      xlink:href="/groups/subgroup"/>
        """)
        self.assertEqual(expected, result, diff (expected, result))

    def testDELETE(self):
        from schooltool.component import getPath
        url = "http://localhost%s" % getPath(self.link)
        request = RequestStub(url, method="DELETE")
        self.assertEqual(len(self.sub.listLinks()), 1)
        result = self.view.render(request)
        self.assertEqual(len(self.sub.listLinks()), 0)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHelpers))
    suite.addTest(unittest.makeSuite(TestTemplate))
    suite.addTest(unittest.makeSuite(TestErrorViews))
    suite.addTest(unittest.makeSuite(TestView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestApplicationObjectTraverserView))
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestAppObjContainerView))
    suite.addTest(unittest.makeSuite(TestUtilityServiceView))
    suite.addTest(unittest.makeSuite(TestUtilityView))
    suite.addTest(unittest.makeSuite(TestFacetView))
    suite.addTest(unittest.makeSuite(TestEventLogView))
    suite.addTest(unittest.makeSuite(TestFacetManagementView))
    suite.addTest(unittest.makeSuite(TestRelationshipsView))
    suite.addTest(unittest.makeSuite(TestXMLPseudoParser))
    suite.addTest(unittest.makeSuite(TestLinkView))
    return suite

if __name__ == '__main__':
    unittest.main()
