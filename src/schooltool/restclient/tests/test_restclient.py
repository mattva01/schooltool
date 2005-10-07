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
Unit tests for restclient.py
"""

import unittest
import socket
import datetime
import urllib
import base64

from zope.testing.doctest import DocTestSuite

from schooltool.app.rest.testing import dedent, diff
from schooltool.app.rest.testing import XMLCompareMixin
from schooltool.app.rest.testing import NiceDiffsMixin
from schooltool.app.rest.testing import QuietLibxml2Mixin

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
            self._headers[k.replace('_', '-').lower()] = v
        self._read_called = False

    def read(self):
        if self._read_called:
            raise RuntimeError('ResponseStub.read called more than once')
        self._read_called = True
        return self._body

    def getheader(self, name):
        return self._headers[name.lower()]


class TestSchoolToolClient(QuietLibxml2Mixin, XMLCompareMixin, NiceDiffsMixin,
                           unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def newClient(self, response=None, error=None):
        from schooltool.restclient.restclient import SchoolToolClient
        client = SchoolToolClient()
        factory = ConnectionFactory(response, error)
        client._connections = factory.connections
        client.connectionFactory = factory.create
        client.secureConnectionFactory = factory.createSSL
        return client

    def newClientMulti(self, responses):
        from schooltool.restclient.restclient import SchoolToolClient
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

    def test_init(self):
        from schooltool.restclient.restclient import SchoolToolClient
        client = SchoolToolClient()
        self.assertEquals(client.server, 'localhost')
        self.assertEquals(client.port, 7001)
        self.assertEquals(client.ssl, False)
        self.assertEquals(client.user, None)
        self.assertEquals(client.password, '')

        client = SchoolToolClient('uni.edu.mars', 32764, ssl=True)
        self.assertEquals(client.server, 'uni.edu.mars')
        self.assertEquals(client.port, 32764)
        self.assertEquals(client.ssl, True)

        client = SchoolToolClient(user='mangler', password='42')
        self.assertEquals(client.user, 'mangler')
        self.assertEquals(client.password, '42')

    def test_setServer(self):
        from schooltool.restclient.restclient import SchoolToolClient
        server = 'example.com'
        port = 8081
        version = 'UnitTest/0.0'
        dummy_uris = "<uriobjects></uriobjects>"
        response = ResponseStub(200, 'OK', dummy_uris, server=version)
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
        from schooltool.restclient.restclient import SchoolToolClient
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
        from schooltool.restclient.restclient import SchoolToolClient
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
        from schooltool.restclient.restclient import SchoolToolClient
        path = '/path'
        body = 'spam'
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        client = self.newClient(response)
        result = client._request('FOO', path)
        conn = self.oneConnection(client)
        self.assertEquals(conn.server, 'localhost')
        self.assertEquals(conn.port, 7001)
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
        from schooltool.restclient.restclient import SchoolToolClient
        path = '/path'
        body = 'spam'
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        client = self.newClient(response)
        result = client._request('BAR', path, 'body body body',
                                 {'X-Foo': 'Foo!'})
        conn = self.oneConnection(client)
        self.assertEquals(conn.server, 'localhost')
        self.assertEquals(conn.port, 7001)
        self.assertEquals(conn.method, 'BAR')
        self.assertEquals(conn.path, path)
        self.assertEquals(conn.headers,
                          {'X-Foo': 'Foo!',
                           'Content-Type': 'text/xml'})
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
        from schooltool.restclient.restclient import SchoolToolError
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

    def test_getPersons(self):
        from schooltool.restclient.restclient import PersonRef
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred" xlink:title="Fred" />
                <item xlink:href="/persons/barney" xlink:title="Barney"/>
              </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getPersons()
        expected = [PersonRef(client, '/persons/fred', 'Fred'),
                    PersonRef(client, '/persons/barney', 'Barney')]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/persons')

    def test_getPersons_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of persons'))
        self.assertRaises(SchoolToolError, client.getPersons)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getPersons)

    def test_getGroups(self):
        from schooltool.restclient.restclient import GroupRef
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/groups/fred" xlink:title="Fred" />
                <item xlink:href="/groups/barney" xlink:title="Barney"/>
              </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getGroups()
        expected = [GroupRef(client, '/groups/fred', 'Fred'),
                    GroupRef(client, '/groups/barney', 'Barney')]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/groups')

    def test_getGroups_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getGroups)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getGroups)

    def test_getResources(self):
        from schooltool.restclient.restclient import ResourceRef
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/resources/nut" xlink:title="Nut" />
                <item xlink:href="/resources/bolt" xlink:title="Bolt"/>
              </items>
            </container>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getResources()
        expected = [ResourceRef(client, '/resources/nut', 'Nut'),
                    ResourceRef(client, '/resources/bolt', 'Bolt')]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/resources')

    def test_getResources_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(error=socket.error(23, 'out of resources'))
        self.assertRaises(SchoolToolError, client.getResources)

        client = self.newClient(ResponseStub(500, 'Internal Error'))
        self.assertRaises(SchoolToolError, client.getResources)

    def test_getGroupInfo(self):
        from schooltool.restclient.restclient import MemberInfo
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink"
                           xmlns="http://schooltool.org/ns/model/0.1">
              <existing>
                <relationship xlink:type="simple"
                              xlink:role="http://schooltool.org/ns/membership/member"
                              xlink:arcrole="http://schooltool.org/ns/membership"
                              xlink:href="/persons/person1">
                  <manage xlink:type="simple"
                          xlink:href="/groups/manager/relationships/1"/>
                </relationship>
              </existing>
            </relationships>
        """)
        expected = [MemberInfo('/persons/person1')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        group_id = '/groups/group1'
        group_relationships = '/groups/group1/relationships'
        result = client.getGroupInfo(group_id)
        self.assertEquals(list(result.members), expected)
        self.checkConnPath(client, group_relationships)

    def test_getGroupInfo_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getGroupInfo, group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getGroupInfo, group_id)

    def test_getPersonInfo(self):
        from schooltool.restclient.restclient import PersonInfo
        body = dedent("""
            <person xmlns:xlink="http://www.w3.org/1999/xlink"
                    xmlns="http://schooltool.org/ns/model/0.1">
              <title>SchoolTool Manager</title>
              <relationships xlink:type="simple"
                             xlink:title="Relationships"
                             xlink:href="/persons/manager/relationships"/>
              <acl xlink:type="simple" xlink:title="ACL"
                   xlink:href="/persons/manager/acl"/>
              <calendar xlink:type="simple" xlink:title="Calendar"
                        xlink:href="/persons/manager/calendar"/>
              <relationships xlink:type="simple"
                             xlink:title="Calendar subscriptions"
                             xlink:href="/persons/manager/calendar/relationships"/>
              <acl xlink:type="simple" xlink:title="Calendar ACL"
                   xlink:href="/persons/manager/calendar/acl"/>
            </person>
        """)
        client = self.newClient(ResponseStub(200, 'OK', body))
        person_path = '/persons/manager'
        result = client.getPersonInfo(person_path)
        self.assertEquals(result.title, 'SchoolTool Manager')

    def test_savePersonInfo(self):
        from schooltool.restclient.restclient import PersonInfo
        body = dedent("""
            <object title="Albertas Agejevas" xmlns="http://schooltool.org/ns/model/0.1"
                    xmlns:xlink="http://www.w3.org/1999/xlink"/>
        """)
        client = self.newClient(ResponseStub(200, 'OK'))
        data = PersonInfo('Albertas Agejevas')
        result = client.savePersonInfo('/persons/albert', data)
        conn = self.oneConnection(client)
        self.assertEqualsXML(conn.body, body)
        self.assertEquals(conn.path, '/persons/albert')
        self.assertEquals(conn.method, "PUT")

    def test_getPersonPhoto(self):
        from schooltool.restclient.restclient import SchoolToolError
        body = "[pretend this is JPEG]"
        client = self.newClient(ResponseStub(200, 'OK', body))
        result = client.getPersonPhoto('/persons/jfk')
        self.assertEquals(result, body)
        self.checkConnPath(client, '/persons/jfk/photo')

        client = self.newClient(ResponseStub(404, 'Not found', 'Not found'))
        result = client.getPersonPhoto('/persons/jfk')
        self.assert_(result is None)

        client = self.newClient(ResponseStub(401, 'Unauthorized', 'errmsg'))
        self.assertRaises(SchoolToolError, client.getPersonPhoto, '/persons/x')

    def test_savePersonPhoto(self):
        body = "[pretend this is JPEG]"
        client = self.newClient(ResponseStub(200, 'OK', 'Uploaded'))
        client.savePersonPhoto('/persons/jfk', body)
        conn = self.oneConnection(client)
        self.assertEqualsXML(conn.body, body)
        self.assertEquals(conn.path, '/persons/jfk/photo')
        self.assertEquals(conn.headers['Content-Type'],
                          'application/octet-stream')
        self.assertEquals(conn.method, "PUT")

    def test_removePersonPhoto(self):
        client = self.newClient(ResponseStub(200, 'OK', 'Deleted'))
        client.removePersonPhoto('/persons/jfk')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons/jfk/photo')
        self.assertEquals(conn.method, "DELETE")

    def test_getObjectRelationships(self):
        from schooltool.restclient.restclient import RelationshipInfo, URIObject
        from schooltool.restclient.restclient import URIMembership_uri
        from schooltool.restclient.restclient import URIGroup_uri
        URIMembership = URIObject(URIMembership_uri)
        URIGroup = URIObject(URIGroup_uri)
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink"
                           xmlns="http://schooltool.org/ns/model/0.1">
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
        group_id = '/groups/group1'
        client = self.newClient(ResponseStub(200, 'OK', body))
        arcrole1 = URIObject('test://arcrole1')
        role1 = URIObject('test://role1')
        results = list(client.getObjectRelationships(group_id))
        expected = [('test://role1',
                     'test://arcrole1',
                     'title1', 'href1', 'mhref1'),
                    ('http://schooltool.org/ns/membership/group',
                     'http://schooltool.org/ns/membership',
                     'title2', 'href2', 'mhref2')]
        results = [(result.role.uri, result.arcrole.uri,
                    result.target_title, result.target_path, result.link_path)
                   for result in results]
        self.assertEquals(results, expected)
        self.checkConnPath(client, '%s/relationships' % group_id)

    def test_getObjectRelationships_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        group_id = '/groups/group1'
        client = self.newClient(error=socket.error(23, 'out of groups'))
        self.assertRaises(SchoolToolError, client.getObjectRelationships,
                          group_id)

        client = self.newClient(ResponseStub(404, 'Not Found'))
        self.assertRaises(SchoolToolError, client.getObjectRelationships,
                          group_id)

    def test_getTerms(self):
        body = """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>terms</name>
              <items>
                <item xlink:type="simple"
                      xlink:href="/terms/2003-fall"
                      xlink:title="2003-fall"/>
                <item xlink:type="simple"
                      xlink:href="/terms/2004-spring"
                      xlink:title="2003-fall"/>
              </items>
              <acl xlink:type="simple" xlink:title="ACL"
                   xlink:href="http://localhost:7001/terms/acl"/>
            </container>
        """
        expected = [(u'2003-fall', u'/terms/2003-fall'),
                    (u'2003-fall', u'/terms/2004-spring')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getTerms()
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/terms')

    def test_getTerms_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(ResponseStub(500, 'BSOD', "<xml>Error!</xml>"))
        self.assertRaises(SchoolToolError, client.getTerms)

    def test_getTimetableSchemas(self):
        body = """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>ttschemas</name>
              <items>
                <item xlink:type="simple"
                      xlink:href="/ttschemas/six-day"
                      xlink:title="six-day"/>
                <item xlink:type="simple"
                      xlink:href="/ttschemas/weekly"
                      xlink:title="weekly"/>
              </items>
              <acl xlink:type="simple" xlink:title="ACL"
                   xlink:href="http://localhost:7001/ttschemas/acl"/>
            </container>
        """
        expected = [(u'six-day', u'/ttschemas/six-day'), (u'weekly', u'/ttschemas/weekly')]
        client = self.newClient(ResponseStub(200, 'OK', body))
        results = client.getTimetableSchemas()
        self.assertEquals(results, expected)
        self.checkConnPath(client, '/ttschemas')

    def test_getTimetableSchemas_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(ResponseStub(500, 'BSOD', "<xml>Error!</xml>"))
        self.assertRaises(SchoolToolError, client.getTimetableSchemas)

    def test_createPerson(self):
        client = self.newClient(
            ResponseStub(201, 'OK', 'Created',
                         location='http://localhost/persons/john'))
        result = client.createPerson('John "mad cat" Doe', "john")
        self.assertEquals(result, '/persons/john')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons/john')
        self.assertEquals(conn.method, 'PUT')
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
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.createPerson,
                          'John Doe', 'john')

    def test_changePassword(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(ResponseStub(200, 'OK', 'Password set'))
        client.changePassword('luser1', 'wp')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/persons/luser1/password')
        self.assertEquals(conn.method, 'PUT')
        self.assertEquals(conn.headers['Content-Type'], 'text/plain')
        self.assertEqualsXML(conn.body, 'wp')

    def test_changePassword_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError,
                          client.changePassword, 'luser1', 'wp')

    def test_createGroup(self):
        client = self.newClient(ResponseStub(201, 'OK', 'Created',
                                    location='http://localhost/groups/titlewithstrangechars'))
        result = client.createGroup('Title<with"strange&chars')
        self.assertEquals(result, '/groups/titlewithstrangechars')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/groups')
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body,
                '<object xmlns="http://schooltool.org/ns/model/0.1"'
                       ' title="Title&lt;with&quot;strange&amp;chars"'
                       ' description=""/>')

    def test_createGroup_description(self):
        client = self.newClient(ResponseStub(201, 'OK', 'Created',
                                    location='http://localhost/groups/huba'))
        result = client.createGroup('<Huba>',
                                    description='<Buba>')
        self.assertEquals(result, '/groups/huba')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/groups')
        self.assertEquals(conn.method, 'POST')
        self.assertEquals(conn.headers['Content-Type'], 'text/xml')
        self.assertEqualsXML(conn.body,
                '<object xmlns="http://schooltool.org/ns/model/0.1"'
                       ' title="&lt;Huba&gt;"'
                       ' description="&lt;Buba&gt;"/>')

    def test_createGroup_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.createGroup, 'Slackers')

    def test_createRelationship(self):
        from schooltool.restclient.restclient import URIObject
        from schooltool.restclient.restclient import URIMembership_uri
        from schooltool.restclient.restclient import URIGroup_uri
        client = self.newClient(ResponseStub(201, 'Created',
                location='http://localhost/persons/john/relationships/004'))
        result = client.createRelationship('/persons/john', '/groups/teachers',
                                           URIMembership_uri, URIGroup_uri)
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
                 xlink:role="http://schooltool.org/ns/membership/group"
                 />
                 """
        self.assertEqualsXML(conn.body, expected)

    def test_createRelationship_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
        from schooltool.restclient.restclient import URIObject
        from schooltool.restclient.restclient import URIMembership_uri
        from schooltool.restclient.restclient import URIGroup_uri
        URIMembership = URIObject(URIMembership_uri)
        URIGroup = URIObject(URIGroup_uri)
        client = self.newClient(ResponseStub(400, 'Bad Request'))
        self.assertRaises(SchoolToolError, client.createRelationship,
                '/persons/john', '/groups/teachers', URIMembership, URIGroup)

    def test_deleteObject(self):
        client = self.newClient(ResponseStub(200, 'OK', 'Deleted'))
        client.deleteObject('/path/to/object')
        conn = self.oneConnection(client)
        self.assertEquals(conn.path, '/path/to/object')
        self.assertEquals(conn.method, 'DELETE')
        self.assertEquals(conn.body, '')

    def test_deleteObject_with_errors(self):
        from schooltool.restclient.restclient import SchoolToolError
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


class TestResponse(unittest.TestCase):

    class RealResponseStub:
        status = 42
        reason = 'of life, the universe, and everything'
        _used = False
        _headers = {'Beauty': 'True'}

        def read(self):
            if self._used: raise EOFError
            self._used = True
            return '<body/>'

        def getheader(self, header):
            return self._headers[header]

    def test(self):
        from schooltool.restclient.restclient import Response
        real_response = RealResponseStub()
        response = Response(real_response)
        self.assertEquals(response.status, real_response.status)
        self.assertEquals(response.reason, real_response.reason)
        self.assertEquals(response.body, '<body/>')
        self.assertEquals(response.getheader('Beauty'), 'True')
        self.assertEquals(str(response), '<body/>')
        self.assertEquals(response.read(), '<body/>')
        # can do that multiple times, and it doesn't call real_response.read()
        # again
        self.assertEquals(response.read(), '<body/>')
        # just to make sure -- if response did call real_response.read() again,
        # it would get an error
        self.assertRaises(EOFError, real_response.read)


class TestParseFunctions(NiceDiffsMixin, QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def test__parseContainer(self):
        from schooltool.restclient.restclient import _parseContainer
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

    def test__parseRelationships(self):
        from schooltool.restclient.restclient import _parseRelationships
        from schooltool.restclient.restclient import RelationshipInfo, URIObject
        from schooltool.restclient.restclient import URIMembership_uri
        from schooltool.restclient.restclient import URIGroup_uri
        URIMembership = URIObject(URIMembership_uri)
        URIGroup = URIObject(URIGroup_uri)
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink"
                           xmlns="http://schooltool.org/ns/model/0.1">
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
        role1 = URIObject('test://role1')
        arcrole1 = URIObject('test://arcrole1')
        uriobjects = {role1.uri: role1,
                      arcrole1.uri: arcrole1,
                      URIMembership_uri: URIMembership,
                      URIGroup_uri: URIGroup}
        result = _parseRelationships(body, uriobjects)
        role3 = uriobjects['test://role3']
        self.assertEquals(role3.uri, role3.name)
        arcrole3 = uriobjects['test://arcrole3']
        self.assertEquals(arcrole3.uri, arcrole3.name)

        expected = [RelationshipInfo(*args) for args in [
                (arcrole1, role1, u'title1 \u2730', 'href1', 'mhref1'),
                (URIMembership, URIGroup, u'title2 \u2730', 'href2', 'mhref2'),
                (arcrole3, role3, u'href3', '/objects/href3', 'mhref3'),
            ]]
        self.assertEquals(list(result), expected)

    def test__parseRelationships_errors(self):
        from schooltool.restclient.restclient import _parseRelationships
        from schooltool.restclient.restclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parseRelationships, body, {})

        # Two manage elements
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink"
                           xmlns="http://schooltool.org/ns/model/0.1">
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
        self.assertRaises(SchoolToolError, _parseRelationships, body, {})

        # No manage elements
        body = dedent("""
            <relationships xmlns:xlink="http://www.w3.org/1999/xlink"
                           xmlns="http://schooltool.org/ns/model/0.1">
              <existing>
                <relationship xlink:title="title1" xlink:href="href1"
                              xlink:role="test://role1"
                              xlink:arcrole="test://arcrole1" />
              </existing>
            </relationships>
        """)
        self.assertRaises(SchoolToolError, _parseRelationships, body, {})

    def test__parsePersonInfo(self):
        from schooltool.restclient.restclient import _parsePersonInfo
        from schooltool.restclient.restclient import SchoolToolError
        body = """
            <person xmlns:xlink="http://www.w3.org/1999/xlink"
                    xmlns="http://schooltool.org/ns/model/0.1">
              <title>John \xe2\x9c\xb0 Doe \xe2\x9c\xb0</title>
              <relationships xlink:type="simple"
                             xlink:title="Relationships"
                             xlink:href="/persons/john/relationships"/>
              <acl xlink:type="simple" xlink:title="ACL"
                   xlink:href="/persons/john/acl"/>
              <calendar xlink:type="simple" xlink:title="Calendar"
                        xlink:href="/persons/john/calendar"/>
              <relationships xlink:type="simple"
                             xlink:title="Calendar subscriptions"
                             xlink:href="/persons/john/calendar/relationships"/>
              <acl xlink:type="simple" xlink:title="Calendar ACL"
                   xlink:href="/persons/john/calendar/acl"/>
            </person>
        """
        result = _parsePersonInfo(body)
        self.assertEquals(result.title, u'John \u2730 Doe \u2730')

    def test__parsePersonInfo_errors(self):
        from schooltool.restclient.restclient import _parsePersonInfo
        from schooltool.restclient.restclient import SchoolToolError
        body = "<This is not XML"
        self.assertRaises(SchoolToolError, _parsePersonInfo, body)
        body = """
            <person xmlns:xlink="http://www.w3.org/1999/xlink"
                    xmlns="http://schooltool.org/ns/model/0.1">
              <relationships xlink:type="simple"
                             xlink:title="Relationships"
                             xlink:href="/persons/john/relationships"/>
              <acl xlink:type="simple" xlink:title="ACL"
                   xlink:href="/persons/john/acl"/>
              <calendar xlink:type="simple" xlink:title="Calendar"
                        xlink:href="/persons/john/calendar"/>
              <relationships xlink:type="simple"
                             xlink:title="Calendar subscriptions"
                             xlink:href="/persons/john/calendar/relationships"/>
              <acl xlink:type="simple" xlink:title="Calendar ACL"
                   xlink:href="/persons/john/calendar/acl"/>
            </person>
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
        from schooltool.restclient.restclient import MemberInfo
        self._test_repr(MemberInfo, 1)
        self._test_cmp(MemberInfo, 1, ('person_path', ))

    def test_RelationshipInfo(self):
        from schooltool.restclient.restclient import RelationshipInfo
        self._test_repr(RelationshipInfo, 5)
        self._test_cmp(RelationshipInfo, 5,
                       ('arcrole', 'role', 'target_title'))

    def test_URIObject(self):
        from schooltool.restclient.restclient import URIObject
        uriobj = URIObject('http://foo')
        self.assertEquals(uriobj.uri, 'http://foo')
        self.assertEquals(uriobj.name, 'http://foo')
        uriobj = URIObject('http://foo', "name", "desc")
        self.assertEquals(uriobj.uri, 'http://foo')
        self.assertEquals(uriobj.name, 'name')
        self.assertEquals(uriobj.description, 'desc')

        self.assertRaises(AssertionError, URIObject, "invalid_uri")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.restclient.restclient'))
    suite.addTest(unittest.makeSuite(TestSchoolToolClient))
    suite.addTest(unittest.makeSuite(TestParseFunctions))
    suite.addTest(unittest.makeSuite(TestInfoClasses))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
