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
The schooltool package.

$Id$
"""
import httplib
import csv
import sys

class HTTPClient:

    http = httplib.HTTPConnection

    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port

    def request(self, method, resource, body=None):
        conn = self.http(self.host, self.port)
        conn.putrequest(method, resource)
        if body is not None:
            conn.putheader('Content-Length', len(body))
        conn.endheaders()
        if body is not None:
            conn.send(body)
        return conn.getresponse()


class CSVImporter:

    file = file

    def  __init__(self,  host='localhost', port=8080):
        self.server = HTTPClient(host, port)

    def membership(self, group, member_path):
        """A tuple (path, method, body) to add a member to a group"""
        return ('/groups/%s/relationships' % group, 'POST',
                'arcrole="http://schooltool.org/ns/membership"\n'
                'role="http://schooltool.org/ns/membership/group"\n'
                'href="%s"\n' % member_path)

    def teaching(self, teacher, taught):
        """A tuple (path, method, body) to add a me"""
        return ('/groups/%s/relationships' % taught, 'POST',
                'arcrole="http://schooltool.org/ns/teaching"\n'
                'role="http://schooltool.org/ns/teaching/taught"\n'
                'href="/persons/%s"\n' % teacher)

    def importGroup(self, name, title, parents, facet):
        """Returns a list of tuples of (path, method, body) to run
        through the server to import this group.
        """
        result = []
        result.append(('/groups/%s' % name, 'PUT', 'title="%s"' % title))
        for parent in parents.split():
            result.append(self.membership(parent, "/groups/%s" % name))
        if facet:
            result.append(('/groups/%s/facets' % name, 'POST',
                           'factory="%s"' % facet))
        return result

    def importPerson(self, title):
        """Returns a list of tuples of (path, method, body) to run
        through the server to import this person.
        """
        return [('/persons', 'POST', 'title="%s"' % title)]

    def importPupil(self, name, parents):
        """Adds a pupil to the groups.  Need a name (generated path
        element), so it is separate from importPerson()
        """
        result = []
        result.append(self.membership('pupils', "/persons/%s" % name))
        for parent in parents.split():
            result.append(self.membership(parent, "/persons/%s" % name))
        return result

    def importTeacher(self, name, taught):
        """Adds a pupil to the groups.  Need a name (generated path
        element), so it is separate from importPerson()
        """
        result = []
        result.append(self.membership('teachers', "/persons/%s" % name))
        for group in taught.split():
            result.append(self.teaching(name, group))
        return result

    def getPersonName(self, response):
        loc = response.getheader('Location')
        if loc is None:
            raise ValueError('response has no Location header!')
        last = loc.rindex('/')
        return loc[last+1:]

    def process(self, method, resource, body):
        response = self.server.request(method, resource, body=body)
        if response.status == 200:
            sys.stdout.write('.')
        if response.status == 201:
            sys.stdout.write('+')
        sys.stdout.flush()
        if response.status == 400:
            print
            print method, resource
            print
            print body
            print '-' * 70
            print response.status, response.reason
            print
            print response.read()
            sys.exit(1)
        return response
    
    def run(self):
        print
        print "Creating groups... "
        for resource, method, body in self.importGroup("teachers", "Teachers",
                                                       "root", ''):
            self.process(method, resource, body=body)

        for resource, method, body in self.importGroup("pupils", "Pupils",
                                                       "root", ''):
            self.process(method, resource, body=body)

        for row in csv.reader(self.file("groups.csv")):
            for resource, method, body in self.importGroup(*row):
                self.process(method, resource, body=body)

        print
        print "Creating teachers... "
        for title, groups in csv.reader(self.file("teachers.csv")):
            for resource, method, body in self.importPerson(title):
                response = self.process(method, resource, body=body)
                name = self.getPersonName(response)

            for resource, method, body in self.importTeacher(name, groups):
                response = self.process(method, resource, body=body)

        print
        print "Creating pupils... "
        for title, groups in csv.reader(self.file("pupils.csv")):
            for resource, method, body in self.importPerson(title):
                response = self.process(method, resource, body=body)
                name = self.getPersonName(response)

            for resource, method, body in self.importPupil(name, groups):
                self.process(method, resource, body=body)


if __name__ == '__main__':
    importer = CSVImporter(port=8080)
    importer.run()
