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
Schooltool command line client.
"""
import readline
from cmd import Cmd
import sys
import httplib
import socket
from xml.sax.handler import ContentHandler, feature_namespaces
from xml.sax import make_parser, SAXParseException
from StringIO import StringIO

class Client(Cmd):

    intro = """\
SchoolTool client 0.0alpha-pre0
This is free software, covered by the GNU General Public License, and you are
welcome to change it and/or distribute copies of it under certain conditions."""

    prompt = "\001\033[33m\002SchoolTool>\001\033[0m\002 "

    doc_header = "Available commands:"
    ruler = ""

    server = 'localhost'
    accept = 'text/xml'
    links = False

    http = httplib.HTTPConnection
    port = 80

    def emit(self, *args):
        """Output the arguments.  A hook for tests"""
        print ' '.join(args)

    def default(self, line):
        """This is called when a nonexistent command is invoked."""
        if line == "EOF":
            self.emit("quit")
            self.do_quit(line)
        else:
            self.emit("I beg your pardon?")

    def help_help(self):
        self.emit("This help.")

    def do_quit(self, line):
        """Exit the client."""
        sys.exit(0);

    def do_server(self, line):
        """Set the server to talk to.

        server [server [port]]
        """
        if line.strip():
            pieces = line.split()
            self.server = pieces[0]
            self.port = 80
            if len(pieces) > 1:
                self.port = int(pieces[1])
            self.do_get("/")
        else:
            self.emit(self.server)

    def do_accept(self, line):
        """Set the accepted content type.

        accept [type]
        """
        if line.strip():
            line = ' '.join(line.split())
            self.accept = line
        self.emit(self.accept)

    def do_get(self, line):
        """Get and display a resource from the server.

        get <resource>
        """
        try:
            conn = self.http(self.server, self.port)
            resource = line.split()[0]
            conn.putrequest('GET', resource)
            conn.putheader('Accept', self.accept)
            conn.endheaders()
            response = conn.getresponse()
            data = response.read()
            self.emit(data)
            if self.links:
                self.emit("=" * 50)
                try:
                    parser = make_parser()
                    handler = XLinkHandler()
                    parser.setContentHandler(handler)
                    parser.setFeature(feature_namespaces, 1)
                    parser.parse(StringIO(data))
                    nr = 0
                    self.resources = []
                    for link in handler.links:
                        nr += 1
                        if 'title' in link:
                            title = link['title']
                        else:
                            title = ""

                        if 'href' in link:
                            href = link['href']
                        else:
                            href = "no href"
                        try:
                            self.resources.append(http_join(resource, href))
                            self.emit("%-3d %s (%s)" % (nr, title, href))
                        except (IndexError, ValueError):
                            pass
                except SAXParseException, e:
                    self.emit("Could not extract links: %s" % e)
        except socket.error:
            self.emit('Error: could not connect to %s' % self.server)

    def do_links(self, line):
        """Toggle the display of xlinks found in the response.

        links [on|off]
        """
        if not line:
            self.emit(self.links and "on" or "off")
        if line.lower() == "on":
            self.links = True
        if line.lower() == "off":
            self.links = False

    def do_follow(self, line):
        """Follow the link from the last document.

        follow <nr>
        """
        try:
            link = self.resources[int(line.split()[0])-1]
            self.do_get(link)
        except (IndexError, ValueError):
            self.emit("Wrong link number")

class XLinkHandler(ContentHandler):

    def __init__(self):
        self.links = []

    def startElementNS(self, name, qname, attrs):
        link = {}
        for namespace, attr in attrs.getNames():
            if namespace == u"http://www.w3.org/1999/xlink":
                link[attr] = attrs.get((namespace, attr))
        if link:
            self.links.append(link)

def http_join(path, rel):
    """os.path.join for HTTP paths.

    The first argument should be an abs. path, the second argument
    is a relative path.  Directory names must end with a '/'.
    """

    if rel.startswith('/'):
        return rel

    chunks = path.split('/')
    if chunks[0]:
        raise ValueError, "The path should be absolute"
    chunks = chunks[1:-1]

    for chunk in rel.split('/'):
        if chunk == '..':
            del chunks[-1]
        elif chunk == ".":
            pass
        elif chunk == '':
            raise ValueError, "Empty path elements are not allowed"
        else:
            chunks.append(chunk)
    chunks.insert(0, '')
    return '/'.join(chunks)

def main():
    Client().cmdloop()

if __name__ == '__main__':
    main()
