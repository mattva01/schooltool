#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
SchoolTool functional test setup code.

Functional tests in SchoolTool use named test fixtures.  A test fixture is a
certain state of the application that needs to be build before we can execute
a test.  Examples of test fixtures are "empty database", "standard set of users
and groups", and so on.

$Id$
"""

import unittest
import httplib
import sets


class TestCase(unittest.TestCase):

    # These should be the same as defined in test.conf
    rest_server = 'http://localhost:8813'
    web_server = 'http://localhost:8814'
    rest_server_ssl = 'https://localhost:8815'
    web_server_ssl = 'https://localhost:8816'

    # Subclasses can override this to ask for a different test fixture
    fixture_name = "empty"

    # Shared set of known test fixtures
    known_fixtures = sets.Set(["empty"])

    def setUp(self):
        unittest.TestCase.setUp(self)
        self._loadSnapshot(self.fixture_name)

    def _saveSnapshot(self, name):
        """Ask the server to make a named snapshot of the database state."""
        self._makeRequest({'X-Testing-Save-Snapshot': name})
        self.known_fixtures.add(name)

    def _loadSnapshot(self, name):
        """Ask the server to load a named snapshot of the database state."""
        self._makeRequest({'X-Testing-Load-Snapshot': name})

    def _makeRequest(self, headers):
        """Perform an HTTP GET of / with extra HTTP headers.

        Raises RuntimeError if the server returns a status code other than 200.
        """
        server = self.rest_server.split('://')[1]    # "hostname:port"
        c = httplib.HTTPConnection(server)
        try:
            c.request('GET', '/', headers=headers)
            r = c.getresponse()
            if r.status != 200:
                raise RuntimeError('server returned code %s: %s\n%s'
                                   % (r.status, r.reason, r.read()))
        finally:
            c.close()

