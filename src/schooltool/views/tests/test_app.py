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
Unit tests for schooltool.views.app

$Id: test_views.py 397 2003-11-21 11:38:01Z mg $
"""

import unittest
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.views.tests import RequestStub, UtilityStub, XPathTestContext

__metaclass__ = type


class TestAppView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.app import ApplicationView
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

        self.app.utilityService["foo"] = UtilityStub("Foo utility")

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
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
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
              <schooltt xlink:href="/schooltt"
                        xlink:title="Whole school timetables"
                        xlink:type="simple"/>
              <time-periods xlink:href="/time-periods"
                            xlink:title="Time periods"
                            xlink:type="simple"/>
              <ttschemas xlink:href="/ttschemas"
                         xlink:title="Timetable schemas"
                         xlink:type="simple"/>
       </schooltool>
            """, recursively_sort=["schooltool"])

    def test__traverse(self):
        from schooltool.views.app import ApplicationObjectContainerView
        from schooltool.views.utility import UtilityServiceView
        from schooltool.views.timetable import SchoolTimetableTraverseView
        request = RequestStub("http://localhost/groups")
        view = self.view._traverse('groups', request)
        self.assert_(view.__class__ is ApplicationObjectContainerView)
        self.assertRaises(KeyError, self.view._traverse, 'froups', request)

        view = self.view._traverse('utils', request)
        self.assert_(view.__class__ is UtilityServiceView)

        view = self.view._traverse('schooltt', request)
        self.assert_(view.__class__ is SchoolTimetableTraverseView)


class TestAppObjContainerView(XMLCompareMixin, RegistriesSetupMixin,
                              unittest.TestCase):

    def setUp(self):
        from schooltool.views.app import ApplicationObjectContainerView
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
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>groups</name>
              <items>
                <item xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="Root group"/>
              </items>
            </container>
            """)

    def test_post(self, suffix="", method="POST", body=None, view=None):
        if view is None:
            view = self.view
        request = RequestStub("http://localhost:8080/groups" + suffix,
                              method=method, body=body)
        result = view.render(request)
        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        location = request.headers['Location']
        base = "http://localhost:8080/groups/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['groups'].keys())
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assert_(location in result)
        return name

    def test_post_with_a_title(self):
        name = self.test_post(body='title="New Group"')
        self.assert_(self.app['groups'][name].title == 'New Group')

    def test_get_child(self, method="GET"):
        from schooltool.views.app import ApplicationObjectCreatorView
        view = ApplicationObjectCreatorView(self.app['groups'], 'foo')
        request = RequestStub("http://localhost/groups/foo", method=method)
        result = view.render(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")

    def test_delete_child(self):
        self.test_get_child(method="DELETE")

    def test_put_child(self):
        from schooltool.views.app import ApplicationObjectCreatorView
        view = ApplicationObjectCreatorView(self.app['groups'], 'foo')
        name = self.test_post(method="PUT", suffix="/foo", view=view)
        self.assertEquals(name, 'foo')

        view = ApplicationObjectCreatorView(self.app['groups'], 'bar')
        name = self.test_post(method="PUT", suffix="/bar", view=view,
                              body='title="Bar Bar"')
        self.assertEquals(name, 'bar')
        self.assert_(self.app['groups'][name].title == 'Bar Bar')

    def test__traverse(self):
        from schooltool.views.model import GroupView
        from schooltool.views.app import ApplicationObjectCreatorView
        request = RequestStub("http://localhost/groups/root")
        view = self.view._traverse('root', request)
        self.assert_(view.__class__ is GroupView)
        view = self.view._traverse('newchild', request)
        self.assert_(view.__class__ is ApplicationObjectCreatorView)
        self.assertEquals(view.context, self.view.context)
        self.assertEquals(view.name, 'newchild')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestAppObjContainerView))
    return suite

if __name__ == '__main__':
    unittest.main()
