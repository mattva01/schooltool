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
from zope.publisher.browser import TestRequest
from zope.testing import doctest

from schoolbell.app.rest.tests.test_app import ApplicationObjectViewTestMixin
from schoolbell.app.rest.tests.test_app import ContainerViewTestMixin
from schoolbell.app.rest.tests.test_app import FileFactoriesSetUp

from schoolbell.app.group.group import Group, GroupContainer
from schoolbell.app.group.interfaces import IGroupContainer
from schoolbell.app.group.rest.group import GroupView, GroupFile
from schoolbell.app.group.rest.group import GroupContainerView
from schoolbell.app.group.rest.group import GroupFileFactory


class TestGroupFileFactory(unittest.TestCase):

    def setUp(self):
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


class TestGroupContainerView(ContainerViewTestMixin,
                             unittest.TestCase):
    """Test for GroupContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
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
              <acl xlink:href="http://127.0.0.1/groups/acl" xlink:title="ACL"
                   xlink:type="simple"/>
            </container>
            """)


class TestGroupFile(FileFactoriesSetUp, unittest.TestCase):
    """A test for IGroup IWriteFile adapter"""

    def testWrite(self):
        gc = GroupContainer()
        group = Group("Lillies")
        gc['group1'] = group

        file = GroupFile(group)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="New Group"
                              description="Boo"/>''')

        self.assertEquals(group.title, "New Group")
        self.assertEquals(group.description, "Boo")


class TestGroupView(ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of a group."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        self.testObject = self.app['groups']['root']

    def makeTestView(self, object, request):
        return GroupView(object, request)

    def testGET(self):

        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<group xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root group</title>
                   <description/>
                   <relationships xlink:href="http://127.0.0.1/groups/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/groups/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/groups/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </group>""")

    def testGETDescription(self):

        self.testObject.description = "Foo"

        result, response = self.get()

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<group xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root group</title>
                   <description>Foo</description>
                   <relationships xlink:href="http://127.0.0.1/groups/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/groups/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/groups/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </group>""")



def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(test) for test in
                    (TestGroupContainerView,
                     TestGroupFileFactory,
                     TestGroupFile,
                     TestGroupView)])

    suite.addTest(doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
