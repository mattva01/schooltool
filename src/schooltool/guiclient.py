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
SchoolTool GUI client.

SchoolTool is a common information systems platform for school administration
Visit http://www.schooltool.org/

Copyright (c) 2003 Shuttleworth Foundation

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import httplib
import socket
import libxml2
import datetime
import cgi
from schooltool.uris import strURI
from schooltool.common import parse_datetime

__metaclass__ = type


#
# Client/server communication
#

class SchoolToolClient:
    """Client for the SchoolTool HTTP server.

    Every method that communicates with the server sets the status and version
    attributes.

    All URIs used to identify objects are relative and contain the absolute
    path within the server.
    """

    connectionFactory = httplib.HTTPConnection

    server = 'localhost'
    port = 8080
    status = ''
    version = ''

    role_names = {'http://schooltool.org/ns/membership/member': 'Member',
                  'http://schooltool.org/ns/membership/group': 'Group',
                  'http://schooltool.org/ns/membership': 'Membership',
                  'http://schooltool.org/ns/teaching': 'Teaching',
                  'http://schooltool.org/ns/teaching/teacher': 'Teacher',
                  'http://schooltool.org/ns/teaching/taught': 'Taught',
                 }

    # Generic HTTP methods

    def setServer(self, server, port):
        """Set the server name and port number.

        Tries to connect to the server and sets the status message.
        """
        self.server = server
        self.port = port
        self.tryToConnect()

    def tryToConnect(self):
        """Try to connect to the server and set the status message."""
        try:
            self.get('/')
        except SchoolToolError, e:
            pass

    def get(self, path):
        """Perform an HTTP GET request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('GET', path)

    def post(self, path, body):
        """Perform an HTTP POST request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('POST', path, body)

    def delete(self, path):
        """Perform an HTTP DELETE request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        return self._request('DELETE', path, '')

    def _request(self, method, path, body=None, headers=None):
        """Perform an HTTP request for a given path.

        Returns the response object.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        conn = self.connectionFactory(self.server, self.port)
        try:
            hdrs = {}
            if body:
                hdrs['Content-Type'] = 'text/xml'
                hdrs['Content-Length'] = len(body)
            if headers:
                hdrs.update(headers)
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

    def getListOfPersons(self):
        """Return the list of all persons.

        Returns a sequence of tuples (person_title, person_path).
        """
        response = self.get('/persons')
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getListOfGroups(self):
        """Return the list of all groups.

        Returns a sequence of tuples (group_title, group_path).
        """
        response = self.get('/groups')
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseContainer(response.read())

    def getGroupTree(self):
        """Return the tree of groups.

        Returns a sequence of tuples (level, title, path).

        Example: the following group tree

           root
             group1
               group1a
               group1b
                 group1bb
             group2

        returns the following sequence

          (0, 'root',     '/groups/root'),
          (1, 'group1',   '/groups/group1'),
          (2, 'group1a',  '/groups/group1a'),
          (2, 'group1b',  '/groups/group1b'),
          (3, 'group1bb', '/groups/group1bb'),
          (1, 'group2',   '/groups/group2'),
        """
        # XXX instead of hardcoding a single root we could find out all
        #     actual roots by getting and parsing /
        response = self.get('/groups/root/tree')
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseGroupTree(response.read())

    def getGroupInfo(self, group_path):
        """Return information page about a group.

        Returns a GroupInfo object.
        """
        response = self.get(group_path)
        if response.status != 200:
            raise ResponseStatusError(response)
        members = _parseMemberList(response.read())
        return GroupInfo(members)

    def getObjectRelationships(self, object_path):
        """Return relationships of an application object (group or person).

        Returns a list of RelationshipInfo objects.
        """
        response = self.get('%s/relationships' % object_path)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseRelationships(response.read(), self.role_names)

    def getRollCall(self, group_path):
        """Return a roll call template for a group.

        Returns a list of RollCallInfo objects.
        """
        response = self.get('%s/rollcall' % group_path)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseRollCall(response.read())

    def submitRollCall(self, group_path, roll_call,
                       reporter_path='/persons/anonymous'):
        """Post a roll call for a group.

        Expects roll_call to be a list of RollCallEntry objects.
        """
        body = ['<rollcall xmlns:xlink="http://www.w3.org/1999/xlink">\n'
                '<reporter xlink:type="simple" xlink:href="%s"/>\n'
                % cgi.escape(reporter_path, True)]
        for entry in roll_call:
            href = cgi.escape(entry.person_path, True)
            if entry.presence is Unchanged: presence = ''
            elif entry.presence: presence = ' presence="present"'
            else: presence = ' presence="absent"'
            if not entry.comment: comment = ''
            else: comment = ' comment="%s"' % cgi.escape(entry.comment, True)
            if entry.resolved is Unchanged: resolved = ''
            elif entry.resolved: resolved = ' resolved="resolved"'
            else: resolved = ' resolved="unresolved"'
            body.append('<person xlink:type="simple" xlink:href="%s"%s%s%s/>\n'
                        % (href, presence, comment, resolved))
        body += ['</rollcall>\n']
        body = ''.join(body)
        response = self.post('%s/rollcall' % group_path, body)
        if response.status != 200:
            raise ResponseStatusError(response)

    def getAbsences(self, path):
        """Return a list of absences for an object.

        Returns a list of AbsenceInfo objects.

        The path can point to the following places:
        - an absence view for a person (/persons/person_name/absences)
        - the global absence utility (/utils/absences)
        - an absence tracker facet (/some/object/facets/absences)
        """
        response = self.get(path)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseAbsences(response.read())

    def getAbsenceComments(self, absence_path):
        """Return a list of comments for a given absence.

        Returns a list of AbsenceComment objects.
        """
        response = self.get(absence_path)
        if response.status != 200:
            raise ResponseStatusError(response)
        return _parseAbsenceComments(response.read())

    def createFacet(self, object_path, factory_name):
        """Create a facet using a given factory an place it on an object.

        Returns the URI of the new facet.
        """
        body = '<facet factory="%s"/>' % cgi.escape(factory_name, True)
        response = self.post('%s/facets' % object_path, body)
        if response.status != 201:
            raise ResponseStatusError(response)
        return self._pathFromResponse(response)

    def createPerson(self, person_title):
        body = '<person title="%s"/>' % cgi.escape(person_title, True)
        response = self.post('/persons', body)
        if response.status != 201:
            raise ResponseStatusError(response)
        return self._pathFromResponse(response)

    def createGroup(self, group_title):
        body = '<group title="%s"/>' % cgi.escape(group_title, True)
        response = self.post('/groups', body)
        if response.status != 201:
            raise ResponseStatusError(response)
        return self._pathFromResponse(response)

    def createRelationship(self, obj1_path, obj2_path, reltype, obj1_role):
        """Create a relationship between two objects.

        Example:
          from schooltool.uris import URIMembership, URIMember
          client.createRelationship('/persons/john', '/groups/teachers',
                                    URIMembership, URIMember)
        """
        body = ('<relationship href="%s" arcrole="%s" role="%s" />'
                % tuple(map(cgi.escape, [obj2_path, strURI(reltype),
                                         strURI(obj1_role)])))
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

    def deleteObject(self, object_path):
        """Delete an object."""
        response = self.delete(object_path)
        if response.status != 200:
            raise ResponseStatusError(response)

#
# Parsing utilities
#

def _parseContainer(body):
    """Parse the contents of a container.

    Returns a list of tuples (object_title, object_href).
    """
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError("Could not parse item list")
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/container/items/item[@xlink:href]")
        items = []
        for node in res:
            href = node.nsProp('href', xlink)
            title = node.nsProp('title', xlink)
            if title is None:
                title = href.split('/')[-1]
            items.append((title, href))
        return items
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()

def _parseGroupTree(body):
    """Parse the tree of groups returned from the server.

    XXX the parser assumes xlink is the namespace used for xlinks in the
        document rather than parsing xmlns:... attributes
    """

    class Handler:

        def __init__(self):
            self.level = 0
            self.result = []
            self.exception = None

        def startElement(self, tag, attrs):
            if self.exception:
                return
            if tag == 'group':
                href = attrs and attrs.get('xlink:href', None)
                if not href:
                    self.exception = SchoolToolError("Group tag does not"
                                                     " have xlink:href")
                    return
                title = attrs.get('xlink:title', None)
                if title is None:
                    title = href.split('/')[-1]
                self.result.append((self.level, title, href))
                self.level += 1

        def endElement(self, tag):
            if self.exception:
                return
            if tag == 'group':
                self.level -= 1

    try:
        handler = Handler()
        ctx = libxml2.createPushParser(handler, body, len(body), "")
        retval = ctx.parseChunk("", 0, True)
        if handler.exception:
            raise handler.exception
        if retval:
            raise SchoolToolError("Could not parse group tree")
        return handler.result
    except libxml2.parserError:
        raise SchoolToolError("Could not parse group tree")

def _parseMemberList(body):
    """Parse the list of group members (persons only)."""
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError("Could not parse member list")
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/group/item[@xlink:href]")
        people = []
        for node in res:
            anchor = node.nsProp('href', xlink)
            if anchor.startswith('/persons/'):
                name =  anchor[len('/persons/'):]
                if '/' not in name:
                    title = node.nsProp('title', xlink)
                    if title is None:
                        title = name
                    people.append(MemberInfo(title, anchor))
        return people
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()

def _parseRelationships(body, role_names):
    """Parse the list of relationships."""
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError("Could not parse relationship list")
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/relationships/existing/relationship")
        relationships = []
        for node in res:
            href = node.nsProp('href', xlink)
            role = node.nsProp('role', xlink)
            arcrole = node.nsProp('arcrole', xlink)
            if not href or not role or not arcrole:
                continue
            title = node.nsProp('title', xlink)
            if title is None:
                title = href.split('/')[-1]
            role = role_names.get(role, role)
            arcrole = role_names.get(arcrole, arcrole)
            ctx.setContextNode(node)
            manage_nodes = ctx.xpathEval("manage/@xlink:href")
            if len(manage_nodes) != 1:
                raise SchoolToolError("Could not parse relationship list")
            link_href = manage_nodes[0].content
            relationships.append(RelationshipInfo(arcrole, role, title,
                                                  href, link_href))
        return relationships
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()

def _parseRollCall(body):
    """Parse a roll call template."""
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError("Could not parse roll call")
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/rollcall/person")
        persons = []
        for node in res:
            href = node.nsProp('href', xlink)
            if not href:
                continue
            title = node.nsProp('title', xlink)
            if not title:
                title = href.split('/')[-1]
            presence = node.nsProp('presence', None)
            if presence not in ('present', 'absent'):
                raise SchoolToolError("Unrecognized presence value: %s"
                                      % presence)
            presence = (presence == 'present')
            persons.append(RollCallInfo(title, href, presence))
        return persons
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()

def _parseAbsences(body):
    """Parse a list of absences."""
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError("Could not parse absences")
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/absences/absence")
        absences = []
        for node in res:
            href = node.nsProp('href', xlink)
            if not href:
                continue
            person_path = '/'.join(href.split('/')[:-2])
            person_title = node.nsProp('person_title', None)
            if not person_title:
                person_title = person_path.split('/')[-1]
            dt = node.nsProp('datetime', None)
            if dt is None:
                raise SchoolToolError("Datetime not given")
            else:
                try:
                    dt = parse_datetime(dt)
                except ValueError, e:
                    raise SchoolToolError(str(e))
            ended = node.nsProp('ended', None)
            if ended not in ('ended', 'unended'):
                raise SchoolToolError("Unrecognized ended value: %s"
                                      % ended)
            resolved = node.nsProp('resolved', None)
            if resolved not in ('resolved', 'unresolved'):
                raise SchoolToolError("Unrecognized resolved value: %s"
                                      % resolved)
            expected_presence = node.nsProp('expected_presence', None)
            if expected_presence is not None:
                try:
                    expected_presence = parse_datetime(expected_presence)
                except ValueError, e:
                    raise SchoolToolError(str(e))
            last_comment = node.content.strip()
            absences.append(AbsenceInfo(href, dt, person_title,
                                        person_path,
                                        ended == "ended",
                                        resolved == "resolved",
                                        expected_presence, last_comment))
        return absences
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()

def _parseAbsenceComments(body):
    """Parse a list of absence comments."""
    try:
        doc = libxml2.parseDoc(body)
    except libxml2.parserError:
        raise SchoolToolError("Could not parse absence comments")
    ctx = doc.xpathNewContext()
    try:
        xlink = "http://www.w3.org/1999/xlink"
        ctx.xpathRegisterNs("xlink", xlink)
        res = ctx.xpathEval("/absence/comment")
        comments = []
        for node in res:
            ctx.setContextNode(node)
            res = ctx.xpathEval("reporter")
            if len(res) < 1:
                raise SchoolToolError("Reporter not given")
            elif len(res) > 1:
                raise SchoolToolError("More than one reporter given")
            reporter = res[0]
            reporter_href = reporter.nsProp('href', xlink)
            if not reporter_href:
                raise SchoolToolError("Reporter does not have xlink:href")
            reporter_title = reporter.nsProp('title', xlink)
            if not reporter_title:
                reporter_title = reporter_href.split('/')[-1]

            res = ctx.xpathEval("absentfrom")
            if len(res) > 1:
                raise SchoolToolError("More than one absentfrom given")
            absent_from_href = absent_from_title = ""
            if res:
                absent_from_href = res[0].nsProp('href', xlink)
                if not absent_from_href:
                    raise SchoolToolError("absentfrom does not have"
                                          " xlink:href")
                absent_from_title = res[0].nsProp('title', xlink)
                if not absent_from_title:
                    absent_from_title = absent_from_href.split('/')[-1]

            dt = node.nsProp('datetime', None)
            if dt is None:
                raise SchoolToolError("Datetime not given")
            else:
                try:
                    dt = parse_datetime(dt)
                except ValueError, e:
                    raise SchoolToolError(str(e))

            ended = node.nsProp('ended', None)
            if ended is None:
                ended = Unchanged
            elif ended in ('ended', 'unended'):
                ended = (ended == 'ended')
            else:
                raise SchoolToolError("Unrecognized ended value: %s"
                                      % ended)

            resolved = node.nsProp('resolved', None)
            if resolved is None:
                resolved = Unchanged
            elif resolved in ('resolved', 'unresolved'):
                resolved = (resolved == 'resolved')
            else:
                raise SchoolToolError("Unrecognized resolved value: %s"
                                      % resolved)

            expected_presence = node.nsProp('expected_presence', None)
            if expected_presence is None:
                expected_presence = Unchanged
            elif expected_presence == "":
                expected_presence = None
            else:
                try:
                    expected_presence = parse_datetime(expected_presence)
                except ValueError, e:
                    raise SchoolToolError(str(e))

            text = ""
            res = ctx.xpathEval("text")
            if len(res) > 1:
                raise SchoolToolError("More than one text node")
            if res:
                text = res[0].content.strip()

            comments.append(AbsenceComment(dt, reporter_title,
                                reporter_href, absent_from_title,
                                absent_from_href, ended, resolved,
                                expected_presence, text))
        return comments
    finally:
        doc.freeDoc()
        ctx.xpathFreeContext()


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


#
# Application object representation
#


Unchanged = "Unchanged"


class GroupInfo:
    """Information about a group."""

    members = None              # List of group members

    def __init__(self, members):
        self.members = members


class MemberInfo:
    """Information about a group member."""

    person_title = None
    person_path = None

    def __init__(self, title, path):
        self.person_title = title
        self.person_path = path

    def __cmp__(self, other):
        if not isinstance(other, MemberInfo):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp((self.person_title, self.person_path),
                   (other.person_title, other.person_path))

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.person_title,
                               self.person_path)


class RelationshipInfo:
    """Information about a relationship."""

    arcrole = None              # Role of the target (user friendly string)
    role = None                 # Role of the relationship (user friendly)
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


class RollCallInfo:
    """Information about a person participating in a roll call"""

    person_title = None         # Person (title)
    person_path = None          # Person (path)
    present = None              # Is the person present?

    def __init__(self, title, path, present):
        self.person_title = title
        self.person_path = path
        self.present = present

    def __cmp__(self, other):
        if not isinstance(other, RollCallInfo):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp((self.person_title, self.person_path, self.present),
                   (other.person_title, other.person_path, other.present))

    def __repr__(self):
        return "%s(%r, %r, %r)" % (self.__class__.__name__, self.person_title,
                                   self.person_path, self.present)


class RollCallEntry:
    """Information about a person participating in a roll call"""

    person_path = None          # Person (path)
    presence = Unchanged        # Present (True/False/Unchanged)?
    comment = None              # Comment (or None)
    resolved = Unchanged        # Resolved (True/False/Unchanged)?

    def __init__(self, path, presence=Unchanged, comment=None,
                 resolved=Unchanged):
        self.person_path = path
        self.presence = presence
        self.comment = comment
        self.resolved = resolved

    def __repr__(self):
        return "%s(%r, %r, %r, %r)" % (self.__class__.__name__,
                    self.person_path, self.presence, self.comment,
                    self.resolved)


class AbsenceInfo:
    """Information about an absence."""

    now = datetime.datetime.utcnow       # Hook for unit tests

    absence_path = None         # URI of this absence
    datetime = None             # Date and time of first report
    person_title = None         # Person (title)
    person_path = None          # Person (path)
    ended = None                # Is the absence ended? (bool)
    resolved = None             # Is the absence resolved? (bool)
    expected_presence = None    # Expected presence or None
    last_comment = None         # Last comment text

    def __init__(self, absence_path, datetime, person_title, person_path,
                 ended, resolved, expected_presence, last_comment):
        self.absence_path = absence_path
        self.datetime = datetime
        self.person_title = person_title
        self.person_path = person_path
        self.ended = ended
        self.resolved = resolved
        self.expected_presence = expected_presence
        self.last_comment = last_comment

    def expected(self):
        """Is this absence expected?"""
        return (self.expected_presence is not None and
                self.expected_presence >= self.now())

    def __cmp__(self, other):
        if not isinstance(other, AbsenceInfo):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp((self.datetime, self.absence_path, self.person_title,
                    self.person_path, self.ended, self.resolved,
                    self.expected_presence, self.last_comment),
                   (other.datetime, other.absence_path, other.person_title,
                    other.person_path, other.ended, other.resolved,
                    other.expected_presence, other.last_comment))

    def __str__(self):
        if self.expected_presence:
            return ("%s expected %s, at %s %s"
                    % (self.person_title,
                       self.format_age(self.now() - self.expected_presence,
                                       '%s ago', 'in %s'),
                       self.expected_presence.strftime("%I:%M%P"),
                       self.format_date(self.expected_presence)))
        else:
            return ("%s absent for %s, since %s %s"
                    % (self.person_title,
                       self.format_age(self.now() - self.datetime),
                       self.datetime.strftime("%I:%M%P"),
                       self.format_date(self.datetime)))

    def format_age(self, age, fmt_positive='%s', fmt_negative='-%s'):
        """Format a time interval.

        >>> from datetime import timedelta
        >>> format_age(timedelta(minutes=5))
        '0h5m'
        >>> format_age(timedelta(hours=2, minutes=15))
        '2h15m'
        >>> format_age(timedelta(0))
        '0h0m'
        >>> format_age(-timedelta(minutes=5))
        '-0h5m'
        >>> format_age(-timedelta(hours=2, minutes=15))
        '-2h15m'
        >>> format_age(timedelta(hours=2, minutes=15), 'in %s', '%s ago')
        'in 2h15m'
        >>> format_age(-timedelta(hours=2, minutes=15), 'in %s', '%s ago')
        '2h15m ago'
        """
        fmt = fmt_positive
        age = age.days * 86400 + age.seconds
        if age < 0:
            age = -age
            fmt = fmt_negative
        return fmt % '%dh%dm' % divmod(age / 60, 60)

    def format_date(self, date):
        """Format the date part of a datetime.

        >>> from datetime import date
        >>> format_date(date(2001, 2, 3))
        '2001-02-03'
        >>> format_date(date.utcnow())
        'today'
        """
        if date.date() == self.now().date():
            return 'today'
        else:
            return date.strftime('%Y-%m-%d')

    def __repr__(self):
        return "%s(%r, %r, %r, %r, %r, %r, %r)" % (self.__class__.__name__,
                    self.absence_path, self.datetime, self.person_title,
                    self.person_path, self.ended, self.resolved,
                    self.expected_presence)


class AbsenceComment:
    """Information about an absence comment."""

    datetime = None             # Date and time of the comment
    reporter_title = None       # Reporter (title)
    reporter_path = None        # Reporter (path)
    absent_from_title = None    # Absent from (title)
    absent_from_path = None     # Absent from (path)
    ended = None                # Is the absence ended? (bool or Unchanged)
    resolved = None             # Is the absence resolved? (bool or Unchanged)
    expected_presence = None    # Expected presence or None (or Unchanged)
    text = None                 # Text of the comment

    def __init__(self, datetime, reporter_title, reporter_path,
                 absent_from_title, absent_from_path, ended, resolved,
                 expected_presence, text):
        self.datetime = datetime
        self.reporter_title = reporter_title
        self.reporter_path = reporter_path
        self.absent_from_title = absent_from_title
        self.absent_from_path = absent_from_path
        self.ended = ended
        self.resolved = resolved
        self.expected_presence = expected_presence
        self.text = text

    def __cmp__(self, other):
        if not isinstance(other, AbsenceComment):
            raise NotImplementedError("cannot compare %r with %r"
                                      % (self, other))
        return cmp((self.datetime, self.reporter_title, self.reporter_path,
                    self.absent_from_title, self.absent_from_path,
                    self.ended, self.resolved, self.expected_presence,
                    self.text),
                   (other.datetime, other.reporter_title, other.reporter_path,
                    other.absent_from_title, other.absent_from_path,
                    other.ended, other.resolved, other.expected_presence,
                    other.text))

    def __repr__(self):
        return "%s(%r, %r, %r, %r, %r, %r, %r, %r, %r)" % (
                    self.__class__.__name__,
                    self.datetime, self.reporter_title, self.reporter_path,
                    self.absent_from_title, self.absent_from_path,
                    self.ended, self.resolved, self.expected_presence,
                    self.text)


#
# Exceptions
#

class SchoolToolError(Exception):
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

