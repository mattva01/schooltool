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
from schooltool.views.tests import RequestStub

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
        return self.body


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
            ("2000-01-01 00:00:00.000000", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2000-01-01T00:00:00", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2005-12-23 11:22:33", dt(2005, 12, 23, 11, 22, 33)),
            ("2005-12-23T11:22:33", dt(2005, 12, 23, 11, 22, 33)),
            ("2005-12-23T11:22:33.4", dt(2005, 12, 23, 11, 22, 33, 400000)),
            ("2005-12-23T11:22:33.456789", dt(2005, 12, 23, 11, 22, 33,
                                              456789)),
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

    def test_notFoundPage(self):
        from schooltool.views import notFoundPage
        request = RequestStub()
        result = notFoundPage(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")

    def test_textErrorPage(self):
        from schooltool.views import textErrorPage
        request = RequestStub()
        result = textErrorPage(request, "Not ready to take off", 747, "Wait")
        self.assertEquals(request.code, 747)
        self.assertEquals(request.reason, "Wait")
        self.assertEquals(result, "Not ready to take off")

        request = RequestStub()
        result = textErrorPage(request, 42)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(result, "42")


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
        request = RequestStub()
        view.template = TemplateStub(request, view, context, body)
        self.assertEquals(view.render(request), body)

    def test_do_HEAD(self):
        from schooltool.views import View
        context = object()
        body = 'foo'
        view = View(context)
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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHelpers))
    suite.addTest(unittest.makeSuite(TestTemplate))
    suite.addTest(unittest.makeSuite(TestErrorViews))
    suite.addTest(unittest.makeSuite(TestView))
    suite.addTest(unittest.makeSuite(TestXMLPseudoParser))
    return suite

if __name__ == '__main__':
    unittest.main()
