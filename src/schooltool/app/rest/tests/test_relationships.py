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
Tests for schollbell.rest.relationship

$Id$
"""

import unittest
from StringIO import StringIO

import zope
from zope.interface import Interface
from zope.app.traversing.interfaces import ITraversable
from zope.app.container.interfaces import INameChooser
from zope.publisher.browser import TestRequest
from zope.app.testing import setup, ztapi

from schooltool.app.rest.errors import RestError
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.interfaces import IRelationshipSchema
from schooltool.relationship.uri import IURIObject
from schooltool.app.membership import Membership, URIMember, URIGroup
from schooltool.app.app import SimpleNameChooser
from schooltool.relationship.annotatable import getRelationshipLinks
from schooltool.group.interfaces import IGroupContainer
from schooltool.app.rest.testing import XMLCompareMixin, QuietLibxml2Mixin
from schooltool.xmlparsing import XMLParseError
from schooltool.xmlparsing import XMLValidationError
from schooltool.testing import setup as sbsetup


class CommonSetupMixin(XMLCompareMixin, QuietLibxml2Mixin):

    def setUp(self):
        from schooltool.group.group import Group
        from schooltool.person.person import Person
        from schooltool.relationship.tests import setUpRelationships

        setup.placefulSetUp()
        setup.setUpAnnotations()
        self.setUpLibxml2()
        setUpRelationships()

        ztapi.provideUtility(IRelationshipSchema,
                             Membership,
                             name="http://schooltool.org/ns/membership")
        ztapi.provideUtility(IURIObject,
                             URIGroup,
                             name="http://schooltool.org/ns/membership/member")
        ztapi.provideUtility(IURIObject,
                             URIMember,
                             name="http://schooltool.org/ns/membership/group")
        ztapi.provideView(Interface, Interface, ITraversable, 'view',
                          zope.app.traversing.namespace.view)
        ztapi.provideAdapter(IGroupContainer,
                             INameChooser,
                             SimpleNameChooser)

        self.app = sbsetup.setupSchoolToolSite()

        self.group = self.app['groups']["root"] = Group("group")
        self.new = self.app['groups']["new"] = Group("New Group")
        self.person = self.app['persons']["pete"] = Person(username="pete",
                                                           title="Pete")
        self.person2 = self.app['persons']["john"] = Person(username="john",
                                                            title="John")

        Membership(group=self.group, member=self.person)
        Membership(group=self.new, member=self.person)
        Membership(group=self.new, member=self.person2)

    def tearDown(self):
        self.tearDownLibxml2()
        setup.placefulTearDown()


class TestRelationshipsView(CommonSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.app.rest.relationships import RelationshipsView
        CommonSetupMixin.setUp(self)
        self.request = TestRequest()
        self.view = RelationshipsView(IRelationshipLinks(self.new), self.request)

    def test_listLinks(self):
        from pprint import pformat
        result = self.view.listLinks()
        self.assertEquals(len(result), 2)
        self.assert_({'traverse': 'http://127.0.0.1/persons/pete',
                      'role': 'http://schooltool.org/ns/membership/member',
                      'type': 'http://schooltool.org/ns/membership',
                      'href': 'http://127.0.0.1/groups/new/relationships/1'}
                     in result, pformat(result))
        self.assert_({'traverse': 'http://127.0.0.1/persons/john',
                      'role': 'http://schooltool.org/ns/membership/member',
                      'type': 'http://schooltool.org/ns/membership',
                      'href': 'http://127.0.0.1/groups/new/relationships/2'}
                     in result, pformat(result))

    def testGET(self):
        result = self.view.GET()
        response = self.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")

        self.assertEqualsXML(result,
            """<relationships xmlns="http://schooltool.org/ns/model/0.1"
                              xmlns:xlink="http://www.w3.org/1999/xlink">
                 <existing>
                   <relationship xlink:arcrole="http://schooltool.org/ns/membership"
                                 xlink:href="http://127.0.0.1/persons/pete"
                                 xlink:role="http://schooltool.org/ns/membership/member"
                                 xlink:type="simple">
                     <manage xlink:href="http://127.0.0.1/groups/new/relationships/1"
                             xlink:type="simple"/>
                   </relationship>
                   <relationship xlink:arcrole="http://schooltool.org/ns/membership"
                                 xlink:href="http://127.0.0.1/persons/john"
                                 xlink:role="http://schooltool.org/ns/membership/member"
                                 xlink:type="simple">
                     <manage xlink:href="http://127.0.0.1/groups/new/relationships/2"
                             xlink:type="simple"/>
                   </relationship>
                 </existing>
               </relationships>""")

    def testPOST(self):
        from schooltool.app.rest.relationships import RelationshipsView

        body = """<relationship xmlns="http://schooltool.org/ns/model/0.1"
                                     xmlns:xlink="http://www.w3.org/1999/xlink"
                                     xlink:type="simple"
                                     xlink:role="http://schooltool.org/ns/membership/member"
                                     xlink:arcrole="http://schooltool.org/ns/membership"
                                     xlink:href="http://127.0.0.1/persons/john"/>"""

        request = TestRequest(StringIO(body))
        view = RelationshipsView(IRelationshipLinks(self.group), request)

        self.assertEquals(len(view.listLinks()), 1)
        self.assert_(self.person2 not in
                     [l.target for l in getRelationshipLinks(self.group)])
        result = view.POST()
        response = view.request.response
        self.assertEquals(response.getStatus(), 201)
        self.assertEquals(len(view.listLinks()), 2)
        self.assert_(self.person2 in
                     [l.target for l in getRelationshipLinks(self.group)])
        self.assertEquals(response.getHeader('content-type'),
                          "text/plain; charset=UTF-8")
        location = "http://127.0.0.1/groups/root/relationships/2"
        self.assertEquals(response.getHeader('location'), location)
        self.assert_(location in result)

    def testBadPOSTs(self):
        from schooltool.app.rest.relationships import RelationshipsView
        bad_requests = [
            # Document not valid according to schema.
            (XMLValidationError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/membership/group"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="/groups/new"/>"""),
            # Bad URI: BADPATH
            (RestError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/membership/group"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="BADPATH"/>"""),
            # Bad URI: BADURI
            (RestError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:role="BADURI"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="/groups/new"/>"""),
            # Bad URI: http://schooltool.org/ns/nonexistent
            (RestError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/nonexistent"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="/groups/new"/>"""),
            # Document not valid according to schema.
            (XMLValidationError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/membership/group"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              />"""),
            # Document not valid according to schema.
            (XMLValidationError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="/groups/new"/>"""),
            # Document not valid according to schema.
            (XMLValidationError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/membership"
                              xlink:href="/groups/new"/>"""),
            # Ill-formed document.
            (XMLParseError,
             """<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                              xmlns="http://schooltool.org/ns/model/0.1"
                              xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/membership/group"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="/groups/root" bad_xml>"""),
            ]

        for exception, body in bad_requests:
            body = StringIO(body)
            request = TestRequest(body)
            view = RelationshipsView(IRelationshipLinks(self.new), request)

            self.assertEquals(len(view.listLinks()), 2)
            self.assertRaises(exception, view.POST)
            self.assertEquals(len(view.listLinks()), 2)


class TestLinkView(CommonSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.app.rest.relationships import LinkView
        CommonSetupMixin.setUp(self)
        self.request = TestRequest()
        self.view = LinkView(getRelationshipLinks(self.group)['1'], self.request)

    def testGET(self):
        result = self.view.GET()
        self.assertEquals(self.request.response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
        <relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple"
                      xlink:role="http://schooltool.org/ns/membership/member"
                      xlink:arcrole="http://schooltool.org/ns/membership"
                      xlink:href="http://127.0.0.1/persons/pete"/>
        """)

    def testDELETE(self):
        self.assertEqual(
            len([link for link in getRelationshipLinks(self.group)]), 1)
        result = self.view.DELETE()
        self.assertEqual(result, 'Link removed')
        self.assertEqual(
            len([link for link in getRelationshipLinks(self.group)]), 0)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationshipsView))
    suite.addTest(unittest.makeSuite(TestLinkView))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

