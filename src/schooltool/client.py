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

class Client(Cmd):

    intro = """\
SchoolTool client 0.0alpha-pre0
This is free software, covered by the GNU General Public License, and you are
welcome to change it and/or distribute copies of it under certain conditions."""

    prompt = "\001\033[33m\002SchoolTool>\001\033[0m\002 "

    doc_header = "Available commands:"
    ruler=""

    server = 'localhost'
    accept = 'text/xml'

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

    def do_quit(self,line):
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
            self.do_get("/")
            if len(pieces) > 1:
                self.port = int(pieces[1])
        else:
            self.emit(self.server)

    def do_accept(self, line):
        """Set the accepted content type."""
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
            conn.putrequest('GET', line.split()[0])
            conn.putheader('Accept', self.accept)
            conn.endheaders()
            response = conn.getresponse()
            self.emit(response.read())
        except socket.error:
            self.emit('Error: could not connect to %s' % self.server)

def main():
    Client().cmdloop()

if __name__ == '__main__':
    main()
