#!/usr/bin/env python2.3
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
Functional tests for RESTive pages.

Requirements:
 - some HTTP server listening on localhost:80
 - the server returns 404 for GET /does-not-exist
 - the server returns some HTML for GET /
 - the server returns 404 for POST /does-not-exist
 - the server returns 405 or 406 for POST /
 - the server returns 405 for PUT /does-not-matter
 - the server returns 404 or 405 for DELETE /does-not-exist
 - the server returns 404 for DELETE /

The default Debian apache (or apache2) installation satisfies all those
requirements.
"""

import unittest
import httplib
import urllib

class TestRestiveThings(unittest.TestCase):

    SERVER = 'localhost'        # can also be 'host:port' or 'host', port

    def setUp(self):
        self._connections = []

    def tearDown(self):
        for c in self._connections:
            c.close()

    def new_connection(self, *args):
        c = httplib.HTTPConnection(*args)
        self._connections.append(c)
        return c

    def test_get_nonexistent(self):
        c = self.new_connection(self.SERVER)
        c.request("GET", "/does-not-exist")
        response = c.getresponse()
        self.assertEqual(response.status, 404)

    def test_get_root(self):
        c = self.new_connection(self.SERVER)
        c.request("GET", "/")
        response = c.getresponse()
        self.assertEqual(response.status, 200)
        self.assert_(response.getheader("Content-Type")
                        .startswith("text/html"))
        body = response.read()
        self.assert_(body.index('html') != -1 or body.index('HTML') != -1)

    def test_post_nonexistent(self):
        c = self.new_connection(self.SERVER)
        c.request("POST", "/does-not-exist")
        response = c.getresponse()
        self.assertEqual(response.status, 404)

    def test_post_form(self):
        c = self.new_connection(self.SERVER)
        params = urllib.urlencode({'spam': 1, 'eggs': 2, 'bacon': 0})
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        c.request("POST", "/", params, headers)
        response = c.getresponse()
        self.assert_(response.status in (405, 406))

    def test_put_non_allowed(self):
        c = self.new_connection(self.SERVER)
        c.request("PUT", "/does-not-matter")
        response = c.getresponse()
        self.assertEqual(response.status, 405)

    def test_delete_non_existing(self):
        c = self.new_connection(self.SERVER)
        c.request("DELETE", "/does-not-matter")
        response = c.getresponse()
        self.assert_(response.status in (404, 405))

    def test_delete_not_allowed(self):
        c = self.new_connection(self.SERVER)
        c.request("DELETE", "/")
        response = c.getresponse()
        self.assertEqual(response.status, 405)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRestiveThings))
    return suite

if __name__ == '__main__':
    unittest.main()
