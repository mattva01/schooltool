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
Unit tests for schooltool.client
"""

import unittest
import httplib
import socket
from StringIO import StringIO
from xml.sax import make_parser
from xml.sax.handler import feature_namespaces

__metaclass__ = type

class HTTPStub:

    def __init__(self, host, port=80):
        self.host = host
        self.port = port

        if host == 'badhost':
            raise socket.error(-2, 'Name or service not known')
        if port != 80:
            raise socket.error(111, 'Connection refused')

    def putrequest(self, method, resource, *args, **kw):
        self.method = method
        self.resource = resource

    def putheader(self, key, value):
        pass

    def endheaders(self):
        pass

    def getresponse(self):
        return ResponseStub(self)

class ResponseStub:

    def __init__(self, request):
        self.request = request

    def read(self):
        if self.request.resource == "/":
            return "Welcome"
        if self.request.resource == "/doc.xml":
            return """\
<index xmlns:xlink="http://www.w3.org/1999/xlink">
  <student xlink:type="simple"
           xlink:href="student1"
           xlink:title="John"/>
  <student xlink:type="simple"
           xlink:href="student2"
           xlink:title="Kate"/>
</index>
"""
        else:
            return "404 :-)"

class TestClient(unittest.TestCase):

    def setUp(self):
        from schooltool.client import Client
        self.client = Client()
        self.emitted = ""
        def emit(*args):
            if self.emitted:
                self.emitted = "%s\n%s" % (self.emitted, ' '.join(args))
            else:
                self.emitted = ' '.join(args)
        self.client.emit = emit
        self.client.http = HTTPStub

    def test_help(self):
        self.client.onecmd("?help")
        self.assertEqual(self.emitted, "This help.")

    def test_server(self):
        self.client.do_server("server.example.com")
        self.assertEqual(self.client.server, "server.example.com")
        self.assertEqual(self.emitted, "Welcome")

        self.emitted = ""
        self.client.do_server("server2.example.com  \t")
        self.assertEqual(self.client.server, "server2.example.com")
        self.assertEqual(self.emitted, "Welcome")

        self.emitted = ""
        self.client.do_server("")
        self.assertEqual(self.client.server, "server2.example.com")
        self.assertEqual(self.emitted, "server2.example.com")

        self.emitted = ""
        self.client.do_server("server 31337")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 31337)
        self.assertEqual(self.emitted, "Error: could not connect to server")

        self.client.do_server("server")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 80)

    def test_accept(self):
        self.client.do_accept(" ")
        self.assertEqual(self.emitted, 'text/xml')

        self.emitted = ""
        self.client.do_accept("text/plain  ")
        self.assertEqual(self.emitted, 'text/plain')

        self.emitted = ""
        self.client.do_accept("text/xml; text/plain;  text/*   ")
        self.assertEqual(self.emitted, 'text/xml; text/plain; text/*')

    def test_get(self):
        self.client.server = 'localhost'
        self.client.do_get("/")
        self.assertEqual(self.emitted, "Welcome")

    def test_get_error(self):
        self.client.server = 'badhost'
        self.client.do_get("/")
        self.assertEqual(self.emitted, "Error: could not connect to badhost")

    def test_links(self):
        self.assertEqual(self.client.links, False)
        data = (('on', True), ('off', False), ('ON', True), ('OFf', False))
        for set, result in data:
            self.client.do_links(set)
            self.assertEqual(self.client.links, result)
        self.assertEqual(self.emitted, "")

        self.client.do_links("")
        self.assertEqual(self.emitted, "off")
        self.client.do_links("on")
        self.emitted = ""
        self.client.do_links("")
        self.assertEqual(self.emitted, "on")

    def test_links_get(self):
        self.assertEqual(self.client.links, False)
        self.client.do_links("on")
        self.assertEqual(self.client.links, True)
        self.client.do_get("/doc.xml")
        self.assertEqual(self.emitted, """\
<index xmlns:xlink="http://www.w3.org/1999/xlink">
  <student xlink:type="simple"
           xlink:href="student1"
           xlink:title="John"/>
  <student xlink:type="simple"
           xlink:href="student2"
           xlink:title="Kate"/>
</index>

==================================================
1   John (student1)
2   Kate (student2)"""
                         )
        self.assertEqual(self.client.resources,
                         ['/student1', '/student2'])

    def test_follow(self):
        self.client.resources = ['/doc.xml']
        self.client.do_follow('1')
        self.assertEqual(self.emitted, """\
<index xmlns:xlink="http://www.w3.org/1999/xlink">
  <student xlink:type="simple"
           xlink:href="student1"
           xlink:title="John"/>
  <student xlink:type="simple"
           xlink:href="student2"
           xlink:title="Kate"/>
</index>
"""
                         )

class TestXLinkHandler(unittest.TestCase):

    def setUp(self):
        from schooltool.client import XLinkHandler
        self.parser = make_parser()
        self.handler = XLinkHandler()
        self.parser.setContentHandler(self.handler)
        self.parser.setFeature(feature_namespaces, 1)

    def test_simple(self):
        link = ("""<top xmlns:xlink="http://www.w3.org/1999/xlink">
                     <tag xlink:type="simple"
                          xlink:title="foo"
                          xlink:href="bar"
                          name="Bond"
                          />

                     <noxlinks />
                     <tag xlink:type="simple"
                          xlink:title="moo"
                          xlink:href="spoo"
                          xlink:role="http://www.example.com/role"/>
                   </top>
                   """)
        self.parser.parse(StringIO(link))
        self.assertEqual(self.handler.links,
                         [{'type':'simple', 'title': 'foo', 'href': 'bar'},
                          {'type':'simple', 'title': 'moo', 'href': 'spoo',
                           'role': "http://www.example.com/role"}])


class TestUtilities(unittest.TestCase):

    def test_http_join(self):
        from schooltool.client import http_join
        self.assertEqual(http_join('/', 'foo'), '/foo')
        self.assertEqual(http_join('/foo', 'bar'), '/bar')
        self.assertEqual(http_join('/foo/bar', '../baz'), '/baz')
        self.assertEqual(http_join('/foo/bar', '/baz'), '/baz')
        self.assertRaises(IndexError, http_join, '/foo/bar', '../../baz')
        self.assertRaises(ValueError, http_join, 'foo/bar', '../baz')
        self.assertRaises(ValueError, http_join, '/foo/bar', 'baz//quux')
        # That ain't right, but let's document it anyway
        self.assertRaises(ValueError, http_join,
                          'http://example.com/foo', '../baz')
        self.assertRaises(ValueError, http_join,
                          '/foo/bar', 'http://www.akl.lt/programos')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestClient))
    suite.addTest(unittest.makeSuite(TestXLinkHandler))
    suite.addTest(unittest.makeSuite(TestUtilities))
    return suite

if __name__ == '__main__':
    unittest.main()
