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
Unit tests for schooltool.client
"""

import unittest
import socket
import sys
from StringIO import StringIO
from xml.sax import make_parser
from xml.sax.handler import feature_namespaces
from helpers import dedent

__metaclass__ = type

class HTTPStub:

    def __init__(self, host, port=80):
        self.host = host
        self.port = port

        if host == 'badhost':
            raise socket.error(-2, 'Name or service not known')
        if port != 80:
            raise socket.error(111, 'Connection refused')

    def putrequest(self, method, resource, *args, **kw):
        self.method = method
        self.resource = resource

    def putheader(self, key, value):
        pass

    def endheaders(self):
        pass

    def getresponse(self):
        return ResponseStub(self)

class ResponseStub:

    def __init__(self, request):
        self.request = request

    def read(self):
        if self.request.resource == "/":
            return "Welcome"
        elif self.request.resource == "/binfile":
            return "(binary data)"
        elif self.request.resource == "/doc.xml":
            return dedent("""
                <index xmlns:xlink="http://www.w3.org/1999/xlink">
                  <student xlink:type="simple"
                           xlink:href="student1"
                           xlink:title="John"/>
                  <student xlink:type="simple"
                           xlink:href="student2"
                           xlink:title="Kate"/>
                </index>
                """)
        else:
            return "404 :-)"

    def getheader(self, name, default=None):
        if name.lower() == 'content-type':
            if self.request.resource == "/":
                return 'text/plain'
            elif self.request.resource == "/binfile":
                return 'application/octet-stream'
            elif self.request.resource == "/doc.xml":
                return 'text/xml'
            else:
                return 'text/plain'
        return default


class TestClient(unittest.TestCase):

    def setUp(self):
        from schooltool.client import Client
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
        self.client.http = HTTPStub

    def test_setupPrompt_noninteractive(self):
        class StdinStub:
            isatty = lambda self: False
        self.client.stdin = StdinStub()
        self.client.prompt = "# "
        self.client.intro = "Hello"
        self.client._setupPrompt()
        self.assertEquals(self.client.prompt, "")
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
            self.client.intro = "Hello"
            self.client._setupPrompt()
            self.assertEquals(self.client.prompt, "# ")
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
            self.client.intro = "Hello"
            self.client._setupPrompt()
            self.assertEquals(self.client.prompt, "# ")
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
            self.client.intro = "Hello"
            self.client._setupPrompt()
            self.assertEquals(self.client.prompt,
                              "\001<B>\002SchoolTool>\001<N>\002 ")
            self.assertEquals(self.client.intro, "Hello")
        finally:
            try:
                del sys.modules['curses']
            except KeyError:
                pass

    def test_help(self):
        self.client.onecmd("?help")
        self.assertEqual(self.emitted, "This help.")

    def test_server(self):
        self.client.do_server("server.example.com")
        self.assertEqual(self.client.server, "server.example.com")
        self.assertEqual(self.emitted, "Welcome")

        self.emitted = ""
        self.client.do_server("server2.example.com  \t")
        self.assertEqual(self.client.server, "server2.example.com")
        self.assertEqual(self.emitted, "Welcome")

        self.emitted = ""
        self.client.do_server("")
        self.assertEqual(self.client.server, "server2.example.com")
        self.assertEqual(self.emitted, "server2.example.com")

        self.emitted = ""
        self.client.do_server("server 31337")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 31337)
        self.assertEqual(self.emitted, "Error: could not connect to server")

        self.client.do_server("server")
        self.assertEqual(self.client.server, "server")
        self.assertEqual(self.client.port, 80)

    def test_accept(self):
        self.client.do_accept(" ")
        self.assertEqual(self.emitted, 'text/xml')

        self.emitted = ""
        self.client.do_accept("text/plain  ")
        self.assertEqual(self.emitted, 'text/plain')

        self.emitted = ""
        self.client.do_accept("text/xml, text/plain,  text/*   ")
        self.assertEqual(self.emitted, 'text/xml, text/plain, text/*')

    def test_get(self):
        self.client.server = 'localhost'
        self.client.do_get("/")
        self.assertEqual(self.emitted, "Welcome")
        self.assertEqual(self.client.last_data, "Welcome")

    def test_get_binary(self):
        self.client.server = 'localhost'
        self.client.do_get("/binfile")
        self.assertEqual(self.emitted,
                         "Resource is not text: application/octet-stream\n"
                         "use save <filename> to save it")
        self.assertEqual(self.client.last_data, "(binary data)")

    def test_get_error(self):
        self.client.server = 'badhost'
        self.client.do_get("/")
        self.assertEqual(self.emitted, "Error: could not connect to badhost")
        self.assert_(self.client.last_data is None)

    def test_save_no_get(self):
        self.client.do_save("tempfile")
        self.assertEqual(self.emitted, "Perform a get first")

    def test_save_no_filename(self):
        self.client.last_data = "xyzzy"
        self.client.do_save("")
        self.assertEqual(self.emitted, "No filename")

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
        self.assertEqual(self.emitted, "Saved %s: %d bytes"
                         % (filename, len(data)))

    def test_save_failure(self):
        class FileStub:
            msg = 'simulated failure'
            def __init__(self, filename, mode):
                raise EnvironmentError(self.msg)
        filename = "tempfile"
        self.client.last_data = data = "xyzzy"
        self.client.file_hook = FileStub
        self.client.do_save(filename)
        self.assertEqual(self.emitted, FileStub.msg)

    def test_links(self):
        self.assertEqual(self.client.links, False)
        data = (('on', True), ('off', False), ('ON', True), ('OFf', False))
        for set, result in data:
            self.client.do_links(set)
            self.assertEqual(self.client.links, result)
        self.assertEqual(self.emitted, "")

        self.client.do_links("")
        self.assertEqual(self.emitted, "off")
        self.client.do_links("on")
        self.emitted = ""
        self.client.do_links("")
        self.assertEqual(self.emitted, "on")

    def test_links_get(self):
        self.assertEqual(self.client.links, False)
        self.client.do_links("on")
        self.assertEqual(self.client.links, True)
        self.client.do_get("/doc.xml")
        self.assertEqual(self.emitted, dedent("""
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

    def test_follow(self):
        self.client.do_follow('1')
        self.assertEqual(self.emitted, "Wrong link number")
        self.emitted = ""
        self.client.resources = ['/doc.xml']
        self.client.do_follow('1')
        self.assertEqual(self.emitted, dedent("""
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
        self.assertEqual(self.emitted, "quit")
        self.emitted = ""
        self.assert_(not self.client.default("somethingelse"))
        self.assertEqual(self.emitted, "I beg your pardon?")


class TestXLinkHandler(unittest.TestCase):

    def setUp(self):
        from schooltool.client import XLinkHandler
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
        from schooltool.client import http_join
        self.assertEqual(http_join('/', 'foo'), '/foo')
        self.assertEqual(http_join('/foo', 'bar'), '/bar')
        self.assertEqual(http_join('/foo/bar', '../baz'), '/baz')
        self.assertEqual(http_join('/foo/bar', '/baz'), '/baz')
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
