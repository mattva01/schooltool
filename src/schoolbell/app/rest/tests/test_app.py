#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Tests for schollbell.rest.app

$Id$
"""

import unittest
from StringIO import StringIO

from zope.app.testing import ztapi
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.app.testing import setup
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.container.interfaces import INameChooser

from schoolbell.app.app import SimpleNameChooser
from schoolbell.app.rest.app import GroupContainerView
from schoolbell.app.interfaces import IGroupContainer


from schoolbell.app.rest.tests.utils import XMLCompareMixin, QuietLibxml2Mixin
from schoolbell.app.rest.xmlparsing import XMLDocument, XMLParseError


class TestAppView(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        from schoolbell.app.rest.app import ApplicationView
        from schoolbell.app.app import SchoolBellApplication
        setup.placefulSetUp()
        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)
        self.view = ApplicationView(self.app, TestRequest())

    def tearDown(self):
        setup.placefulTearDown()

    def test_render_Usingxpath(self):
        result = self.view.GET()

        doc = XMLDocument(result)
        doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

        def oneNode(expr):
            nodes = doc.query(expr)
            self.assertEquals(len(nodes), 1,
                              "%s matched %d nodes" % (expr, len(nodes)))
            return nodes[0]

        try:
            nodes = doc.query('/schooltool/containers')
            self.assertEquals(len(nodes), 1)
            nodes = doc.query('/schooltool/containers/container')
            self.assertEquals(len(nodes), 3)

            persons = oneNode('/schooltool/containers/container'
                              '[@xlink:href="http://127.0.0.1/persons"]')
            self.assertEquals(persons['xlink:type'], 'simple')
            self.assertEquals(persons['xlink:title'], 'persons')

            groups = oneNode('/schooltool/containers/container'
                             '[@xlink:href="http://127.0.0.1/groups"]')
            self.assertEquals(groups['xlink:type'], 'simple')
            self.assertEquals(groups['xlink:title'], 'groups')

            notes = oneNode('/schooltool/containers/container'
                            '[@xlink:href="http://127.0.0.1/resources"]')
            self.assertEquals(notes['xlink:type'], 'simple')
            self.assertEquals(notes['xlink:title'], 'resources')
        finally:
            doc.free()

    def test_render(self):
        result = self.view.GET()
        response = self.view.request.response
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
              <message>Welcome to the SchoolTool server</message>
              <containers>
                <container xlink:type="simple"
                           xlink:href="http://127.0.0.1/persons"
                           xlink:title="persons"/>
                <container xlink:href="http://127.0.0.1/resources"
                           xlink:title="resources"
                           xlink:type="simple"/>
                <container xlink:type="simple"
                           xlink:href="http://127.0.0.1/groups"
                           xlink:title="groups"/>
              </containers>
            </schooltool>
            """, recursively_sort=["schooltool"])


class ContainerViewTestMixin(XMLCompareMixin, QuietLibxml2Mixin):
    """Common code for Container View tests"""

    def setUp(self):
        from schoolbell.app.app import SchoolBellApplication

        setup.placefulSetUp()
        self.setUpLibxml2()

        ztapi.provideAdapter(IGroupContainer,
                             INameChooser,
                             SimpleNameChooser)

        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)

    def tearDown(self):
        self.tearDownLibxml2()
        setup.placefulTearDown()


class TestGroupContainerView(ContainerViewTestMixin,
                             unittest.TestCase):
    """Test for GroupContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
        from schoolbell.app.app import Group

        self.group = self.app['groups']['root'] = Group("Root group")
        self.groupContainer = self.app['groups']

    def test_render(self):
        view = GroupContainerView(self.groupContainer,
                                  TestRequest())
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>groups</name>
              <items>
                <item xlink:href="http://127.0.0.1/groups/root"
                      xlink:type="simple" xlink:title="Root group"/>
              </items>
            </container>
            """)

    def test_post(self, suffix="", view=None,
                  body="""<object xmlns="http://schooltool.org/ns/model/0.1"
                                  title="New Group"/>"""):
        view = GroupContainerView(self.groupContainer,
                                  TestRequest(StringIO(body)))
        result = view.POST()
        response = view.request.response

        self.assertEquals(response.getStatus(), 201)
        self.assertEquals(response._reason, "Created")

        location = response.getHeader('location')
        base = "http://127.0.0.1/groups/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['groups'].keys())
        self.assertEquals(response.getHeader('content-type'),
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        return name

    def test_post_with_a_description(self):
        name = self.test_post(body='''
            <object title="New Group"
                    description="A new group"
                    xmlns='http://schooltool.org/ns/model/0.1'/>''')
        self.assertEquals(self.app['groups'][name].title, 'New Group')
        self.assertEquals(self.app['groups'][name].description, 'A new group')
        self.assertEquals(name, 'new-group')

    def test_post_error(self):
        view = GroupContainerView(
            self.groupContainer,
            TestRequest(StringIO('<element title="New Group">')))
        self.assertRaises(XMLParseError, view.POST)


class TestGroupFileFactory(unittest.TestCase):

    def setUp(self):
        from schoolbell.app.app import GroupContainer
        from schoolbell.app.rest.app import GroupFileFactory

        self.groupContainer = GroupContainer()
        self.factory = GroupFileFactory(self.groupContainer)

    def test_title(self):
        group = self.factory("new_group", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Group"/>''')

        self.assertEquals(group.title, "New Group")

    def test_description(self):
        group = self.factory("new_group", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Group"
                                description="Boo"/>''')

        self.assertEquals(group.title, "New Group")
        self.assertEquals(group.description, "Boo")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(test) for test in
                    (TestAppView,
                     TestGroupContainerView,
                     TestGroupFileFactory)])
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
