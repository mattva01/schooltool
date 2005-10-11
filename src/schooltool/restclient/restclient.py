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
Backend for the SchoolTool GUI client.  This module abstracts all communication
with the SchoolTool server.

Note that all strings used in data objects are Unicode strings.
"""

import httplib
import socket
import datetime
import urllib
import urlparse
import base64
import cgi

from schooltool.common import parse_datetime, parse_date, to_unicode
from schooltool.common import UnicodeAwareException
from schooltool.common import looks_like_a_uri
from schooltool.xmlparsing import XMLDocument
from schooltool import SchoolToolMessageID as _

__metaclass__ = type


#
# Client/server communication
#


def make_basic_auth(username, password):
    r"""Generate HTTP basic authentication credentials.

    Example:

        >>> make_basic_auth('myusername', 'secret')
        'Basic bXl1c2VybmFtZTpzZWNyZXQ='

    Usernames and passwords that contain non-ASCII characters are converted to
    UTF-8 before encoding.

        >>> make_basic_auth('myusername', '\u263B')
        'Basic bXl1c2VybmFtZTpcdTI2M0I='

    """
    creds = "%s:%s" % (username, password)
    return "Basic " + base64.encodestring(creds.encode('UTF-8')).strip()


def to_xml(s):
    r"""Prepare `s` for inclusion into XML (convert to UTF-8 and escape).

        >>> to_xml('foo')
        'foo'
        >>> to_xml(u'\u263B')
        '\xe2\x98\xbb'
        >>> to_xml('<brackets> & "quotes"')
        '&lt;brackets&gt; &amp; &quot;quotes&quot;'
        >>> to_xml(42)
        '42'

    """
    return cgi.escape(unicode(s).encode('UTF-8'), True)


class SchoolToolClient:
    """Client for the SchoolTool HTTP server.

    Every method that communicates with the server sets the status and version
    attributes.

    All URIs used to identify objects are relative and contain the absolute
    path within the server.
    """

    # Hooks for unit tests.
    connectionFactory = httplib.HTTPConnection
    secureConnectionFactory = httplib.HTTPSConnection

    def __init__(self, server='localhost', port=7001, ssl=False,
                 user=None, password=''):
        self.server = server
        self.port = port
        self.ssl = ssl
        self.user = user
        self.password = password
        self.status = ''
        self.version = ''


    # Generic HTTP methods

    def setServer(self, server, port, ssl=False):
        """Set the server name and port number.

        Tries to connect to the server and sets the status message.
        """
        self.server = server
        self.port = port
        self.ssl = ssl
        self.tryToConnect()

    def setUser(self, user, password):
        """Set the server name and port number.

        Tries to connect to the server and sets the status message.
        """
        if user:
            self.user = user
            self.password = password
        else:
            self.user = None
            self.password = ""

    def tryToConnect(self):
        """Try to connect to the server and set the status message.

        If connection is successful, try to update the URI list."""
        try:
            self.get('/')
        except SchoolToolError, e:
            # self.status has been set and will be shown on the status bar
            pass

    def get(self, url, headers=None):
        """Perform an HTTP GET request for a given URL.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('GET', url, headers=headers)

    def post(self, url, body, headers=None):
        """Perform an HTTP POST request for a given url.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('POST', url, body, headers=headers)

    def put(self, url, body, headers=None):
        """Perform an HTTP PUT request for a given url.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('PUT', url, body, headers=headers)

    def delete(self, url, headers=None):
        """Perform an HTTP DELETE request for a given url.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('DELETE', url, '', headers=headers)

    def canonizeUrl(self, url):
        """Converts absolute urls to relative, leaving relative urls untouched.

            >>> client = SchoolToolClient()
            >>> client.canonizeUrl("/persons/john")
            '/persons/john'
            >>> client.canonizeUrl("http://localhost:7001/persons/john")
            '/persons/john'

        """
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        my_scheme = self.ssl and "https" or "http"
        my_netloc = "%s:%s" % (self.server, self.port)
        if netloc == self.server:
            netloc = "%s:%s" % (self.server, self.ssl and 443 or 80)
        if scheme not in ('', my_scheme) or netloc not in ('', my_netloc):
            raise SchoolToolError("won't follow external URL %s" % url)
        if not path:
            path = '/'
        return urlparse.urlunsplit(('', '', path, query, fragment))

    def _request(self, method, url, body=None, headers=None):
        """Perform an HTTP request for a given URL.

        The URL can be an absolute path (e.g. '/persons'), or a full
        absolute URL, but only if it points to the right server.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        if self.ssl:
            conn = self.secureConnectionFactory(self.server, self.port)
        else:
            conn = self.connectionFactory(self.server, self.port)
        try:
            hdrs = {}
            if body:
                hdrs['Content-Type'] = 'text/xml'
                # Do *not* specify a Content-Length header here.  It will
                # be provided by httplib automatically.  In fact, if you do
                # specify it here, httplib will happily send out a request
                # with two Content-Type headers and confuse proxies such as
                # Apache.
            if self.user is not None:
                creds = make_basic_auth(self.user, self.password)
                hdrs['Authorization'] = creds
            if headers:
                hdrs.update(headers)
            path = self.canonizeUrl(url)
            conn.request(method, path, body, hdrs)
            response = Response(conn.getresponse())
            conn.close()
            self.status = "%d %s" % (response.status, response.reason)
            self.version = response.getheader('Server')
            return response
        except socket.error, e:
            conn.close()
            errno, message = e.args
            self.status = "%s (%d)" % (message, errno)
            self.version = ""
            raise SchoolToolError(self.status)

    # SchoolTool specific methods

    def getContainerItems(self, url, ref_class):
        """Parse an XML representation of a container.

        Returns a sequence of ref_class items.
        """
        response = self.get(url)
        if response.status != 200:
            raise ResponseStatusError(response)
        return [ref_class(self, url, title)
                for title, url in _parseContainer(response.read())]

    def getPersons(self):
        """Return the list of all persons.

        Returns a sequence of PersonRef objects.
        """
        return self.getContainerItems('/persons', PersonRef)

    def getGroups(self):
        """Return the list of all groups.

        Returns a sequence of GroupRef objects.
        """
        return self.getContainerItems('/groups', GroupRef)

    def getResources(self):
        """Return the list of all resources.

        Returns a sequence of ResourceRef objects.
        """
        return self.getContainerItems('/resources', ResourceRef)

    def getSections(self):
        """Return the list of all sections.

        Returns a sequence of SectionRef objects.
        """
        return self.getContainerItems('/sections', SectionRef)

    def getCourses(self):
        """Return the list of all courses.

        Returns a sequence of CourseRef objects.
        """
        return self.getContainerItems('/courses', CourseRef)

    def savePersonInfo(self, person_url, person_info):
        """Put a PersonInfo object."""
        body = """
            <object xmlns:xlink="http://www.w3.org/1999/xlink"
                    xmlns="http://schooltool.org/ns/model/0.1"
                    title="%s" />
        """ % to_xml(person_info.title)

        response = self.put(person_url, body)
        if response.status / 100 != 2:
            raise ResponseStatusError(response)

    def getPersonPhoto(self, person_url):
        """Return the photo of a person.

        Returns an 8-bit string with JPEG data.

        Returns None if the person does not have a photo.
        """
        response = self.get(person_url + '/photo')
        if response.status == 404:
            return None
        elif response.status != 200:
            raise ResponseStatusError(response)
        else:
            return response.read()

    def removePersonPhoto(self, person_url):
        """Remove a person's photo."""
        url = person_url + '/photo'
        response = self.delete(url)
        if response.status / 100 != 2:
            raise ResponseStatusError(response)

    def getObjectRelationships(self, object_url):
        """Return relationships of an application object (group or person).

        Returns a list of RelationshipInfo objects.
        """
        response = self.get('%s/relationships' % object_url)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseRelationships(response.read())

    def getTerms(self):
        """Return a list of terms.

        Returns a sequence of tuples (term_title, term_url).
        """
        response = self.get("/terms")
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getTimetableSchemas(self):
        """Return a list of timetable schemas.

        Returns a sequence of tuples (term_title, term_url).
        """
        response = self.get("/ttschemas")
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def createPerson(self, person_title, name, password=None):
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"/>' % to_xml(person_title))

        url = '/persons/' + name
        response = self.put(url, body)

        if response.status not in (200, 201):
            raise ResponseStatusError(response)

        if password is not None:
            response = self.put(url + '/password', password)
            if response.status != 200:
                raise ResponseStatusError(response)
        return PersonRef(self, url, person_title)

    def createGroup(self, title, description=""):
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"'
                ' description="%s"/>' % (to_xml(title), to_xml(description)))
        response = self.post('/groups', body)
        if response.status != 201:
            raise ResponseStatusError(response)
        url = self._pathFromResponse(response)
        return GroupRef(self, url, title)

    def createResource(self, title, description=""):
        body = ('<object xmlns="http://schooltool.org/ns/model/0.1"'
                ' title="%s"'
                ' description="%s"/>' % (to_xml(title), to_xml(description)))
        response = self.post('/resources', body)
        if response.status != 201:
            raise ResponseStatusError(response)
        url = self._pathFromResponse(response)
        return ResourceRef(self, url, title)

    def createRelationship(self, obj1_url, obj2_url, reltype, obj2_role):
        """Create a relationship between two objects.

        reltype and obj2_role are simple string URIs, not URIObjects.

        Example:
          client.createRelationship('/persons/john', '/groups/teachers',
                                    URIMembership_uri, URIMember_uri)
        """
        obj1_path = self.canonizeUrl(obj1_url)
        obj2_path = self.canonizeUrl(obj2_url)
        body = ('<relationship xmlns="http://schooltool.org/ns/model/0.1"'
                ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xlink:type="simple"'
                ' xlink:href="%s" xlink:arcrole="%s" xlink:role="%s"/>'
                % tuple(map(to_xml, [obj2_path, reltype, obj2_role])))
        response = self.post('%s/relationships' % obj1_path, body)
        if response.status != 201:
            raise ResponseStatusError(response)
        return self._pathFromResponse(response)

    def _pathFromResponse(self, response):
        """Return the path portion of the Location header in the response."""
        location = response.getheader('Location')
        slashslash = location.index('//')
        slash = location.index('/', slashslash + 2)
        return location[slash:]

    def deleteObject(self, object_url):
        """Delete an object."""
        response = self.delete(object_url)
        if response.status != 200:
            raise ResponseStatusError(response)


class Response:
    """HTTP response.

    Wraps httplib.HTTPResponse and stores the response body as a string.
    The whole point of this class is that you can get the response body
    after the connection has been closed.
    """

    def __init__(self, response):
        self.status = response.status
        self.reason = response.reason
        self.body = response.read()
        self._response = response

    def getheader(self, header):
        return self._response.getheader(header)

    def read(self):
        return self.body

    __str__ = read


#
# Parsing utilities
#

def _parseContainer(body):
    """Parse the contents of a container.

    Returns a list of tuples (object_title, object_href).
    """
    doc = XMLDocument(body)
    doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')
    items = []
    for node in doc.query("/container/items/item[@xlink:href]"):
        href = node['xlink:href']
        title = node.get('xlink:title', href.split('/')[-1])
        items.append((title, href))
    return items


def _parseRelationships(body, uriobjects=None):
    """Parse the list of relationships.

    uriobjects is a mapping from URIs to URIObjects.  Note that new keys
    may be added to this mapping, to register unknown URIs.
    """
    if uriobjects is None:
        uriobjects = {}

    doc = XMLDocument(body)
    doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')
    doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
    relationships = []
    for node in doc.query("/m:relationships/m:existing/m:relationship"):
        href = node.get('xlink:href')
        role_uri = node.get('xlink:role')
        arcrole_uri = node.get('xlink:arcrole')
        if (not href
            or not looks_like_a_uri(role_uri)
            or not looks_like_a_uri(arcrole_uri)):
            continue
        title = node.get('xlink:title', href.split('/')[-1])
        try:
            role = uriobjects[role_uri]
        except KeyError:
            role = uriobjects[role_uri] = URIObject(role_uri)
        try:
            arcrole = uriobjects[arcrole_uri]
        except KeyError:
            arcrole = uriobjects[arcrole_uri] = URIObject(arcrole_uri)
        manage_nodes = node.query("m:manage/@xlink:href")
        if len(manage_nodes) != 1:
            raise SchoolToolError(_("Could not parse relationship list"))
        link_href = manage_nodes[0].content
        relationships.append(RelationshipInfo(arcrole, role, title,
                                              href, link_href))
    return relationships


def _parsePersonInfo(body):
    """Parse the data provided by the person XML representation."""
    doc = XMLDocument(body)
    doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')
    doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
    try:
        node = doc.query("/m:person/m:title")[0]
        return PersonInfo(node.content)
    except IndexError:
        raise SchoolToolError(_("Insufficient data in person info"))


def _parseGroupInfo(body):
    """Parse the data provided by the group XML representation."""
    doc = XMLDocument(body)
    doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')
    doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
    try:
        title = doc.query("/m:group/m:title")[0].content
        description = doc.query("/m:group/m:description")[0].content
        return GroupInfo(title, description)
    except IndexError:
        raise SchoolToolError(_("Insufficient data in group info"))


#
# Object representations
#


class ObjectRef(object):
    """Reference to an object.

    Pythonic equivalent of an xlink.  Has a URL and an (optional) title.  Knows
    whence it came from (that is, has a reference to the SchoolToolClient).
    """

    def __init__(self, client, url, title=None):
        """Create an object reference.

            >>> client = SchoolToolClient()
            >>> obj_ref = ObjectRef(client, 'http://localhost:7001/foo')
            >>> obj_ref.client is client
            True
            >>> obj_ref.title
            >>> obj_ref.url
            'http://localhost:7001/foo'

            >>> obj_ref = ObjectRef(client, 'http://localhost:7001/foo', 'Me!')
            >>> obj_ref.title
            'Me!'

        """
        self.client = client
        self.url = url
        self.title = title

    def __eq__(self, other):
        """Compare object references.

            >>> client = SchoolToolClient()
            >>> other_client = SchoolToolClient()
            >>> r = ObjectRef(client, '/path/r1', 'Some title')
            >>> r == ObjectRef(client, '/path/r1', 'Some other title')
            True
            >>> r == ObjectRef(client, '/path/r2', 'Some title')
            False
            >>> r == ObjectRef(other_client, '/path/r1', 'Some title')
            False
            >>> r == 42
            False

        """
        return (type(self) == type(other)
                and self.client == other.client and self.url == other.url)

    def __repr__(self):
        """Return a string representation of the object reference.

            >>> ObjectRef(None, 'http://street.corner:7001/bar', 'A Bar')
            <ObjectRef A Bar at http://street.corner:7001/bar>

        """
        return '<%s %s at %s>' % (self.__class__.__name__, self.title,
                                  self.url)


class PersonRef(ObjectRef):
    """Reference to a person object.

        >>> pr = PersonRef(None, 'http://street.corner:7001/bar', 'A Bar')
        >>> pr
        <PersonRef A Bar at http://street.corner:7001/bar>

    References of different types are not equal.

        >>> pr == ObjectRef(None, 'http://street.corner:7001/bar', 'A Bar')
        False

    """

    def getInfo(self):
        """Return information about a person.

        Returns a PersonInfo object.
        """
        response = self.client.get(self.url)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parsePersonInfo(response.read())

    def setPassword(self, new_password):
        """Change the password for this person."""
        response = self.client.put('%s/password' % self.url, new_password,
                                   headers={'Content-Type': 'text/plain'})
        if response.status != 200:
            raise ResponseStatusError(response)

    def setPhoto(self, photo, content_type='application/octet-stream'):
        """Upload a photo for a person.

        photo should be an 8-bit string with image data.
        """
        url = self.url + '/photo'
        response = self.client.put(url, photo,
                                   headers={'Content-Type':
                                            content_type})
        if response.status not in (200, 201):
            raise ResponseStatusError(response)


class GroupRef(ObjectRef):
    """Reference to a group object."""

    def getInfo(self):
        """Return information about a group.

        Returns a GroupInfo object.
        """
        response = self.client.get(self.url)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseGroupInfo(response.read())

    def getMembers(self):
        """Return a list of group members.

        Returns a list of MemberRef objects.
        """
        relationships = self.client.getObjectRelationships(self.url)
        member_relationships = [relationship for relationship in relationships
                                if relationship.role.uri == URIMember_uri]
        return [PersonRef(self.client, member_relationship.target_path)
                for member_relationship in member_relationships]

    def addMember(self, member):
        """Add a member to this group."""
        self.client.createRelationship(self.url, member.url,
                                       URIMembership_uri, URIMember_uri)


class ResourceRef(ObjectRef):
    """Reference to a resource object."""


class CourseRef(ObjectRef):
    """Reference to a course object."""

    def addSection(self, section):
        """Add a section to this course."""
        self.client.createRelationship(self.url, section.url,
                                       URICourseSections_uri,
                                       URISectionOfCourse_uri)


class SectionRef(ObjectRef):
    """Reference to a section object."""

    def addInstructor(self, instructor):
        """Add an instructor to this section."""
        self.client.createRelationship(self.url, instructor.url,
                                       URIInstruction_uri, URIInstructor_uri)

    def addLearner(self, learner):
        """Add a learner to this section."""
        self.client.createRelationship(self.url, learner.url,
                                       URIMembership_uri, URIMember_uri)


class PersonInfo:
    """An object containing the data for a person."""

    def __init__(self, title=None):
        self.title = title


class GroupInfo:
    """An object containing the data for a group."""

    def __init__(self, title, description=None):
        self.title = title
        self.description = description


#
# Old-school application object representation
# XXX mg: will go away *soon*, I promise.  Yes.  Really.  Err.  Yes.
#


Unchanged = "Unchanged"


class URIObject:
    """An object that represents an URI."""

    def __init__(self, uri, name=None, description=''):
        assert looks_like_a_uri(uri)
        self.uri = uri
        if name is None:
            name = uri
        self.name = name
        self.description = description


URIMembership_uri = 'http://schooltool.org/ns/membership'
URIMember_uri = 'http://schooltool.org/ns/membership/member'
URIGroup_uri = 'http://schooltool.org/ns/membership/group'

URIInstruction_uri = 'http://schooltool.org/ns/instruction'
URISection_uri = 'http://schooltool.org/ns/instruction/section'
URIInstructor_uri = 'http://schooltool.org/ns/instruction/instructor'

URICourseSections_uri = 'http://schooltool.org/ns/coursesections'
URICourse_uri = 'http://schooltool.org/ns/coursesections/course'
URISectionOfCourse_uri = 'http://schooltool.org/ns/coursesections/section'


class RelationshipInfo:
    """Information about a relationship."""

    arcrole = None              # Role of the target (URIObject)
    role = None                 # Role of the relationship (URIObject)
    target_title = None         # Title of the target
    target_path = None          # Path of the target
    link_path = None            # Path of the link

    def __init__(self, arcrole, role, title, path, link_path):
        self.arcrole = arcrole
        self.role = role
        self.target_title = title
        self.target_path = path
        self.link_path = link_path

    def __cmp__(self, other):
        if not isinstance(other, RelationshipInfo):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp((self.arcrole, self.role, self.target_title,
                    self.target_path, self.link_path),
                   (other.arcrole, other.role, other.target_title,
                    other.target_path, other.link_path))

    def __repr__(self):
        return "%s(%r, %r, %r, %r, %r)" % (self.__class__.__name__,
                   self.arcrole, self.role, self.target_title,
                   self.target_path, self.link_path)


#
# Exceptions
#

class SchoolToolError(UnicodeAwareException):
    """Communication error"""


class ResponseStatusError(SchoolToolError):
    """The server returned an unexpected HTTP status code."""

    def __init__(self, response):
        errmsg = "%d %s" % (response.status, response.reason)
        if response.getheader('Content-Type') == 'text/plain':
            errmsg += '\n%s' % response.read()
        SchoolToolError.__init__(self, errmsg)
        self.status = response.status
        self.reason = response.reason

