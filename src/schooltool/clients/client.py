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

$Id$
"""

import sys
import getopt
import socket
import httplib
import base64
from cmd import Cmd
from StringIO import StringIO
from xml.sax import make_parser, SAXParseException
from xml.sax.handler import ContentHandler, feature_namespaces
from schooltool.common import to_unicode, StreamWrapper

__metaclass__ = type


class Client(Cmd):

    intro = """\
SchoolTool client $Id$
This is free software, covered by the GNU General Public License, and you are
welcome to change it and/or distribute copies of it under certain conditions.
"""

    prompt = "SchoolTool> "
    extra_prompt = "%(what)s> "

    doc_header = "Available commands:"
    ruler = ""

    server = 'localhost'
    port = 7001
    user = None
    password = ""
    ssl = False
    accept = 'text/xml'
    links = True

    # Hooks for unit tests.
    connectionFactory = httplib.HTTPConnection
    secureConnectionFactory = httplib.HTTPSConnection

    file_hook = file
    input_hook = raw_input

    def __init__(self, *args, **kw):
        Cmd.__init__(self, *args, **kw)
        self._setupPrompt()
        self.last_data = None
        self.resources = []

    def _setupPrompt(self):
        """Sets up the prompt suitable to operating environment.

        Noninteractive sessions (self.stdin is not a tty) get no prompt.
        Interactive sessions get a coloured prompt if the terminal supports
        it, or just a simple prompt otherwise.
        """
        if not self.stdin.isatty():
            self.prompt = ""
            self.extra_prompt = ""
            self.intro = ""
        else:
            try:
                import curses
                curses.error
            except (ImportError, AttributeError):
                pass
            else:
                try:
                    curses.setupterm()
                    bold = curses.tigetstr('bold')
                    normal = curses.tigetstr('sgr0')
                    if bold:
                        self.prompt = ("\001%s\002SchoolTool>\001%s\002 "
                                       % (bold, normal))
                        self.extra_prompt = ("\001%s\002%%(what)s>\001%s\002 "
                                             % (bold, normal))
                except curses.error:
                    pass
        # Do this after curses.setupterm()
        self.stdout = StreamWrapper(self.stdout)

    def emit(self, *args):
        """Output the arguments.  A hook for tests"""
        print >> self.stdout, ' '.join(args)

    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""
        if not stop:
            self.emit("")   # make sure there's an empty line between commands
        return stop

    def emptyline(self):
        """Called when an empty line is entered in response to the prompt."""
        pass

    def default(self, line):
        """This is called when a nonexistent command is invoked."""
        if line == "EOF":
            if self.stdin.isatty():
                self.emit("quit")
            return self.do_quit(line)
        else:
            self.emit("I beg your pardon?")

    def help_help(self):
        self.emit("This help.")

    def do_quit(self, line):
        """Exit the client."""
        return True

    def do_server(self, line):
        """Set the server to talk to.

        server [server [port [ssl]]]
        """
        args = line.split()
        if args:
            if len(args) > 3:
                self.emit("Extra arguments provided")
                return
            ssl = False
            if len(args) > 2:
                if args[2].upper() == 'SSL':
                    ssl = True
                elif args[2].upper() == 'PLAIN':
                    pass # ssl is already False
                else:
                    self.emit("'ssl' or 'plain' expected, got '%s'" % args[2])
                    return
            if len(args) > 1:
                try:
                    port = int(args[1])
                except ValueError:
                    self.emit("Invalid port number")
                    return
            else:
                port = 80
            self.server = args[0]
            self.port = port
            self.ssl = ssl
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

    def do_user(self, line):
        """Set the user and password to be used with the server.

        user [username] [password]

        Missing password means empty password, missing username means
        no authentication.
        """
        args = line.split(None, 1)
        if len(args) == 0:
            self.user = None
            self.password = ""
        elif len(args) == 1:
            self.user = args[0]
            self.password = ""
        elif len(args) == 2:
            self.user = args[0]
            self.password = args[1]
        user = self.user
        if user == None:
            user = 'Anonymous'
        self.emit("User %s" % user)

    def _request(self, method, resource, headers=(), body=None,
                 ignore_data=False):
        """Perform an HTTP request.

        Displays the response (if it is text/*), stores it for later
        perusal (see do_save), parses xlinks if the response is text/xml
        and link parsing is enabled.
        """
        self.last_data = None
        self.resources = []
        try:
            if self.ssl:
                factory = self.secureConnectionFactory
            else:
                factory = self.connectionFactory
            conn = factory(self.server, self.port)
            self.lastconn = conn # Test hook
            hdrdict = {}
            if self.user is not None:
                data = "%s:%s" % (self.user, self.password)
                basic = "Basic %s" % base64.encodestring(data).strip()
                hdrdict['Authorization'] = basic
            for k, v in headers:
                hdrdict[k] = v
            conn.request(method, resource, body, hdrdict)
            response = conn.getresponse()
            self.emit("%s %s" % (response.status, response.reason))
            if ignore_data:
                data = response.read()
                conn.close()
                return
            ctype = response.getheader('Content-Type',
                                       'application/octet-stream')
            self.emit("Content-Type: %s" % ctype)
            self.last_data = data = response.read()
            conn.close()
            if not ctype.startswith('text/'):
                self.emit("Resource is not text, use save <filename>"
                          " to save it")
                return
            self.emit(to_unicode(data))
            if self.links and ctype.startswith('text/xml'):
                try:
                    parser = make_parser()
                    handler = XLinkHandler()
                    parser.setContentHandler(handler)
                    parser.setFeature(feature_namespaces, 1)
                    parser.parse(StringIO(data))
                    first = True
                    for nr, link in enumerate(handler.links):
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
                            if first:
                                self.emit("=" * 50)
                                first = False
                            self.emit("%-3d %s (%s)" % (nr + 1, title, href))
                        except (IndexError, ValueError):
                            pass
                except SAXParseException, e:
                    self.emit("=" * 50)
                    self.emit("Could not extract links: %s" % e)
        except socket.error:
            self.emit('Error: could not connect to %s:%s'
                      % (self.server, self.port))

    def do_get(self, line):
        """Get and display a resource from the server.

        get <resource>
        """
        args = line.split()
        if len(args) < 1:
            self.emit("Resource not provided")
            return
        if len(args) > 1:
            self.emit("Extra arguments provided")
            return
        resource = args[0]
        self._request('GET', resource, [('Accept', self.accept)])

    def _do_put_or_post(self, what, line):
        """Common implementation of do_put and do_post."""
        assert what in ('PUT', 'POST')
        args = line.split()
        if len(args) < 1:
            self.emit("Resource not provided")
            return
        if len(args) > 2:
            self.emit("Extra arguments provided")
            return
        resource = args[0]
        content_type = 'text/plain'
        if len(args) > 1:
            content_type = args[1]
        if self.stdin.isatty():
            self.emit("End data with a line containing just a single period.")
        data = []
        prompt = self.extra_prompt % {'what': what}
        while 1:
            try:
                row = self.input_hook(prompt)
            except EOFError:
                self.emit('Unexpected EOF -- %s aborted' % what)
                return
            if row.startswith('.'):
                if row == '.':
                    break
                if row == '.' * len(row):
                    row = row[:-1]
            data.append(row)
        data.append('')
        data = '\n'.join(data)
        self._request(what, resource,
                      [('Content-Type', content_type),
                       ('Content-Length', len(data))],
                      data)

    def do_put(self, line):
        """Put a resource on the server.

        put <resource> [<content-type>]

        Content-type defaults to text/plain.  The new representation of the
        resource should be terminated with a line containing just a single
        period.  If the data contains a line consisting of just periods,
        prepend it with an additional one that will be stripped automatically.
        """
        self._do_put_or_post('PUT', line)

    def do_post(self, line):
        """Post a resource to the server.

        post <resource> [<content-type>]

        Content-type defaults to text/plain.  The representation of the new
        resource should be terminated with a line containing just a single
        period.  If the data contains a line consisting of just periods,
        prepend it with an additional one that will be stripped automatically.
        """
        self._do_put_or_post('POST', line)

    def do_delete(self, line):
        """Delete a resource from the server.

        delete <resource>
        """
        args = line.split()
        if len(args) < 1:
            self.emit("Resource not provided")
            return
        if len(args) > 1:
            self.emit("Extra arguments provided")
            return
        resource = args[0]
        self._request('DELETE', resource)

    def do_save(self, line):
        """Save the last downloaded resource to a file.

        save <filename>
        """
        if not line:
            self.emit("No filename")
            return
        filename = line
        if not self.last_data:
            self.emit("Perform a get first")
            return
        try:
            f = self.file_hook(filename, 'wb')
            f.write(self.last_data)
            f.close()
        except EnvironmentError, e:
            self.emit(str(e))
        else:
            self.emit("Saved %s: %d bytes" % (filename, len(self.last_data)))

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

    def do_save_snapshot(self, line):
        """Save a snapshot of database state.

        Only available in functional tests.

        save_snapshot snapshot1
        """
        name = line.strip()
        if not line:
            self.emit("Please specify a name.")
        self._request('GET', '/', [('X-Testing-Save-Snapshot', name)],
                      ignore_data=True)

    def do_load_snapshot(self, line):
        """Load a snapshot of database state.

        Only available in functional tests.

        load_snapshot snapshot1
        """
        name = line.strip()
        if not line:
            self.emit("Please specify a name.")
            return
        self._request('GET', '/', [('X-Testing-Load-Snapshot', name)],
                      ignore_data=True)


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
    c = Client()
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h:p:s', ['host=', 'port=',
                                                           'ssl'])
    except getopt.error, e:
        print >> sys.stderr, "%s: %s" % (sys.argv[0], e)
        sys.exit(1)

    for k, v in opts:
        if k in ('-h', '--host'):
            c.server = v
        if k in ('-p', '--port'):
            try:
                c.port = int(v)
            except ValueError, e:
                print >> sys.stderr, "%s: invalid port: %s" % (sys.argv[0], v)
                sys.exit(1)
        elif k in ('-s', '--ssl'):
            c.ssl = True

    c.cmdloop()


if __name__ == '__main__':
    main()
