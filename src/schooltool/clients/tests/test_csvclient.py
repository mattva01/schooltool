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
from schooltool.tests.utils import NiceDiffsMixin
from zope.testing.doctestunit import DocTestSuite

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
        self.assertEqual(h.ssl, False)

        h.connectionFactory = HTTPStub
        h.secureConnectionFactory = None
        result = h.request('GET', '/')
        self.assertEqual(result.read(), "Welcome")

    def test_ssl(self):
        from schooltool.clients.csvclient import HTTPClient
        h = HTTPClient('localhost', 7001, ssl=True)
        self.assertEqual(h.host, 'localhost')
        self.assertEqual(h.port, 7001)
        self.assertEqual(h.ssl, True)

        h.connectionFactory = None
        h.secureConnectionFactory = HTTPStub
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


class processStub:

    def __init__(self):
        self.requests = []

    def __call__(self, method, path, body):
        self.requests.append((method, path, body))


class TestCSVImporter(NiceDiffsMixin, unittest.TestCase):

    def test_importGroup(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()
        im.process = processStub()

        im.importGroup('Name', 'Title', 'root foo', '')
        self.assertEqual(im.process.requests,[
            ('PUT', '/groups/Name',
             '<object xmlns="http://schooltool.org/ns/model/0.1"'
             ' title="Title"/>'),
            ('POST', '/groups/root/relationships',
             membership_pattern % "/groups/Name"),
            ('POST', '/groups/foo/relationships',
             membership_pattern % "/groups/Name"),
            ])

        im.process = processStub()
        im.importGroup('Name', 'Title', '', 'super_facet')
        self.assertEqual(im.process.requests,
                         [('PUT', '/groups/Name',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Title"/>'),
                          ('POST', '/groups/Name/facets',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="super_facet"/>'),
                          ])

        im.process = processStub()
        im.importGroup('Name', 'Title', '', 'ff1 ff2')
        self.assertEqual(im.process.requests,
                         [('PUT', '/groups/Name',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Title"/>'),
                          ('POST', '/groups/Name/facets',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="ff1"/>'),
                          ('POST', '/groups/Name/facets',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="ff2"/>'),
                          ])

    def test_importPerson(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()
        im.getName = lambda response: 'quux'

        im.process = processStub()
        im.importPerson('Joe Hacker', 'pupils', 'foo bar', im.membership)
        self.assertEqual(im.process.requests,
                         [('POST', '/persons',
                           '<object xmlns="http://schooltool.org/ns/model/0.1"'
                           ' title="Joe Hacker"/>'),
                          ('POST', '/groups/pupils/relationships',
                           membership_pattern % "/persons/quux"),
                          ('POST', '/groups/foo/relationships',
                           membership_pattern % "/persons/quux"),
                          ('POST', '/groups/bar/relationships',
                           membership_pattern % "/persons/quux")])

    def test_importResource(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()
        im.process = processStub()
        im.getName = lambda response: 'r123'

        im.importResource('Room 3', 'locations misc')
        self.assertEqual(im.process.requests, [
            ('POST', '/resources',
             '<object xmlns="http://schooltool.org/ns/model/0.1"'
             ' title="Room 3"/>'),
            ('POST', '/groups/locations/relationships',
             membership_pattern % "/resources/r123"),
            ('POST', '/groups/misc/relationships',
             membership_pattern % "/resources/r123")])

    def test_importPersonInfo(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()
        im.process = processStub()

        im.importPersonInfo('123','Joe Hacker', '1978-01-02', 'comment')
        self.assertEquals(im.process.requests, [(
            'PUT', '/persons/123/facets/person_info',
            ('<person_info xmlns="http://schooltool.org/ns/model/0.1"'
             ' xmlns:xlink="http://www.w3.org/1999/xlink">'
             '<first_name>Joe</first_name>'
             '<last_name>Hacker</last_name>'
             '<date_of_birth>1978-01-02</date_of_birth>'
             '<comment>comment</comment>'
             '</person_info>'))])

    def test_getName(self):
        from schooltool.clients.csvclient import CSVImporter

        im = CSVImporter()

        class FakeResponse:
            def getheader(self, header, default=None):
                if header.lower() == 'location':
                    return 'http://localhost/people/123'
                return default

        name = im.getName(FakeResponse())
        self.assertEqual(name, '123')

    def test_run(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()
        im.verbose = True
        im.fopen = lambda f: f

        messages = []
        def blatherStub(msg):
            messages.append(msg)
        im.blather = blatherStub
        im.membership = '<membership>'
        im.teaching = '<teaching>'

        calls = []
        im.importGroupsCsv = lambda f: calls.append('groups: %s' % f)
        def importPeopleCsvStub(csvdata, parent_group, relation):
            calls.append('people: %s %s %s'
                         % (csvdata, parent_group, relation))
        im.importPeopleCsv = importPeopleCsvStub
        im.importResourcesCsv = lambda f: calls.append('resources: %s' % f)

        im.run()
        self.assertEquals(messages, [u'Creating groups... ',
                                     u'Creating teachers... ',
                                     u'Creating pupils... ',
                                     u'Creating resources... ',
                                     u'Import finished successfully'])
        self.assertEquals(calls, ['groups: groups.csv',
                                  'people: teachers.csv teachers <teaching>',
                                  'people: pupils.csv pupils <membership>',
                                  'resources: resources.csv'])

    def test_importGroupsCsv(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()

        groups = []
        def importGroupStub(name, title, parents, facets):
            groups.append((name, title, parents, facets))
        im.importGroup = importGroupStub

        im.importGroupsCsv(['"year1","Year 1","root",'])
        self.assertEquals(groups,
                          [('teachers', u'Teachers', 'root', 'teacher_group'),
                           ('pupils', u'Pupils', 'root', ''),
                           (u'year1', u'Year 1', u'root', u'')])

    def test_importResourcesCsv(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()

        resources = []
        def importResourceStub(title, groups):
            resources.append((title, groups))
        im.importResource = importResourceStub

        im.importResourcesCsv(['"Hall","locations"'])
        self.assertEquals(resources, [(u'Hall', u'locations')])

    def test_importPeopleCsv(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()

        persons = []
        def importPersonStub(title, parent, groups, relation):
            persons.append((title, parent, groups, relation))
            return title
        im.importPerson = importPersonStub

        personinfo = []
        def importPersonInfoStub(name, title, dob, comment):
            personinfo.append((name, title, dob, comment))
        im.importPersonInfo = importPersonInfoStub

        im.importPeopleCsv(['"Jay Hacker","group1 group2","1998-01-01",""'],
                           'teachers', '<rel>')
        self.assertEquals(persons, [(u'Jay Hacker', 'teachers',
                                     u'group1 group2', '<rel>')])
        self.assertEquals(personinfo, [(u'Jay Hacker', u'Jay Hacker',
                                        u'1998-01-01', u'')])

    def test_import_badData(self):
        from schooltool.clients.csvclient import CSVImporter
        from schooltool.clients.csvclient import DataError
        im = CSVImporter()
        im.verbose = False

        class ResponseStub:
            def getheader(self, header):
                return 'foo://bar/baz/quux'

        im.process = lambda x, y, body=None: ResponseStub()

        def raisesDataError(method, *args):
            im.fopen = lambda fn: StringIO('"invalid","csv')
            self.assertRaises(DataError, method, "fn")

        self.assertRaises(DataError, im.importGroupsCsv,
                          ['"year1","Year 1","root"'])
        self.assertRaises(DataError, im.importResourcesCsv,
                          ['"year1","Year 1","root"'])
        self.assertRaises(DataError, im.importPeopleCsv,
                          ['"Foo","bar","baz"'], 'pupils', im.membership)

        self.assertRaises(DataError, im.importGroupsCsv, ['"invalid","csv'])
        self.assertRaises(DataError, im.importResourcesCsv, ['"b0rk","b0rk'])
        self.assertRaises(DataError, im.importPeopleCsv, ['"invalid","csv'],
                          'pupils', im.membership)


    def test_process(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter()
        im.server.connectionFactory = HTTPStub
        im.process("POST", "/people/001/password", "foo")
        self.assertEqual(im.server.lastconn.sent_headers['authorization'],
                         'Basic bWFuYWdlcjpzY2hvb2x0b29s')

    def test_ssl(self):
        from schooltool.clients.csvclient import CSVImporter
        im = CSVImporter(ssl=True)
        self.assert_(im.server.ssl)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.clients.csvclient'))
    suite.addTest(unittest.makeSuite(TestHTTPClient))
    suite.addTest(unittest.makeSuite(TestCSVImporter))
    return suite

if __name__ == '__main__':
    unittest.main()
