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
from schooltool.tests.helpers import dedent

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

    def request(self, method, path):
        if self.request_called:
            raise RuntimeError('ConnectionStub.request called more than once')
        self.request_called = True
        self.method = method
        self.path = path
        if self.error is not None:
            raise self.error

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class ResponseStub:

    def __init__(self, status, reason, body, **kw):
        self.status = status
        self.reason = reason
        self.body = body
        self.headers = {}
        for k, v in kw.items():
            self.headers[k.lower()] = v
        self.read_called = False

    def read(self):
        if self.read_called:
            raise RuntimeError('ResponseStub.read called more than once')
        self.read_called = True
        return self.body

    def getheader(self, name):
        return self.headers[name.lower()]


class TestSchoolToolClient(unittest.TestCase):

    def test_get(self):
        from schooltool.guiclient import SchoolToolClient
        path = '/path'
        body = 'spam'
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.get(path)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.server, SchoolToolClient.server)
        self.assertEquals(conn.port, SchoolToolClient.port)
        self.assertEquals(conn.method, 'GET')
        self.assertEquals(conn.path, path)
        self.assertEquals(result, body)
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)
        self.assert_(conn.closed)

    def test_get_with_errors(self):
        from schooltool.guiclient import SchoolToolClient
        path = '/path'
        e = socket.error(23, 'out of spam')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.get(path)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(result, None)
        self.assertEquals(client.status, "(23, 'out of spam')")
        self.assertEquals(client.version, '')
        self.assert_(conn.closed)

    def test_tryToConnect(self):
        from schooltool.guiclient import SchoolToolClient
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', 'doesnotmatter', server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        client.tryToConnect()
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)

    def test_setServer(self):
        from schooltool.guiclient import SchoolToolClient
        server = 'example.com'
        port = 8081
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', 'doesnotmatter', server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        client.setServer(server, port)
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)
        conn = factory.connections[0]
        self.assertEquals(conn.server, server)
        self.assertEquals(conn.port, port)
        self.assertEquals(client.server, server)
        self.assertEquals(client.port, port)

    def test__parsePeopleList(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred">Fred</item>
                <item xlink:href="/persons/barney">Barney</item>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
               </items>
            </container>
        """)
        client = SchoolToolClient()
        result = client._parsePeopleList(body)
        self.assertEquals(result, ['/persons/fred', '/persons/barney'])

    def test__parsePeopleListEmpty(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
               </items>
            </container>
        """)
        client = SchoolToolClient()
        result = client._parsePeopleList(body)
        self.assertEquals(result, [])

    def test_getListOfPersons(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <items>
                <item xlink:href="/persons/fred">Fred</item>
                <item xlink:href="/persons/barney">Barney</item>
                <item xlink:href="http://example.com/buy/stuff">Click!</item>
               </items>
            </container>
        """)
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getListOfPersons()
        self.assertEquals(result, ['/persons/fred', '/persons/barney'])
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/persons')

    def test_getListOfPersons_with_errors(self):
        from schooltool.guiclient import SchoolToolClient
        version = 'UnitTest/0.0'
        e = socket.error(23, 'out of persons')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getListOfPersons()
        self.assertEquals(result, [])

    def test_getPersonInfo(self):
        from schooltool.guiclient import SchoolToolClient
        body = dedent("""
            <html>
              <h1>Foo!</h1>
            </html>
        """)
        version = 'UnitTest/0.0'
        person_id = '/persons/foo'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getPersonInfo(person_id)
        self.assertEquals(result, body)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/persons/foo')

    def test_getGroupTree(self):
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
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getGroupTree()
        self.assertEquals(list(result), expected)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/groups/root/tree')

    def test_getGroupTree_with_errors(self):
        from schooltool.guiclient import SchoolToolClient
        version = 'UnitTest/0.0'
        e = socket.error(23, 'out of trees')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getGroupTree()
        self.assertEquals(result, [])

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
                  <group xlink:type="simple" xlink:href="/groups/group1b"
                         xlink:title="group1b">
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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchoolToolClient))
    return suite

if __name__ == '__main__':
    unittest.main()
