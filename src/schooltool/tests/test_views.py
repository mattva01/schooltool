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

__metaclass__ = type


class RequestStub:

    code = 200
    reason = 'OK'

    def __init__(self, uri='', method='GET'):
        self.headers = {}
        self.uri = uri
        self.method = method

    def setHeader(self, header, value):
        self.headers[header] = value

    def setResponseCode(self, code, reason):
        self.code = code
        self.reason = reason


class TestTemplate(unittest.TestCase):

    def test_call(self):
        from schooltool.views import Template
        templ = Template('sample.pt')
        request = RequestStub()
        result = templ(request, foo='Foo', bar='Bar')
        self.assertEquals(request.headers['Content-Type'],
                     "text/html; charset=UTF-8")
        self.assertEquals(result, "code: 200\nfoo: Foo\nbar: Bar\n")


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

    def test_render(self):
        from schooltool.views import View, NotFoundView
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

        request = RequestStub(method='HEAD')
        view.template = TemplateStub(request, view, context, body)
        self.assertEquals(view.render(request), '')
        self.assertEquals(request.headers['Content-Length'], len(body))

        request = RequestStub(method='PUT')
        self.assertNotEquals(view.render(request), '')
        self.assertEquals(request.code, 405)
        self.assertEquals(request.reason, 'Method Not Allowed')
        self.assertEquals(request.headers['Allow'], 'GET, HEAD')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTemplate))
    suite.addTest(unittest.makeSuite(TestErrorViews))
    suite.addTest(unittest.makeSuite(TestView))
    return suite

if __name__ == '__main__':
    unittest.main()
