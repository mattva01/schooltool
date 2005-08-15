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
Tests for groups.

$Id: test_app.py 4691 2005-08-12 18:59:44Z srichter $
"""
import unittest
from cStringIO import StringIO
from zope.publisher.browser import TestRequest
from zope.testing import doctest

from schoolbell.app.rest.tests.test_app import ApplicationObjectViewTestMixin
from schoolbell.app.rest.tests.test_app import ContainerViewTestMixin
from schoolbell.app.rest.tests.test_app import FileFactoriesSetUp
from schoolbell.app.rest.xmlparsing import XMLParseError

from schoolbell.app.resource.resource import Resource, ResourceContainer
from schoolbell.app.resource.interfaces import IResourceContainer
from schoolbell.app.resource.rest.resource import ResourceView, ResourceFile
from schoolbell.app.resource.rest.resource import ResourceContainerView
from schoolbell.app.resource.rest.resource import ResourceFileFactory


class TestResourceContainerView(ContainerViewTestMixin,
                                unittest.TestCase):
    """Test for ResourceContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)

        self.resourceContainer = self.app['resources'] = ResourceContainer()
        self.resource = self.app['resources']['root'] = Resource("Root resource")

    def test_render(self):
        view = ResourceContainerView(self.resourceContainer,
                                  TestRequest())
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>resources</name>
              <items>
                <item xlink:href="http://127.0.0.1/resources/root"
                      xlink:type="simple" xlink:title="Root resource"/>
              </items>
              <acl xlink:href="http://127.0.0.1/resources/acl" xlink:title="ACL"
                   xlink:type="simple"/>
            </container>
            """)

    def test_post(self, suffix="", view=None,
                  body="""<object xmlns="http://schooltool.org/ns/model/0.1"
                                  title="New Resource"/>"""):
        view = ResourceContainerView(self.resourceContainer,
                                  TestRequest(StringIO(body)))
        result = view.POST()
        response = view.request.response

        self.assertEquals(response.getStatus(), 201)
        self.assertEquals(response._reason, "Created")

        location = response.getHeader('location')
        base = "http://127.0.0.1/resources/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['resources'].keys())
        self.assertEquals(response.getHeader('content-type'),
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        return name

    def test_post_with_a_description(self):
        name = self.test_post(body='''
            <object title="New Resource"
                    description="A new resource"
                    xmlns='http://schooltool.org/ns/model/0.1'/>''')
        self.assertEquals(self.app['resources'][name].title, 'New Resource')
        self.assertEquals(self.app['resources'][name].description, 'A new resource')
        self.assertEquals(name, 'Resource')

    def test_post_error(self):
        view = ResourceContainerView(
            self.resourceContainer,
            TestRequest(StringIO('<element title="New Resource">')))
        self.assertRaises(XMLParseError, view.POST)


class TestResourceFileFactory(unittest.TestCase):

    def setUp(self):
        self.resourceContainer = ResourceContainer()
        self.factory = ResourceFileFactory(self.resourceContainer)

    def test_title(self):
        resource = self.factory("new_resource", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Resource"/>''')

        self.assertEquals(resource.title, "New Resource")

    def test_description(self):
        resource = self.factory("new_resource", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Resource"
                                description="Boo"/>''')

        self.assertEquals(resource.title, "New Resource")
        self.assertEquals(resource.description, "Boo")



class TestResourceFile(FileFactoriesSetUp, unittest.TestCase):
    """A test for IResource IWriteFile adapter"""

    def testWrite(self):
        rc = ResourceContainer()
        resource = Resource("Mud")
        rc['resource'] = resource

        file = ResourceFile(resource)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="New Mud"
                              description="Baa"/>''')

        self.assertEquals(resource.title, "New Mud")
        self.assertEquals(resource.description, "Baa")


class TestResourceView(ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of a resource."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        self.app['resources'] = ResourceContainer()
        self.testObject = self.app['resources']['root'] = Resource("Root resource")

    def makeTestView(self, object, request):
        return ResourceView(object, request)

    def testGET(self):
        """Tests the GET method of the view."""

        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<resource xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root resource</title>
                   <description/>
                   <isLocation>
                     False
                   </isLocation>

                   <relationships xlink:href="http://127.0.0.1/resources/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/resources/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/resources/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </resource>""")

    def testGETDescription(self):

        self.testObject.description = "Foo"

        result, response = self.get()

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<resource xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root resource</title>
                   <description>Foo</description>
                   <isLocation>False</isLocation>
                   <relationships xlink:href="http://127.0.0.1/resources/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/resources/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/resources/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </resource>""")

    def testGETIsLocation(self):

        self.testObject.isLocation = True

        result, response = self.get()

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<resource xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root resource</title>
                   <description/>
                   <isLocation>True</isLocation>
                   <relationships xlink:href="http://127.0.0.1/resources/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/resources/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/resources/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </resource>""")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(test) for test in
                    (TestResourceContainerView,
                     TestResourceFileFactory,
                     TestResourceFile,
                     TestResourceView)])

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
