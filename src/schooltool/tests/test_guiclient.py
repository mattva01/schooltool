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
import libxml2
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

    def setUp(self):
        libxml2.registerErrorHandler(lambda ctx, error: None, None)

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
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        path = '/path'
        e = socket.error(23, 'out of spam')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        try:
            result = client.get(path)
        except SchoolToolError, e:
            self.assertEquals(str(e), 'out of spam (23)')
        else:
            self.fail("did not raise SchoolToolError")
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(client.status, "out of spam (23)")
        self.assertEquals(client.version, '')
        self.assert_(conn.closed)

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
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        version = 'UnitTest/0.0'
        e = socket.error(23, 'out of persons')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        self.assertRaises(SchoolToolError, client.getListOfPersons)

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
        from schooltool.guiclient import SchoolToolClient, SchoolToolError
        version = 'UnitTest/0.0'
        e = socket.error(23, 'out of trees')
        factory = ConnectionFactory(None, error=e)
        client = SchoolToolClient()
        client.connectionFactory = factory
        self.assertRaises(SchoolToolError, client.getGroupTree)

    def test_getGroupInfo(self):
        from schooltool.guiclient import SchoolToolClient
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
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getGroupInfo('/groups/group1')
        self.assertEquals(list(result.members), expected)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/groups/group1')

    def test_getObjectRelationships(self):
        from schooltool.guiclient import SchoolToolClient
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
        version = 'UnitTest/0.0'
        response = ResponseStub(200, 'OK', body, server=version)
        factory = ConnectionFactory(response)
        client = SchoolToolClient()
        client.connectionFactory = factory
        result = client.getObjectRelationships('/groups/group1')
        self.assertEquals(list(result), expected)
        self.assertEquals(len(factory.connections), 1)
        conn = factory.connections[0]
        self.assertEquals(conn.path, '/groups/group1/relationships')

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchoolToolClient))
    return suite

if __name__ == '__main__':
    unittest.main()
