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
from schooltool.browser.tests import RequestStub, setPath


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


class TestAppView(unittest.TestCase):

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

    def test(self):
        view = self.createView()
        request = RequestStub()
        result = view.render(request)
        self.assert_('Username' in result)
        self.assert_('error' not in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")

    def test_post(self):
        view = self.createView()
        request = RequestStub(method='POST',
                              args={'username': 'manager',
                                    'password': 'schooltool'})
        request.site = SiteStub()
        result = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/manager')

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
        from schooltool.browser.app import PersonContainerView
        from schooltool.browser.app import GroupContainerView
        view = self.createView()
        app = view.context
        request = RequestStub()

        def assertTraverses(name, viewclass, context=None):
            destination = view._traverse(name, request)
            self.assert_(isinstance(destination, viewclass))
            self.assert_(destination.context is context)
            return destination

        assertTraverses('persons', PersonContainerView, app['persons'])
        assertTraverses('groups', GroupContainerView, app['groups'])
        css = assertTraverses('schooltool.css', StaticFile)
        self.assertEquals(css.content_type, 'text/css')
        self.assertRaises(KeyError, view._traverse, 'nosuchpage', request)


class TestPersonContainerView(unittest.TestCase):

    def test_traverse(self):
        from schooltool.model import Person
        from schooltool.browser.app import PersonContainerView
        from schooltool.browser.model import PersonView
        container = {'person': Person()}
        view = PersonContainerView(container)
        personview = view._traverse('person', RequestStub())
        self.assert_(isinstance(personview, PersonView))
        self.assertRaises(KeyError, view._traverse, 'missing', RequestStub())


class TestGroupContainerView(unittest.TestCase):

    def test_container(self):
        from schooltool.model import Group
        from schooltool.browser.app import GroupContainerView
        container = {'foo': Group('foo')}
        view = GroupContainerView(container)
        view2 = view._traverse('foo', RequestStub())
        self.assertEquals(view2.__class__.__name__, 'GroupView')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestPersonContainerView))
    suite.addTest(unittest.makeSuite(TestGroupContainerView))
    return suite


if __name__ == '__main__':
    unittest.main()
