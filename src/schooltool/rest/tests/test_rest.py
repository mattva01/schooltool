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
Unit tests for schooltool.rest

$Id$
"""

import unittest
from zope.testing.doctestunit import DocTestSuite
from schooltool.rest.tests import RequestStub
from schooltool.interfaces import IContainmentRoot, ILocation
from zope.interface.declarations import implements, directlyProvides

__metaclass__ = type


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
        request.setHeader('Content-Type', 'text/plain')
        return self.body


class LocationStub:
    implements(ILocation)

    def __init__(self, parent, name):
        self.__parent__ = parent
        self.__name__ = name
        self.dict = {}

    def __getitem__(self, key):
        return self.dict[key]

    def __repr__(self):
        return "LocationStub(%r, %r)" % (self.__parent__, self.__name__)


class ContextStub:

    def __init__(self):
        self.vars = {}


class TestTemplate(unittest.TestCase):

    def test_call(self):
        from schooltool.rest import Template
        templ = Template('sample.pt')
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assertEquals(request.headers['content-type'],
                     "text/html; charset=UTF-8")
        self.assertEquals(result, "code: 200\nfoo: Foo\nbar: Bar\n")

    def test_content_type(self):
        from schooltool.rest import Template
        templ = Template('sample_xml.pt', content_type='text/plain')
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assertEquals(request.headers['content-type'],
                     "text/plain; charset=UTF-8")
        self.assertEquals(result, "code: 200\n")

    def test_no_content_type(self):
        from schooltool.rest import Template
        templ = Template('sample_xml.pt', content_type=None)
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assert_('content-type' not in request.headers)
        self.assertEquals(result, "code: 200\n")

    def test_no_charset(self):
        from schooltool.rest import Template
        templ = Template('sample_xml.pt', content_type='text/plain',
                         charset=None)
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assertEquals(request.headers['content-type'], "text/plain")
        self.assertEquals(result, u"code: 200\n")

    def test_no_request(self):
        from schooltool.rest import Template
        templ = Template('sample_no_request.pt')
        result = templ(None, foo='Foo', bar='Bar')
        self.assertEquals(result, "foo: Foo\nbar: Bar\n")

    def test_translate(self):
        from schooltool.rest import Template
        templ = Template('sample_i18n.pt')

        def fake_ugettext(msgid):
            return unicode({'Hello': 'Labas'}.get(msgid, msgid))

        templ.ugettext_hook = fake_ugettext
        result = templ(RequestStub())
        self.assertEquals(result, '<span title="A tooltip">Labas</span>\n')

    def buildTree(self):
        a = LocationStub(None, 'root')
        directlyProvides(a, IContainmentRoot)
        b = LocationStub(a, 'foo')
        c = LocationStub(b, 'bar')
        return a, b, c

    def test_absoluteURL(self):
        from schooltool.rest import Template
        templ = Template('sample_url.pt')
        context = self.buildTree()[2]
        result = templ(RequestStub(), context=context)
        self.assertEquals(result,
                          '<span>http://localhost:7001/foo/bar</span>\n'
                          '<span>/foo/bar</span>\n'
                          '<span>/foo/bar</span>\n')


class TestSchoolToolTraverse(unittest.TestCase):

    def test(self):
        from schooltool.rest import schooltoolTraverse
        a = LocationStub(None, 'root')
        directlyProvides(a, IContainmentRoot)
        b = LocationStub(a, 'foo')
        a.foo = b
        c = LocationStub(b, 'bar')
        b.bar = c
        d = LocationStub(c, 'baz')

        b.dict['magic'] = d
        assert b['magic'] is d

        assert schooltoolTraverse(a, ['foo', 'bar'], None) is c
        assert schooltoolTraverse(a, ['foo', 'magic'], None) is d
        assert schooltoolTraverse(a, ['foo', '@@path'], None) == '/foo'


        cx = ContextStub()
        cx.vars['request'] = RequestStub()
        assert (schooltoolTraverse(a, ['foo', '@@absolute_path'], cx)
                == '/foo')

        assert (schooltoolTraverse(a, ['foo', '@@absolute_url'], cx)
                == 'http://localhost:7001/foo')


class TestErrorViews(unittest.TestCase):

    def test_textErrorPage(self):
        from schooltool.rest import textErrorPage
        request = RequestStub()
        result = textErrorPage(request, u"Not ready to take off \u2639",
                               747, "Wait")
        self.assertEquals(request.code, 747)
        self.assertEquals(request.reason, "Wait")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, "Not ready to take off \xe2\x98\xb9")

        request = RequestStub()
        result = textErrorPage(request, 42)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(result, "42")

    def test_notFoundPage(self):
        from schooltool.rest import notFoundPage
        request = RequestStub(uri='/path')
        result = notFoundPage(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, "Not found: /path")

    def test_NotFoundView(self):
        from schooltool.rest import NotFoundView
        view = NotFoundView()
        request = RequestStub(uri='/path')
        result = view.render(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, "Not found: /path")


class TestView(unittest.TestCase):

    def test_getChild(self):
        from schooltool.rest import View, NotFoundView
        context = None
        request = RequestStub(uri='http://foo/')
        view = View(context)
        self.assert_(view.getChild('', request) is view)
        result = view.getChild('anything', request)
        self.assert_(result.__class__ is NotFoundView)

        request = RequestStub(uri='http://foo/x')
        result = view.getChild('', request)
        self.assert_(result.__class__ is NotFoundView)

    def test_getChild_with_traverse(self):
        from schooltool.rest import View, NotFoundView
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

    def test_getChild_with_exceptions(self):
        from schooltool.rest import View
        context = None
        request = RequestStub()
        view = View(context)
        frob = object()

        def _traverse(name, request):
            raise AssertionError('just testing')

        view._traverse = _traverse
        self.assertRaises(AssertionError, view.getChild, 'frob', request)

    def test_do_GET(self):
        from schooltool.rest import View
        context = object()
        body = 'foo'
        view = View(context)
        request = RequestStub()
        view.template = TemplateStub(request, view, context, body)
        view.authorization = lambda ctx, rq: True
        self.assertEquals(view.render(request), body)

    def test_do_HEAD(self):
        from schooltool.rest import View
        context = object()
        body = 'foo'
        view = View(context)
        request = RequestStub(method='HEAD')
        view.template = TemplateStub(request, view, context, body)
        view.authorization = lambda ctx, rq: True
        self.assertEquals(view.render(request), '')
        self.assertEquals(request.headers['content-length'], len(body))

    def test_render(self):
        from schooltool.rest import View
        context = object()

        class ViewSubclass(View):

            def do_FOO(self, request, testcase=self):
                testcase.assert_(request is self.request)
                request.setHeader('Content-Type', 'text/x-foo')
                return u"Foo \u263a"

        view = ViewSubclass(context)
        view.authorization = lambda ctx, rq: True

        request = RequestStub(method='PUT')
        self.assertNotEquals(view.render(request), '')
        self.assertEquals(request.code, 405)
        self.assertEquals(request.reason, 'Method Not Allowed')
        self.assertEquals(request.headers['allow'], 'FOO, GET, HEAD')

        request = RequestStub(method='FOO')
        self.assert_(view.request is None)
        self.assertEquals(view.render(request), 'Foo \xe2\x98\xba')
        self.assertEquals(request.code, 200)
        self.assertEquals(request.reason, 'OK')
        self.assertEquals(request.headers['content-type'],
                          'text/x-foo; charset=UTF-8')
        self.assert_(view.request is None)

        view.authorization = lambda ctx, rq: False
        request = RequestStub(method='FOO')
        result = view.render(request)
        self.assertEquals(request.code, 401)
        self.assertEquals(result, "Bad username or password")
        self.assertEquals(request.headers['www-authenticate'],
                          'basic realm="SchoolTool"')
        self.assertEquals(request.headers['content-type'],
                          'text/plain; charset=UTF-8')
        self.assert_(view.request is None)

    def test_unauthorized(self):
        from schooltool.rest import View
        view = View(None)
        request = RequestStub()
        result = view.unauthorized(request)
        self.assertEquals(request.code, 401)
        self.assertEquals(result, "Bad username or password")
        self.assertEquals(request.headers['www-authenticate'],
                          'basic realm="SchoolTool"')
        self.assertEquals(request.headers['content-type'],
                          'text/plain; charset=UTF-8')

    def test_render_calls_unauthorized(self):
        from schooltool.rest import View
        from schooltool.rest import Unauthorized
        view = View(None)

        def do_GET(request):
            raise Unauthorized

        view.do_GET = do_GET
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(result, "Bad username or password")
        self.assertEquals(request.code, 401)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.rest'))
    suite.addTest(unittest.makeSuite(TestTemplate))
    suite.addTest(unittest.makeSuite(TestSchoolToolTraverse))
    suite.addTest(unittest.makeSuite(TestErrorViews))
    suite.addTest(unittest.makeSuite(TestView))
    return suite

if __name__ == '__main__':
    unittest.main()
