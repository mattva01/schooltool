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
Unit tests for guiclient.py
"""

import unittest
import socket
import datetime
from pprint import pformat
import libxml2
from schooltool.tests.helpers import dedent, diff
from schooltool.tests.utils import XMLCompareMixin

__metaclass__ = type

class ConnectionFactory:

    def __init__(self, response, error=None):
        self.response = response
        self.error = error
        self.connections = []

    def __call__(self, server, port):
        c = ConnectionStub(server, port, self.response, self.error)
        self.connections.append(c)
        return c


class ConnectionStub:

    def __init__(self, server, port, response, error):
        self.server = server
        self.port = port
        self.response = response
        self.error = error
        self.closed = False
        self.request_called = False

    def request(self, method, path, body=None, headers=None):
        if self.request_called:
            raise RuntimeError('ConnectionStub.request called more than once')
        self.request_called = True
        self.method = method
        self.path = path
        self.body = body
        self.headers = headers
        if self.error is not None:
            raise self.error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True
        if self.response is not None:
            self.response._body = ''


class ResponseStub:

    def __init__(self, status, reason, body='', **kw):
        self.status = status
        self.reason = reason
        self._body = body
        self._headers = {'server': 'UnitTest/0.0'}
        for k, v in kw.items():
            self._headers[k.lower()] = v
        self._read_called = False

    def read(self):
        if self._read_called:
            raise RuntimeError('ResponseStub.read called more than once')
        self._read_called = True
        return self._body

    def getheader(self, name):
        return self._headers[name.lower()]


class TestSchoolToolClient(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def newClient(self, response=None, error=None):
        from schooltool.guiclient import SchoolToolClient
        client = SchoolToolClient()
        client.connectionFactory = ConnectionFactory(response, error)
        return client

    def oneConnection(self, client):
        self.assertEquals(len(client.connectionFactory.connections), 1)
        return client.connectionFactory.connections[0]

    def checkConnPath(self, client, path):
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, path)

    def test_setServer(self):
        from schooltool.guiclient import SchoolToolClient
        server = 'example.com'
        port = 8081
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', 'doesnotmatter', server=version)
        client = self.newClient(response)
        client.setServer(server, port)
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)
        conn = self.oneConnection(client)
        self.assertEquals(conn.server, server)
        self.assertEquals(conn.port, port)
        self.assertEquals(client.server, server)
        self.assertEquals(client.port, port)

    def test_tryToConnect(self):
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', 'doesnotmatter', server=version)
        client = self.newClient(response)
        client.tryToConnect()
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)

        e = socket.error(23, 'out of spam')
        client = self.newClient(error=e)
        client.tryToConnect()
        self.assertEquals(client.status, 'out of spam (23)')
        self.assertEquals(client.version, '')

    def test_request(self):
        from schooltool.guiclient import SchoolToolClient
        path = '/path'
        body = 'spam'
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        client = self.newClient(response)
        result = client._request('FOO', path)
        conn = self.oneConnection(client)
        self.assertEquals(conn.server, SchoolToolClient.server)
        self.assertEquals(conn.port, SchoolToolClient.port)
        self.assertEquals(conn.method, 'FOO')
        self.assertEquals(conn.path, path)
        self.assertEquals(conn.headers, {})
        self.assert_(conn.body is None)
        self.assertEquals(result.status, 200)
        self.assertEquals(result.reason, 'OK')
        self.assertEquals(result.body, body)
        self.assert_(result._response is response)
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)
        self.assert_(conn.closed)

    def test_request_with_body_and_headers(self):
        from schooltool.guiclient import SchoolToolClient
        path = '/path'
        body = 'spam'
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        client = self.newClient(response)
        result = client._request('BAR', path, 'body body body',
                                 {'X-Foo': 'Foo!'})
        conn = self.oneConnection(client)
        self.assertEquals(conn.server, SchoolToolClient.server)
        self.assertEquals(conn.port, SchoolToolClient.port)
        self.assertEquals(conn.method, 'BAR')
        self.assertEquals(conn.path, path)
        self.assertEquals(conn.headers,
                          {'X-Foo': 'Foo!',
                           'Content-Type': 'text/xml',
                           'Content-Length': len('body body body')})
        self.assertEquals(conn.body, 'body body body')
        self.assertEquals(result.status, 200)
        self.assertEquals(result.reason, 'OK')
        self.assertEquals(result.body, body)
        self.assert_(result._response is response)
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)
        self.assert_(conn.closed)

    def test_request_with_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        path = '/path'
        e = socket.error(23, 'out of spam')
        client = self.newClient(error=e)
        try:
            result = client._request('GET', path)
        except SchoolToolError, e:
            self.assertEquals(str(e), 'out of spam (23)')
        else:
            self.fail("did not raise SchoolToolError")
        conn = self.oneConnection(client)
        self.assertEquals(client.status, "out of spam (23)")
        self.assertEquals(client.version, '')
        self.assert_(conn.closed)

    def test_getListOfPersons(self):
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred">Fred</item>
                <item xlink:href="/persons/barney">Barney</item>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
               </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        result = client.getListOfPersons()
        self.assertEquals(result, ['/persons/fred', '/persons/barney'])
        self.checkConnPath(client, '/persons')

    def test_getListOfPersons_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of persons'))
        self.assertRaises(SchoolToolError, client.getListOfPersons)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getListOfPersons)

    def test_getPersonInfo(self):
        person_id = '/persons/foo'
        body = dedent("""
            <html>
              <h1>Foo!</h1>
            </html>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        result = client.getPersonInfo(person_id)
        self.assertEquals(result, body)
        self.checkConnPath(client, person_id)

    def test_getPersonInfo_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        person_id = '/persons/bar'
        client = self.newClient(error=socket.error(23, 'out of persons'))
        self.assertRaises(SchoolToolError, client.getPersonInfo, person_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getPersonInfo, person_id)

    def test_getGroupTree(self):
        body = dedent("""
            <tree xmlns:xlink="http://www.w3.org/1999/xlink">
              <group xlink:type="simple" xlink:href="/groups/root"
                     xlink:title="root group">
                <group xlink:type="simple" xlink:href="/groups/group2"
                       xlink:title="group2">
                </group>
                <group xlink:type="simple" xlink:href="/groups/group1"
                       xlink:title="group1">
                  <group xlink:type="simple" xlink:href="/groups/group1a"
                         xlink:title="group1a">
                  </group>
                  <group xlink:type="simple" xlink:href="/groups/group1b"
                         xlink:title="group1b">
                  </group>
                </group>
              </group>
            </tree>
        """)
        expected = [(0, 'root group', '/groups/root'),
                    (1, 'group2',     '/groups/group2'),
                    (1, 'group1',     '/groups/group1'),
                    (2, 'group1a',    '/groups/group1a'),
                    (2, 'group1b',    '/groups/group1b'),
                   ]
        client = self.newClient(ResponseStub(200, 'OK', body))
        result = client.getGroupTree()
        self.assertEquals(list(result), expected)
        self.checkConnPath(client, '/groups/root/tree')

    def test_getGroupTree_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of trees'))
        self.assertRaises(SchoolToolError, client.getGroupTree)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getGroupTree)

    def test_getGroupInfo(self):
        body = dedent("""
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <item xlink:type="simple" xlink:href="/groups/group2"
                     xlink:title="group2" />
              <item xlink:type="simple" xlink:href="/persons/person1"
                     xlink:title="person1" />
              <item xlink:type="simple" xlink:href="/persons/person1/facets"
                     xlink:title="person1 facets" />
            </group>
        """)
        expected = [('person1', '/persons/person1')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        result = client.getGroupInfo(group_id)
        self.assertEquals(list(result.members), expected)
        self.checkConnPath(client, group_id)

    def test_getGroupInfo_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getGroupInfo, group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getGroupInfo, group_id)

    def test_getObjectRelationships(self):
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="title1" xlink:href="href1"
                              xlink:role="role1" xlink:arcrole="arcrole1" />
                <relationship xlink:title="title2" xlink:href="href2"
                    xlink:role="http://schooltool.org/ns/membership/group"
                    xlink:arcrole="http://schooltool.org/ns/membership" />
              </existing>
              <valencies>
                <relationship xlink:title="title3" xlink:href="href3"
                              xlink:role="role3" xlink:arcrole="arcrole3" />
              </valencies>
            </relationships>
        """)
        expected = [('arcrole1', 'role1', 'title1', 'href1'),
                    ('Membership', 'Group', 'title2', 'href2')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        result = client.getObjectRelationships(group_id)
        self.assertEquals(list(result), expected)
        self.checkConnPath(client, '%s/relationships' % group_id)

    def test_getObjectRelationships_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getObjectRelationships,
                          group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getObjectRelationships,
                          group_id)

    def test_getRollCall(self):
        body = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:href="/persons/p1" xlink:title="person 1"
                      presence="present" />
            </rollcall>
        """)
        expected = [('person 1', '/persons/p1', 'present')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        result = client.getRollCall(group_id)
        self.assertEquals(list(result), expected)
        self.checkConnPath(client, '%s/rollcall' % group_id)

    def test_getRollCall_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getRollCall, group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getRollCall, group_id)

    def test_submitRollCall(self):
        client = self.newClient(ResponseStub(200, 'OK', 'Accepted'))
        group_id = '/groups/group1'
        rollcall = [('/persons/p1', True, 'foo', True),
                    ('/persons/p2', False, 'bar', False),
                    ('/persons/p3', None, None, None)]
        client.submitRollCall(group_id, rollcall)
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '%s/rollcall' % group_id)
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body, dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
                <reporter xlink:type="simple" xlink:href="/persons/anonymous"/>
                <person xlink:type="simple" xlink:href="/persons/p1"
                        presence="present" comment="foo" resolved="resolved"/>
                <person xlink:type="simple" xlink:href="/persons/p2"
                        presence="absent" comment="bar" resolved="unresolved"/>
                <person xlink:type="simple" xlink:href="/persons/p3"/>
            </rollcall>
            """))

    def test_submitRollCall_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request', 'No foo'))
        group_id = '/groups/group1'
        rollcall = [('/persons/p3', None, None, None)]
        self.assertRaises(SchoolToolError,
                          client.submitRollCall, group_id, rollcall)

    def test_getAbsences(self):
        from schooltool.guiclient import AbsenceInfo
        body = dedent("""
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple" xlink:href="/p/absences/003"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06" />
            </absences>
        """)
        expected = [AbsenceInfo('/p/absences/003',
                                datetime.datetime(2001, 2, 28, 1, 1, 1), True,
                                False, datetime.datetime(2001, 2, 3, 4, 5, 6))]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getAbsences('/p')
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/p/absences')

    def test_getAbsences_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getAbsences, '/p')

    def test_getAbsenceComments(self):
        from schooltool.guiclient import AbsenceComment
        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="reporter"
                          xlink:href="/persons/supervisor001"/>
                <text>foo</text>
              </comment>
            </absence>
        """)
        expected = [AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   "reporter", "/persons/supervisor001",
                                   "", "", True, False,
                                   datetime.datetime(2001, 2, 3, 4, 5, 6),
                                   "foo")]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getAbsenceComments('/persons/john/absences/002')
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/persons/john/absences/002')

    def test_getAbsences_with_errors(self):
        from schooltool.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getAbsenceComments, '/p')

    def test__parsePeopleList(self):
        from schooltool.guiclient import SchoolToolClient
        client = SchoolToolClient()
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred">Fred</item>
                <item xlink:href="/persons/barney">Barney</item>
                <item xlink:href="/persons/barney/facets">Barney's facets</item>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
               </items>
            </container>
        """)
        result = client._parsePeopleList(body)
        self.assertEquals(result, ['/persons/fred', '/persons/barney'])

        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
               </items>
            </container>
        """)
        result = client._parsePeopleList(body)
        self.assertEquals(result, [])

        body = """<xml>but not schooltoolish</xml>"""
        result = client._parsePeopleList(body)
        self.assertEquals(result, []) # or should it raise an error?

    def test__parsePeopleList_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "This is not XML"
        self.assertRaises(SchoolToolError, client._parsePeopleList, body)

        body = """<xml>but not well-formed</mlx>"""
        self.assertRaises(SchoolToolError, client._parsePeopleList, body)

        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred">Fred</item>
                <item xlink:href="/persons/barney">Barney</item>
                <item xlink:href="/persons/barney/facets">Barney's facets</item>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
            </container>
        """)
        self.assertRaises(SchoolToolError, client._parsePeopleList, body)

    def test__parseGroupTree(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <tree xmlns:xlink="http://www.w3.org/1999/xlink">
              <group xlink:type="simple" xlink:href="/groups/root"
                     xlink:title="root group">
                <group xlink:type="simple" xlink:href="/groups/group2"
                       xlink:title="group2">
                </group>
                <group xlink:type="simple" xlink:href="/groups/group1"
                       xlink:title="group1">
                  <group xlink:type="simple" xlink:href="/groups/group1a"
                         xlink:title="group1a">
                  </group>
                  <group xlink:type="simple" xlink:href="/groups/group1b">
                  </group>
                </group>
              </group>
            </tree>
        """)
        client = SchoolToolClient()
        result = client._parseGroupTree(body)
        expected = [(0, 'root group', '/groups/root'),
                    (1, 'group2',     '/groups/group2'),
                    (1, 'group1',     '/groups/group1'),
                    (2, 'group1a',    '/groups/group1a'),
                    (2, 'group1b',    '/groups/group1b'),
                   ]
        self.assertEquals(list(result), expected)

    def test__parseGroupTree_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "This is not XML"
        self.assertRaises(SchoolToolError, client._parseGroupTree, body)

        body = "<tree>ill-formed</tere>"
        self.assertRaises(SchoolToolError, client._parseGroupTree, body)

        body = "<tree><group>without href</group></tree>"
        self.assertRaises(SchoolToolError, client._parseGroupTree, body)

        body = "<tree><group xlink:href=''>without href</group></tree>"
        self.assertRaises(SchoolToolError, client._parseGroupTree, body)

    def test__parseMemberList(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <item xlink:type="simple" xlink:href="/groups/group2"
                     xlink:title="group2 title" />
              <item xlink:type="simple" xlink:href="/persons/person1"
                     xlink:title="person1 title" />
              <item xlink:type="simple" xlink:href="/persons/person2"
                     xlink:title="person2 title" />
              <item xlink:type="simple" xlink:href="/persons/person1/facets"
                     xlink:title="person1 facets" />
              <item xlink:type="simple" xlink:title="person3 title" />
              <item xlink:type="simple" xlink:href="/persons/person4" />
            </group>
        """)
        expected = [('person1 title', '/persons/person1'),
                    ('person2 title', '/persons/person2'),
                    ('person4', '/persons/person4')]
        client = SchoolToolClient()
        result = client._parseMemberList(body)
        self.assertEquals(list(result), expected)

    def test__parseMemberList_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, client._parseMemberList, body)

    def test__parseRelationships(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="title1" xlink:href="href1"
                              xlink:role="role1" xlink:arcrole="arcrole1" />
                <relationship xlink:title="title2" xlink:href="href2"
                    xlink:role="http://schooltool.org/ns/membership/group"
                    xlink:arcrole="http://schooltool.org/ns/membership" />
                <relationship                       xlink:href="/objects/href3"
                              xlink:role="role3"    xlink:arcrole="arcrole3" />
                <relationship xlink:title="title4"
                              xlink:role="role4"    xlink:arcrole="arcrole4" />
                <relationship                       xlink:href=""
                              xlink:role="role4b"   xlink:arcrole="arcrole4b"/>
                <relationship xlink:title="title5"  xlink:href="href5"
                                                    xlink:arcrole="arcrole5" />
                <relationship xlink:title="title5b" xlink:href="href5b"
                              xlink:role=""         xlink:arcrole="arcrole5b"/>
                <relationship xlink:title="title6"  xlink:href="href6"
                              xlink:role="role6"                             />
                <relationship xlink:title="title6b" xlink:href="href6b"
                              xlink:role="role6b"   xlink:arcrole=""         />
              </existing>
              <valencies>
                <relationship xlink:title="title0" xlink:href="href0"
                              xlink:role="role0" xlink:arcrole="arcrole0" />
              </valencies>
            </relationships>
        """)
        expected = [('arcrole1', 'role1', 'title1', 'href1'),
                    ('Membership', 'Group', 'title2', 'href2'),
                    ('arcrole3', 'role3', 'href3', '/objects/href3')]
        client = SchoolToolClient()
        result = client._parseRelationships(body)
        self.assertEquals(list(result), expected)

    def test__parseRelationships_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, client._parseRelationships, body)

    def test__parseRollCall(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        body = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:href="/persons/p1" xlink:title="person 1"
                      presence="present" />
              <person xlink:href="/persons/p2" xlink:title=""
                      presence="absent" />
              <person href="/persons/p3" xlink:title="person 3"
                      presence="absent" />
              <person xlink:href="/persons/p4"
                      presence="absent" />
            </rollcall>
        """)
        expected = [('person 1', '/persons/p1', 'present'),
                    ('p2',       '/persons/p2', 'absent'),
                    ('p4',       '/persons/p4', 'absent')]
        client = SchoolToolClient()
        result = client._parseRollCall(body)
        self.assertEquals(result, expected)

    def test__parseRollCall_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, client._parseRollCall, body)

        body = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:href="/persons/p3" xlink:title="person 3"
                      presence="dunno" />
            </rollcall>
        """)
        self.assertRaises(SchoolToolError, client._parseRollCall, body)

    def test__parseAbsences(self):
        from schooltool.guiclient import SchoolToolClient, AbsenceInfo
        body = dedent("""
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple" href="/p/absences/000"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="resolved" />
              <absence xlink:type="simple" xlink:href="/p/absences/001"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="resolved" />
              <absence xlink:type="simple" xlink:href="/p/absences/002"
                       datetime="2001-02-28 01:01:01"
                       ended="unended" resolved="unresolved" />
              <absence xlink:type="simple" xlink:href="/p/absences/003"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06" />
            </absences>
        """)
        expected = [AbsenceInfo('/p/absences/001',
                                datetime.datetime(2001, 2, 28, 1, 1, 1),
                                True, True, None),
                    AbsenceInfo('/p/absences/002',
                                datetime.datetime(2001, 2, 28, 1, 1, 1),
                                False, False, None),
                    AbsenceInfo('/p/absences/003',
                                datetime.datetime(2001, 2, 28, 1, 1, 1), True,
                                False, datetime.datetime(2001, 2, 3, 4, 5, 6))]
        client = SchoolToolClient()
        result = client._parseAbsences(body)
        self.assertEquals(result, expected)

    def test__parseAbsences_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, client._parseAbsences, body)

        for incorrectness in ('ended="ended" resolved="resolved"',
            'datetime="2001-02-30 01:01:01" ended="ended" resolved="resolved"',
            'datetime="2001-02-28 01:01:01" ended="wha" resolved="resolved"',
            'datetime="2001-02-28 01:01:01" resolved="resolved"',
            'datetime="2001-02-28 01:01:01" ended="ended" resolved="whatever"',
            'datetime="2001-02-28 01:01:01" ended="ended"',
            'datetime="2001-02-28 01:01:01" ended="ended" resolved="resolved"'
              ' expected_presence="not a date time"'):
            body = dedent("""
                <absences xmlns:xlink="http://www.w3.org/1999/xlink">
                  <absence xlink:type="simple" xlink:href="/p/absences/001"
                           %s />
                </absences>
            """ % incorrectness)
            try:
                client._parseAbsences(body)
            except SchoolToolError, e:
                pass
            else:
                self.fail("did not raise with <absence %s ..." % incorrectness)

    def test__parseAbsenceComments(self):
        from schooltool.guiclient import SchoolToolClient, AbsenceComment
        from schooltool.guiclient import Unchanged
        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
              <comment datetime="2001-02-28 01:01:01"
                       ended="unended" resolved="resolved"
                       expected_presence="">
                <reporter xlink:type="simple" xlink:title="Supervisor 2"
                          xlink:href="/persons/supervisor002" />
              </comment>
              <comment datetime="2001-02-28 01:01:01">
                <reporter xlink:type="simple"
                          xlink:href="/persons/supervisor003" />
                <absentfrom xlink:type="simple" xlink:href="/groups/003"
                            xlink:title="Group"/>
                <text>
                  Comment
                  Three
                </text>
              </comment>
            </absence>
        """)
        expected = [AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   "Reporter", "/persons/supervisor001",
                                   "001", "/groups/001", True, False,
                                   datetime.datetime(2001, 2, 3, 4, 5, 6),
                                   "Comment One"),
                    AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   "Supervisor 2", "/persons/supervisor002",
                                   "", "", False, True, None, ""),
                    AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   "supervisor003", "/persons/supervisor003",
                                   "Group", "/groups/003", Unchanged, Unchanged,
                                   Unchanged,
                                   "Comment\n      Three")]
        client = SchoolToolClient()
        results = client._parseAbsenceComments(body)
        self.assertEquals(results, expected, "\n" + 
                          diff(pformat(expected), pformat(results)))

    def test__parseAbsenceComments_errors(self):
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        client = SchoolToolClient()
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="around noonish"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="maybe" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="perhaps"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="next Tuesday">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)

        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple" xlink:title="Reporter"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
                <text>Comment and two</text>
              </comment>
            </absence>
        """)
        self.assertRaises(SchoolToolError, client._parseAbsenceComments, body)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchoolToolClient))
    return suite

if __name__ == '__main__':
    unittest.main()
