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
import urllib
import base64
from zope.testing.doctestunit import DocTestSuite
from schooltool.tests.helpers import dedent, diff
from schooltool.tests.utils import XMLCompareMixin, RegistriesSetupMixin
from schooltool.tests.utils import NiceDiffsMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.uris import URIMembership, URIGroup, getURI
from schooltool.uris import URITeaching, URITaught, URITeacher

__metaclass__ = type


class ConnectionFactory:

    def __init__(self, response, error=None):
        self.response = response
        self.error = error
        self.connections = []

    def create(self, server, port):
        c = ConnectionStub(server, port, self.response, self.error, False)
        self.connections.append(c)
        return c

    def createSSL(self, server, port):
        c = ConnectionStub(server, port, self.response, self.error, True)
        self.connections.append(c)
        return c


class MultiConnectionFactory:

    def __init__(self, responses):
        self.responses = responses
        self.connections = []

    def create(self, server, port):
        n = len(self.connections)
        c = ConnectionStub(server, port, self.responses[n], None, False)
        self.connections.append(c)
        return c

    def createSSL(self, server, port):
        n = len(self.connections)
        c = ConnectionStub(server, port, self.responses[n], None, True)
        self.connections.append(c)
        return c


class ConnectionStub:

    def __init__(self, server, port, response, error, ssl):
        self.server = server
        self.port = port
        self.response = response
        self.error = error
        self.closed = False
        self.request_called = False
        self.ssl = ssl

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
        self._headers = {'server': 'UnitTest/0.0',
                         'content-type': 'text/plain'}
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


class TestSchoolToolClient(QuietLibxml2Mixin, XMLCompareMixin, NiceDiffsMixin,
                           RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()
        self.setUpRegistries()
        import schooltool.uris
        schooltool.uris.setUp()

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def newClient(self, response=None, error=None):
        from schooltool.clients.guiclient import SchoolToolClient
        client = SchoolToolClient()
        factory = ConnectionFactory(response, error)
        client._connections = factory.connections
        client.connectionFactory = factory.create
        client.secureConnectionFactory = factory.createSSL
        return client

    def newClientMulti(self, responses):
        from schooltool.clients.guiclient import SchoolToolClient
        client = SchoolToolClient()
        factory = MultiConnectionFactory(responses)
        client._connections = factory.connections
        client.connectionFactory = factory.create
        client.secureConnectionFactory = factory.createSSL
        return client

    def oneConnection(self, client):
        self.assertEquals(len(client._connections), 1)
        return client._connections[0]

    def checkConnPath(self, client, path):
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, path)

    def checkConnPaths(self, client, paths):
        self.assertEquals(len(client._connections),
                          len(paths))
        for conn, path in zip(client._connections, paths):
            self.assertEquals(conn.path, path)

    def test_setServer(self):
        from schooltool.clients.guiclient import SchoolToolClient
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
        self.assertEquals(conn.ssl, False)
        self.assertEquals(client.server, server)
        self.assertEquals(client.port, port)
        self.assertEquals(client.ssl, False)

    def test_setServer_SSL(self):
        from schooltool.clients.guiclient import SchoolToolClient
        server = 'example.com'
        port = 8443
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', 'doesnotmatter', server=version)
        client = self.newClient(response)
        client.setServer(server, port, ssl=True)
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)
        conn = self.oneConnection(client)
        self.assertEquals(conn.server, server)
        self.assertEquals(conn.port, port)
        self.assertEquals(conn.ssl, True)
        self.assertEquals(client.server, server)
        self.assertEquals(client.port, port)
        self.assertEquals(client.ssl, True)

    def test_setUser(self):
        from schooltool.clients.guiclient import SchoolToolClient
        client = self.newClient()
        client.setUser("gandalf", "123")
        self.assertEquals(client.user, "gandalf")
        self.assertEquals(client.password, "123")

        client.setUser("", "123")
        self.assertEquals(client.user, None)
        self.assertEquals(client.password, "")

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
        from schooltool.clients.guiclient import SchoolToolClient
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
        from schooltool.clients.guiclient import SchoolToolClient
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

    def test_request_auth(self):
        response = ResponseStub(200, 'OK')
        client = self.newClient(response)
        result = client._request('GET', '/')
        conn = self.oneConnection(client)
        self.assert_('Authorization' not in conn.headers)

        response = ResponseStub(200, 'OK')
        client = self.newClient(response)
        client.user = 'foo'
        client.password = 'bar'
        data = base64.encodestring("foo:bar").strip()
        result = client._request('GET', '/')
        conn = self.oneConnection(client)
        self.assertEquals(conn.headers['Authorization'], "Basic " + data)

        response = ResponseStub(200, 'OK')
        client = self.newClient(response)
        client.user = 'erk'
        client.password = 'frump'
        data = base64.encodestring("erk:frump").strip()
        result = client._request('GET', '/')
        conn = self.oneConnection(client)
        self.assertEquals(conn.headers['Authorization'], "Basic " + data)

    def test_request_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
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
                <item xlink:href="/persons/fred" xlink:title="Fred" />
                <item xlink:href="/persons/barney" xlink:title="Barney"/>
              </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getListOfPersons()
        expected = [('Fred', '/persons/fred'),
                    ('Barney', '/persons/barney')]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/persons')

    def test_getListOfPersons_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of persons'))
        self.assertRaises(SchoolToolError, client.getListOfPersons)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getListOfPersons)

    def test_getListOfGroups(self):
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/groups/fred" xlink:title="Fred" />
                <item xlink:href="/groups/barney" xlink:title="Barney"/>
              </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getListOfGroups()
        expected = [('Fred', '/groups/fred'),
                    ('Barney', '/groups/barney')]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/groups')

    def test_getListOfGroups_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getListOfGroups)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getListOfGroups)

    def test_getListOfResources(self):
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/resources/nut" xlink:title="Nut" />
                <item xlink:href="/resources/bolt" xlink:title="Bolt"/>
              </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getListOfResources()
        expected = [('Nut', '/resources/nut'),
                    ('Bolt', '/resources/bolt')]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/resources')

    def test_getListOfResources_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of resources'))
        self.assertRaises(SchoolToolError, client.getListOfResources)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getListOfResources)

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
        results = list(client.getGroupTree())
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/groups/root/tree')

    def test_getGroupTree_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of trees'))
        self.assertRaises(SchoolToolError, client.getGroupTree)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getGroupTree)

    def test_getGroupInfo(self):
        from schooltool.clients.guiclient import MemberInfo
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
        expected = [MemberInfo('person1', '/persons/person1')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        result = client.getGroupInfo(group_id)
        self.assertEquals(list(result.members), expected)
        self.checkConnPath(client, group_id)

    def test_getGroupInfo_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getGroupInfo, group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getGroupInfo, group_id)

    def test_getPersonInfo(self):
        from schooltool.clients.guiclient import PersonInfo
        body = dedent("""
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name>Albertas</first_name>
              <last_name>Agejevas</last_name>
              <date_of_birth>1978-05-17</date_of_birth>
              <comment>Programmer</comment>
              <photo xlink:type="simple" xlink:title="Photo"
                     xlink:href="/persons/albert/facets/person_info/photo"/>
            </person_info>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        person_path = '/persons/albert'
        result = client.getPersonInfo(person_path)
        self.assertEquals(result.first_name, 'Albertas')
        self.assertEquals(result.last_name, 'Agejevas')
        self.assertEquals(result.date_of_birth, datetime.date(1978, 5, 17))
        self.assertEquals(result.comment, 'Programmer')

    def test_getPersonInfo(self):
        from schooltool.clients.guiclient import PersonInfo
        body = dedent("""
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name>Albertas</first_name>
              <last_name>Agejevas</last_name>
              <date_of_birth>1978-05-17</date_of_birth>
              <comment>Hacker</comment>
            </person_info>
        """)
        client = self.newClient(ResponseStub(200, 'OK'))
        data = PersonInfo('Albertas', 'Agejevas', datetime.date(1978, 5, 17),
                          'Hacker')
        result = client.savePersonInfo('/persons/albert', data)
        conn = self.oneConnection(client)
        self.assertEqualsXML(conn.body, body)
        self.assertEquals(conn.path, '/persons/albert/facets/person_info')
        self.assertEquals(conn.method, "PUT")

    def test_getPersonPhoto(self):
        from schooltool.clients.guiclient import SchoolToolError
        body = "[pretend this is JPEG]"
        client = self.newClient(ResponseStub(200, 'OK', body))
        result = client.getPersonPhoto('/persons/jfk')
        self.assertEquals(result, body)
        self.checkConnPath(client, '/persons/jfk/facets/person_info/photo')

        client = self.newClient(ResponseStub(404, 'Not found', 'Not found'))
        result = client.getPersonPhoto('/persons/jfk')
        self.assert_(result is None)

        client = self.newClient(ResponseStub(401, 'Unauthorized', 'XXX'))
        self.assertRaises(SchoolToolError, client.getPersonPhoto, '/persons/x')

    def test_savePersonPhoto(self):
        body = "[pretend this is JPEG]"
        client = self.newClient(ResponseStub(200, 'OK', 'Uploaded'))
        client.savePersonPhoto('/persons/jfk', body)
        conn = self.oneConnection(client)
        self.assertEqualsXML(conn.body, body)
        self.assertEquals(conn.path, '/persons/jfk/facets/person_info/photo')
        self.assertEquals(conn.headers['Content-Type'],
                          'application/octet-stream')
        self.assertEquals(conn.method, "PUT")

    def test_removePersonPhoto(self):
        client = self.newClient(ResponseStub(200, 'OK', 'Deleted'))
        client.removePersonPhoto('/persons/jfk')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons/jfk/facets/person_info/photo')
        self.assertEquals(conn.method, "DELETE")

    def test_getObjectRelationships(self):
        from schooltool.clients.guiclient import RelationshipInfo
        from schooltool.clients.guiclient import stubURI
        arcrole1 = stubURI("test://arcrole1")
        role1 = stubURI("test://role1")
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="title1" xlink:href="href1"
                              xlink:role="test://role1"
                              xlink:arcrole="test://arcrole1">
                    <manage xlink:href="mhref1"/>
                </relationship>
                <relationship xlink:title="title2" xlink:href="href2"
                    xlink:role="http://schooltool.org/ns/membership/group"
                    xlink:arcrole="http://schooltool.org/ns/membership">
                    <manage xlink:href="mhref2"/>
                </relationship>
              </existing>
              <valencies>
                <relationship xlink:title="title3" xlink:href="href3"
                              xlink:role="test://role3"
                              xlink:arcrole="test://arcrole3" />
              </valencies>
            </relationships>
        """)
        expected = [RelationshipInfo(*args) for args in [
                (arcrole1, role1, 'title1', 'href1', 'mhref1'),
                (URIMembership, URIGroup, 'title2', 'href2', 'mhref2'),
            ]]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        results = list(client.getObjectRelationships(group_id))
        self.assertEquals(results, expected)
        self.checkConnPath(client, '%s/relationships' % group_id)

    def test_getObjectRelationships_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getObjectRelationships,
                          group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getObjectRelationships,
                          group_id)

    def test_getRollCall(self):
        from schooltool.clients.guiclient import RollCallInfo
        body = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:href="/persons/p1" xlink:title="person 1"
                      presence="present" />
            </rollcall>
        """)
        expected = [RollCallInfo('person 1', '/persons/p1', True)]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        results = client.getRollCall(group_id)
        self.assertEquals(results, expected)
        self.checkConnPath(client, '%s/rollcall' % group_id)

    def test_getRollCall_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getRollCall, group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getRollCall, group_id)

    def test_submitRollCall(self):
        from schooltool.clients.guiclient import RollCallEntry, Unchanged
        client = self.newClient(ResponseStub(200, 'OK', 'Accepted'))
        group_id = '/groups/group1'
        rollcall = [RollCallEntry('/persons/p1', True, 'foo', True),
                    RollCallEntry('/persons/p2', False, 'bar', False),
                    RollCallEntry('/persons/p3', Unchanged, None, Unchanged)]
        client.submitRollCall(group_id, rollcall)
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '%s/rollcall' % group_id)
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body, dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
                <person xlink:type="simple" xlink:href="/persons/p1"
                        presence="present" comment="foo" resolved="resolved"/>
                <person xlink:type="simple" xlink:href="/persons/p2"
                        presence="absent" comment="bar" resolved="unresolved"/>
                <person xlink:type="simple" xlink:href="/persons/p3"/>
            </rollcall>
            """))

    def test_submitRollCall_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError, RollCallEntry
        client = self.newClient(ResponseStub(400, 'Bad Request', 'No foo'))
        group_id = '/groups/group1'
        rollcall = [RollCallEntry('/persons/p3')]
        self.assertRaises(SchoolToolError,
                          client.submitRollCall, group_id, rollcall)

    def test_getAbsences(self):
        from schooltool.clients.guiclient import AbsenceInfo
        body = dedent("""
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple" xlink:href="/p/absences/003"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06" />
            </absences>
        """)
        expected = [AbsenceInfo('/p/absences/003',
                                datetime.datetime(2001, 2, 28, 1, 1, 1),
                                'p', '/p', True, False,
                                datetime.datetime(2001, 2, 3, 4, 5, 6), '')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getAbsences('/p/absences')
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/p/absences')

    def test_getAbsences_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getAbsences, '/p')

    def test_getAbsenceComments(self):
        from schooltool.clients.guiclient import AbsenceComment
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
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getAbsenceComments, '/p')

    def test_getSchoolTimetable(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        body1 = dedent("""
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
              <teacher xlink:type="simple" xlink:href="/persons/0013"
                       xlink:title="Fred">
                <day id="A">
                  <period id="Green">
                    <activity group="/groups/002" title="French">
                      <resource xlink:type="simple" xlink:title="101"
                                xlink:href="/resources/room101" />
                    </activity>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/003" title="Math"/>
                  </period>
                </day>
                <day id="B">
                  <period id="Green">
                    <activity group="/groups/004" title="English"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/005" title="Biology"/>
                  </period>
                </day>
              </teacher>
              <teacher xlink:type="simple" xlink:href="/persons/0014"
                       xlink:title="Barney">
                <day id="A">
                  <period id="Green">
                    <activity group="/groups/006" title="Geography"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/007" title="History"/>
                  </period>
                </day>
                <day id="B">
                  <period id="Green">
                    <activity group="/groups/008" title="Physics"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/009" title="Chemistry"/>
                  </period>
                </day>
              </teacher>
            </schooltt>
            """)
        body2 = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="Maths" xlink:href="/groups/maths"
                    xlink:role="http://schooltool.org/ns/teaching/taught"
                    xlink:arcrole="http://schooltool.org/ns/teaching">
                    <manage xlink:href="not interesting"/>
                </relationship>
              </existing>
            </relationships>
        """)
        body3 = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
              </existing>
            </relationships>
        """)

        expected = SchoolTimetableInfo(
            [('/persons/0013', 'Fred', [('Maths', '/groups/maths')]),
             ('/persons/0014', 'Barney', [])],
            [("A", "Green"),
             ("A", "Blue"),
             ("B", "Green"),
             ("B", "Blue")],
            [[[('French', '/groups/002', [('101', '/resources/room101')])],
              [('Math', '/groups/003', [])],
              [('English', '/groups/004', [])],
              [('Biology', '/groups/005', [])]],
             [[('Geography', '/groups/006', [])],
              [('History', '/groups/007', [])],
              [('Physics', '/groups/008', [])],
              [('Chemistry', '/groups/009', [])]]]
            )

        client = self.newClientMulti([ResponseStub(200, 'OK', body1),
                                      ResponseStub(200, 'OK', body2),
                                      ResponseStub(200, 'OK', body3)])
        results = client.getSchoolTimetable('2003-fall', 'weekly')
        self.checkConnPaths(client, ['/schooltt/2003-fall/weekly',
                                     '/persons/0013/relationships',
                                     '/persons/0014/relationships'])
        self.assertEquals(results, expected)

    def test_putSchooltoolTimetable(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        from schooltool.clients.guiclient import SchoolToolError
        tt = SchoolTimetableInfo(
            [('/persons/0013', 'Fred', [('Maths', '/groups/maths')]),
             ('/persons/0014', 'Barney', [])],
            [("A", "Green"),
             ("A", "Blue"),
             ("B", "Green"),
             ("B", "Blue")],
            [[[('French', '/groups/002', [])],
              [('Math', '/groups/003', [])],
              [('English', '/groups/004', [])],
              [('Biology', '/groups/005', [])]],
             [[('Geography', '/groups/006', [])],
              [('History', '/groups/007', [])],
              [('Physics', '/groups/008', [])],
              [('Chemistry', '/groups/009', [])]]]
            )
        client = self.newClient(ResponseStub(200, 'OK'))
        client.putSchooltoolTimetable('2003-fall', '4-day', tt)
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/schooltt/2003-fall/4-day')
        self.assertEquals(conn.method, 'PUT')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEquals(conn.body, tt.toXML())

        client = self.newClient(ResponseStub(400, 'Bad'))
        self.assertRaises(SchoolToolError, client.putSchooltoolTimetable,
                          '2003-all', '4-day', tt)

    def test_getTimePeriods(self):
        body = """
            <timePeriods xmlns:xlink="http://www.w3.org/1999/xlink">
              <period xlink:type="simple"
                      xlink:href="/time-periods/2003-fall"
                      xlink:title="2003-fall"/>
              <period xlink:type="simple"
                      xlink:href="/time-periods/2004-spring"
                      xlink:title="2004-spring"/>
            </timePeriods>
        """
        expected = ["2003-fall", "2004-spring"]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getTimePeriods()
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/time-periods')

    def test_getTimePeriods_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(500, 'BSOD', "<xml>Error!</xml>"))
        self.assertRaises(SchoolToolError, client.getTimePeriods)

    def test_getTimetableSchemas(self):
        body = """
            <timetableSchemas xmlns:xlink="http://www.w3.org/1999/xlink">
              <schema xlink:type="simple"
                      xlink:href="/ttschemas/six-day"
                      xlink:title="six-day"/>
              <schema xlink:type="simple" xlink:href="/ttschemas/weekly"
                      xlink:title="weekly"/>
            </timetableSchemas>
        """
        expected = ["six-day", "weekly"]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getTimetableSchemas()
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/ttschemas')

    def test_getTimetableSchemas_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(500, 'BSOD', "<xml>Error!</xml>"))
        self.assertRaises(SchoolToolError, client.getTimetableSchemas)

    def test_createFacet(self):
        client = self.newClient(ResponseStub(201, 'OK', 'Created',
                                    location='http://localhost/p/facets/001'))
        result = client.createFacet('/p', 'foo"factory')
        self.assertEquals(result, '/p/facets/001')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/p/facets')
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(
            conn.body,
            '<facet xmlns="http://schooltool.org/ns/model/0.1"'
            ' factory="foo&quot;factory"/>')

    def test_createFacet_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.createFacet, '/p', 'foo')

    def test_createPerson(self):
        client = self.newClient(ResponseStub(201, 'OK', 'Created',
                                    location='http://localhost/persons/00004'))
        result = client.createPerson('John "mad cat" Doe', "")
        self.assertEquals(result, '/persons/00004')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons')
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body,
                '<object xmlns="http://schooltool.org/ns/model/0.1"'
                       ' title="John &quot;mad cat&quot; Doe"/>')

        client = self.newClientMulti([
            ResponseStub(201, 'OK', 'Created',
                         location=('http://localhost/persons/root')),
            ResponseStub(200, 'OK', 'Password set')])
        result = client.createPerson('John "mad cat" Doe', "root", "foo")
        self.assertEquals(result, '/persons/root')
        self.assertEquals(len(client._connections), 2)
        conn = client._connections[0]
        self.assertEquals(conn.path, '/persons/root')
        self.assertEquals(conn.method, 'PUT')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body,
                '<object xmlns="http://schooltool.org/ns/model/0.1"'
                       ' title="John &quot;mad cat&quot; Doe"/>')
        conn = client._connections[1]
        self.assertEquals(conn.path, '/persons/root/password')
        self.assertEquals(conn.method, 'PUT')
        self.assertEqualsXML(conn.body, 'foo')

    def test_createPerson_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.createPerson, 'John Doe')

    def test_changePassword(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(200, 'OK', 'Password set'))
        client.changePassword('luser1', 'wp')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons/luser1/password')
        self.assertEquals(conn.method, 'PUT')
        self.assertEquals(conn.headers['Content-Type'], 'text/plain')
        self.assertEqualsXML(conn.body, 'wp')

    def test_changePassword_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError,
                          client.changePassword, 'luser1', 'wp')

    def test_createGroup(self):
        client = self.newClient(ResponseStub(201, 'OK', 'Created',
                                    location='http://localhost/groups/00004'))
        result = client.createGroup('Title<with"strange&chars')
        self.assertEquals(result, '/groups/00004')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/groups')
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body,
                '<object xmlns="http://schooltool.org/ns/model/0.1"'
                       ' title="Title&lt;with&quot;strange&amp;chars"/>')

    def test_createGroup_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.createGroup, 'Slackers')

    def test_createRelationship(self):
        from schooltool.uris import URIMembership, URIMember
        client = self.newClient(ResponseStub(201, 'Created',
                location='http://localhost/persons/john/relationships/004'))
        result = client.createRelationship('/persons/john', '/groups/teachers',
                                           URIMembership, URIMember)
        self.assertEquals(result, '/persons/john/relationships/004')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons/john/relationships')
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        expected = """
            <relationship xmlns="http://schooltool.org/ns/model/0.1"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 xlink:type="simple"
                 xlink:href="/groups/teachers"
                 xlink:arcrole="http://schooltool.org/ns/membership"
                 xlink:role="http://schooltool.org/ns/membership/member"
                 />
                 """
        self.assertEqualsXML(conn.body, expected)

    def test_createRelationship_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        from schooltool.uris import URIMembership, URIMember
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.createRelationship,
                '/persons/john', '/groups/teachers', URIMembership, URIMember)

    def test_deleteObject(self):
        client = self.newClient(ResponseStub(200, 'OK', 'Deleted'))
        client.deleteObject('/path/to/object')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/path/to/object')
        self.assertEquals(conn.method, 'DELETE')
        self.assertEquals(conn.body, '')

    def test_deleteObject_with_errors(self):
        from schooltool.clients.guiclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.deleteObject, '/path')

    def test__pathFromResponse(self):
        client = self.newClient(None)
        response = ResponseStub(200, 'OK',
                                location='http://localhost/path/to/something')
        self.assertEquals(client._pathFromResponse(response),
                          '/path/to/something')

        # XXX What if the server is broken and does not return a Location
        #     header, or returns an ill-formed location header, or something
        #     unexpected like 'mailto:jonas@example.com' or 'http://webserver'
        #     without a trailing slash?

    def test_availabilitySearch(self):
        from schooltool.clients.guiclient import ResourceTimeSlot
        body = """
            <availability xmlns:xlink="http://www.w3.org/1999/xlink">
              <resource xlink:type="simple"
                        xlink:href="/resources/room101" xlink:title="101">
                <slot duration="1440" start="2004-01-01 00:00:00"/>
              </resource>
              <resource xlink:type="simple"
                        xlink:href="/resources/hall" xlink:title="Hall">
                <slot duration="1440" start="2004-01-01 00:00:00"/>
                <slot duration="30" start="2004-01-02 12:30:00"/>
              </resource>
            </availability>
        """
        expected = [ResourceTimeSlot('101', '/resources/room101',
                                     datetime.datetime(2004, 1, 1),
                                     datetime.timedelta(minutes=1440)),
                    ResourceTimeSlot('Hall', '/resources/hall',
                                     datetime.datetime(2004, 1, 1),
                                     datetime.timedelta(minutes=1440)),
                    ResourceTimeSlot('Hall', '/resources/hall',
                                     datetime.datetime(2004, 1, 2, 12, 30),
                                     datetime.timedelta(minutes=30))]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.availabilitySearch(first=datetime.date(2004, 1, 1),
                        last=datetime.date(2004, 1, 2), duration=30,
                        hours=[0, 12], resources=['room101', 'hall'])
        self.assertEquals(results, expected)
        qs = urllib.urlencode([('first', '2004-01-01'), ('last', '2004-01-02'),
                               ('duration', '30'), ('hours', [0, 12]),
                               ('resources', ['room101', 'hall'])], True)
        self.checkConnPath(client, '/busysearch?' + qs)

    def test_bookResource(self):
        client = self.newClient(ResponseStub(200, 'OK', 'Booked'))
        client.bookResource('/resources/r001', '/persons/p001',
                            datetime.datetime(2004, 2, 16, 14, 45),
                            30, True)
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/resources/r001/booking')
        self.assertEquals(conn.method, 'POST')
        self.assertEqualsXML(conn.body, """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1"
                     conflicts="ignore">
              <owner path="/persons/p001" />
              <slot start="2004-02-16 14:45:00" duration="30" />
            </booking>
        """)

        client = self.newClient(ResponseStub(200, 'OK', 'Booked'))
        client.bookResource('/resources/r001', '/persons/p001',
                            datetime.datetime(2004, 2, 16, 14, 45),
                            30, False)
        conn = self.oneConnection(client)
        self.assertEqualsXML(conn.body, """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/p001" />
              <slot start="2004-02-16 14:45:00" duration="30" />
            </booking>
        """)


class TestParseFunctions(NiceDiffsMixin, RegistriesSetupMixin,
                         QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()
        self.setUpRegistries()
        import schooltool.uris
        schooltool.uris.setUp()

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def test__parseContainer(self):
        from schooltool.clients.guiclient import _parseContainer
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred" xlink:title="Fred \xc5\xbe."/>
                <item xlink:href="/persons/barney"/>
              </items>
            </container>
        """)
        results = _parseContainer(body)
        expected = [(u'Fred \u017e.', '/persons/fred'),
                    (u'barney', '/persons/barney')]
        self.assertEquals(results, expected)

    def test__parseGroupTree(self):
        from schooltool.clients.guiclient import _parseGroupTree
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
                         xlink:title="group1a \xe2\x98\xbb">
                  </group>
                  <group xlink:type="simple" xlink:href="/groups/group1b">
                  </group>
                </group>
              </group>
            </tree>
        """)
        result = _parseGroupTree(body)
        expected = [(0, 'root group',      '/groups/root'),
                    (1, 'group2',          '/groups/group2'),
                    (1, 'group1',          '/groups/group1'),
                    (2, u'group1a \u263B', '/groups/group1a'),
                    (2, 'group1b',         '/groups/group1b'),
                   ]
        self.assertEquals(list(result), expected)

    def test__parseGroupTree_errors(self):
        from schooltool.clients.guiclient import _parseGroupTree
        from schooltool.clients.guiclient import SchoolToolError
        body = "This is not XML"
        self.assertRaises(SchoolToolError, _parseGroupTree, body)

        body = "<tree>ill-formed</tere>"
        self.assertRaises(SchoolToolError, _parseGroupTree, body)

        body = "<tree><group>without href</group></tree>"
        self.assertRaises(SchoolToolError, _parseGroupTree, body)

        body = "<tree><group xlink:href=''>without href</group></tree>"
        self.assertRaises(SchoolToolError, _parseGroupTree, body)

    def test__parseMemberList(self):
        from schooltool.clients.guiclient import _parseMemberList, MemberInfo
        body = dedent("""
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <item xlink:type="simple" xlink:href="/groups/group2"
                     xlink:title="group2 title" />
              <item xlink:type="simple" xlink:href="/persons/person1"
                     xlink:title="person1 \xe2\x9c\xb0 title" />
              <item xlink:type="simple" xlink:href="/persons/person2"
                     xlink:title="person2 \xe2\x9c\xb0 title" />
              <item xlink:type="simple" xlink:href="/persons/person1/facets"
                     xlink:title="person1 facets" />
              <item xlink:type="simple" xlink:title="person3 title" />
              <item xlink:type="simple" xlink:href="/persons/person4" />
            </group>
        """)
        expected = [MemberInfo(u'person1 \u2730 title', '/persons/person1'),
                    MemberInfo(u'person2 \u2730 title', '/persons/person2'),
                    MemberInfo(u'person4', '/persons/person4')]
        result = _parseMemberList(body)
        self.assertEquals(list(result), expected)

    def test__parseMemberList_errors(self):
        from schooltool.clients.guiclient import _parseMemberList
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseMemberList, body)

    def test__parseRelationships(self):
        from schooltool.clients.guiclient import _parseRelationships
        from schooltool.clients.guiclient import RelationshipInfo
        from schooltool.clients.guiclient import stubURI
        role1 = stubURI('test://role1')
        arcrole1 = stubURI('test://arcrole1')
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="title1 \xe2\x9c\xb0"
                              xlink:href="href1"
                              xlink:role="test://role1"
                              xlink:arcrole="test://arcrole1">
                    <manage xlink:href="mhref1"/>
                </relationship>
                <relationship xlink:title="title2 \xe2\x9c\xb0"
                    xlink:href="href2"
                    xlink:role="http://schooltool.org/ns/membership/group"
                    xlink:arcrole="http://schooltool.org/ns/membership">
                    <manage xlink:href="mhref2"/>
                </relationship>
                <relationship xlink:href="/objects/href3"
                              xlink:role="test://role3"
                              xlink:arcrole="test://arcrole3">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <!-- the rest are ignored for because of missing/empty
                     attributes -->
                <relationship xlink:title="title4"
                              xlink:role="test://role4"
                              xlink:arcrole="test://arcrole4">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:href=""
                              xlink:role="test://role4b"
                              xlink:arcrole="test://arcrole4b">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:title="title5"  xlink:href="href5"
                              xlink:arcrole="test://arcrole5">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:title="title5b" xlink:href="href5b"
                              xlink:role=""
                              xlink:arcrole="test://arcrole5b">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:title="title6"  xlink:href="href6"
                              xlink:role="test://role6">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:title="title6b" xlink:href="href6b"
                              xlink:role="test://role6b" xlink:arcrole="">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:title="title7b" xlink:href="href7b"
                              xlink:role="not-a-uri"
                              xlink:arcrole="test://arcrole7">
                    <manage xlink:href="mhref3"/>
                </relationship>
                <relationship xlink:title="title8b" xlink:href="href8b"
                              xlink:role="test://role7"
                              xlink:arcrole="not a uri">
                    <manage xlink:href="mhref3"/>
                </relationship>
              </existing>
              <valencies>
                <relationship xlink:title="title0" xlink:href="href0"
                              xlink:role="test://role0"
                              xlink:arcrole="test://arcrole0" />
              </valencies>
            </relationships>
        """)
        result = _parseRelationships(body)
        role3 = getURI('test://role3')
        arcrole3 = getURI('test://arcrole3')
        expected = [RelationshipInfo(*args) for args in [
                (arcrole1, role1, u'title1 \u2730', 'href1', 'mhref1'),
                (URIMembership, URIGroup, u'title2 \u2730', 'href2', 'mhref2'),
                (arcrole3, role3, u'href3', '/objects/href3', 'mhref3'),
            ]]
        self.assertEquals(list(result), expected)

    def test__parseRelationships_errors(self):
        from schooltool.clients.guiclient import _parseRelationships
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseRelationships, body)

        # Two manage elements
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="title1" xlink:href="href1"
                              xlink:role="test://role1"
                              xlink:arcrole="test://arcrole1">
                    <manage xlink:href="mhref1"/>
                    <manage xlink:href="mhref2"/>
                </relationship>
              </existing>
            </relationships>
        """)
        self.assertRaises(SchoolToolError, _parseRelationships, body)

        # No manage elements
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink">
              <existing>
                <relationship xlink:title="title1" xlink:href="href1"
                              xlink:role="test://role1"
                              xlink:arcrole="test://arcrole1" />
              </existing>
            </relationships>
        """)
        self.assertRaises(SchoolToolError, _parseRelationships, body)

    def test__parseRollCall(self):
        from schooltool.clients.guiclient import _parseRollCall, RollCallInfo
        body = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:href="/persons/p1"
                      xlink:title="person 1 \xe2\x9c\xb0"
                      presence="present" />
              <person xlink:href="/persons/p2" xlink:title=""
                      presence="absent" />
              <person href="/persons/p3" xlink:title="person 3"
                      presence="absent" />
              <person xlink:href="/persons/p4"
                      presence="absent" />
            </rollcall>
        """)
        expected = [RollCallInfo(u'person 1 \u2730', '/persons/p1', True),
                    RollCallInfo(u'p2', '/persons/p2', False),
                    RollCallInfo(u'p4', '/persons/p4', False)]
        results = _parseRollCall(body)
        self.assertEquals(results, expected)

    def test__parseRollCall_errors(self):
        from schooltool.clients.guiclient import _parseRollCall
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseRollCall, body)

        body = dedent("""
            <rollcall xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:href="/persons/p3" xlink:title="person 3"
                      presence="dunno" />
            </rollcall>
        """)
        self.assertRaises(SchoolToolError, _parseRollCall, body)

    def test__parseAbsences(self):
        from schooltool.clients.guiclient import _parseAbsences, AbsenceInfo
        body = dedent("""
            <absences xmlns:xlink="http://www.w3.org/1999/xlink">
              <absence xlink:type="simple" href="/p/absences/000"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="resolved" />
              <absence xlink:type="simple" xlink:href="/persons/p/absences/001"
                       person_title="Person Foo \xe2\x9c\xb0"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="resolved">
                Some text
              </absence>
              <absence xlink:type="simple" xlink:href="/p/absences/002"
                       datetime="2001-02-28 01:01:01"
                       ended="unended" resolved="unresolved">
                More
                text
              </absence>
              <absence xlink:type="simple" xlink:href="/p/absences/003"
                       datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06" />
            </absences>
        """)
        expected = [AbsenceInfo('/persons/p/absences/001',
                                datetime.datetime(2001, 2, 28, 1, 1, 1),
                                u'Person Foo \u2730', '/persons/p',
                                True, True, None, 'Some text'),
                    AbsenceInfo('/p/absences/002',
                                datetime.datetime(2001, 2, 28, 1, 1, 1),
                                'p', '/p',
                                False, False, None, 'More\n    text'),
                    AbsenceInfo('/p/absences/003',
                                datetime.datetime(2001, 2, 28, 1, 1, 1),
                                'p', '/p', True, False,
                                datetime.datetime(2001, 2, 3, 4, 5, 6), '')]
        results = _parseAbsences(body)
        self.assertEquals(results, expected)

    def test__parseAbsences_errors(self):
        from schooltool.clients.guiclient import _parseAbsences
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseAbsences, body)

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
                _parseAbsences(body)
            except SchoolToolError, e:
                pass
            else:
                self.fail("did not raise with <absence %s ..." % incorrectness)

    def test__parseAbsenceComments(self):
        from schooltool.clients.guiclient import _parseAbsenceComments
        from schooltool.clients.guiclient import AbsenceComment, Unchanged
        body = dedent("""
            <absence xmlns:xlink="http://www.w3.org/1999/xlink">
              <person xlink:type="simple" xlink:href="/persons/a" />
              <comment datetime="2001-02-28 01:01:01"
                       ended="ended" resolved="unresolved"
                       expected_presence="2001-02-03 04:05:06">
                <reporter xlink:type="simple"
                          xlink:title="Reporter \xe2\x9c\xb0"
                          xlink:href="/persons/supervisor001" />
                <absentfrom xlink:type="simple" xlink:href="/groups/001" />
                <text>Comment One</text>
              </comment>
              <comment datetime="2001-02-28 01:01:01"
                       ended="unended" resolved="resolved"
                       expected_presence="">
                <reporter xlink:type="simple"
                          xlink:title="Supervisor 2 \xe2\x9c\xb0"
                          xlink:href="/persons/supervisor002" />
              </comment>
              <comment datetime="2001-02-28 01:01:01">
                <reporter xlink:type="simple"
                          xlink:href="/persons/supervisor003" />
                <absentfrom xlink:type="simple" xlink:href="/groups/003"
                            xlink:title="Group \xe2\x9c\xb0"/>
                <text>
                  Comment \xe2\x9c\xb0
                  Three
                </text>
              </comment>
            </absence>
        """)
        expected = [AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   u"Reporter \u2730",
                                   u"/persons/supervisor001",
                                   u"001", u"/groups/001", True, False,
                                   datetime.datetime(2001, 2, 3, 4, 5, 6),
                                   u"Comment One"),
                    AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   u"Supervisor 2 \u2730",
                                   u"/persons/supervisor002",
                                   u"", u"", False, True, None, u""),
                    AbsenceComment(datetime.datetime(2001, 2, 28, 1, 1, 1),
                                   u"supervisor003", u"/persons/supervisor003",
                                   u"Group \u2730", u"/groups/003", Unchanged,
                                   Unchanged, Unchanged,
                                   u"Comment \u2730\n      Three")]
        results = _parseAbsenceComments(body)
        self.assertEquals(results, expected)

    def test__parseAbsenceComments_errors(self):
        from schooltool.clients.guiclient import _parseAbsenceComments
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

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
        self.assertRaises(SchoolToolError, _parseAbsenceComments, body)

    def test__parseTimePeriods(self):
        from schooltool.clients.guiclient import _parseTimePeriods
        body = """
            <timePeriods xmlns:xlink="http://www.w3.org/1999/xlink">
              <period xlink:type="simple"
                      xlink:href="/time-periods/2003-fall"
                      xlink:title="2003-fall \xe2\x9c\xb0"/>
              <period xlink:type="simple"
                      xlink:href="/time-periods/2004-spring"
                      xlink:title="2004-spring"/>
            </timePeriods>
        """
        expected = [u"2003-fall \u2730", u"2004-spring"]
        results = _parseTimePeriods(body)
        self.assertEquals(results, expected)

    def test__parseTimePeriods_errors(self):
        from schooltool.clients.guiclient import _parseTimePeriods
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseTimePeriods, body)

    def test__parseTimetableSchemas(self):
        from schooltool.clients.guiclient import _parseTimetableSchemas
        body = """
            <timetableSchemas xmlns:xlink="http://www.w3.org/1999/xlink">
              <schema xlink:type="simple"
                      xlink:href="/ttschemas/six-day"
                      xlink:title="six-day \xe2\x9c\xb0"/>
              <schema xlink:type="simple" xlink:href="/ttschemas/weekly"
                      xlink:title="weekly"/>
            </timetableSchemas>
        """
        expected = [u"six-day \u2730", u"weekly"]
        results = _parseTimetableSchemas(body)
        self.assertEquals(results, expected)

    def test__parseTimetableSchemas_errors(self):
        from schooltool.clients.guiclient import _parseTimetableSchemas
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseTimetableSchemas, body)

    def test__parseAvailabilityResults(self):
        from schooltool.clients.guiclient import _parseAvailabilityResults
        from schooltool.clients.guiclient import ResourceTimeSlot
        body = """
            <availability xmlns:xlink="http://www.w3.org/1999/xlink">
               <resource xlink:type="simple"
                         xlink:href="/resources/room101"
                         xlink:title="101 \xe2\x9c\xb0">
                 <slot duration="1440" start="2004-01-01 00:00:00"/>
               </resource>
               <resource xlink:type="simple"
                         xlink:href="/resources/hall"
                         xlink:title="Hall \xe2\x9c\xb0">
                 <slot duration="1440" start="2004-01-01 00:00:00"/>
                 <slot duration="30" start="2004-01-02 12:30:00"/>
               </resource>
            </availability>
        """
        expected = [ResourceTimeSlot(u'101 \u2730', '/resources/room101',
                                     datetime.datetime(2004, 1, 1),
                                     datetime.timedelta(minutes=1440)),
                    ResourceTimeSlot(u'Hall \u2730', '/resources/hall',
                                     datetime.datetime(2004, 1, 1),
                                     datetime.timedelta(minutes=1440)),
                    ResourceTimeSlot(u'Hall \u2730', '/resources/hall',
                                     datetime.datetime(2004, 1, 2, 12, 30),
                                     datetime.timedelta(minutes=30))]
        results = _parseAvailabilityResults(body)
        self.assertEquals(results, expected)

    def test__parseAvailabilityResults_errors(self):
        from schooltool.clients.guiclient import _parseAvailabilityResults
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseAvailabilityResults, body)
        body = """
            <availability xmlns:xlink="http://www.w3.org/1999/xlink">
               <resource xlink:type="simple"
                         xlink:href="/resources/room101" xlink:title="101">
                 <slot duration="1440" start="not a datetime"/>
               </resource>
            </availability>
        """
        self.assertRaises(SchoolToolError, _parseAvailabilityResults, body)
        body = """
            <availability xmlns:xlink="http://www.w3.org/1999/xlink">
               <resource xlink:type="simple"
                         xlink:href="/resources/room101" xlink:title="101">
                 <slot duration="a month" start="2001-01-01 00:00:00"/>
               </resource>
            </availability>
        """
        self.assertRaises(SchoolToolError, _parseAvailabilityResults, body)

    def test__parsePersonInfo(self):
        from schooltool.clients.guiclient import _parsePersonInfo
        from schooltool.clients.guiclient import SchoolToolError
        body = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name>John \xe2\x9c\xb0</first_name>
              <last_name>Doe \xe2\x9c\xb0</last_name>
              <date_of_birth>2001-01-01</date_of_birth>
              <comment>Foo bar baz \xe2\x9c\xb0</comment>
              <photo xlink:type="simple" xlink:title="Photo \xe2\x9c\xb0"
                     xlink:href="/persons/000033/facets/person_info/photo"/>
            </person_info>
        """
        result = _parsePersonInfo(body)
        self.assertEquals(result.first_name, u'John \u2730')
        self.assertEquals(result.last_name, u'Doe \u2730')
        self.assertEquals(result.date_of_birth, datetime.date(2001, 1, 1))
        self.assertEquals(result.comment, u'Foo bar baz \u2730')

        body = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name/>
              <last_name/>
              <date_of_birth/>
              <comment/>
              <photo xlink:type="simple" xlink:title="Photo \xe2\x9c\xb0"
                     xlink:href="/persons/000033/facets/person_info/photo"/>
            </person_info>
        """
        result = _parsePersonInfo(body)
        self.assertEquals(result.first_name, '')
        self.assertEquals(result.last_name, '')
        self.assertEquals(result.date_of_birth, None)
        self.assertEquals(result.comment, '')

    def test__parsePersonInfo_errors(self):
        from schooltool.clients.guiclient import _parsePersonInfo
        from schooltool.clients.guiclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parsePersonInfo, body)
        body = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <first_name></first_name>
              <last_name></last_name>
              <date_of_birth>baddate</date_of_birth>
              <comment></comment>
              <photo xlink:type="simple" xlink:title="Photo"
                     xlink:href="/persons/Aiste/facets/person_info/photo"/>
            </person_info>
        """
        self.assertRaises(SchoolToolError, _parsePersonInfo, body)
        body = """
            <person_info xmlns="http://schooltool.org/ns/model/0.1"
                         xmlns:xlink="http://www.w3.org/1999/xlink">
              <last_name>asd</last_name>
              <comment>asdfasdf</comment>
              <photo xlink:type="simple" xlink:title="Photo"
                     xlink:href="/persons/Aiste/facets/person_info/photo"/>
            </person_info>
        """
        self.assertRaises(SchoolToolError, _parsePersonInfo, body)


class InfoClassTestMixin:
    """Mixin for testing classes that are tuple replacements."""

    def _test_repr(self, cls, nargs):
        """Test the __repr__ method of a class."""
        obj = cls(*range(nargs))

        result = repr(obj)
        expected = "%s(%s)" % (cls.__name__, ', '.join(map(str, range(nargs))))
        self.assertEquals(result, expected)

    def _test_cmp(self, cls, nargs, attrs=()):
        """Test the __cmp__ method of a class.

        nargs is the number of arguments the constructor takes

        attrs is a sequence of attributes that should be more important for
        ordering.
        """
        clsname = cls.__name__
        obj1 = cls(*range(nargs))
        self.assertEquals(obj1, obj1,
                          "%s does not compare equal to itself:\n  %r != %r"
                          % (clsname, obj1, obj1))

        for i in range(nargs):
            args = range(nargs)
            args[i] = -1
            obj2 = cls(*args)
            self.assertNotEquals(obj1, obj2,
                          "%s does not notice changes in the %dth argument:\n"
                          "  %r == %r" % (clsname, i + 1, obj1, obj2))

        obj1 = cls(*([1] * nargs))
        obj2 = cls(*([2] * nargs))
        self.assert_(obj1 < obj2, "%r >= %r" % (obj1, obj2))

        for attrname in attrs:
            setattr(obj1, attrname, 2)
            setattr(obj2, attrname, 1)
            self.assert_(obj1 > obj2,
                         "%s is not sorted by %s:\n  %r <= %r"
                         % (clsname, attrname, obj1, obj2))
            setattr(obj1, attrname, 3)
            setattr(obj2, attrname, 3)


class TestInfoClasses(unittest.TestCase, InfoClassTestMixin):

    def test_MemberInfo(self):
        from schooltool.clients.guiclient import MemberInfo
        self._test_repr(MemberInfo, 2)
        self._test_cmp(MemberInfo, 2, ('person_title', ))

    def test_RelationshipInfo(self):
        from schooltool.clients.guiclient import RelationshipInfo
        self._test_repr(RelationshipInfo, 5)
        self._test_cmp(RelationshipInfo, 5,
                       ('arcrole', 'role', 'target_title'))

    def test_RollCallInfo(self):
        from schooltool.clients.guiclient import RollCallInfo
        self._test_repr(RollCallInfo, 3)
        self._test_cmp(RollCallInfo, 3, ('person_title', ))

    def test_RollCallEntry(self):
        from schooltool.clients.guiclient import RollCallEntry
        self._test_repr(RollCallEntry, 4)

    def test_AbsenceComment(self):
        from schooltool.clients.guiclient import AbsenceComment
        self._test_repr(AbsenceComment, 9)
        self._test_cmp(AbsenceComment, 9, ('datetime', ))

    def test_ResourceTimeSlot(self):
        from schooltool.clients.guiclient import ResourceTimeSlot
        self._test_repr(ResourceTimeSlot, 4)
        self._test_cmp(ResourceTimeSlot, 4,
                       ('resource_title', 'resource_path', 'available_from'))


class TestAbsenceInfo(unittest.TestCase, InfoClassTestMixin):

    def test(self):
        from schooltool.clients.guiclient import AbsenceInfo
        self._test_cmp(AbsenceInfo, 8, ('datetime', ))

    def test_expected(self):
        from schooltool.clients.guiclient import AbsenceInfo
        dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
        ai = AbsenceInfo(None, dt, None, None, None, None, None, None)
        self.assert_(not ai.expected())

        et = datetime.datetime(2002, 3, 4, 5, 6, 7)
        ai = AbsenceInfo(None, dt, None, None, None, None, et, None)
        ai.now = lambda: datetime.datetime(2002, 3, 4, 5, 6, 6)
        self.assert_(ai.expected())
        ai.now = lambda: datetime.datetime(2002, 3, 4, 5, 6, 7)
        self.assert_(ai.expected())
        ai.now = lambda: datetime.datetime(2002, 3, 4, 5, 6, 8)
        self.assert_(not ai.expected())

    def test_unicode(self):
        from schooltool.clients.guiclient import AbsenceInfo
        dt = datetime.datetime(2001, 2, 3, 15, 44, 57)
        ai = AbsenceInfo(None, dt, 'John Smith', None, None, None, None, None)
        ai.now = lambda: datetime.datetime(2001, 2, 3, 17, 59, 58)
        self.assertEquals(unicode(ai), u"John Smith absent for 2h15m,"
                                        " since 03:44PM today")

        et = datetime.datetime(2001, 2, 3, 18, 30, 00)
        ai = AbsenceInfo(None, dt, 'John Smith', None, None, None, et, None)
        ai.now = lambda: datetime.datetime(2001, 2, 3, 17, 59, 58)
        self.assertEquals(unicode(ai), "John Smith expected in 0h30m,"
                                       " at 06:30PM today")

        et = datetime.datetime(2001, 2, 3, 18, 30, 00)
        ai = AbsenceInfo(None, dt, 'John Smith', None, None, None, et, None)
        ai.now = lambda: datetime.datetime(2001, 2, 4, 12, 14, 17)
        self.assertEquals(unicode(ai), "John Smith expected 17h44m ago,"
                                       " at 06:30PM 2001-02-03")

    def test_format_date(self):
        from schooltool.clients.guiclient import AbsenceInfo
        ai = AbsenceInfo(None, None, None, None, None, None, None, None)
        dt = datetime.datetime(2001, 2, 3, 4, 5, 6)
        ai.now = lambda: datetime.datetime(2001, 2, 3, 6, 5, 4)
        self.assertEquals(ai.format_date(dt), 'today')
        ai.now = lambda: datetime.datetime(2001, 2, 4, 6, 5, 4)
        self.assertEquals(ai.format_date(dt), '2001-02-03')

    def test_format_age(self):
        from schooltool.clients.guiclient import AbsenceInfo
        ai = AbsenceInfo(None, None, None, None, None, None, None, None)
        format_age = ai.format_age
        self.assertEquals(format_age(datetime.timedelta(minutes=5)), '0h5m')
        self.assertEquals(format_age(datetime.timedelta(hours=2, minutes=15)),
                          '2h15m')
        self.assertEquals(format_age(datetime.timedelta(days=2, hours=2,
                                                    minutes=15, seconds=3)),
                          '50h15m')
        self.assertEquals(format_age(datetime.timedelta(0)), '0h0m')
        self.assertEquals(format_age(-datetime.timedelta(minutes=5)), '-0h5m')
        self.assertEquals(format_age(-datetime.timedelta(hours=2, minutes=15)),
                          '-2h15m')
        self.assertEquals(format_age(datetime.timedelta(hours=2, minutes=15),
                          'in %s', '%s ago'), 'in 2h15m')
        self.assertEquals(format_age(-datetime.timedelta(hours=2, minutes=15),
                          'in %s', '%s ago'), '2h15m ago')


class TestSchoolTimetableInfo(NiceDiffsMixin, QuietLibxml2Mixin,
                              unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def test_loadData(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        st = SchoolTimetableInfo()
        data = dedent("""
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
              <teacher xlink:type="simple" xlink:href="/persons/0013"
                       xlink:title="A Teacher \xe2\x9c\xb0">
                <day id="A \xe2\x9c\xb0">
                  <period id="Green \xe2\x9c\xb0">
                    <activity group="/groups/002" title="French \xe2\x9c\xb0">
                      <resource xlink:type="simple"
                                xlink:title="101 \xe2\x9c\xb0"
                                xlink:href="/resources/room101" />
                    </activity>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/003" title="Math \xe2\x9c\xb0"/>
                  </period>
                </day>
                <day id="B">
                  <period id="Green">
                    <activity group="/groups/004"
                              title="English"/>
                    <activity group="/groups/005"
                              title="English"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/005" title="Biology"/>
                  </period>
                </day>
              </teacher>
              <teacher xlink:type="simple" xlink:href="/persons/0014">
                <day id="A \xe2\x9c\xb0">
                  <period id="Green">
                    <activity group="/groups/006" title="Geography"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/007" title="History"/>
                  </period>
                </day>
                <day id="B">
                  <period id="Green">
                    <activity group="/groups/008" title="Physics"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/009" title="Chemistry"/>
                  </period>
                </day>
              </teacher>
            </schooltt>
            """)
        st.loadData(data)

        self.assertEquals(st.teachers,
                          [('/persons/0013', u'A Teacher \u2730', None),
                           ('/persons/0014', None, None)])
        self.assertEquals(st.periods,
                          [(u"A \u2730", u"Green \u2730"),
                           (u"A \u2730", u"Blue"),
                           (u"B", u"Green"),
                           (u"B", u"Blue")])
        self.assertEquals(st.tt,
                          [
                            # Day A
                            [
                              [(u'French \u2730', u'/groups/002',
                                [(u'101 \u2730', u'/resources/room101')])],
                              [(u'Math \u2730', u'/groups/003', [])],
                              [(u'English', u'/groups/004', []),
                               (u'English', u'/groups/005', [])],
                              [(u'Biology', u'/groups/005', [])]
                            ],
                            # Day B
                            [
                              [(u'Geography', u'/groups/006', [])],
                              [(u'History',   u'/groups/007', [])],
                              [(u'Physics',   u'/groups/008', [])],
                              [(u'Chemistry', u'/groups/009', [])]
                            ]
                          ])

    def test_loadData_breakage(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        from schooltool.clients.guiclient import SchoolToolError
        st = SchoolTimetableInfo()
        self.assertRaises(SchoolToolError, st.loadData, "not xml")

    def test_loadData_no_teachers(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        from schooltool.clients.guiclient import SchoolToolError
        st = SchoolTimetableInfo()
        data = dedent("""
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
            </schooltt>
            """)

        self.assertRaises(SchoolToolError, st.loadData, data)

        # The following error cases are not tested:
        #  - different days and/or periods for different teachers
        #  - different order of days/periods for different teachers
        # Our server does not generate such timetables.

    def test_toXML_empty(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        st = SchoolTimetableInfo([('a', None), ('b', None)],
                                 [("1", "A"), ("1", "B"),
                                  ("2", "A"), ("2", "B")])
        result = st.toXML()
        expected = dedent("""
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
              <teacher xlink:type="simple" xlink:href="a">
                <day id="1">
                  <period id="A">
                  </period>
                  <period id="B">
                  </period>
                </day>
                <day id="2">
                  <period id="A">
                  </period>
                  <period id="B">
                  </period>
                </day>
              </teacher>
              <teacher xlink:type="simple" xlink:href="b">
                <day id="1">
                  <period id="A">
                  </period>
                  <period id="B">
                  </period>
                </day>
                <day id="2">
                  <period id="A">
                  </period>
                  <period id="B">
                  </period>
                </day>
              </teacher>
            </schooltt>
            """)
        self.assertEquals(result, expected, "\n" + diff(expected, result))

    def test_setTeacherRelationships(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        from schooltool.clients.guiclient import RelationshipInfo
        st = SchoolTimetableInfo([('/path1', None, None),
                                  ('/path2', None, None)])
        st.setTeacherRelationships(0, [
                RelationshipInfo(URITeaching, URITaught, 'Maths',
                                 '/groups/maths', None),
                RelationshipInfo(URITeaching, URITeacher, 'Foo',
                                 '/groups/foo', None),
                RelationshipInfo(URIMembership, URITaught, 'Bar',
                                 '/groups/bar', None),
            ])
        self.assertEquals(st.teachers, [('/path1', None,
                                         [('Maths', '/groups/maths')]),
                                        ('/path2', None, None)])

    def test_loadData_toXML_roundtrip(self):
        from schooltool.clients.guiclient import SchoolTimetableInfo
        st = SchoolTimetableInfo()
        data = dedent("""
            <schooltt xmlns="http://schooltool.org/ns/schooltt/0.2"
                      xmlns:xlink="http://www.w3.org/1999/xlink">
              <teacher xlink:type="simple" xlink:href="/persons/0013">
                <day id="A">
                  <period id="Green">
                    <activity group="/groups/002" title="French">
                      <resource xlink:type="simple" \\
            xlink:href="/resources/room101" xlink:title="101"/>
                    </activity>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/003" title="Math"/>
                  </period>
                </day>
                <day id="B">
                  <period id="Green">
                    <activity group="/groups/004" title="English"/>
                    <activity group="/groups/005" title="English"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/005" title="Biology"/>
                  </period>
                </day>
              </teacher>
              <teacher xlink:type="simple" xlink:href="/persons/0014">
                <day id="A">
                  <period id="Green">
                    <activity group="/groups/006" title="Geography"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/007" title="History"/>
                  </period>
                </day>
                <day id="B">
                  <period id="Green">
                    <activity group="/groups/008" title="Physics"/>
                  </period>
                  <period id="Blue">
                    <activity group="/groups/009" title="Chemistry"/>
                  </period>
                </day>
              </teacher>
            </schooltt>
            """).replace('\\\n', '')
        st.loadData(data)
        output = st.toXML()
        self.assertEquals(data, output, "\n" + diff(data, output))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.clients.guiclient'))
    suite.addTest(unittest.makeSuite(TestSchoolToolClient))
    suite.addTest(unittest.makeSuite(TestParseFunctions))
    suite.addTest(unittest.makeSuite(TestInfoClasses))
    suite.addTest(unittest.makeSuite(TestAbsenceInfo))
    suite.addTest(unittest.makeSuite(TestSchoolTimetableInfo))
    return suite

if __name__ == '__main__':
    unittest.main()
