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
Functional tests for SchoolTool mockup RESTive pages.

Requirements:
 - schooltool mockup HTTP server should be listening on localhost:8080
"""

import unittest
import httplib
import urllib

__metaclass__ = type


class ConnectionMixin:
    """Mixin for initiating HTTP connections.

    SERVER attribute can be
     - a string containing a hostname (e.g. 'localhost')
     - a string containing a hostname and a port (e.g. 'localhost:8080')
    """

    SERVER = 'localhost:8080'

    def setUp(self):
        self.__connections = []

    def tearDown(self):
        """Closes any connections created with new_connection"""
        for c in self.__connections:
            c.close()

    def new_connection(self, host=SERVER, *args, **kw):
        """A thin wrapper around httplib.HTTPConnection.

        By calling new_connection instead of instantiating HTTPConnections
        manually you gain two things:
         - connections are automatically closed in tearDown
         - default hostname is automatically supplied for you (although you
           can override it if you want to)
        """
        c = httplib.HTTPConnection(host, *args, **kw)
        self.__connections.append(c)
        return c

    def make_request(self, *args, **kw):
        """Makes a request to the default server and returns a HTTPResponse.

        Arguments are passed as-is to HTTPConnection.request.  They are,
        in order:
         - HTTP method
         - location
         - body
         - headers as dict
        """
        c = self.new_connection()
        c.request(*args, **kw)
        return c.getresponse()


class TestRootPage(ConnectionMixin, unittest.TestCase):
    """Tests the root page."""

    def test_get(self):
        response = self.make_request("GET", "/")
        self.assertEqual(response.status, 200)
        ctype = response.getheader("Content-Type")
        self.assert_(ctype == "text/html" or ctype.startswith("text/html;"))

    def test_other_methods(self):
        response = self.make_request("POST", "/")
        self.assertEqual(response.status, 405)
        response = self.make_request("PUT", "/")
        self.assertEqual(response.status, 405)
        response = self.make_request("DELETE", "/")
        self.assertEqual(response.status, 405)


class TestPeople(ConnectionMixin, unittest.TestCase):
    """Tests the /people resource."""

    def test_get(self):
        for resource in ("/people", "/people/"):
            response = self.make_request("GET", "/people")
            self.assertEqual(response.status, 200)
            ctype = response.getheader("Content-Type")
            self.assert_(ctype == "text/html"
                         or ctype.startswith("text/html;"))
            body = response.read()
            self.assert_('John' in body)
            self.assert_('Steve' in body)
            self.assert_('Mark' in body)


    def test_other_methods(self):
        response = self.make_request("POST", "/people")
        self.assertEqual(response.status, 405)
        response = self.make_request("PUT", "/people")
        self.assertEqual(response.status, 405)
        response = self.make_request("DELETE", "/people")
        self.assertEqual(response.status, 405)


class TestPerson(ConnectionMixin, unittest.TestCase):
    """Tests the /people/someone resource."""

    def test_get(self):
        response = self.make_request("GET", "/people/0")
        self.assertEqual(response.status, 200)
        ctype = response.getheader("Content-Type")
        self.assert_(ctype == "text/html" or ctype.startswith("text/html;"))
        body = response.read()
        self.assert_('John' in body)

    def test_get_with_a_slash(self):
        response = self.make_request("GET", "/people/0")
        self.assertEqual(response.status, 200)
        ctype = response.getheader("Content-Type")
        self.assert_(ctype == "text/html" or ctype.startswith("text/html;"))

    def test_other_methods(self):
        response = self.make_request("POST", "/people/0")
        self.assertEqual(response.status, 405)
        response = self.make_request("PUT", "/people/0")
        self.assertEqual(response.status, 405)
        response = self.make_request("DELETE", "/people/0")
        self.assertEqual(response.status, 405)

    def test_photo(self):
        response = self.make_request("GET", "/people/0/photo")
        self.assertEqual(response.status, 200)
        ctype = response.getheader("Content-Type")
        self.assertEqual(ctype, "image/jpeg")


class TestNotFoundPage(ConnectionMixin, unittest.TestCase):
    """Tests the 404 page."""

    def test_get(self):
        response = self.make_request("GET", "/nonexisting")
        self.assertEqual(response.status, 404)
        ctype = response.getheader("Content-Type")
        self.assert_(ctype == "text/html" or ctype.startswith("text/html;"))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRootPage))
    suite.addTest(unittest.makeSuite(TestPeople))
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestNotFoundPage))
    return suite

if __name__ == '__main__':
    unittest.main()
