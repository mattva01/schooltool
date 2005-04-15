import unittest
from StringIO import StringIO

import zope

from zope.interface import Interface
from zope.app.traversing.interfaces import ITraversable
from zope.app.container.interfaces import INameChooser
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.publisher.http import HTTPRequest
from zope.app.testing import setup, ztapi
from zope.app.traversing.interfaces import IContainmentRoot

from schoolbell.app.rest.errors import RestError
from schoolbell.relationship.interfaces import IRelationshipSchema
from schoolbell.relationship.uri import IURIObject
from schoolbell.app.membership import Membership
from schoolbell.app.app import SimpleNameChooser
from schoolbell.relationship.annotatable import getRelationshipLinks
from schoolbell.app.interfaces import IGroupContainer
from schoolbell.app.rest.tests.utils import XMLCompareMixin, QuietLibxml2Mixin
from schoolbell.app.rest.xmlparsing import XMLDocument, XMLParseError
from schoolbell.app.membership import Membership, URIMember, URIGroup
from schoolbell.app.rest.xmlparsing import XMLValidationError

class CommonSetupMixin(XMLCompareMixin, QuietLibxml2Mixin):
    def setUp(self):
        from schoolbell.app.app import SchoolBellApplication
        from schoolbell.app.app import Group, Person
        from schoolbell.relationship.tests import setUpRelationships

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

        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)
        self.group = self.app['groups']["root"] = Group("group")
        self.new = self.app['groups']["new"] = Group("New Group")
        self.person = self.app['persons']["pete"] = Person(username="pete",
                                                           title="Pete")
        self.person2 = self.app['persons']["john"] = Person(username="john",
                                                            title="John")

        Membership(group=self.group, member=self.person)
        Membership(group=self.new, member=self.person)
        Membership(group=self.new, member=self.person2)


class TestRelationshipsView(CommonSetupMixin, unittest.TestCase):

    def setUp(self):
        from schoolbell.app.rest.relationships import RelationshipsView
        CommonSetupMixin.setUp(self)
        self.request = TestRequest()
        self.view = RelationshipsView(self.new, self.request)

    def tearDown(self):
        self.tearDownLibxml2()

    def test_listLinks(self):
        from pprint import pformat
        result = self.view.listLinks()
        self.assertEquals(len(result), 2)
        self.assert_({'traverse': '/persons/pete',
                      'role': 'http://schooltool.org/ns/membership/group',
                      'type': 'http://schooltool.org/ns/membership',
                      'href': '/groups/new/relationships/1'}
                     in result, pformat(result))
        self.assert_({'traverse': '/persons/john',
                      'role': 'http://schooltool.org/ns/membership/group',
                      'type': 'http://schooltool.org/ns/membership',
                      'href': '/groups/new/relationships/2'}
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
                                 xlink:href="/persons/pete"
                                 xlink:role="http://schooltool.org/ns/membership/group"
                                 xlink:type="simple">
                     <manage xlink:href="/groups/new/relationships/1"
                             xlink:type="simple"/>
                   </relationship>
                   <relationship xlink:arcrole="http://schooltool.org/ns/membership"
                                 xlink:href="/persons/john"
                                 xlink:role="http://schooltool.org/ns/membership/group"
                                 xlink:type="simple">
                     <manage xlink:href="/groups/new/relationships/2"
                             xlink:type="simple"/>
                   </relationship>
                 </existing>
               </relationships>""")

    def testPOST(self):
        from schoolbell.app.rest.relationships import RelationshipsView

        body = """<relationship xmlns="http://schooltool.org/ns/model/0.1"
                                     xmlns:xlink="http://www.w3.org/1999/xlink"
                                     xlink:type="simple"
                                     xlink:role="http://schooltool.org/ns/membership/group"
                                     xlink:arcrole="http://schooltool.org/ns/membership"
                                     xlink:href="/persons/john"/>"""

        request = TestRequest(StringIO(body))
        view = RelationshipsView(self.group, request)

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
        location = "/groups/root/relationships/2"
        self.assertEquals(response.getHeader('location'), location)
        self.assert_(location in result)

    def testBadPOSTs(self):
        from schoolbell.app.rest.relationships import RelationshipsView
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
            view = RelationshipsView(self.new, request)

            self.assertEquals(len(view.listLinks()), 2)
            self.assertRaises(exception, view.POST)
            self.assertEquals(len(view.listLinks()), 2)


class TestLinkView(CommonSetupMixin, unittest.TestCase):

    def setUp(self):
        from schoolbell.app.rest.relationships import LinkView
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
                      xlink:href="/persons/pete"/>
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

