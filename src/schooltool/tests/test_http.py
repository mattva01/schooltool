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
Unit tests for schooltool.http

$Id$
"""

import unittest
import re
import os
import time
import logging

import ZODB.DB
import ZODB.MappingStorage
import transaction
from StringIO import StringIO
from zope.interface import moduleProvides
from zope.testing.doctestunit import DocTestSuite
from schooltool.interfaces import IModuleSetup, AuthenticationError
from twisted.internet.address import IPv4Address
from twisted.python.failure import Failure

__metaclass__ = type

moduleProvides(IModuleSetup)


def setUp():
    """Empty setUp. This is replaced by a unit test below."""


# RFC 2616, section 3.3
http_date_rx = re.compile(r'(Sun|Mon|Tue|Wed|Thu|Fri|Sat), \d{2}'
                          r' (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
                          r' \d{4} \d{2}:\d{2}:\d{2} GMT')


class ReactorStub:

    def __init__(self):
        self._called_in_thread = []
        self._called_from_thread = []
        self._tcp_listeners = []
        self._suggested_thread_pool_size = None
        self._main_loop_running = False

    def callInThread(self, callback):
        self._called_in_thread.append(callback)

    def callFromThread(self, *args):
        self._called_from_thread.append(args)

    def suggestThreadPoolSize(self, size):
        self._suggested_thread_pool_size = size

    def listenTCP(self, port, site, interface=None):
        self._tcp_listeners.append((port, site, interface))

    def run(self):
        self._main_loop_running = True


class EventLogStub:
    enabled = False


class AppStub:

    def __init__(self):
        self.utilityService = {'eventlog': EventLogStub()}


class ConnectionStub:
    app = AppStub()

    def __init__(self):
        self._root = {'app': self.app}
        self.closed = False

    def root(self):
        return self._root

    def close(self):
        self.closed = True


class DbStub:

    def __init__(self):
        self._connections = []

    def open(self):
        conn = ConnectionStub()
        self._connections.append(conn)
        return conn


class SiteStub:

    fred = object()

    def __init__(self):
        self.conflictRetries = 5
        self.rootName = 'app'
        self.db = DbStub()

    def authenticate(self, context, user, password):
        if user == 'fred' and password == 'wilma':
            return self.fred
        else:
            raise AuthenticationError('bad login (%r, %r)' % (user, password))


class ChannelStub:
    site = SiteStub()
    data = None

    def write(self, data):
        self.data = data


class TransactionStub:

    def __init__(self):
        self._note = None
        self._user = None
        self.history = ''

    def note(self, note):
        self._note = note

    def setUser(self, user):
        self._user = user

    def abort(self):
        self.history += 'A'

    def commit(self):
        self.history += 'C'

    def get(self):
        return self


class LoggerStub:

    def __init__(self):
        self.log = []

    def info(self, msg):
        self.log.append(msg)


class AppLoggerStub:

    def __init__(self):
        self.applog = []

    def log(self, level, msg):
        self.applog.append((level, msg))

    def warn(self, msg):
        self.log(logging.WARN, msg)


class TCPWrapStub:

    def __init__(self, servicename, clientname, clientip):
        self.ip = clientip

    def Deny(self):
        if self.ip == '192.16.4.2':
            return True
        return False


class TestSite(unittest.TestCase):

    def test(self):
        from schooltool.http import Site
        db = object()
        rootName = 'foo'
        viewFactory = object()
        authenticator = lambda c, u, p: None
        site = Site(db, rootName, viewFactory, authenticator, 'filename')
        self.assert_(site.db is db)
        self.assert_(site.viewFactory is viewFactory)
        self.assert_(site.rootName is rootName)
        self.assert_(site.authenticate is authenticator)
        self.assertEqual(site.applog_path, 'filename')
        self.assertEqual(site.conflictRetries, 5)

    def test_buildProtocol(self):
        from schooltool.http import Site, Request
        db = object()
        rootName = 'foo'
        viewFactory = object()
        authenticator = lambda c, u, p: None
        site = Site(db, rootName, viewFactory, authenticator, None)
        site.tcpwrapper_hook = TCPWrapStub
        addr = IPv4Address("TCP", "192.123.243.1", 123, 'INET')
        channel = site.buildProtocol(addr)
        self.assert_(channel.requestFactory is Request)
        self.assert_(channel.site is site)
        addr = IPv4Address("TCP", "192.16.4.2", 123, 'INET')
        self.assertEqual(site.buildProtocol(addr),None)

    def test_buildProtocol_custom_request(self):
        from schooltool.http import Site, Request

        class MyRequest(Request):
            pass

        db = object()
        rootName = 'foo'
        viewFactory = object()
        authenticator = lambda c, u, p: None
        site = Site(db, rootName, viewFactory, authenticator, None,
                    requestFactory=MyRequest)
        site.tcpwrapper_hook = TCPWrapStub
        addr = IPv4Address("TCP", "192.123.243.1", 123, 'INET')
        channel = site.buildProtocol(addr)
        self.assert_(channel.requestFactory is MyRequest)
        self.assert_(channel.site is site)


class TestAcceptParsing(unittest.TestCase):

    def test_parseAcept(self):
        from schooltool.http import parseAccept as p
        self.assertEqual(p(None), [])
        self.assertEqual(p(''), [])
        self.assertEqual(p(', ,\t'), [])
        self.assertEqual(p('*/*'), [(1.0, '*/*', {}, {})])
        self.assertEqual(p('text/html;q=0.5'),
                         [(0.5, 'text/html', {}, {})])
        self.assertEqual(p('text/html;level=2;q=0.123'),
                         [(0.123, 'text/html', {'level': '2'}, {})])
        self.assertEqual(p('text/*; level=2; q=0.1; foo=xyzzy'),
                         [(0.1, 'text/*', {'level': '2'}, {'foo': 'xyzzy'})])
        self.assertEqual(p('text/html;q=0.5,\t'
                           'text/html;level=2;q=0.123, '
                           'text/*; level=2; q=0.1; foo=xyzzy,\r\n\t'
                           'image/png,'),
                         [(0.5, 'text/html', {}, {}),
                          (0.123, 'text/html', {'level': '2'}, {}),
                          (0.1, 'text/*', {'level': '2'}, {'foo': 'xyzzy'}),
                          (1.0, 'image/png', {}, {})])
        self.assertEqual(p('\ttext/html ; q="0.5" , '
                           'text/html ; level=2 ; Q=0.123 , '
                           'text/* ; level=2; q=0.1 ; foo=xyzzy ,\n\t'
                           'image/png , '),
                         [(0.5, 'text/html', {}, {}),
                          (0.123, 'text/html', {'level': '2'}, {}),
                          (0.1, 'text/*', {'level': '2'}, {'foo': 'xyzzy'}),
                          (1.0, 'image/png', {}, {})])
        self.assertEqual(p('text/x-foo;bar="fee fie foe foo";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': 'fee fie foe foo'}, {})])
        self.assertEqual(p('text/x-foo; bar="fee fie foe foo" ; q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': 'fee fie foe foo'}, {})])
        self.assertEqual(p(r'text/x-foo;bar="qu\"ux";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': r'qu\"ux'}, {})])
        self.assertEqual(p(r'text/x-foo;bar="qu\\ux";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': r'qu\\ux'}, {})])
        self.assertEqual(p(r'text/x-foo;bar="qu\\";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': r'qu\\'}, {})])
        self.assertEqual(p(r'text/x-foo;bar="qu=ux";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': r'qu=ux'}, {})])
        self.assertEqual(p(r'text/x-foo;bar="qu;ux";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': r'qu;ux'}, {})])
        self.assertEqual(p(r'text/x-foo;bar="qu,ux";q=0.1'),
                         [(0.1, 'text/x-foo', {'bar': r'qu,ux'}, {})])
        # now check tolerance for invalid headers
        self.assertRaises(ValueError, p, 'error')
        self.assertRaises(ValueError, p, 'text/')
        self.assertRaises(ValueError, p, '@%@%#/@%@%')
        self.assertRaises(ValueError, p, 'foo/bar;')
        self.assertRaises(ValueError, p, 'foo/bar;q=')
        self.assertRaises(ValueError, p, 'foo/bar;q=xyzzy')
        self.assertRaises(ValueError, p, 'foo/bar;q=1.001')
        self.assertRaises(ValueError, p, 'foo/bar;Q="1.001"')
        self.assertRaises(ValueError, p, 'foo/bar;q=-2')
        self.assertRaises(ValueError, p, 'foo/bar;q=1.2.3')
        self.assertRaises(ValueError, p, 'foo/bar;;q=1')
        self.assertRaises(ValueError, p, 'foo/bar;arg')
        self.assertRaises(ValueError, p, 'foo/bar;arg=a=b')
        self.assertRaises(ValueError, p, 'foo/bar;x"y"z=w')
        self.assertRaises(ValueError, p, 'foo /bar;q=1')
        self.assertRaises(ValueError, p, 'foo/ bar;q=1')
        self.assertRaises(ValueError, p, 'foo/bar;q =1')
        self.assertRaises(ValueError, p, 'foo/bar;q= 1')

    def test_splitQuoted(self):
        from schooltool.http import splitQuoted
        self.assertEqual(splitQuoted('', ','), [''])
        self.assertEqual(splitQuoted('xyzzy', ','), ['xyzzy'])
        self.assertEqual(splitQuoted('x,y,zzy', ','), ['x', 'y', 'zzy'])
        self.assertEqual(splitQuoted(',xyzzy', ','), ['', 'xyzzy'])
        self.assertEqual(splitQuoted('xyzzy,', ','), ['xyzzy', ''])
        self.assertEqual(splitQuoted('x,y,zzy', 'y'), ['x,', ',zz', ''])
        self.assertEqual(splitQuoted(',,,', ','), ['', '', '', ''])
        self.assertEqual(splitQuoted('"xy, zzy"', ','), ['"xy, zzy"'])
        self.assertEqual(splitQuoted('"x,y",z,"z",y', ','),
                         ['"x,y"', 'z', '"z"', 'y'])
        self.assertEqual(splitQuoted(r'"x\"y,z","zy"', ','),
                         [r'"x\"y,z"', '"zy"'])

    def test_validToken(self):
        from schooltool.http import validToken
        self.assert_(validToken('foo'))
        self.assert_(validToken('abcdefghijklmnopqrstuvwxyz'))
        self.assert_(validToken('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        self.assert_(validToken('0123456789'))
        self.assert_(validToken('`~!#$%^&*-_+\'|.'))
        self.assert_(not validToken(''))
        for c in '()<>@,;:\\"/[]?={} \t':
            self.assert_(not validToken(c),
                         '%r should not be a valid token' % c)
        for c in range(33):
            self.assert_(not validToken(chr(c)),
                         'chr(%r) should not be a valid token' % c)
        self.assert_(not validToken(chr(127)),
                     'chr(127) should not be a valid token')

    def test_validMediaType(self):
        from schooltool.http import validMediaType
        self.assert_(validMediaType('foo/bar'))
        self.assert_(validMediaType('foo/*'))
        self.assert_(validMediaType('*/*'))
        self.assert_(not validMediaType(''))
        self.assert_(not validMediaType('foo'))
        self.assert_(not validMediaType('*'))
        self.assert_(not validMediaType('/'))
        self.assert_(not validMediaType('foo/'))
        self.assert_(not validMediaType('foo/bar/baz'))
        self.assert_(not validMediaType('foo / bar'))
        self.assert_(not validMediaType('*/bar'))
        self.assert_(not validMediaType('foo/"bar"'))

    def test_qualityOf(self):
        from schooltool.http import qualityOf as q
        self.assertEquals(1.0, q('text/plain', {}, []))
        self.assertEquals(0.0, q('text/plain', {}, [
                                    (0.5, 'text/html', {}, {}),
                                  ]))
        self.assertEquals(0.5, q('text/plain', {}, [
                                    (0.5, '*/*',       {}, {}),
                                    (0.7, 'text/html', {}, {}),
                                  ]))
        self.assertEquals(0.6, q('text/plain', {},[
                                    (0.5, '*/*',       {}, {}),
                                    (0.6, 'text/*',    {}, {}),
                                    (0.7, 'text/html', {}, {}),
                                  ]))
        # Examples from of RFC 2616 section 14.1
        levels = [(0.3, 'text/*',    {}, {}),
                  (0.7, 'text/html', {}, {}),
                  (1.0, 'text/html', {'level': '1'}, {}),
                  (0.4, 'text/html', {'level': '2'}, {}),
                  (0.5, '*/*',       {}, {}),]
        self.assertEquals(q('text/html', {'level': '1'}, levels), 1)
        self.assertEquals(q('text/html', {}, levels), 0.7)
        self.assertEquals(q('text/plain', {}, levels), 0.3)
        self.assertEquals(q('image/jpeg', {}, levels), 0.5)
        self.assertEquals(q('text/html', {'level': '2'}, levels), 0.4)
        self.assertEquals(q('text/html', {'level': '3'}, levels), 0.7)

    def test_chooseMediaType(self):
        from schooltool.http import chooseMediaType
        self.assertEquals(chooseMediaType([], []), None)
        self.assertEquals(chooseMediaType(['text/plain', 'image/png'], []),
                          'text/plain')
        levels = [(0.3, 'text/*',    {}, {}),
                  (0.7, 'text/html', {}, {}),
                  (1.0, 'text/html', {'level': '1'}, {}),
                  (0.4, 'text/html', {'level': '2'}, {}),
                  (0.0, 'application/x-msword', {}, {}),
                  (0.5, '*/*',       {}, {}),]
        self.assertEquals(chooseMediaType(['text/html', 'image/png'], levels),
                          'text/html')
        self.assertEquals(chooseMediaType(['text/html', 'image/png'], levels),
                          'text/html')
        self.assertEquals(chooseMediaType(['application/x-msword'], levels),
                          None)
        self.assertEquals(chooseMediaType(['text/html',
                                           ('text/html', {'level': '1'}),
                                           ('text/html', {'level': '2'})],
                                          levels),
                          ('text/html', {'level': '1'}))
        self.assertEquals(chooseMediaType(['text/plain'],
                                          [(1, 'image/*', {}, {})]), None)


class TestRequest(unittest.TestCase):

    def tearDown(self):
        hitlogger = logging.getLogger('schooltool.rest_access')
        del hitlogger.handlers[:]
        hitlogger.propagate = True
        hitlogger.setLevel(0)

    def test_reset(self):
        from schooltool.http import Request
        rq = Request(None, True)
        rq.setHeader('x-bar', 'fee fie foe foo')
        rq.addCookie('foo', 'xyzzy')
        rq.setResponseCode(505, 'this is an error')
        rq.setLastModified(123)
        rq.setETag('spam')
        rq.reset()
        self.assertEquals(rq.headers, {})
        self.assertEquals(rq.cookies, [])
        self.assertEquals(rq.code, 200)
        self.assertEquals(rq.code_message, 'OK')
        self.assertEquals(rq.lastModified, None)
        self.assertEquals(rq.etag, None)

    def test_process(self):
        from schooltool.http import Request, SERVER_VERSION
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.reactor_hook = ReactorStub()
        rq.path = '/foo/ba%72'
        rq.process()
        self.assertEqual(rq.site, ChannelStub.site)
        self.assertEqual(rq.prepath, [])
        self.assertEqual(rq.postpath, ['foo', 'bar'])
        self.assertEqual(rq.headers['server'], SERVER_VERSION)
        self.assert_(http_date_rx.match(rq.headers['date']))
        self.assertEqual(rq.headers['content-type'], 'text/plain')
        self.assertEqual(rq.reactor_hook._called_in_thread, [rq._process])
        self.assertEqual(rq.accept, [])

        rq.received_headers['accept'] = 'text/plain;q=0.5, text/html'
        rq.process()
        self.assertEqual(rq.accept, [(0.5, 'text/plain', {}, {}),
                                     (1.0, 'text/html', {}, {})])

        rq.received_headers['accept'] = 'invalid value for this header'
        rq.client = IPv4Address("TCP", "192.193.194.195", 123, 'INET')
        rq.hitlogger = LoggerStub()
        rq.process()
        self.assertEqual(rq.code, 400)
        self.assertEqual(len(rq.hitlogger.log), 1)

    def test_process_vh(self):
        from schooltool.http import Request
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.reactor_hook = ReactorStub()
        rq.path = '/++vh++https:www.example.com:443/foo/ba%72'
        rq.process()
        self.assertEqual(rq.postpath, ['foo', 'bar'])
        host = rq.getHost()
        self.assertEquals(host.host, 'www.example.com')
        self.assertEquals(host.port, 443)
        self.assert_(rq.isSecure())

        rq = Request(channel, True)
        rq.hitlogger = LoggerStub()
        rq.reactor_hook = ReactorStub()
        rq.path = '/++vh++https:www.example.com/schooltool/foo/ba%72'
        rq.client = IPv4Address("TCP", "192.193.194.195", 123, 'INET')
        rq.process()
        self.assertEqual(rq.code, 400)
        self.assertEqual(len(rq.hitlogger.log), 1)

    def test_handleVh(self):
        from schooltool.http import Request
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.setHost('localhost', 80)
        rq.reactor_hook = ReactorStub()
        rq.postpath = ['++vh++https:host:443', 'groups', 'teachers']
        rq._handleVh()
        self.assertEqual(rq.postpath, ['groups', 'teachers'])
        host = rq.getHost()
        self.assertEquals(host.host, 'host')
        self.assertEquals(host.port, 443)
        self.assert_(rq.isSecure())

        # No vh directive
        rq = Request(channel, True)
        rq.setHost('localhost', 80)
        rq.reactor_hook = ReactorStub()
        rq.postpath = ['groups', 'teachers']
        rq._handleVh()
        self.assertEqual(rq.postpath, ['groups', 'teachers'])
        host = rq.getHost()
        self.assertEquals(host.host, 'localhost')
        self.assertEquals(host.port, 80)
        self.assert_(not rq.isSecure())

    def test_handleVh_errors(self):
        from schooltool.http import Request
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.setHost('localhost', 80)
        rq.reactor_hook = ReactorStub()

        # Too few colons
        rq.postpath = ['++vh++https:host', 'groups', 'teachers']
        self.assertRaises(ValueError, rq._handleVh)

        # Too many colons
        rq.postpath = ['++vh++https:host:and:443', 'groups', 'teachers']
        self.assertRaises(ValueError, rq._handleVh)

        # Bad port
        rq.postpath = ['++vh++https:host:www', 'groups', 'teachers']
        self.assertRaises(ValueError, rq._handleVh)

    def newRequest(self, path, render_stub=None, traverse_stub=None,
                   user=None, password=None):
        from schooltool.http import Request
        channel = None
        rq = Request(channel, True)
        rq.path = path
        rq.uri = path
        rq.method = "GET"
        rq.site = SiteStub()
        if traverse_stub is None:
            rq.traverse = lambda app: path
        else:
            rq.traverse = traverse_stub
        if render_stub is not None:
            rq.render = render_stub
        if user is not None:
            rq.user = user
        if password is not None:
            rq.password = password
        return rq

    def do_test__process(self, path, render_stub=None, traverse_stub=None,
                         user=None, password=None):
        rq = self.newRequest(path, render_stub, traverse_stub, user, password)
        transaction = rq.transaction_hook = TransactionStub()
        rq.reactor_hook = ReactorStub()
        rq._process()

        self.assert_(rq.zodb_conn is None)
        self.assert_(len(rq.site.db._connections) > 0)
        for connection in rq.site.db._connections:
            self.assert_(connection.closed)

        return rq, transaction

    def test__process(self):
        path = '/foo'
        body = 'spam and eggs'
        user = 'fred'
        password = 'wilma'

        def render_stub(resource):
            assert resource is path
            return body

        rq, transaction = self.do_test__process(path, render_stub,
                                user=user, password=password)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 3)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))
        self.assertEquals(called[2], (rq.logHit, ))

        self.assertEquals(transaction.history, 'C')

        self.assertEquals(transaction._note, "GET %s" % path)
        self.assertEquals(transaction._user, user)

    def test_appLog(self):
        from schooltool.http import Request

        request = Request('bla', 'bla')
        request.authenticated_user = None

        class UserStub:
            def __init__(self, username):
                self.username = username

        request.applogger = AppLoggerStub()

        request.appLog('Hello')
        request.authenticated_user = UserStub('peter')
        request.appLog('Bye', level=logging.WARNING)
        request.appLog(u'\u263B')
        self.assertEquals(request.applogger.applog,
                          [(logging.INFO, "(UNKNOWN) Hello"),
                           (logging.WARNING, "(peter) Bye"),
                           (logging.INFO, u"(peter) \u263B")])

    def test__process_on_errors(self):
        path = '/foo'
        body = "Error"

        class ResourceStub:

            def render(self, request):
                request.setResponseCode(400)
                return body

        traverse_stub = lambda app: ResourceStub()

        rq, transaction = self.do_test__process(path,
                                traverse_stub=traverse_stub)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 3)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))
        self.assertEquals(called[2], (rq.logHit, ))

        self.assertEquals(transaction.history, 'A')

    def test__process_on_exception(self):
        path = '/foo'
        error_type = RuntimeError
        error_msg = 'Testing exception handling'

        def render_stub(resource):
            assert resource is path
            raise error_type(error_msg)

        rq, transaction = self.do_test__process(path, render_stub)

        self.assertEquals(transaction.history, 'A')

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 4)
        self.assertEquals(called[1], (rq.write, error_msg))
        self.assertEquals(called[2], (rq.finish, ))
        self.assertEquals(called[3], (rq.logHit, ))

    def test__process_many_conflict_errors(self):
        from ZODB.POSException import ConflictError

        path = '/foo'
        error_type = ConflictError
        error_msg = 'Testing exception handling'

        def render_stub(resource):
            assert resource is path
            raise error_type(error_msg)

        rq, transaction = self.do_test__process(path, render_stub)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 4)
        self.assertEquals(called[1], (rq.write, error_msg))
        self.assertEquals(called[2], (rq.finish, ))
        self.assertEquals(called[3], (rq.logHit, ))

        retries = rq.site.conflictRetries + 1
        self.assertEquals(transaction.history, 'A' * retries)

        self.assertEquals(len(rq.site.db._connections),
                          1 + rq.site.conflictRetries)

    def test__process_some_conflict_errors(self):
        from ZODB.POSException import ConflictError

        path = '/foo'
        body = 'spam and eggs'
        user = 'fred'
        password = 'wilma'
        retries = 3
        counter = [retries]

        def render_stub(resource):
            assert resource is path
            if counter[0] > 0:
                counter[0] -= 1
                raise ConflictError
            return body

        rq, transaction = self.do_test__process(path, render_stub,
                                    user=user, password=password)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 3)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))
        self.assertEquals(called[2], (rq.logHit, ))

        # these checks are a bit coarse...
        self.assertEquals(transaction.history, 'A' * retries + 'C')

        self.assertEquals(transaction._note, "GET %s" % path)
        self.assertEquals(transaction._user, user)

        self.assertEquals(len(rq.site.db._connections),
                          1 + retries)

    def test__generate_response(self):
        path = '/foo'
        body = 'Hoo!'
        def render_stub(resource):
            assert resource is path
            return body
        rq = self.newRequest(path, render_stub)
        rq.applogger = AppLoggerStub()
        rq.zodb_conn = ConnectionStub()
        result = rq._generate_response()
        self.assertEquals(result, body)
        self.assert_(rq.authenticated_user is None)

        rq.user = 'fred'
        rq.password = 'wilma'
        result = rq._generate_response()
        self.assertEquals(result, body)
        self.assert_(rq.authenticated_user is SiteStub.fred)

        rq.user = 'fred'
        rq.password = 'wilbur'
        result = rq._generate_response()
        self.assertEquals(result, "Bad username or password")
        self.assertEquals(rq.code, 401)
        self.assertEquals(rq.headers['www-authenticate'],
                          'basic realm="SchoolTool"')

        rq.user = 'freq'
        rq.password = 'wilma'
        result = rq._generate_response()
        self.assertEquals(result, "Bad username or password")
        self.assertEquals(rq.code, 401)
        self.assertEquals(rq.headers['www-authenticate'],
                          'basic realm="SchoolTool"')

        self.assertEquals(rq.applogger.applog,
                  [(logging.WARNING, "Failed login, username: 'fred'"),
                   (logging.WARNING, "Failed login, username: 'freq'")])

    def test_getApplication(self):
        rq = self.newRequest('/')
        rq.zodb_conn = ConnectionStub()
        app = rq.getApplication()
        self.assert_(app is ConnectionStub.app)

    def test_maybeAuthenticate(self):
        rq = self.newRequest('/')
        rq.applogger = AppLoggerStub()
        rq.zodb_conn = ConnectionStub()
        rq.authenticated_user = None
        rq.maybeAuthenticate()
        self.assert_(rq.authenticated_user is None)

        rq.user = 'fred'
        rq.password = 'wilma'
        rq.maybeAuthenticate()
        self.assert_(rq.authenticated_user is SiteStub.fred)

    def test_authenticate_success(self):
        rq = self.newRequest('/')
        rq.applogger = AppLoggerStub()
        rq.zodb_conn = ConnectionStub()
        rq.authenticate('fred', 'wilma')
        self.assert_(rq.authenticated_user is SiteStub.fred)
        self.assertEquals(rq.getUser(), 'fred')

    def test_authenticate_failure(self):
        rq = self.newRequest('/')
        rq.applogger = AppLoggerStub()
        rq.zodb_conn = ConnectionStub()
        self.assertRaises(AuthenticationError, rq.authenticate, 'fred', 'wima')
        self.assertRaises(AuthenticationError, rq.authenticate, 'fed', 'wilma')
        self.assert_(rq.authenticated_user is None)
        self.assertEquals(rq.getUser(), '')
        self.assertEquals(rq.applogger.applog,
                  [(logging.WARNING, "Failed login, username: 'fred'"),
                   (logging.WARNING, "Failed login, username: 'fed'")])

    # _handle_exception is tested indirectly, in test__process_on_exception
    # and test__process_many_conflict_errors

    def test_traverse(self):
        from schooltool.http import Request

        class ResourceStub:
            isLeaf = True

        class SiteStub:
            rootName = 'app'
            resource = ResourceStub()

            def viewFactory(self, context):
                assert context is ConnectionStub.app
                return self.resource

        rq = Request(None, True)
        rq.zodb_conn = ConnectionStub()
        rq.site = SiteStub()
        rq.postpath = []
        self.assertEquals(rq.traverse(ConnectionStub.app), SiteStub.resource)

    def test_render(self):
        from schooltool.http import Request
        rq = Request(None, True)

        class ResourceStub:
            _body = 'some text'
            def render(self, request):
                return self._body

        resource = ResourceStub()
        body = rq.render(resource)
        self.assertEquals(body, ResourceStub._body)
        self.assertEquals(rq.headers['content-length'],
                          len(ResourceStub._body))

    def test_render_head_empty(self):
        from schooltool.http import Request
        rq = Request(None, True)

        class ResourceStub:
            _len = 42
            def render(self, request):
                request.setHeader('Content-Length', self._len)
                return ''

        resource = ResourceStub()
        rq.method = 'HEAD'
        body = rq.render(resource)
        self.assertEquals(body, '')
        self.assertEquals(rq.headers['content-length'], ResourceStub._len)

    def test_render_head_not_empty(self):
        from schooltool.http import Request
        rq = Request(None, True)

        class ResourceStub:
            _body = 'some text'
            def render(self, request):
                return self._body

        resource = ResourceStub()
        rq.method = 'HEAD'
        body = rq.render(resource)
        self.assertEquals(body, '')
        self.assertEquals(rq.headers['content-length'],
                          len(ResourceStub._body))

    def test_render_not_a_string(self):
        from schooltool.http import Request
        rq = Request(None, True)

        class ResourceStub:
            def render(self, request):
                return 42

        resource = ResourceStub()
        self.assertRaises(AssertionError, rq.render, resource)

    def test_logHit(self):
        from schooltool.http import Request
        buffer = StringIO()
        hitlogger = logging.getLogger('schooltool.rest_access')
        hitlogger.propagate = False
        hitlogger.setLevel(logging.INFO)
        hitlogger.addHandler(logging.StreamHandler(buffer))

        rq = Request(None, True)
        rq.user = 'manager'
        rq.uri = '/foo/bar'
        rq.client = IPv4Address("TCP", "192.193.194.195", 123, 'INET')
        rq.method = 'FOO'
        rq.clientproto = 'bar/1.2'
        rq.received_headers['referer'] = 'http://example.com'
        rq.received_headers['user-agent'] = 'Godzilla/115.0'
        rq.sentLength = 42
        rq.logHit()
        self.assertEquals(buffer.getvalue(),
                '192.193.194.195 - manager [%s]'
                ' "FOO /foo/bar bar/1.2" 200 42 "http://example.com"'
                ' "Godzilla/115.0"\n' % rq.hit_time)

    def test_renderRequestError(self):
        from schooltool.http import Request
        rq = Request(None, True)
        # Request does this before calling renderRequestError:
        rq.setResponseCode(400)
        result = rq.renderRequestError(ValueError('Invalid Accept header'))
        self.assert_(isinstance(result, str))
        self.assert_(rq.code, 400)
        self.assertEqual(rq.headers['content-type'],
                         'text/plain; charset=UTF-8')

    def test_renderInternalError(self):
        from schooltool.http import Request
        rq = Request(None, True)
        # Request does this before calling renderInternalError:
        rq.setResponseCode(500)
        failure = Failure(AttributeError('foo'))
        result = rq.renderInternalError(failure)
        self.assert_(isinstance(result, str))
        self.assert_(rq.code, 500)
        self.assertEqual(rq.headers['content-type'],
                         'text/plain; charset=UTF-8')

    def test_renderAuthError(self):
        from schooltool.http import Request
        rq = Request(None, True)
        result = rq.renderAuthError()
        self.assert_(isinstance(result, str))
        self.assert_(rq.code, 401)
        self.assertEqual(rq.headers['content-type'],
                         'text/plain; charset=UTF-8')
        self.assertEqual(rq.headers['www-authenticate'],
                         'basic realm="SchoolTool"')

    def test_getContentType(self):
        from schooltool.http import Request
        rq = Request(None, True)

        def test(ctype):
            rq.getHeader = lambda h: {'content-type': ctype}[h.lower()]
            return rq.getContentType()

        self.assertEquals(test('text/html'), 'text/html')
        self.assertEquals(test('text/html; charset=UTF-8'), 'text/html')
        self.assertEquals(test(None), None)

    def test_load_snapshot(self):
        from schooltool.http import Request
        channel = ChannelStub()
        channel.site = SiteStub()
        channel.site.db = DbStub()
        called = []
        channel.site.db.restoreSnapshot = lambda snapshot: \
                                             called.append(snapshot)
        rq = Request(channel, True)
        rq.reactor_hook = ReactorStub()
        rq.received_headers['x-testing-load-snapshot'] = 'snap'
        rq.path = '/'
        rq.process()
        self.assertEquals(called, ['snap'])

    def test_load_snapshot_bad_snapshot(self):
        from schooltool.http import Request
        channel = ChannelStub()
        channel.site = SiteStub()
        channel.site.db = DbStub()
        channel.site.db.restoreSnapshot = lambda snapshot: {}[snapshot]
        rq = Request(channel, True)
        rq.reactor_hook = ReactorStub()
        rq.received_headers['x-testing-load-snapshot'] = 'nosuch'
        rq.path = '/'
        rq.client = IPv4Address("TCP", "192.193.194.195", 123, 'INET')
        rq.hitlogger = LoggerStub()
        rq.process()
        self.assertEqual(rq.code, 400)

    def test_load_snapshot_when_disabled(self):
        from schooltool.http import Request
        rq = Request(ChannelStub(), True)
        rq.reactor_hook = ReactorStub()
        rq.received_headers['x-testing-load-snapshot'] = 'snap'
        rq.path = '/'
        rq.process() # no AttributeError when db has no restoreSnapshot method
        assert not hasattr(rq.site.db, 'restoreSnapshot')

    def test_save_snapshot(self):
        from schooltool.http import Request
        rq = Request(None, True)
        rq.site = SiteStub()
        rq.site.db.makeSnapshot = lambda snapshot: None
        rq.reactor_hook = ReactorStub()
        rq.received_headers['x-testing-save-snapshot'] = 'snap'
        rq._process()
        called = rq.reactor_hook._called_from_thread
        self.assertEquals(called[-1], (rq.site.db.makeSnapshot, 'snap'))

    def test_save_snapshot_when_disabled(self):
        from schooltool.http import Request
        rq = Request(None, True)
        rq.site = SiteStub()
        rq.reactor_hook = ReactorStub()
        rq.received_headers['x-testing-save-snapshot'] = 'snap'
        rq._process() # no AttributeError when db has no makeSnapshot method
        assert not hasattr(rq.site.db, 'makeSnapshot')


class TestTimeFormatting(unittest.TestCase):

    def setUp(self):
        self.have_tzset = hasattr(time, 'tzset')
        self.touched_tz = False
        self.old_tz = os.getenv('TZ')

    def tearDown(self):
        if self.touched_tz:
            self.setTZ(self.old_tz)

    def setTZ(self, tz):
        self.touched_tz = True
        if tz is None:
            os.unsetenv('TZ')
        else:
            os.putenv('TZ', tz)
        time.tzset()

    def test_with_regex(self):
        from schooltool.http import formatHitTime

        rx = re.compile(r'^\d{2}/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov'
                        r'|Dec)/\d{4}:\d{2}:\d{2}:\d{2} [-+]\d{4}$')
        s = formatHitTime()
        m = rx.match(s)
        self.assert_(m is not None,
                     "%r does not match the regex for timestamps" % s)

    def test_default_arg(self):
        from schooltool.http import formatHitTime

        # The 'seconds' argument is the traditional time_t value that defaults
        # to time.time() if not specified explicitly.

        def date_part(s):
            return s.split(':')[0]

        self.assertEquals(date_part('01/Apr/2003:14:44:34 +0100'),
                          '01/Apr/2003')

        # There is a small race in the following test, expect if to fail
        # occasionally if you run it at midnight.

        self.assertEquals(date_part(formatHitTime()),
                          date_part(formatHitTime(time.time())))

    def test_in_unix_timezones(self):
        from schooltool.http import formatHitTime

        if not self.have_tzset:
            return # skipping this test on Windows

        self.setTZ('UTC')
        self.assertEquals(formatHitTime(0),
                          '01/Jan/1970:00:00:00 +0000')
        self.assertEquals(formatHitTime(1083251124),
                          '29/Apr/2004:15:05:24 +0000')

        # XXX This test fails on Mac OS X, which apparently does not understand
        #     time zone specifications of the following form.  Try this on a
        #     shell:
        #
        #       $ TZ=TTT-2 date -r 8506131627
        #       Tue Jan 19 05:14:07 TTT 2038
        #       $ TZ=TTT-2YYY date -r 8506131627
        #       Tue Jan 19 03:14:07 GMT 2038
        #       $ TZ= date -r 8506131627
        #       Bus error.
        #
        #     Since the manual page for tzset(3) claims that this syntax
        #     (STDoffsetDST) is supposed to work, I can only assume that there
        #     is a bug in Mac OS X.
        self.setTZ('EET-2EEST')
        self.assertEquals(formatHitTime(1083251124),
                          '29/Apr/2004:18:05:24 +0300')
        self.assertEquals(formatHitTime(1075475124),
                          '30/Jan/2004:17:05:24 +0200')

        self.setTZ('EST+5EDT')
        self.assertEquals(formatHitTime(1083251124),
                          '29/Apr/2004:11:05:24 -0400')
        self.assertEquals(formatHitTime(1075475124),
                          '30/Jan/2004:10:05:24 -0500')


class TestSnapshottableDB(unittest.TestCase):

    def tearDown(self):
        logger = logging.getLogger('schooltool.app')
        del logger.handlers[:]
        logger.propagate = True
        logger.setLevel(0)

    def test(self):
        from schooltool.http import SnapshottableDB

        # Create a logger
        buffer = StringIO()
        logger = logging.getLogger('schooltool.app')
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler(buffer))

        # Create a database
        db = ZODB.DB(ZODB.MappingStorage.MappingStorage())
        snapshottable_db = SnapshottableDB(db)

        # Sanity check: can we change the DB and see our changes?
        self.setObject(snapshottable_db, 'name', 'some_value')
        self.assertEquals(self.getObject(snapshottable_db, 'name'),
                          'some_value')

        # Make one snapshot, check that the DB is still accessible
        snapshottable_db.makeSnapshot('snapshot1')
        self.assertEquals(self.getObject(snapshottable_db, 'name'),
                          'some_value')
        self.assertEquals(buffer.getvalue(), "Saved snapshot 'snapshot1'\n")

        # Make a change and verify that it worked
        self.setObject(snapshottable_db, 'name', 'other_value')
        self.assertEquals(self.getObject(snapshottable_db, 'name'),
                          'other_value')

        # Make another snapshot
        snapshottable_db.makeSnapshot('snapshot2')
        self.assertEquals(self.getObject(snapshottable_db, 'name'),
                          'other_value')

        # Load the first snapshot and see if we can see the old value
        buffer.truncate(0)
        snapshottable_db.restoreSnapshot('snapshot1')
        self.assertEquals(self.getObject(snapshottable_db, 'name'),
                          'some_value')
        self.assertEquals(buffer.getvalue(), "Loaded snapshot 'snapshot1'\n")

        # Load the second snapshot and see if we can see the new value
        snapshottable_db.restoreSnapshot('snapshot2')
        self.assertEquals(self.getObject(snapshottable_db, 'name'),
                          'other_value')

    def setObject(self, db, name, value):
        conn = db.open()
        conn.root()[name] = value
        transaction.commit()
        conn.close()

    def getObject(self, db, name):
        conn = db.open()
        value = conn.root()[name]
        transaction.commit()
        conn.close()
        return value


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.http'))
    suite.addTest(unittest.makeSuite(TestSite))
    suite.addTest(unittest.makeSuite(TestAcceptParsing))
    suite.addTest(unittest.makeSuite(TestRequest))
    suite.addTest(unittest.makeSuite(TestTimeFormatting))
    suite.addTest(unittest.makeSuite(TestSnapshottableDB))
    return suite


if __name__ == '__main__':
    unittest.main()
