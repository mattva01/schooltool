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
from helpers import dedent, diff

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

class MemberStub:
    from zope.interface import implements
    from schooltool.interfaces import IGroupMember
    added = None
    removed = None
    implements(IGroupMember)
    def notifyAdd(self, group, name):
        self.added = group
    def notifyRemove(self, group):
        self.removed = group


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


class TestGroupView(unittest.TestCase):

    def setUp(self):
        from schooltool.views import GroupView
        from schooltool.model import RootGroup, Group, Person

        self.group = RootGroup("group")
        self.sub = Group("subgroup")
        self.per = Person("p")
        self.subkey = self.group.add(self.sub)
        self.perkey = self.group.add(self.per)

        self.view = GroupView(self.group)

    def test_traverse(self):
        from schooltool.views import GroupView, PersonView
        from schooltool.interfaces import ComponentLookupError

        subview = self.view._traverse(str(self.subkey), RequestStub())
        self.assertEqual(subview.__class__, GroupView)

        perview = self.view._traverse(str(self.perkey), RequestStub())
        self.assertEqual(perview.__class__, PersonView)

        self.assertRaises(KeyError, self.view._traverse,
                          "Nonexistent", RequestStub())

        self.assertRaises(KeyError, self.view._traverse,
                          None, RequestStub())

        trash = self.group.add(MemberStub())
        self.assertRaises(ComponentLookupError, self.view._traverse,
                          trash, RequestStub())

    def test_render(self):
        request = RequestStub("http://localhost/group/")
        request.method = "GET"
        request.path = '/group'
        result = self.view.render(request)
        expected = dedent("""
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>group</name>
              <item xlink:type="simple" xlink:title="subgroup"
                    xlink:href="/%s" />
              <item xlink:type="simple" xlink:title="p" xlink:href="/%s" />
            </group>
            """ % (self.subkey, self.perkey))
        self.assertEqual(result, expected,
                         'expected != actual\n%s' % diff(expected, result))


class TestPersonView(unittest.TestCase):

    def setUp(self):
        from schooltool.views import PersonView
        from schooltool.model import Group, Person
        from schooltool.interfaces import IContainmentRoot
        from zope.interface import directlyProvides

        self.group = Group("group")
        directlyProvides(self.group, IContainmentRoot)
        self.sub = Group("subgroup")
        self.per = Person("Pete")
        self.subkey = self.group.add(self.sub)
        self.perkey = self.group.add(self.per)
        self.sub.add(self.per)

        self.view = PersonView(self.per)

    def test_render(self):
        request = RequestStub("http://localhost/group/")
        request.method = "GET"
        request.path = '/group/%s' % self.perkey
        result = self.view.render(request)
        expected = dedent("""
            <person xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>Pete</name>
              <groups>
                <item xlink:type="simple" xlink:href="/"
                      xlink:title="group" />
                <item xlink:type="simple" xlink:href="/0"
                      xlink:title="subgroup" />
              </groups>
            </person>
            """)
        self.assertEqual(result, expected,
                         'expected != actual\n%s' % diff(expected, result))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTemplate))
    suite.addTest(unittest.makeSuite(TestErrorViews))
    suite.addTest(unittest.makeSuite(TestView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestPersonView))
    return suite

if __name__ == '__main__':
    unittest.main()
