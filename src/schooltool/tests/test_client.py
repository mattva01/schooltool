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

__metaclass__ = type

class HTTPStub:

    def __init__(self, host, port=80):
        self.host = host
        self.port = port

        if host == 'badhost':
            raise socket.error(-2, 'Name or service not known')

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
        else:
            return "404 :-)"

class TestClient(unittest.TestCase):

    def setUp(self):
        from schooltool.client import Client
        self.client = Client()
        self.emitted = ""
        def emit(*args):
            self.emitted += ' '.join(args)
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

        self.client.do_server("server 31337")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 31337)

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

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestClient))
    return suite

if __name__ == '__main__':
    unittest.main()
