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
The CSV (comma-separated value) importer for SchoolTool.

This is just the back-end part.  See import-sampleschool.py at the project root
for an executable script.

The importer expects to find the following files in the current directory:

  groups.csv
  persons.csv
  resources.csv

There's a script called datagen.py (see generate-sampleschool.py at the project
root) that can generate samples for you.


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
  facets  -- A space separated list of facet factories to add to this group.
             The list can be empty.

The following two groups are always created and should not be defined
explicitly:
  - Pupils group (/groups/pupils).
  - Teachers group (/groups/teachers) with teacher_group facet added to it.

Sample groups.cvs::

  "math","Mathematics Department","root",""
  "year1","Year 1","root",""
  "math1","Mathematics 1","math year1","subject_group"


persons.csv contains lines of comma-separated values with the following columns:

  id          -- unique id of person (optional)
  surname     -- person's surname
  given_name  -- person's given name
  groups      -- A space-separated list of groups this person is a member of.
  dob         -- Date of birth in ISO 8601 format (YYYY-MM-DD).
  comment     -- a comment


Sample pupils.csv::

  "jcox","Cox","James","pupils year1 esl","1990-04-25","Splay footed."
  "","Smith","Nicola","teachers bio","",""


resources.csv contains lines of comma-separated values with the following
columns:

  title  -- The human readable name of the resource.
  groups -- A space-separated list of groups that this resource belongs to.

Sample resources.csv::

  "Hall", "locations"
  "Stadium", "locations"
  "Projector 1", ""
  "Projector 2", ""
  "Room 1", "locations"
  "Room 2", "locations miscgroup"


$Id$
"""

import cgi
import sys
import base64
import httplib
from schooltool.translation import ugettext as _
from schooltool.csvimport import CSVImporterBase, DataError
from schooltool.common import from_locale
from schooltool.common import to_unicode


class HTTPClient:

    connectionFactory = httplib.HTTPConnection
    secureConnectionFactory = httplib.HTTPSConnection

    def __init__(self, host='localhost', port=7001, ssl=False):
        self.host = host
        self.port = port
        self.ssl = ssl

    def request(self, method, resource, body=None, headers={}):
        if self.ssl:
            factory = self.secureConnectionFactory
        else:
            factory = self.connectionFactory
        conn = factory(self.host, self.port)
        self.lastconn = conn # for unit tests
        conn.request(method, resource, body, headers)
        response = conn.getresponse()
        text = response.read()
        conn.close()
        return response, text


class CSVImporterHTTP(CSVImporterBase):
    """A CSV importer that works over HTTP.

    Prints random stuff, including unicode strings to sys.stdout.
    In other words, make sure sys.stdout is wrapped with a StreamWrapper,
    or you may get unicode errors.
    """

    fopen = open
    verbose = True
    user = 'manager'
    password = 'schooltool'

    def  __init__(self,  host='localhost', port=7001, ssl=False):
        self.server = HTTPClient(host, port, ssl)

    def recode(self, value):
        return from_locale(value)

    def run(self):
        """Run the batch import.

        Used by the command-line client.
        """
        try:
            self.blather(_("Creating groups... "))
            self.importGroupsCsv(self.fopen('groups.csv'))
            self.blather(_("Creating people... "))
            self.importPersonsCsv(self.fopen('persons.csv'))
            self.blather(_("Creating resources... "))
            self.importResourcesCsv(self.fopen('resources.csv'))
            self.blather(_("Import finished successfully"))
        except DataError:
            raise

    def blather(self, message):
        """Print message to stdandard output if self.verbose is True."""
        if self.verbose:
            print
            print message

    def membership(self, group, member_path):
        """Return a tuple (method, path, body) to add a member to a group."""
        return ('POST', '/groups/%s/relationships' % group,
                '<relationship xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xmlns="http://schooltool.org/ns/model/0.1"'
                ' xlink:type="simple"'
                ' xlink:arcrole="http://schooltool.org/ns/membership"'
                ' xlink:role="http://schooltool.org/ns/membership/group"'
                ' xlink:href="%s"/>' % to_xml(member_path))

    def teaching(self, taught, teacher):
        """A tuple (method, path, body) to add a teacher to a group"""
        return ('POST', '/groups/%s/relationships' % taught,
                '<relationship xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xmlns="http://schooltool.org/ns/model/0.1"'
                ' xlink:type="simple"'
                ' xlink:arcrole="http://schooltool.org/ns/teaching"'
                ' xlink:role="http://schooltool.org/ns/teaching/taught"'
                ' xlink:href="%s"/>' % to_xml(teacher))

    def importGroup(self, name, title, parents, facets):
        """Import a group."""
        result = []
        result.append(('PUT', '/groups/%s' % name,
                       '<object xmlns="http://schooltool.org/ns/model/0.1" '
                       'title="%s"/>' % to_xml(title)))
        for parent in parents.split():
            result.append(self.membership(parent, "/groups/%s" % name))
        for facet in facets.split():
            result.append(('POST', '/groups/%s/facets' % name,
                           '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                           ' factory="%s"/>' % to_xml(facet)))
        for method, resource, body in result:
            self.process(method, resource, body=body)

    def importPerson(self, name, surname, given_name, groups):
        
        """Import a person.
        Returns the name of the created person object.
        """
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"/>' % to_xml(' '.join([given_name, surname])))
        path = '/persons/%s' % (name)
        response = self.process('POST', '/persons', body=body)
        name = self.getName(response)

        result = []


        for group in groups.split():
            result.append(self.membership(group, "/persons/%s" % name))

        for method, resource, body in result:
            self.process(method, resource, body=body)

        return name

    def importResource(self, title, groups):
        """Import a resource and add it to each of `groups`.

        `groups` is a string of group names separated by spaces.
        """
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"/>' % to_xml(title))
        response = self.process('POST', '/resources', body=body)

        name = self.getName(response)
        result = []
        for group in groups.split():
            result.append(self.membership(group, "/resources/%s" % name))
        for method, resource, body in result:
            self.process(method, resource, body=body)

    def importPersonInfo(self, name, surname, given_name, dob, comment):
        """Add a person info facet to a person"""
        body = ('<person_info xmlns="http://schooltool.org/ns/model/0.1"'
                ' xmlns:xlink="http://www.w3.org/1999/xlink">'
                '<first_name>%s</first_name>'
                '<last_name>%s</last_name>'
                '<date_of_birth>%s</date_of_birth>'
                '<comment>%s</comment>'
                '</person_info>' % (to_xml(given_name), to_xml(surname),
                                    to_xml(dob), to_xml(comment)))
        self.process('PUT', '/persons/%s/facets/person_info' % name,
                     body=body)

    def getName(self, response):
        loc = response.getheader('Location')
        if loc is None:
            raise ValueError('response has no Location header!')
        last = loc.rindex('/')
        return loc[last+1:]

    def process(self, method, resource, body):
        creds = "%s:%s" % (self.user, self.password)
        auth = "Basic " + base64.encodestring(creds.encode('UTF-8')).strip()
        headers = {'Authorization': auth}
        response, text = self.server.request(method, resource,
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
            print to_unicode(body)
            print '-' * 70
            print response.status, response.reason
            print
            print to_unicode(text)
            sys.exit(1)
        return response


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
