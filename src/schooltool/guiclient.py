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
from htmllib import HTMLParser
from formatter import AbstractFormatter, NullWriter

__metaclass__ = type


class SchoolToolClient:

    connectionFactory = httplib.HTTPConnection

    server = 'localhost'
    port = 8080
    status = ''

    def setServer(self, server, port):
        self.server = server
        self.port = port
        self.tryToConnect()

    def tryToConnect(self):
        self.get('/')

    def get(self, path):
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

    def getListOfPersons(self):
        people = self.get('/people')
        if people is not None:
            return self.parsePeopleList(people)
        else:
            return []

    def parsePeopleList(self, body):
        people = []
        parser = HTMLParser(AbstractFormatter(NullWriter()))
        parser.feed(body)
        parser.close()
        for anchor in parser.anchorlist:
            if anchor.startswith('/people/'):
                person = anchor[len('/people/'):]
                if '/' not in person:
                    people.append(person)
        return people

    def getPersonInfo(self, person_id):
        person = self.get('/people/%s' % person_id)
        return person

