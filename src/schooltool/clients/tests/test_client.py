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
Unit tests for schooltool.clients.client
"""

import unittest
import socket
import sys
import base64
from StringIO import StringIO
from xml.sax import make_parser
from xml.sax.handler import feature_namespaces
from schooltool.tests.helpers import dedent, diff

__metaclass__ = type


class HTTPStub:

    def __init__(self, host, port=7001):
        self.host = host
        self.port = port
        self.sent_headers = {}
        self.sent_data = ''

        if host == 'badhost':
            raise socket.error(-2, 'Name or service not known')
        if port != 7001:
            raise socket.error(111, 'Connection refused')

    def putrequest(self, method, resource, *args, **kw):
        self.method = method
        self.resource = resource

    def putheader(self, key, value):
        self.sent_headers[key.lower()] = value

    def endheaders(self):
        pass

    def getresponse(self):
        return ResponseStub(self)

    def send(self, s):
        self.sent_data += s


class ResponseStub:

    def __init__(self, request):
        self.request = request
        self.status = 200
        self.reason = "OK"
        if self.request.resource == "/":
            self._data = "Welcome"
        elif self.request.resource == "/binfile":
            self._data = "(binary data)"
        elif self.request.resource == "/doc.xml":
            self._data = dedent("""
                <index xmlns:xlink="http://www.w3.org/1999/xlink">
                  <student xlink:type="simple"
                           xlink:href="student1"
                           xlink:title="John"/>
                  <student xlink:type="simple"
                           xlink:href="student2"
                           xlink:title="Kate"/>
                </index>
                """)
        elif self.request.resource == "/place_to_put_things":
            self._data = ("%s %s %s\n%s"
                          % (self.request.method,
                             self.request.sent_headers['content-type'],
                             self.request.sent_headers['content-length'],
                             self.request.sent_data))
        elif self.request.resource == "/delete_me":
            self._data = ("%s" % (self.request.method, ))
        else:
            self.status = 404
            self.reason = "Not Found"
            self._data = "404 :-)"

    def read(self):
        return self._data

    def getheader(self, name, default=None):
        if name.lower() == 'content-type':
            if self.request.resource == "/":
                return 'text/plain'
            elif self.request.resource == "/binfile":
                return 'application/octet-stream'
            elif self.request.resource == "/doc.xml":
                return 'text/xml; charset=UTF-8'
            else:
                return 'text/plain'
        return default


class TestClient(unittest.TestCase):

    def setUp(self):
        from schooltool.clients.client import Client
        class StdinStub:
            isatty = lambda self: True
        self.client = Client()
        self.client.stdin = StdinStub()
        self.emitted = ""
        def emit(*args):
            if self.emitted:
                self.emitted = "%s\n%s" % (self.emitted, ' '.join(args))
            else:
                self.emitted = ' '.join(args)
        self.client.emit = emit
        # self.client.ssl = False -- implied
        self.client.connectionFactory = HTTPStub
        self.client.secureConnectionFactory = HTTPStub

    def test_ssl(self):
        self.client.ssl = True
        self.client.connectionFactory = None
        self.client.secureConnectionFactory = HTTPStub
        self.emitted = ""
        self.client.server = 'localhost'
        self.client.links = False
        self.client.do_get("/")
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/plain
            Welcome"""))
        self.assertEqual(self.client.last_data, "Welcome")

        self.emitted = ""
        self.client.ssl = False
        self.client.connectionFactory = HTTPStub
        self.client.do_get("/")
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/plain
            Welcome"""))
        self.assertEqual(self.client.last_data, "Welcome")
        self.client.secureConnectionFactory = None

    def test_setupPrompt_noninteractive(self):
        class StdinStub:
            isatty = lambda self: False
        self.client.stdin = StdinStub()
        self.client.prompt = "# "
        self.client.extra_prompt = "> "
        self.client.intro = "Hello"
        self.client._setupPrompt()
        self.assertEquals(self.client.prompt, "")
        self.assertEquals(self.client.extra_prompt, "")
        self.assertEquals(self.client.intro, "")

    def test_setupPrompt_no_curses(self):
        class StdinStub:
            isatty = lambda self: True
        class CursesStub:
            error = Exception
            def setupterm(self):
                raise self.error, "testing"
        try:
            sys.modules['curses'] = CursesStub()
            self.client.stdin = StdinStub()
            self.client.prompt = "# "
            self.client.extra_prompt = "> "
            self.client.intro = "Hello"
            self.client._setupPrompt()
            self.assertEquals(self.client.prompt, "# ")
            self.assertEquals(self.client.extra_prompt, "> ")
            self.assertEquals(self.client.intro, "Hello")
        finally:
            try:
                del sys.modules['curses']
            except KeyError:
                pass

    def test_setupPrompt_no_color(self):
        class StdinStub:
            isatty = lambda self: True
        class CursesStub:
            error = Exception
            _terminfo = {}
            def setupterm(self):
                pass
            def tigetstr(self, s):
                return self._terminfo.get(s)
        try:
            sys.modules['curses'] = CursesStub()
            self.client.stdin = StdinStub()
            self.client.prompt = "# "
            self.client.extra_prompt = "> "
            self.client.intro = "Hello"
            self.client._setupPrompt()
            self.assertEquals(self.client.prompt, "# ")
            self.assertEquals(self.client.extra_prompt, "> ")
            self.assertEquals(self.client.intro, "Hello")
        finally:
            try:
                del sys.modules['curses']
            except KeyError:
                pass

    def test_setupPrompt_color(self):
        class StdinStub:
            isatty = lambda self: True
        class CursesStub:
            error = Exception
            _terminfo = {'bold': '<B>', 'sgr0': '<N>'}
            def setupterm(self):
                pass
            def tigetstr(self, s):
                return self._terminfo.get(s)
        try:
            sys.modules['curses'] = CursesStub()
            self.client.stdin = StdinStub()
            self.client.prompt = "# "
            self.client.extra_prompt = "> "
            self.client.intro = "Hello"
            self.client._setupPrompt()
            self.assertEquals(self.client.prompt,
                              "\001<B>\002SchoolTool>\001<N>\002 ")
            self.assertEquals(self.client.extra_prompt,
                              "\001<B>\002%(what)s>\001<N>\002 ")
            self.assertEquals(self.client.intro, "Hello")
        finally:
            try:
                del sys.modules['curses']
            except KeyError:
                pass

    def test_help(self):
        self.client.onecmd("?help")
        self.assertEmitted("This help.")

    def test_server(self):
        self.client.do_server('x y z w')
        self.assertEmitted("Extra arguments provided")

        self.emitted = ""
        self.client.do_server("server.example.com")
        self.assertEqual(self.client.server, "server.example.com")
        self.assertEmitted("Error: could not connect to server.example.com:80")

        self.emitted = ""
        self.client.do_server("srvr2.example.com  \t")
        self.assertEqual(self.client.server, "srvr2.example.com")
        self.assertEmitted("Error: could not connect to srvr2.example.com:80")

        self.emitted = ""
        self.client.do_server("")
        self.assertEqual(self.client.server, "srvr2.example.com")
        self.assertEmitted("srvr2.example.com")

        self.emitted = ""
        self.client.do_server("server 31337 plain")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 31337)
        self.assertEqual(self.client.ssl, False)
        self.assertEmitted("Error: could not connect to server:31337")

        self.emitted = ""
        self.client.do_server("server 443 ssl")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 443)
        self.assertEqual(self.client.ssl, True)
        self.assertEmitted("Error: could not connect to server:443")

        self.emitted = ""
        self.client.do_server("other www")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 443)
        self.assertEqual(self.client.ssl, True)
        self.assertEmitted("Invalid port number")

        self.emitted = ""
        self.client.do_server("server 31337")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 31337)
        # Make sure the SSL option has been reset.
        self.assertEqual(self.client.ssl, False)
        self.assertEmitted("Error: could not connect to server:31337")

        self.emitted = ""
        self.client.do_server("ignored 567 bogus")
        self.assertEmitted("'ssl' or 'plain' expected, got 'bogus'")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 31337)
        self.assertEqual(self.client.ssl, False)

    def test_accept(self):
        self.client.do_accept(" ")
        self.assertEmitted('text/xml')

        self.emitted = ""
        self.client.do_accept("text/plain  ")
        self.assertEmitted('text/plain')

        self.emitted = ""
        self.client.do_accept("text/xml, text/plain,  text/*   ")
        self.assertEmitted('text/xml, text/plain, text/*')

    def test_accept(self):
        self.assertEqual(self.client.user, None)
        self.assertEqual(self.client.password, "")
        self.client.do_user(" ")
        self.assertEqual(self.client.user, None)
        self.assertEqual(self.client.password, "")
        self.assertEmitted('User Anonymous')
        self.emitted = ""
        self.client.do_user("foo")
        self.assertEqual(self.client.user, "foo")
        self.assertEqual(self.client.password, "")
        self.assertEmitted('User foo')

        self.emitted = ""
        self.client.do_user("foo bar")
        self.assertEqual(self.client.user, "foo")
        self.assertEqual(self.client.password, "bar")
        self.assertEmitted('User foo')

    def test_get(self):
        self.client.do_get('   ')
        self.assertEmitted("Resource not provided")

        self.emitted = ""
        self.client.do_get('x y')
        self.assertEmitted("Extra arguments provided")

        self.emitted = ""
        self.client.server = 'localhost'
        self.client.links = False
        self.client.do_get("/")
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/plain
            Welcome"""))
        self.assertEqual(self.client.last_data, "Welcome")

    def test_get_binary(self):
        self.client.server = 'localhost'
        self.client.do_get("/binfile")
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: application/octet-stream
            Resource is not text, use save <filename> to save it"""))
        self.assertEqual(self.client.last_data, "(binary data)")

    def test_get_error(self):
        self.client.server = 'badhost'
        self.client.do_get("/")
        self.assertEmitted("Error: could not connect to badhost:7001")
        self.assert_(self.client.last_data is None)

    def test_save_no_get(self):
        self.client.do_save("tempfile")
        self.assertEmitted("Perform a get first")

    def test_save_no_filename(self):
        self.client.last_data = "xyzzy"
        self.client.do_save("")
        self.assertEmitted("No filename")

    def test_save(self):
        instances = []
        class FileStub(StringIO):
            def __init__(self, filename, mode):
                StringIO.__init__(self)
                self.filename = filename
                self.mode = mode
                self.closed = False
                instances.append(self)
            def close(self):
                self.closed = True
        filename = "tempfile"
        self.client.last_data = data = "xyzzy"
        self.client.file_hook = FileStub
        self.client.do_save(filename)
        self.assertEqual(len(instances), 1)
        file = instances[0]
        self.assertEqual(file.filename, filename)
        self.assertEqual(file.mode, 'wb')
        self.assertEqual(file.getvalue(), data)
        self.assert_(file.closed)
        self.assertEmitted("Saved %s: %d bytes" % (filename, len(data)))

    def test_save_failure(self):
        class FileStub:
            msg = 'simulated failure'
            def __init__(self, filename, mode):
                raise EnvironmentError(self.msg)
        filename = "tempfile"
        self.client.last_data = data = "xyzzy"
        self.client.file_hook = FileStub
        self.client.do_save(filename)
        self.assertEmitted(FileStub.msg)

    def test_put(self):
        self.do_test_put_or_post('put')

    def test_post(self):
        self.do_test_put_or_post('post')

    def do_test_put_or_post(self, what):
        doit = getattr(self.client, 'do_%s' % what)
        self.client.input_hook = lambda prompt: '.'
        doit('   ')
        self.assertEmitted("Resource not provided")

        self.emitted = ""
        doit('x y z')
        self.assertEmitted("Extra arguments provided")

        self.emitted = ""
        self.client.resources = ['x']
        doit('/place_to_put_things')
        self.assertEmitted(dedent("""
            End data with a line containing just a single period.
            200 OK
            Content-Type: text/plain
            %s text/plain 0
            """) % what.upper())
        self.assertEqual(self.client.resources, [])
        self.assertEqual(self.client.last_data,
                         '%s text/plain 0\n' % what.upper())

        self.emitted = ""
        lines = ['.', '..', '...', 'foo']
        self.client.input_hook = lambda prompt: lines.pop()
        doit('/place_to_put_things text/x-plain')
        self.assertEmitted(dedent("""
            End data with a line containing just a single period.
            200 OK
            Content-Type: text/plain
            %s text/x-plain 9
            foo
            ..
            .
            """) % what.upper())

        def raise_eof(prompt):
            raise EOFError
        self.emitted = ""
        self.client.input_hook = raise_eof
        doit('/place_to_put_things')
        self.assertEmitted(dedent("""
            End data with a line containing just a single period.
            Unexpected EOF -- %s aborted""") % what.upper())

        self.emitted = ""
        self.client.input_hook = lambda prompt: '.'
        doit('/binfile')
        self.assertEmitted(dedent("""
            End data with a line containing just a single period.
            200 OK
            Content-Type: application/octet-stream
            Resource is not text, use save <filename> to save it"""))
        self.assertEqual(self.client.last_data, "(binary data)")

    def test_delete(self):
        self.client.do_delete('   ')
        self.assertEmitted("Resource not provided")

        self.emitted = ""
        self.client.do_delete('x y')
        self.assertEmitted("Extra arguments provided")

        self.emitted = ""
        self.client.resources = ['x']
        self.client.do_delete('/delete_me')
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/plain
            DELETE"""))
        self.assertEqual(self.client.resources, [])
        self.assertEqual(self.client.last_data, 'DELETE')

    def test_links(self):
        self.assertEqual(self.client.links, True)
        data = (('on', True), ('off', False), ('ON', True), ('OFf', False))
        for set, result in data:
            self.client.do_links(set)
            self.assertEqual(self.client.links, result)
        self.assertEmitted("")

        self.client.do_links("")
        self.assertEmitted("off")
        self.client.do_links("on")
        self.emitted = ""
        self.client.do_links("")
        self.assertEmitted("on")

    def test_links_get(self):
        self.assertEqual(self.client.links, True)
        self.client.do_get("/doc.xml")
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/xml; charset=UTF-8
            <index xmlns:xlink="http://www.w3.org/1999/xlink">
              <student xlink:type="simple"
                       xlink:href="student1"
                       xlink:title="John"/>
              <student xlink:type="simple"
                       xlink:href="student2"
                       xlink:title="Kate"/>
            </index>

            ==================================================
            1   John (student1)
            2   Kate (student2)"""))
        self.assertEqual(self.client.resources,
                         ['/student1', '/student2'])

        self.emitted = ""
        self.client.do_get("/")
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/plain
            Welcome"""))

    def test_follow(self):
        self.client.links = False
        self.client.do_follow('1')
        self.assertEmitted("Wrong link number")
        self.emitted = ""
        self.client.resources = ['/doc.xml']
        self.client.do_follow('1')
        self.assertEmitted(dedent("""
            200 OK
            Content-Type: text/xml; charset=UTF-8
            <index xmlns:xlink="http://www.w3.org/1999/xlink">
              <student xlink:type="simple"
                       xlink:href="student1"
                       xlink:title="John"/>
              <student xlink:type="simple"
                       xlink:href="student2"
                       xlink:title="Kate"/>
            </index>
            """))

    def test_quit(self):
        self.assert_(self.client.do_quit(""))

    def test_default(self):
        self.assert_(self.client.default("EOF"))
        self.assertEmitted("quit")
        self.emitted = ""
        self.assert_(not self.client.default("somethingelse"))
        self.assertEmitted("I beg your pardon?")

    def test_emptyline(self):
        self.client.lastcmd = "quit"
        self.assert_(not self.client.emptyline())
        self.assertEmitted("")

    def test_authentication(self):
        self.client.user = "foo"
        self.client.password = "bar"
        hash = base64.encodestring("foo:bar").strip()
        self.client._request("GET", "/")
        self.assertEqual(self.client.lastconn.sent_headers['authorization'],
                         "Basic " + hash)

    def test_no_authentication(self):
        self.client._request("GET", "/")
        self.assert_('authorization' not in self.client.lastconn.sent_headers)

    def assertEmitted(self, what):
        self.assertEqual(self.emitted, what, "\n" + diff(what, self.emitted))


class TestXLinkHandler(unittest.TestCase):

    def setUp(self):
        from schooltool.clients.client import XLinkHandler
        self.parser = make_parser()
        self.handler = XLinkHandler()
        self.parser.setContentHandler(self.handler)
        self.parser.setFeature(feature_namespaces, 1)

    def test_simple(self):
        link = dedent("""
            <top xmlns:xlink="http://www.w3.org/1999/xlink">
              <tag xlink:type="simple"
                   xlink:title="foo"
                   xlink:href="bar"
                   name="Bond"
                   />

              <noxlinks />
              <tag xlink:type="simple"
                   xlink:title="moo"
                   xlink:href="spoo"
                   xlink:role="http://www.example.com/role"/>
            </top>
            """)
        self.parser.parse(StringIO(link))
        self.assertEqual(self.handler.links,
                         [{'type':'simple', 'title': 'foo', 'href': 'bar'},
                          {'type':'simple', 'title': 'moo', 'href': 'spoo',
                           'role': "http://www.example.com/role"}])


class TestUtilities(unittest.TestCase):

    def test_http_join(self):
        from schooltool.clients.client import http_join
        self.assertEqual(http_join('/', 'foo'), '/foo')
        self.assertEqual(http_join('/foo', 'bar'), '/bar')
        self.assertEqual(http_join('/foo/bar', '../baz'), '/baz')
        self.assertEqual(http_join('/foo/bar', '/baz'), '/baz')
        self.assertEqual(http_join('/foo/bar', './baz'), '/foo/baz')
        self.assertEqual(http_join('/foo/bar/', './baz'), '/foo/bar/baz')
        self.assertRaises(IndexError, http_join, '/foo/bar', '../../baz')
        self.assertRaises(ValueError, http_join, 'foo/bar', '../baz')
        self.assertRaises(ValueError, http_join, '/foo/bar', 'baz//quux')
        # That ain't right, but let's document it anyway
        self.assertRaises(ValueError, http_join,
                          'http://example.com/foo', '../baz')
        self.assertRaises(ValueError, http_join,
                          '/foo/bar', 'http://www.akl.lt/programos')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestClient))
    suite.addTest(unittest.makeSuite(TestXLinkHandler))
    suite.addTest(unittest.makeSuite(TestUtilities))
    return suite


if __name__ == '__main__':
    unittest.main()
