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
Unit tests for schooltool csvclient

$Id$
"""

import unittest
import socket
from StringIO import StringIO
from pprint import pformat
from schooltool.tests.helpers import diff

__metaclass__ = type


class HTTPStub:

    def __init__(self, host, port=7001):
        self.host = host
        self.port = port
        self.sent_headers = {}
        self.sent_data = ''

        if host == 'badhost':
            raise socket.error(-2, 'Name or service not known')
        if port != 7001:
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
        from schooltool.clients.csvclient import HTTPClient
        h = HTTPClient('localhost', 7001)
        self.assertEqual(h.host, 'localhost')
        self.assertEqual(h.port, 7001)

        h.http = HTTPStub
        result = h.request('GET', '/')
        self.assertEqual(result.read(), "Welcome")


membership_pattern = (
    '<relationship xmlns:xlink="http://www.w3.org/1999/xlink"'
    ' xmlns="http://schooltool.org/ns/model/0.1"'
    ' xlink:type="simple"'
    ' xlink:arcrole="http://schooltool.org/ns/membership"'
    ' xlink:role="http://schooltool.org/ns/membership/group"'
    ' xlink:href="%s"/>')

teaching_pattern = (
    '<relationship xmlns:xlink="http://www.w3.org/1999/xlink"'
    ' xmlns="http://schooltool.org/ns/model/0.1"'
    ' xlink:type="simple"'
    ' xlink:arcrole="http://schooltool.org/ns/teaching"'
    ' xlink:role="http://schooltool.org/ns/teaching/taught"'
    ' xlink:href="%s"/>')


class TestCSVImporter(unittest.TestCase):

    def test_importGroup(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importGroup('Name', 'Title', 'root foo', '')
        self.assertEqual(requests,[
            ('/groups/Name', 'PUT',
             '<object xmlns="http://schooltool.org/ns/model/0.1"'
             ' title="Title"/>'),
            ('/groups/root/relationships', 'POST',
             membership_pattern % "/groups/Name"),
            ('/groups/foo/relationships', 'POST',
              membership_pattern % "/groups/Name"),
            ])

        requests = im.importGroup('Name', 'Title', '', 'super_facet')
        self.assertEqual(requests,
                         [('/groups/Name', 'PUT',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Title"/>'),
                          ('/groups/Name/facets', 'POST',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="super_facet"/>'),
                          ])

        requests = im.importGroup('Name', 'Title', '', 'ff1 ff2')
        self.assertEqual(requests,
                         [('/groups/Name', 'PUT',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Title"/>'),
                          ('/groups/Name/facets', 'POST',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="ff1"/>'),
                          ('/groups/Name/facets', 'POST',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="ff2"/>'),
                          ])

    def test_importResource(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importResource('Room 3')
        self.assertEqual(requests, [
            ('/resources', 'POST',
             '<object xmlns="http://schooltool.org/ns/model/0.1"'
             ' title="Room 3"/>')])

    def test_importPupil(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importPerson('Joe Hacker')
        self.assertEqual(requests,
                         [('/persons', 'POST',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Joe Hacker"/>')])

        requests = im.importPupil('007', 'foo bar')
        self.assertEqual(requests,
                         [('/groups/pupils/relationships', 'POST',
                           membership_pattern % "/persons/007"),
                          ('/groups/foo/relationships', 'POST',
                           membership_pattern % "/persons/007"),
                          ('/groups/bar/relationships', 'POST',
                           membership_pattern % "/persons/007"),
                          ])

    def test_importTeacher(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importPerson('Joe Hacker')
        self.assertEqual(requests,
                         [('/persons', 'POST',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Joe Hacker"/>')])

        requests = im.importTeacher('007', 'foo bar')
        expected = [('/groups/teachers/relationships', 'POST',
                     membership_pattern % "/persons/007"),
                    ('/groups/foo/relationships', 'POST',
                     teaching_pattern % "/persons/007"),
                    ('/groups/bar/relationships', 'POST',
                     teaching_pattern % "/persons/007"),
                    ]

        self.assertEqual(requests, expected, "\n" +
                         diff(pformat(expected), pformat(requests)))

    def test_importPersonInfo(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        requests = im.importPersonInfo('123','Joe Hacker',
                                       '1978-01-02', 'comment')
        self.assertEqual(requests, [(
            '/persons/123/facets/person_info', 'PUT',
            '<person_info xmlns="http://schooltool.org/ns/model/0.1"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<first_name>Joe</first_name>'
            '<last_name>Hacker</last_name>'
            '<date_of_birth>1978-01-02</date_of_birth>'
            '<comment>comment</comment>'
            '</person_info>'
            )])

    def test_getPersonName(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        class FakeResnonse:
            def getheader(self, header, default=None):
                if header.lower() == 'location':
                    return 'http://localhost/people/123'
                return default
        name = im.getPersonName(FakeResnonse())
        self.assertEqual(name, '123')

    def test_run_empty(self):
        from schooltool.clients.csvclient import CSVImporter
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
            ('PUT', '/groups/teachers',
             '<object xmlns="http://schooltool.org/ns/model/0.1" '
             'title="Teachers"/>'),
            ('POST', '/groups/root/relationships',
             membership_pattern % "/groups/teachers"),
            ('POST', '/groups/teachers/facets',
             '<facet xmlns="http://schooltool.org/ns/model/0.1"'
             ' factory="teacher_group"/>'),
            ('PUT', '/groups/pupils',
             '<object xmlns="http://schooltool.org/ns/model/0.1"'
             ' title="Pupils"/>'),
            ('POST', '/groups/root/relationships',
             membership_pattern % "/groups/pupils")]

        self.assertEqual(results, expected, diff(pformat(results),
                                                 pformat(expected)))

    def test_run(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()
        im.verbose = False

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2","1998-01-01",""')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1","1968-01-01",""')
            if name == 'resources.csv':
                return StringIO('"Hall"')
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
        expected = [('PUT', '/groups/teachers',
                     '<object xmlns="http://schooltool.org/ns/model/0.1" '
                     'title="Teachers"/>'),
                    ('POST', '/groups/root/relationships',
                     membership_pattern % "/groups/teachers"),
                    ('POST', '/groups/teachers/facets',
                     '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                     ' factory="teacher_group"/>'),
                    ('PUT', '/groups/pupils',
                     '<object xmlns="http://schooltool.org/ns/model/0.1"'
                     ' title="Pupils"/>'),
                    ('POST', '/groups/root/relationships',
                     membership_pattern % "/groups/pupils"),
                    ('PUT', '/groups/year1',
                     '<object xmlns="http://schooltool.org/ns/model/0.1"'
                     ' title="Year 1"/>'),
                    ('POST', '/groups/root/relationships',
                     membership_pattern % "/groups/year1"),
                    ('POST', '/persons',
                     '<object xmlns="http://schooltool.org/ns/model/0.1"'
                     ' title="Doc Doc"/>'),
                    ('POST', '/groups/teachers/relationships',
                     membership_pattern % "/persons/quux"),
                    ('POST', '/groups/group1/relationships',
                     teaching_pattern % "/persons/quux"),
                    ('PUT',
                     '/persons/quux/facets/person_info',
                     '<person_info xmlns="http://schooltool.org/ns/model/0.1" '
                     'xmlns:xlink="http://www.w3.org/1999/xlink">'
                     '<first_name>Doc</first_name><last_name>Doc</last_name>'
                     '<date_of_birth>1968-01-01</date_of_birth>'
                     '<comment></comment></person_info>'),
                    ('POST', '/persons',
                     '<object xmlns="http://schooltool.org/ns/model/0.1"'
                     ' title="Jay Hacker"/>'),
                    ('POST', '/groups/pupils/relationships',
                     membership_pattern % "/persons/quux"),
                    ('POST', '/groups/group1/relationships',
                     membership_pattern % "/persons/quux"),
                    ('POST', '/groups/group2/relationships',
                     membership_pattern % "/persons/quux"),
                    ('PUT',
                     '/persons/quux/facets/person_info',
                     '<person_info xmlns="http://schooltool.org/ns/model/0.1"'
                     ' xmlns:xlink="http://www.w3.org/1999/xlink">'
                     '<first_name>Jay</first_name>'
                     '<last_name>Hacker</last_name>'
                     '<date_of_birth>1998-01-01</date_of_birth>'
                     '<comment></comment></person_info>'),
                    ('POST', '/resources',
                     '<object xmlns="http://schooltool.org/ns/model/0.1"'
                     ' title="Hall"/>')]

        self.assertEqual(results, expected,
                         diff(pformat(results), pformat(expected)))

    def test_run_badData(self):
        from schooltool.clients.csvclient import CSVImporter
        from schooltool.clients.csvclient import DataError
        im = CSVImporter()
        im.verbose = False

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root"')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2","1998-01-01",""')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1","1998-01-01",""')
            if name == 'resources.csv':
                return StringIO('"Hall"')
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
                return StringIO('"Jay Hacker","group1 group2","what is this"'
                                ',"1998-01-01",""')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1","1998-01-01",""')
            if name == 'resources.csv':
                return StringIO('"Hall"')
        im.file = file
        self.assertRaises(DataError, im.run)

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2","1998-01-01",""')
            if name == 'teachers.csv':
                return StringIO('kria kria')
            if name == 'resources.csv':
                return StringIO('"Hall"')
        im.file = file
        self.assertRaises(DataError, im.run)

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2","1998-01-01",""')
            if name == 'teachers.csv':
                return StringIO('1,"2')
            if name == 'resources.csv':
                return StringIO('"Hall"')
        im.file = file
        self.assertRaises(DataError, im.run)

        def file(name):
            if name == 'groups.csv':
                return StringIO('"year1","Year 1","root",')
            if name == 'pupils.csv':
                return StringIO('"Jay Hacker","group1 group2","1998-01-01",""')
            if name == 'teachers.csv':
                return StringIO('"Doc Doc","group1","1998-01-01",""')
            if name == 'resources.csv':
                return StringIO('"Hall","Schmall"')
        im.file = file
        self.assertRaises(DataError, im.run)

    def test_process(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()
        im.server.http = HTTPStub
        im.process("POST", "/people/001/password", "foo")
        self.assertEqual(im.server.lastconn.sent_headers['authorization'],
                         'Basic bWFuYWdlcjpzY2hvb2x0b29s')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHTTPClient))
    suite.addTest(unittest.makeSuite(TestCSVImporter))
    return suite

if __name__ == '__main__':
    unittest.main()
