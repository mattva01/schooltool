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

$Id$
"""

import unittest
import socket
from StringIO import StringIO
from helpers import diff
from pprint import pformat

__metaclass__ = type


class HTTPStub:

    def __init__(self, host, port=8080):
        self.host = host
        self.port = port
        self.sent_headers = {}
        self.sent_data = ''

        if host == 'badhost':
            raise socket.error(-2, 'Name or service not known')
        if port != 8080:
            raise socket.error(111, 'Connection refused')

    def putrequest(self, method, resource, *args, **kw):
        self.method = method
        self.resource = resource

    def putheader(self, key, value):
        self.sent_headers[key.lower()] = value

    def endheaders(self):
        pass

    def getresponse(self):
        return ResponseStub(self)

    def send(self, s):
        self.sent_data += s


class ResponseStub:

    def __init__(self, request):
        self.request = request
        self.status = 200
        self.reason = "OK"
        if self.request.resource == "/":
            self._data = "Welcome"
        else:
            self.status = 404
            self.reason = "Not Found"
            self._data = "404 :-)"

    def read(self):
        return self._data

    def getheader(self, name, default=None):
        if name.lower() == 'content-type':
            if self.request.resource == "/":
                return 'text/plain'
            else:
                return 'text/plain'
        if name.lower() == 'location':
            if self.request.resource == "/people":
                return 'http://localhost/people/006'
        return default


class TestHTTPClient(unittest.TestCase):

    def test(self):
        from schooltool.csvclient import HTTPClient
        h = HTTPClient('localhost', 8080)
        self.assertEqual(h.host, 'localhost')
        self.assertEqual(h.port, 8080)

        h.http = HTTPStub
        result = h.request('GET', '/')
        self.assertEqual(result.read(), "Welcome")


class TestCSVImporter(unittest.TestCase):

    def test_importGroup(self):
        from schooltool.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importGroup('Name', 'Title', 'root foo', '')
        self.assertEqual(requests,
                         [('/groups/Name', 'PUT', 'title="Title"'),
                          ('/groups/root/relationships', 'POST',
                           'arcrole="http://schooltool.org/ns/membership"\n'
                           'role="http://schooltool.org/ns/membership/group"\n'
                           'href="/groups/Name"\n'),
                          ('/groups/foo/relationships', 'POST',
                           'arcrole="http://schooltool.org/ns/membership"\n'
                           'role="http://schooltool.org/ns/membership/group"\n'
                           'href="/groups/Name"\n'),
                          ])

        requests = im.importGroup('Name', 'Title', '', 'Super Facet')
        self.assertEqual(requests,
                         [('/groups/Name', 'PUT', 'title="Title"'),
                          ('/groups/Name/facets', 'POST',
                           'factory="Super Facet"'),
                          ])

    def test_importPupil(self):
        from schooltool.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importPerson('Joe Hacker')
        self.assertEqual(requests,
                         [('/persons', 'POST', 'title="Joe Hacker"')])

        requests = im.importPupil('007', 'foo bar')
        self.assertEqual(requests,
                         [('/groups/pupils/relationships', 'POST',
                           'arcrole="http://schooltool.org/ns/membership"\n'
                           'role="http://schooltool.org/ns/membership/group"\n'
                           'href="/persons/007"\n'),
                          ('/groups/foo/relationships', 'POST',
                           'arcrole="http://schooltool.org/ns/membership"\n'
                           'role="http://schooltool.org/ns/membership/group"\n'
                           'href="/persons/007"\n'),
                          ('/groups/bar/relationships', 'POST',
                           'arcrole="http://schooltool.org/ns/membership"\n'
                           'role="http://schooltool.org/ns/membership/group"\n'
                           'href="/persons/007"\n'),
                          ])

    def test_importTeacher(self):
        from schooltool.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importPerson('Joe Hacker')
        self.assertEqual(requests,
                         [('/persons', 'POST', 'title="Joe Hacker"')])

        requests = im.importTeacher('007', 'foo bar')
        expected = [('/groups/teachers/relationships', 'POST',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/persons/007"\n'),
                    ('/groups/foo/relationships', 'POST',
                     'arcrole="http://schooltool.org/ns/teaching"\n'
                     'role="http://schooltool.org/ns/teaching/taught"\n'
                     'href="/persons/007"\n'),
                    ('/groups/bar/relationships', 'POST',
                     'arcrole="http://schooltool.org/ns/teaching"\n'
                     'role="http://schooltool.org/ns/teaching/taught"\n'
                     'href="/persons/007"\n'),
                    ]

        self.assertEqual(requests, expected, "\n" +
                         diff(pformat(expected), pformat(requests)))

    def test_getPersonName(self):
        from schooltool.csvclient import CSVImporter

        im = CSVImporter()

        class FakeResnonse:
            def getheader(self, header, default=None):
                if header.lower() == 'location':
                    return 'http://localhost/people/123'
                return default
        name = im.getPersonName(FakeResnonse())
        self.assertEqual(name, '123')

    def test_run_empty(self):
        from schooltool.csvclient import CSVImporter
        im = CSVImporter()
        im.verbose = False

        def file(name):
            return StringIO()
        im.file = file

        results = []
        def process(method, resource, body):
            results.append((method, resource, body))
            class ResponseStub:
                def getheader(self, header):
                    return 'foo://bar/baz/quux'
            return ResponseStub()
        im.process = process
        im.run()
        expected = [
            ('PUT', '/groups/teachers', 'title="Teachers"'),
            ('POST', '/groups/root/relationships',
             'arcrole="http://schooltool.org/ns/membership"\n'
             'role="http://schooltool.org/ns/membership/group"\n'
             'href="/groups/teachers"\n'),
            ('POST', '/groups/teachers/facets', 'factory="teacher_group"'),
            ('PUT', '/groups/pupils', 'title="Pupils"'),
            ('POST', '/groups/root/relationships',
             'arcrole="http://schooltool.org/ns/membership"\n'
             'role="http://schooltool.org/ns/membership/group"\n'
             'href="/groups/pupils"\n')]

        self.assertEqual(results, expected, diff(pformat(results),
                                                 pformat(expected)))

    def test_run(self):
        from schooltool.csvclient import CSVImporter
        im = CSVImporter()
        im.verbose = False

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2"')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1"')
        im.file = file

        results = []
        def process(method, resource, body):
            results.append((method, resource, body))
            class ResponseStub:
                def getheader(self, header):
                    return 'foo://bar/baz/quux'
            return ResponseStub()
        im.process = process
        im.run()
        expected = [('PUT', '/groups/teachers', 'title="Teachers"'),
                    ('POST', '/groups/root/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/groups/teachers"\n'),
                    ('POST', '/groups/teachers/facets',
                     'factory="teacher_group"'),
                    ('PUT', '/groups/pupils', 'title="Pupils"'),
                    ('POST', '/groups/root/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/groups/pupils"\n'),
                    ('PUT', '/groups/year1', 'title="Year 1"'),
                    ('POST', '/groups/root/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/groups/year1"\n'),
                    ('POST', '/persons', 'title="Doc Doc"'),
                    ('POST', '/groups/teachers/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/persons/quux"\n'),
                    ('POST', '/groups/group1/relationships',
                     'arcrole="http://schooltool.org/ns/teaching"\n'
                     'role="http://schooltool.org/ns/teaching/taught"\n'
                     'href="/persons/quux"\n'),
                    ('POST', '/persons', 'title="Jay Hacker"'),
                    ('POST', '/groups/pupils/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/persons/quux"\n'),
                    ('POST', '/groups/group1/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/persons/quux"\n'),
                    ('POST', '/groups/group2/relationships',
                     'arcrole="http://schooltool.org/ns/membership"\n'
                     'role="http://schooltool.org/ns/membership/group"\n'
                     'href="/persons/quux"\n')]

        self.assertEqual(results, expected,
                         diff(pformat(results), pformat(expected)))

    def test_run_badData(self):
        from schooltool.csvclient import CSVImporter
        from schooltool.csvclient import DataError
        im = CSVImporter()
        im.verbose = False

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root"')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2"')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1"')
        im.file = file

        class ResponseStub:
            def getheader(self, header):
                return 'foo://bar/baz/quux'

        def process(method, resource, body):
            pass
        im.process = lambda x, y, body=None: ResponseStub()
        self.assertRaises(DataError, im.run)

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2","what is this"')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1"')
        im.file = file
        self.assertRaises(DataError, im.run)

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2"')
            if name == 'teachers.csv':
                return StringIO('kria kria')
        im.file = file
        self.assertRaises(DataError, im.run)

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2"')
            if name == 'teachers.csv':
                return StringIO('1,"2')
        im.file = file
        self.assertRaises(DataError, im.run)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHTTPClient))
    suite.addTest(unittest.makeSuite(TestCSVImporter))
    return suite

if __name__ == '__main__':
    unittest.main()
