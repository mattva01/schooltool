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
Unit tests for schooltool.views.relationship

$Id$
"""

from logging import INFO
import unittest
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.views.tests import RequestStub

__metaclass__ = type


class TestRelationshipsView(RegistriesSetupMixin, QuietLibxml2Mixin,
                            unittest.TestCase):

    def setUp(self):
        from schooltool.views.relationship import RelationshipsView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("sub", title="subgroup")
        self.new = app['groups'].new("new", title="New Group")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.sub, member=self.per)

        self.request = RequestStub("http://localhost/groups/sub/relationships")
        self.view = RelationshipsView(self.sub)
        self.view.request = self.request
        self.view.authorization = lambda ctx, rq: True
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def test_listLinks(self):
        from pprint import pformat
        result = self.view.listLinks()
        self.assertEquals(len(result), 2)
        self.assert_({'traverse': '/persons/p',
                      'role': 'http://schooltool.org/ns/membership/member',
                      'type': 'http://schooltool.org/ns/membership',
                      'title': 'Pete',
                      'href': '/groups/sub/relationships/0002'}
                     in result, pformat(result))
        self.assert_({'traverse': '/groups/root',
                      'role': 'http://schooltool.org/ns/membership/group',
                      'type': 'http://schooltool.org/ns/membership',
                      'title': 'group',
                      'href': '/groups/sub/relationships/0001'}
                     in result, pformat(result))

    def test_getValencies(self):
        result = self.view.getValencies()
        self.assertEquals(result,
                          [{'type':'http://schooltool.org/ns/membership',
                            'role':'http://schooltool.org/ns/membership/group'
                            }])

    def test_traverse(self):
        from schooltool.interfaces import ILink
        from schooltool.views.relationship import LinkView
        request = RequestStub("http://localhost/groups/sub/relationships/0001")
        result = self.view._traverse('0001', request)
        self.assert_(isinstance(result, LinkView), "is LinkView")
        self.assert_(ILink.providedBy(result.context), "is ILink")

    def testGET(self):
        request = RequestStub("http://localhost/groups/sub/relationships/")
        result = self.view.render(request)
        self.assert_('<valencies>' in result)
        self.assert_('<existing>' in result)
        self.assert_(
            '<relationships xmlns:xlink="http://www.w3.org/1999/xlink">'
            in result)
        self.assert_(
            'xlink:role="http://schooltool.org/ns/membership/group"' in result)
        self.assert_(
            'xlink:role="http://schooltool.org/ns/membership/member"'
            in result)

    def testPOST(self):
        request = RequestStub("http://localhost/groups/sub/relationships/",
            method='POST',
            body='''<relationship xmlns="http://schooltool.org/ns/model/0.1"
                      xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple"
                      xlink:role="http://schooltool.org/ns/membership/group"
                      xlink:arcrole="http://schooltool.org/ns/membership"
                      xlink:href="/groups/new"/>''')
        self.assertEquals(len(self.sub.listLinks()), 2)
        self.assert_(self.new not in
                     [l.traverse() for l in self.sub.listLinks()])
        result = self.view.render(request)
        self.assertEquals(request.code, 201)
        self.assertEquals(request.site.applog,
                [(None, 'Relationship created: /groups/sub/relationships/0003',
                  INFO)])
        self.assertEquals(len(self.sub.listLinks()), 3)
        self.assert_(self.new in
                     [l.traverse() for l in self.sub.listLinks()])
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        location = "http://localhost:7001/groups/sub/relationships/0003"
        self.assertEquals(request.headers['location'], location)
        self.assert_(location in result)

    def testBadPOSTs(self):
        bad_requests = [
            # No xmlns
            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="BADPATH"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="BAD URI"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/nonexistent"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            />''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:title="http://schooltool.org/ns/membership"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/member"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/new"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/root"/>''',

            '''<relationship xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns="http://schooltool.org/ns/model/0.1"
            xlink:type="simple"
            xlink:role="http://schooltool.org/ns/membership/group"
            xlink:arcrole="http://schooltool.org/ns/membership"
            xlink:href="/groups/root" bad_xml>''',
            ]

        for body in bad_requests:
            request = RequestStub("http://localhost/groups/sub/relationships",
                                  method="POST", body=body)
            self.assertEquals(len(self.sub.listLinks()), 2)
            result = self.view.render(request)
            self.assertEquals(request.code, 400,
                    "%d: %s\n%s" % (bad_requests.index(body), result, body))
            self.assertEquals(request.site.applog, [])
            self.assertEquals(request.headers['content-type'],
                              "text/plain; charset=UTF-8")
            self.assertEquals(len(self.sub.listLinks()), 2)


class TestLinkView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.relationship import LinkView
        from schooltool.model import Group
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="Subordinate Group")

        links = Membership(group=self.group, member=self.sub)

        self.link = links['member']
        self.view = LinkView(self.link)
        self.view.authorization = lambda ctx, rq: True

    def testGET(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost%s" % getPath(self.link))
        result = self.view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
        <relationship xmlns:xlink="http://www.w3.org/1999/xlink"
                      xlink:type="simple"
                      xlink:role="http://schooltool.org/ns/membership/member"
                      xlink:title="Subordinate Group"
                      xlink:arcrole="http://schooltool.org/ns/membership"
                      xlink:href="/groups/subgroup"/>
        """)

    def testDELETE(self):
        from schooltool.component import getPath
        url = "http://localhost%s" % getPath(self.link)
        request = RequestStub(url, method="DELETE")
        self.assertEqual(len(self.sub.listLinks()), 1)
        result = self.view.render(request)
        self.assertEqual(request.site.applog,
                         [(None, 'Link removed: /groups/root/0001', INFO)])
        self.assertEqual(result, 'Link removed')
        self.assertEqual(len(self.sub.listLinks()), 0)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelationshipsView))
    suite.addTest(unittest.makeSuite(TestLinkView))
    return suite

if __name__ == '__main__':
    unittest.main()

