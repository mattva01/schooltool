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
Unit tests for wxWindows client
"""

import unittest
import socket

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
        from schooltool.wxclient import SchoolToolClient
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
        from schooltool.wxclient import SchoolToolClient
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
        from schooltool.wxclient import SchoolToolClient
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', 'doesnotmatter', server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        client.tryToConnect()
        self.assertEquals(client.status, '200 OK')
        self.assertEquals(client.version, version)

    def test_setServer(self):
        from schooltool.wxclient import SchoolToolClient
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

    def test_parsePeopleList(self):
        from schooltool.wxclient import SchoolToolClient
        body = (
            '<html>\n'
            '  <a href="/people/fred">Fred</a>\n'
            '  <a href="/people/barney">Barney</a>\n'
            '  <a href="http://example.com/buy/our/stuff">Click this!</a>\n'
            '</html>\n'
            )
        client = SchoolToolClient()
        result = client.parsePeopleList(body)
        self.assertEquals(result, ['fred', 'barney'])

    def test_parsePeopleListEmpty(self):
        from schooltool.wxclient import SchoolToolClient
        body = (
            '<html>\n'
            '  <a href="http://example.com/buy/our/stuff">Click this!</a>\n'
            '</html>\n'
            )
        client = SchoolToolClient()
        result = client.parsePeopleList(body)
        self.assertEquals(result, [])

    def test_getListOfPersons(self):
        from schooltool.wxclient import SchoolToolClient
        body = (
            '<html>\n'
            '  <a href="/people/fred">Fred</a>\n'
            '  <a href="/people/barney">Barney</a>\n'
            '  <a href="http://example.com/buy/our/stuff">Click this!</a>\n'
            '</html>\n'
            )
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getListOfPersons()
        self.assertEquals(result, ['fred', 'barney'])
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/people')

    def test_getListOfPersons_with_errors(self):
        from schooltool.wxclient import SchoolToolClient
        version = 'UnitTest/0.0'
        e = socket.error(23, 'out of persons')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getListOfPersons()
        self.assertEquals(result, [])

    def test_getPersonInfo(self):
        from schooltool.wxclient import SchoolToolClient
        body = (
            '<html>\n'
            '  <h1>Foo!</h1>\n'
            '</html>\n'
            )
        version = 'UnitTest/0.0'
        person_id = 'foo'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getPersonInfo(person_id)
        self.assertEquals(result, body)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/people/foo')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchoolToolClient))
    return suite

if __name__ == '__main__':
    unittest.main()
