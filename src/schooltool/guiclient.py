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
    """Client for the SchoolTool HTTP server."""

    connectionFactory = httplib.HTTPConnection

    server = 'localhost'
    port = 8080
    status = ''

    # Generic HTTP methods

    def setServer(self, server, port):
        """Set the server name and port number.

        Tries to connect to the server and sets the status message."""
        self.server = server
        self.port = port
        self.tryToConnect()

    def tryToConnect(self):
        """Try to connect to the server and set the status message."""
        self.get('/')

    def get(self, path):
        """Perform an HTTP GET request for a given path.

        Returns the response body as a string.

        Sets status and version attributes.

        Returns None on error.  XXX: should raise an exception instead
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
            self.status = str(e)
            self.version = ''
            return None

    # SchoolTool specific methods

    def getListOfPersons(self):
        """Return a list of person IDs."""
        people = self.get('/persons')
        if people is not None:
            return self._parsePeopleList(people)
        else:
            return []

    def _parsePeopleList(self, body):
        """Parse the list of persons returned from the server."""
        try:
            doc = libxml2.parseDoc(body)
        except libxml2.parserError:
            self.status = "could not parse people list"
            return []
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
        if tree is not None:
            return self._parseGroupTree(tree)
        else:
            return []

    def _parseGroupTree(self, body):
        """Parse the tree of groups returned from the server.

        XXX the parser assumes xlink is the namespace used for xlinks in the
            document rather than parsing xmlns:... attributes
        """

        class Handler:

            def __init__(self):
                self.level = 0
                self.result = []

            def startElement(self, tag, attrs):
                if tag == 'group':
                    title = attrs['xlink:title']
                    href = attrs['xlink:href']
                    self.result.append((self.level, title, href))
                    self.level += 1

            def endElement(self, tag):
                if tag == 'group':
                    self.level -= 1

        try:
            handler = Handler()
            ctx = libxml2.createPushParser(handler, body, len(body), "")
            ctx.parseChunk("", 0, True)
            return handler.result
        except (libxml2.parserError, KeyError):
            self.status = "could not parse group tree"
            return []

    def getGroupInfo(self, group_id):
        """Return information page about a group."""
        group = self.get(group_id)
        return group

