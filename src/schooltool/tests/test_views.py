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
import libxml2
from zope.interface import Interface, implements
from StringIO import StringIO
from schooltool.tests.helpers import dedent, diff
from schooltool.tests.utils import RegistriesSetupMixin, EventServiceTestMixin
from schooltool.interfaces import IUtility, IFacet, IContainmentRoot
from schooltool.interfaces import ITraversable

__metaclass__ = type


class Libxml2ErrorLogger:

    def __init__(self):
        self.log = []

    def __call__(self, ctx, error):
        self.log.append(error)


class XPathTestContext:
    """XPath context for use in tests that check rendered xml.

    You must call the free() method at the end of the test.

    XXX add option for validating result against a schema
    """

    namespaces = {'xlink': 'http://www.w3.org/1999/xlink'}

    def __init__(self, test, result):
        """Create an XPath test context.

        test is the unit test TestCase, used for assertions.
        result is a string containing XML>
        """
        import libxml2  # import here so we only import if we need it
        self.errorlogger = Libxml2ErrorLogger()
        libxml2.registerErrorHandler(self.errorlogger, None)
        self.test = test
        self.doc = libxml2.parseDoc(result)
        self.context = self.doc.xpathNewContext()
        for nsname, ns in self.namespaces.iteritems():
            self.context.xpathRegisterNs(nsname, ns)

    def free(self):
        """Free C level objects.

        Call this at the end of a test to prevent memory leaks.
        """
        self.doc.freeDoc()
        self.context.xpathFreeContext()

    def query(self, expression):
        """Perform an XPath query.

        Returns a sequence of DOM nodes.
        """
        return self.context.xpathEval(expression)

    def oneNode(self, expression):
        """Perform an XPath query.

        Asserts that the query matches exactly one DOM node.  Returns it.
        """
        nodes = self.context.xpathEval(expression)
        self.test.assertEquals(len(nodes), 1,
                               "%s matched %d nodes"
                               % (expression, len(nodes)))
        return nodes[0]

    def assertNumNodes(self, num, expression):
        """Assert that an XPath expression matches exactly num nodes."""
        nodes = self.context.xpathEval(expression)
        self.test.assertEquals(num, len(nodes),
                               "%s matched %d nodes instead of %d"
                               % (expression, len(nodes), num))

    def assertAttrEquals(self, node, name, value):
        """Assert that an attribute of an element node has a given value.

        Attribute name may contain a namespace (e.g. 'xlink:href').  The
        dict of recongized namespaces is kept in the namespaces attribute.
        """
        name_parts = name.split(':')
        if len(name_parts) > 2:
            raise ValueError('max one colon in attribute name', name)
        elif len(name_parts) == 1:
            localname = name_parts[0]
            ns = None
        else:
            nsname, localname = name_parts
            ns = self.namespaces[nsname]
        self.test.assertEquals(node.nsProp(localname, ns), value)

    def assertNoErrors(self):
        """Assert that no errors were found while parsing the document."""
        self.test.assertEquals(self.errorlogger.log, [])


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


class TraversableStub:
    implements(ITraversable)

    def __init__(self, **kw):
        self.children = kw

    def traverse(self, name):
        return self.children[name]


class TraversableRoot(TraversableStub):
    implements(IContainmentRoot)


def setPath(obj, path, root=None):
    """Trick getPath(obj) into returning path"""
    assert path.startswith('/')
    obj.__name__ = path[1:]
    if root is None:
        obj.__parent__ = TraversableRoot()
    else:
        assert IContainmentRoot.isImplementedBy(root)
        obj.__parent__ = root


class TestHelpers(unittest.TestCase):

    def test_absoluteURL(self):
        from schooltool.views import absoluteURL
        request = RequestStub("http://locahost/foo/bar")
        self.assertEquals(absoluteURL(request, '/moo/spoo'),
                          "http://localhost/moo/spoo")
        self.assertRaises(ValueError, absoluteURL, request, 'relative/path')

    def test_parse_datetime(self):
        from schooltool.views import parse_datetime
        dt = datetime.datetime
        valid_dates = (
            ("2000-01-01 00:00:00", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2000-01-01T00:00:00", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2005-12-23 11:22:33", dt(2005, 12, 23, 11, 22, 33)),
            ("2005-12-23T11:22:33", dt(2005, 12, 23, 11, 22, 33)),
        )
        for s, d in valid_dates:
            result = parse_datetime(s)
            self.assertEquals(result, d,
                              "parse_datetime(%r) returned %r" % (s, result))
        invalid_dates = (
            "2000/01/01",
            "2100-02-29 00:00:00",
            "2005-12-23 11:22:33 "
        )
        for s in invalid_dates:
            try:
                result = parse_datetime(s)
            except ValueError:
                pass
            else:
                self.fail("parse_datetime(%r) did not raise" % s)


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
            self.assert_(segment in result,
                         "\n-- segment\n%s\n-- not in\n%s" % (segment, result))
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

    def test_traverse(self):
        from schooltool.views import RelationshipsView, FacetManagementView
        from schooltool.views import RollcallView, TreeView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/group")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.group)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.isImplementedBy(result.context))

        result = self.view._traverse("rollcall", request)
        self.assert_(isinstance(result, RollcallView))
        self.assert_(result.context is self.group)

        result = self.view._traverse("tree", request)
        self.assert_(isinstance(result, TreeView))
        self.assert_(result.context is self.group)

        self.assertRaises(KeyError, self.view._traverse, "otherthings",
                          request)


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

    def test_traverse(self):
        from schooltool.views import RelationshipsView, FacetManagementView
        from schooltool.views import AbsenceManagementView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/person")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.isImplementedBy(result.context))

        result = self.view._traverse('absences', request)
        self.assert_(isinstance(result, AbsenceManagementView))
        self.assert_(result.context is self.per)

    def test_render(self):
        request = RequestStub("http://localhost/person")
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
        self.assert_(result.context is self.per)

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

    def test_render_Usingxpath(self):
        request = RequestStub("http://localhost/")
        result = self.view.render(request)

        context = XPathTestContext(self, result)
        try:
            containers = context.oneNode('/schooltool/containers')
            context.assertNumNodes(2, '/schooltool/containers/container')
            persons = context.oneNode(
                '/schooltool/containers/container[@xlink:href="/persons"]')
            groups = context.oneNode(
                '/schooltool/containers/container[@xlink:href="/groups"]')

            context.assertAttrEquals(persons, 'xlink:type', 'simple')
            context.assertAttrEquals(persons, 'xlink:title', 'persons')

            context.assertAttrEquals(groups, 'xlink:type', 'simple')
            context.assertAttrEquals(groups, 'xlink:title', 'groups')
        finally:
            context.free()
        context.assertNoErrors()

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


class TestAbsenceCommentParser(unittest.TestCase):

    def test_parseComment(self):
        from schooltool.interfaces import Unchanged
        from schooltool.views import AbsenceCommentParser
        john = object()
        group = object()
        persons = TraversableStub(john=john)
        groups = TraversableStub(aa=group)
        root = TraversableRoot(persons=persons, groups=groups)
        parser = AbsenceCommentParser()
        parser.context = root

        # The very minimum
        request = RequestStub(body="""
                        text="Foo"
                        reporter="/persons/john"
                    """)
        lower_limit = datetime.datetime.utcnow()
        comment = parser.parseComment(request)
        upper_limit = datetime.datetime.utcnow()
        self.assertEquals(comment.text, "Foo")
        self.assertEquals(comment.reporter, john)
        self.assert_(lower_limit <= comment.datetime <= upper_limit)
        self.assert_(comment.absent_from is None)
        self.assert_(comment.ended is Unchanged)
        self.assert_(comment.resolved is Unchanged)
        self.assert_(comment.expected_presence is Unchanged)

        # Everything
        request = RequestStub(body="""
                        text="Foo"
                        reporter="/persons/john"
                        absent_from="/groups/aa"
                        ended="ended"
                        resolved="unresolved"
                        datetime="2004-04-04 04:04:04"
                        expected_presence="2005-05-05 05:05:05"
                    """)
        comment = parser.parseComment(request)
        self.assertEquals(comment.text, "Foo")
        self.assertEquals(comment.reporter, john)
        self.assertEquals(comment.absent_from, group)
        self.assertEquals(comment.ended, True)
        self.assertEquals(comment.resolved, False)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2004, 4, 4, 4, 4, 4))
        self.assertEquals(comment.expected_presence,
                          datetime.datetime(2005, 5, 5, 5, 5, 5))

    def test_parseComment_errors(self):
        from schooltool.views import AbsenceCommentParser
        parser = AbsenceCommentParser()
        parser.context = TraversableRoot(obj=object())
        bad_requests = (
            '',
            'reporter="/obj"',
            'text=""',
            'text="" reporter="/does/not/exist"',
            'text="" reporter="/obj" datetime="now"',
            'text="" reporter="/obj" absent_from="/does/not/exist"',
            'text="" reporter="/obj" ended="mu"',
            'text="" reporter="/obj" resolved="mu"',
            'text="" reporter="/obj" expected_presence="dunno"',
        )
        for body in bad_requests:
            request = RequestStub(body=body)
            try:
                parser.parseComment(request)
            except ValueError:
                pass
            else:
                self.fail("did not raise ValueError for\n\t%s" % body)


class TestAbsenceManagementView(EventServiceTestMixin, unittest.TestCase):

    def test_traverse(self):
        from schooltool.views import AbsenceManagementView, AbsenceView
        from schooltool.model import Person, AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        absence = context.reportAbsence(AbsenceComment())
        view = AbsenceManagementView(context)
        request = RequestStub("http://localhost/person/absences")
        result = view._traverse(absence.__name__, request)
        self.assert_(isinstance(result, AbsenceView))
        self.assert_(result.context is absence)
        self.assertRaises(KeyError,
                          view._traverse, absence.__name__ + 'X', request)

    def test_get(self):
        from schooltool.views import AbsenceManagementView
        from schooltool.model import Person, AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        context.reportAbsence(AbsenceComment(ended=True, resolved=True))
        context.reportAbsence(AbsenceComment())
        self.assertEquals(len(list(context.iterAbsences())), 2)
        view = AbsenceManagementView(context)
        request = RequestStub("http://localhost/person/absences")
        result = view.render(request)
        expected = dedent("""
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
            ---8<---
              <absence xlink:type="simple"
                       xlink:href="/person/absences/001" ended="ended"
                       xlink:title="001" resolved="resolved"/>
            ---8<---
              <absence xlink:type="simple"
                       xlink:href="/person/absences/002" ended="unended"
                       xlink:title="002" resolved="unresolved"/>
            ---8<---
            </absences>
            """)
        for segment in expected.split("---8<---\n"):
            self.assert_(segment in result,
                         "\n-- segment\n%s\n-- not in\n%s" % (segment, result))
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

    def test_post(self):
        from schooltool.views import AbsenceManagementView
        from schooltool.model import Person
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        basepath = "/person/absences/"
        baseurl = "http://localhost%s" % basepath
        view = AbsenceManagementView(context)
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="."')

        result = view.render(request)

        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        location = request.headers['Location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        path = '%s%s' % (basepath, name)
        self.assert_(path in result, '%r not in %r' % (path, result))
        self.assertEquals(len(list(context.iterAbsences())), 1)
        absence = context.getAbsence(name)
        comment = absence.comments[0]
        self.assertEquals(comment.text, "Foo")

    def test_post_another_one(self):
        from schooltool.views import AbsenceManagementView
        from schooltool.model import Person, AbsenceComment
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        absence = context.reportAbsence(AbsenceComment())
        basepath = "/person/absences/"
        baseurl = "http://localhost%s" % basepath
        view = AbsenceManagementView(context)
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Bar" reporter="."')

        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        location = request.headers['Location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        path = '%s%s' % (basepath, name)
        self.assert_(path in result, '%r not in %r' % (path, result))
        self.assertEquals(len(list(context.iterAbsences())), 1)
        self.assertEquals(name, absence.__name__)
        comment = absence.comments[-1]
        self.assertEquals(comment.text, "Bar")

    def test_post_errors(self):
        from schooltool.views import AbsenceManagementView
        from schooltool.model import Person
        context = Person()
        setPath(context, '/person', root=self.serviceManager)
        basepath = "/person/absences/"
        baseurl = "http://localhost%s" % basepath
        view = AbsenceManagementView(context)
        request = RequestStub(baseurl[:-1], method="POST",
                    body='')

        result = view.render(request)

        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Text attribute missing")


class TestAbsenceView(EventServiceTestMixin, unittest.TestCase):

    def createAbsence(self):
        from schooltool.model import Person, Group, AbsenceComment
        reporter1 = Person()
        setPath(reporter1, '/reporter1')
        reporter2 = Person()
        setPath(reporter2, '/reporter2')
        group1 = Group()
        setPath(group1, '/group1')
        person = Person()
        setPath(person, '/person', root=self.serviceManager)
        absence = person.reportAbsence(AbsenceComment(reporter1, 'Some text',
                dt=datetime.datetime(2001, 1, 1)))
        person.reportAbsence(AbsenceComment(reporter2, 'More text\n',
                absent_from=group1, dt=datetime.datetime(2002, 2, 2),
                expected_presence=datetime.datetime(2003, 03, 03),
                ended=True, resolved=False))
        return absence

    def test_get(self):
        from schooltool.views import AbsenceView
        absence = self.createAbsence()
        view = AbsenceView(absence)
        request = RequestStub("http://localhost/person/absences/001")
        result = view.render(request)
        expected = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink"
                     xlink:type="simple" xlink:title="person"
                     resolved="unresolved" ended="ended"
                     xlink:href="/person"
                     expected_presence="2003-03-03 00:00:00">
              <comment xlink:type="simple" xlink:title="reporter"
                       xlink:href="/reporter1"
                       datetime="2001-01-01 00:00:00">Some text</comment>
              <comment xlink:type="simple" xlink:title="reporter"
                       resolved="unresolved"
                       expected_presence="2003-03-03 00:00:00"
                       xlink:href="/reporter2" absentfrom="/group1"
                       datetime="2002-02-02 00:00:00" ended="ended">More text
            </comment>
            </absence>
            """)
        self.assertEquals(result, expected, "\n" + diff(expected, result))
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

    def test_post(self):
        from schooltool.views import AbsenceView
        absence = self.createAbsence()
        view = AbsenceView(absence)
        basepath = "/person/absences/001/"
        baseurl = "http://localhost" + basepath
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="."')
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Comment added")
        comment = absence.comments[-1]
        self.assertEquals(comment.text, "Foo")

    def test_post_errors(self):
        from schooltool.views import AbsenceView
        absence = self.createAbsence()
        self.assertEquals(len(absence.comments), 2)
        basepath = "/person/absences/001/"
        setPath(absence, basepath[:-1])
        baseurl = "http://localhost" + basepath
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="/does/not/exist"')
        view = AbsenceView(absence)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Reporter not found: /does/not/exist")
        self.assertEquals(len(absence.comments), 2)

    def test_post_duplicate(self):
        from schooltool.views import AbsenceView
        from schooltool.model import AbsenceComment
        absence = self.createAbsence()
        absence.person.reportAbsence(AbsenceComment())
        self.assertEquals(len(absence.comments), 2)
        basepath = "/person/absences/001/"
        setPath(absence, basepath[:-1])
        baseurl = "http://localhost" + basepath
        request = RequestStub(baseurl[:-1], method="POST",
                    body='text="Foo" reporter="." ended="unended"')
        view = AbsenceView(absence)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result,
            "Cannot reopen an absence when another one is not ended")
        self.assertEquals(len(absence.comments), 2)


class TestRollcallView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
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
        self.subsub = app['groups'].new("subsubgroup", title="subsubgroup")
        self.persona = app['persons'].new("a", title="a")
        self.personb = app['persons'].new("b", title="b")
        self.personc = app['persons'].new("c", title="c")
        self.persond = app['persons'].new("d", title="d")
        self.personq = app['persons'].new("q", title="q")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.sub, member=self.subsub)
        Membership(group=self.group, member=self.persona)
        Membership(group=self.sub, member=self.personb)
        Membership(group=self.subsub, member=self.personc)
        Membership(group=self.subsub, member=self.persond)

        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def test_get(self):
        from schooltool.views import RollcallView
        from schooltool.model import AbsenceComment
        self.personb.reportAbsence(AbsenceComment())
        self.personc.reportAbsence(AbsenceComment(None, "",
                expected_presence=datetime.datetime(2001, 1, 1, 2, 2, 2)))
        view = RollcallView(self.group)
        request = RequestStub("http://localhost/group/rollcall")
        result = view.render(request)
        expected = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root">
            ---8<---
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
            ---8<---
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
            ---8<---
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c"
                      expected_presence="2001-01-01 02:02:02"
                      presence="absent"/>
            ---8<---
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="present"/>
            ---8<---
            </rollcall>
            """)
        for segment in expected.split("---8<---\n"):
            self.assert_(segment in result,
                         "\n-- segment\n%s\n-- not in\n%s" % (segment, result))
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")

    def test_post(self):
        from schooltool.views import RollcallView
        from schooltool.model import AbsenceComment
        personc_absence = self.personc.reportAbsence(AbsenceComment())
        persond_absence = self.persond.reportAbsence(AbsenceComment())
        view = RollcallView(self.group)
        text = "I just did a roll call and noticed Mr. B. is missing again"
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body="""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"
                      comment="%s"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present" resolved="resolved"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>
                              """ % text)
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, "OK")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "2 absences and 1 presences reported")

        # persona was present and is present, no comments should be added.
        self.assertEqual(len(list(self.persona.iterAbsences())), 0)

        # personb was present, now should be absent
        absence = self.personb.getCurrentAbsence()
        self.assert_(absence is not None)
        comment = absence.comments[-1]
        self.assert_(comment.absent_from is self.group)
        self.assert_(comment.reporter is self.persona)
        self.assertEquals(comment.text, text)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2001, 2, 3, 4, 5, 6))

        # personc was absent, now should be present
        self.assert_(self.personc.getCurrentAbsence() is None)
        comment = personc_absence.comments[-1]
        self.assert_(comment.absent_from is self.group)
        self.assert_(comment.reporter is self.persona)
        self.assertEquals(comment.text, None)
        self.assertEquals(comment.ended, True)
        self.assertEquals(comment.resolved, True)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2001, 2, 3, 4, 5, 6))

        # persond was absent, now should be absent
        absence = self.persond.getCurrentAbsence()
        self.assert_(absence is persond_absence)
        comment = absence.comments[-1]
        self.assert_(comment.absent_from is self.group)
        self.assert_(comment.reporter is self.persona)
        self.assertEquals(comment.text, None)
        self.assertEquals(comment.datetime,
                          datetime.datetime(2001, 2, 3, 4, 5, 6))

    def post_errors(self, body, errmsg):
        from schooltool.views import RollcallView
        view = RollcallView(self.group)
        request = RequestStub("http://localhost/group/rollcall",
                              method="POST", body=body)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad request")
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, errmsg)

    def test_post_syntax_errors(self):
        self.post_errors("""This is not a roll call""",
            "Bad roll call representation")

    def test_post_structure_errors(self):
        # I expect that we can validate all these errors with a schema
        # and just return a generic "Bad roll call representation" error
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Reporter not specified")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Person does not specify xlink:href")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Bad presence value for /persons/a")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent" resolved="xyzzy"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Bad resolved value for /persons/b")

    def test_post_logic_errors(self):
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/x" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Reporter not found: /persons/x")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Person mentioned more than once: /persons/a")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/q"
                      xlink:title="q" presence="present"/>
            </rollcall>""",
            "Person /persons/q is not a member of /groups/root")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Persons not mentioned: /persons/a, /persons/c")
        self.post_errors("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple" xlink:title="group"
                      xlink:href="/groups/root"
                      datetime="2001-02-03 04:05:06">
              <reporter xlink:type="simple" xlink:href="/persons/a" />
              <comment>XXX</comment>
              <person xlink:type="simple" xlink:href="/persons/a"
                      xlink:title="a" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/b"
                      xlink:title="b" presence="absent" resolved="resolved"/>
              <person xlink:type="simple" xlink:href="/persons/c"
                      xlink:title="c" presence="present"/>
              <person xlink:type="simple" xlink:href="/persons/d"
                      xlink:title="d" presence="absent"/>
            </rollcall>""",
            "Cannot resolve an absence for absent person /persons/b")


class TestAbsenceTrackerView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Person, AbsenceTrackerUtility
        from schooltool.model import AbsenceComment
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views import AbsenceTrackerView
        from schooltool.interfaces import IAttendanceEvent
        self.setUpRegistries()
        app = Application()
        self.tracker = AbsenceTrackerUtility()
        app.utilityService['absences'] = self.tracker
        app.eventService.subscribe(self.tracker, IAttendanceEvent)
        app['persons'] = ApplicationObjectContainer(Person)
        self.person = app['persons'].new("a", title="a")
        self.person.reportAbsence(AbsenceComment(None, ""))
        self.view = AbsenceTrackerView(self.tracker)

    def test_get(self):
        request = RequestStub("http://localhost/utils/absences/")
        result = self.view.render(request)
        expected = dedent("""
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple"
                       xlink:href="/persons/a/absences/001"
                       ended="unended" xlink:title="001"
                       resolved="unresolved"/>
            </absences>
            """)
        self.assertEqual(result, expected, diff(result, expected))
        for segment in expected.split("---8<---\n"):
            self.assert_(segment in result,
                         "\n-- segment\n%s\n-- not in\n%s" % (segment, result))
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")


class TestAbsenceTrackerFacetView(TestAbsenceTrackerView):

    def setUp(self):
        from schooltool.model import Person, AbsenceTrackerFacet
        from schooltool.model import AbsenceComment
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.views import AbsenceTrackerFacetView
        from schooltool.interfaces import IAttendanceEvent
        from schooltool.facet import FacetManager

        self.setUpRegistries()
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        self.person = app['persons'].new("a", title="a")

        self.facet = AbsenceTrackerFacet()
        FacetManager(self.person).setFacet(self.facet)

        self.person.reportAbsence(AbsenceComment(None, ""))
        self.view = AbsenceTrackerFacetView(self.facet)

    def testDelete(self):
        request = RequestStub("http://localhost/persons/a/facets/001",
                              method="DELETE")
        result = self.view.render(request)
        expected = "Facet removed"
        self.assertEquals(result, expected, "\n" + diff(expected, result))


class TestTreeView(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="root group")
        self.group1 = app['groups'].new("group1", title="group1")
        self.group2 = app['groups'].new("group2", title="group2")
        self.group1a = app['groups'].new("group1a", title="group1a")
        self.group1b = app['groups'].new("group1b", title="group1b")
        self.persona = app['persons'].new("a", title="a")

        Membership(group=self.group, member=self.group1)
        Membership(group=self.group, member=self.group2)
        Membership(group=self.group1, member=self.group1a)
        Membership(group=self.group1, member=self.group1b)
        Membership(group=self.group2, member=self.persona)

        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def test(self):
        from schooltool.views import TreeView
        view = TreeView(self.group)
        request = RequestStub("http://localhost/groups/root/tree")
        result = view.render(request)
        expected = dedent("""
            <tree xmlns:xlink="http://www.w3.org/1999/xlink">
              <group xlink:type="simple" xlink:href="/groups/root"
                     xlink:title="root group">
                <group xlink:type="simple" xlink:href="/groups/group2"
                       xlink:title="group2">
                </group>
                <group xlink:type="simple" xlink:href="/groups/group1"
                       xlink:title="group1">
                  <group xlink:type="simple" xlink:href="/groups/group1a"
                         xlink:title="group1a">
                  </group>
                  <group xlink:type="simple" xlink:href="/groups/group1b"
                         xlink:title="group1b">
                  </group>
                </group>
              </group>
            </tree>
        """)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        # XXX: Nondeterminism sucks
        # self.assertEquals(result, expected, "\n" + diff(expected, result))


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
    suite.addTest(unittest.makeSuite(TestAbsenceManagementView))
    suite.addTest(unittest.makeSuite(TestAbsenceView))
    suite.addTest(unittest.makeSuite(TestAbsenceCommentParser))
    suite.addTest(unittest.makeSuite(TestRollcallView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerView))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerFacetView))
    suite.addTest(unittest.makeSuite(TestTreeView))
    return suite

if __name__ == '__main__':
    unittest.main()
