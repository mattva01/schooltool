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

__metaclass__ = type


class SchoolToolClient:
    """Client for the SchoolTool HTTP server.

    Every method that communicates with the server sets the status and version
    attributes.
    """

    connectionFactory = httplib.HTTPConnection

    server = 'localhost'
    port = 8080
    status = ''
    version = ''

    role_names = {'http://schooltool.org/ns/membership/member': 'Member',
                  'http://schooltool.org/ns/membership/group': 'Group',
                  'http://schooltool.org/ns/membership': 'Membership'}

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
            self.status = str(e)
            self.version = ''

    def get(self, path):
        """Perform an HTTP GET request for a given path.

        Returns the response body as a string.

        Sets status and version attributes if the communication succeeds.
        Raises SchoolToolError if the communication fails.
        """
        conn = self.connectionFactory(self.server, self.port)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            body = response.read()
            conn.close()
            self.status = "%d %s" % (response.status, response.reason)
            self.version = response.getheader('Server')
            return body
        except socket.error, e:
            conn.close()
            errno, message = e.args
            self.status = "%s (%d)" % (message, errno)
            self.version = ""
            raise SchoolToolError(self.status)

    # SchoolTool specific methods

    def getListOfPersons(self):
        """Return a list of person IDs."""
        people = self.get('/persons')
        return self._parsePeopleList(people)

    def getPersonInfo(self, person_id):
        """Return information page about a person."""
        person = self.get(person_id)
        return person

    def getGroupTree(self):
        """Return the tree of groups.

        Return value is a sequence of tuples (level, title, path)

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
        # XXX this url is hardcoded, we could instead find out all roots
        # by getting /
        tree = self.get('/groups/root/tree')
        return self._parseGroupTree(tree)

    def getGroupInfo(self, group_id):
        """Return information page about a group."""
        group = self.get(group_id)
        persons = self._parseMemberList(group)
        return GroupInfo(persons)

    def getObjectRelationships(self, object_id):
        """Return relationships of an application object (group or person).

        Returns a list of tuples (arcrole, role, title, href_of_target).
        """
        result = self.get('%s/relationships' % object_id)
        return self._parseRelationships(result)

    # Parsing

    def _parsePeopleList(self, body):
        """Parse the list of persons returned from the server."""
        try:
            doc = libxml2.parseDoc(body)
        except libxml2.parserError:
            raise SchoolToolError("Could not parse people list")
        ctx = doc.xpathNewContext()
        try:
            xlink = "http://www.w3.org/1999/xlink"
            ctx.xpathRegisterNs("xlink", xlink)
            res = ctx.xpathEval("/container/items/item/@xlink:href")
            people = []
            for anchor in [node.content for node in res]:
                if anchor.startswith('/persons/'):
                    if '/' not in anchor[len('/persons/'):]:
                        people.append(anchor)
            return people
        finally:
            doc.freeDoc()
            ctx.xpathFreeContext()

    def _parseGroupTree(self, body):
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

    def _parseMemberList(self, body):
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
                        people.append((title, anchor))
            return people
        finally:
            doc.freeDoc()
            ctx.xpathFreeContext()

    def _parseRelationships(self, body):
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
                role = self.role_names.get(role, role)
                arcrole = self.role_names.get(arcrole, arcrole)
                relationships.append((arcrole, role, title, href))
            return relationships
        finally:
            doc.freeDoc()
            ctx.xpathFreeContext()


class GroupInfo:

    def __init__(self, members):
        self.members = members


class SchoolToolError(Exception):
    """Communication error"""

