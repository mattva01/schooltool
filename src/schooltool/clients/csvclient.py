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
The CSV (comma-separated value) import script for SchoolTool.

This script takes no command line arguments.  It expects to find the following
files in the current directory:

  groups.csv
  pupils.csv
  teachers.csv
  resources.csv

There's a script called datagen.py that can generate samples for you.

This script expects the SchoolTool server to be running on localhost port 7001.
The server should contain an empty database; csvclient is not designed to
replace or supplement existing data.

You're probably better off using import-sampleschool.py instead of running
csvclient.py directly.  It does more, has more options, performs more safety
checks and in general is more polished.


Format of the files
-------------------

groups.csv contains lines of comma-separated values with the following columns:

  name    -- The name of this group.  It is used for constructing object URIs
             and cannot be changed.  A group with the name of x will be
             accessible as /groups/x on the server.  Names should not contain
             spaces.
  title   -- A human-readable title of the group.
  parents -- A space separated list of names of the groups this group is a
             member in.  The list can be empty.
  facet   -- A space separated list of facet factories to add to this group.
             The list can be empty.

The following two groups are always created and should not be defined
explicitly:
  - Pupils group (/groups/pupils).
  - Teachers group (/groups/teachers) with teacher_group facet added to it.

Sample groups.cvs::

  "math","Mathematics Department","root",""
  "year1","Year 1","root",""
  "math1","Mathematics 1","math year1","subject_group"


pupils.csv contains lines of comma-separated values with the following columns:

  title    -- The full name of a pupil.
  groups   -- A space-separated list of groups this pupil is a member in.
  birthday -- Date of birth in ISO 8601 format (YYYY-MM-DD).
  comment  -- A comment (a free form string).

Pupils are implicitly added to the pupils group (/groups/pupils).

Sample pupils.csv::

  "James Cox","year1 math1 ling1","1994-03-10",""
  "Tom Hall","year1 biol1 math1","1994-07-20",""


teachers.csv contains lines of comma-separated values with the following
columns:

  title    -- The full name of a teacher.
  groups   -- A space-separated list of groups this teacher teaches to.
  birthday -- Date of birth in ISO 8601 format (YYYY-MM-DD).
  comment  -- A comment (a free form string).

Teachers are implicitly added to the teachers group (/groups/teachers).

Sample teachers.csv::

  "Nicola Smith","ling3","1952-12-06",""
  "Jeff Cox","biol3","1967-06-13",""


resources.csv contains lines of comma-separated values with the following
columns:

  title -- The human readable name of the resource.

Sample resources.csv::

  "Hall"
  "Room 1"
  "Room 2"
  "Projector 1"


$Id$
"""

import csv
import cgi
import sys
import base64
import httplib
from schooltool.translation import ugettext as _
from schooltool.common import UnicodeAwareException, from_locale


class DataError(UnicodeAwareException):
    pass


class HTTPClient:

    http = httplib.HTTPConnection

    def __init__(self, host='localhost', port=7001):
        self.host = host
        self.port = port

    def request(self, method, resource, body=None, headers={}):
        conn = self.http(self.host, self.port)
        self.lastconn = conn
        conn.putrequest(method, resource)
        if body is not None:
            conn.putheader('Content-Length', len(body))
        for header, value in headers.items():
            conn.putheader(header, value)
        conn.endheaders()
        if body is not None:
            conn.send(body)
        return conn.getresponse()


class CSVImporter:

    file = file
    verbose = True
    user = 'manager'
    password = 'schooltool'

    def  __init__(self,  host='localhost', port=7001):
        self.server = HTTPClient(host, port)

    def membership(self, group, member_path):
        """A tuple (path, method, body) to add a member to a group"""
        return ('/groups/%s/relationships' % group, 'POST',
                '<relationship xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xmlns="http://schooltool.org/ns/model/0.1"'
                ' xlink:type="simple"'
                ' xlink:arcrole="http://schooltool.org/ns/membership"'
                ' xlink:role="http://schooltool.org/ns/membership/group"'
                ' xlink:href="%s"/>' % to_xml(member_path))

    def teaching(self, teacher, taught):
        """A tuple (path, method, body) to add a teacher to a group"""
        return ('/groups/%s/relationships' % taught, 'POST',
                '<relationship xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xmlns="http://schooltool.org/ns/model/0.1"'
                ' xlink:type="simple"'
                ' xlink:arcrole="http://schooltool.org/ns/teaching"'
                ' xlink:role="http://schooltool.org/ns/teaching/taught"'
                ' xlink:href="/persons/%s"/>' % to_xml(teacher))

    def importGroup(self, name, title, parents, facets):
        """Returns a list of tuples of (path, method, body) to run
        through the server to import this group.
        """
        result = []
        result.append(('/groups/%s' % name, 'PUT',
                       '<object xmlns="http://schooltool.org/ns/model/0.1" '
                       'title="%s"/>' % to_xml(title)))
        for parent in parents.split():
            result.append(self.membership(parent, "/groups/%s" % name))
        for facet in facets.split():
            result.append(('/groups/%s/facets' % name, 'POST',
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="%s"/>' % to_xml(facet)))
        return result

    def importPerson(self, title):
        """Returns a list of tuples of (path, method, body) to run
        through the server to import this person.
        """
        return [('/persons', 'POST',
                 '<object xmlns="http://schooltool.org/ns/model/0.1" '
                 'title="%s"/>' % to_xml(title))]

    def importResource(self, title):
        """Returns a list of tuples of (path, method, body) to run
        through the server to import this resource.
        """
        return [('/resources', 'POST',
                 '<object xmlns="http://schooltool.org/ns/model/0.1" '
                 'title="%s"/>' % to_xml(title))]

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
        """Adds a teacher to the groups.  Need a name (generated path
        element), so it is separate from importPerson()
        """
        result = []
        result.append(self.membership('teachers', "/persons/%s" % name))
        for group in taught.split():
            result.append(self.teaching(name, group))
        return result

    def importPersonInfo(self, name, title, dob, comment):
        """Add the Person Info to this person"""
        first_name, last_name = title.split(None, 1)
        return [('/persons/%s/facets/person_info' % name, 'PUT',
                 '<person_info xmlns="http://schooltool.org/ns/model/0.1"'
                 ' xmlns:xlink="http://www.w3.org/1999/xlink">'
                 '<first_name>%s</first_name>'
                 '<last_name>%s</last_name>'
                 '<date_of_birth>%s</date_of_birth>'
                 '<comment>%s</comment>'
                 '</person_info>' % (to_xml(first_name), to_xml(last_name),
                                     to_xml(dob), to_xml(comment)))]

    def getPersonName(self, response):
        loc = response.getheader('Location')
        if loc is None:
            raise ValueError('response has no Location header!')
        last = loc.rindex('/')
        return loc[last+1:]

    def process(self, method, resource, body):
        creds = "%s:%s" % (self.user, self.password)
        auth = "Basic " + base64.encodestring(creds.encode('UTF-8')).strip()
        headers = {'Authorization': auth}
        response = self.server.request(method, resource,
                                       body=body, headers=headers)
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
        if self.verbose:
            print _("Creating groups... ")
        for resource, method, body in self.importGroup(
                "teachers", _("Teachers"), "root", 'teacher_group'):
            self.process(method, resource, body=body)

        for resource, method, body in self.importGroup(
                "pupils", _("Pupils"), "root", ''):
            self.process(method, resource, body=body)

        try:
            line = 1
            file = "groups.csv"
            for row in csv.reader(self.file(file)):
                if len(row) != 4:
                    raise DataError(_("Error in %s line %d:"
                                      " expected 4 columns, got %d") %
                                    (file, line, len(row)))
                row = map(from_locale, row)
                for resource, method, body in self.importGroup(*row):
                    self.process(method, resource, body=body)
                line += 1

            if self.verbose:
                print
                print _("Creating teachers... ")

            line = 1
            file = "teachers.csv"
            for row in csv.reader(self.file(file)):
                if len(row) != 4:
                    raise DataError(_("Error in %s line %d:"
                                      " expected 4 columns, got %d") %
                                    (file, line, len(row)))
                title, groups, dob, comment = map(from_locale, row)
                for resource, method, body in self.importPerson(title):
                    response = self.process(method, resource, body=body)
                    name = self.getPersonName(response)

                for resource, method, body in self.importTeacher(name, groups):
                    response = self.process(method, resource, body=body)

                for path, meth, body in self.importPersonInfo(name, title,
                                                              dob, comment):
                    response = self.process(meth, path, body=body)
                line += 1

            if self.verbose:
                print
                print _("Creating pupils... ")

            line = 1
            file = "pupils.csv"
            for row in csv.reader(self.file(file)):
                if len(row) != 4:
                    raise DataError(_("Error in %s line %d:"
                                      " expected 4 columns, got %d") %
                                    (file, line, len(row)))
                title, groups, dob, comment = map(from_locale, row)
                for resource, method, body in self.importPerson(title):
                    response = self.process(method, resource, body=body)
                    name = self.getPersonName(response)

                for resource, method, body in self.importPupil(name, groups):
                    self.process(method, resource, body=body)

                for path, meth, body in self.importPersonInfo(name, title,
                                                              dob, comment):
                    response = self.process(meth, path, body=body)
                line += 1

            if self.verbose:
                print
                print _("Creating resources... ")

            line = 1
            file = "resources.csv"
            for row in csv.reader(self.file(file)):
                if len(row) != 1:
                    raise DataError(_("Error in %s line %d:"
                                      " expected 1 column, got %d") %
                                    (file, line, len(row)))
                title = from_locale(row[0])
                for resource, method, body in self.importResource(title):
                    response = self.process(method, resource, body=body)
                    name = self.getPersonName(response)

            if self.verbose:
                print
        except DataError:
            raise
        except csv.Error, e:
            raise DataError(_("Error in %s line %d: %s") % (file, line, e))


def to_xml(s):
    r"""Prepare s for inclusion into XML (convert to UTF-8 and escape).

        >>> to_xml('foo')
        'foo'
        >>> to_xml('<brackets> & "quotes"')
        '&lt;brackets&gt; &amp; &quot;quotes&quot;'

    It also converts Unicode objects to UTF-8.

        >>> to_xml(u'\u0105')
        '\xc4\x85'

    """
    return cgi.escape(s.encode('UTF-8'), True)


def main():
    from schooltool.common import StreamWrapper
    sys.stdout = StreamWrapper(sys.stdout)
    sys.stderr = StreamWrapper(sys.stderr)
    importer = CSVImporter()
    try:
        importer.run()
    except DataError, e:
        print >> sys.stderr
        print >> sys.stderr, e


if __name__ == '__main__':
    main()

