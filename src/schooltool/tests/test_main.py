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
Unit tests for schooltool.main

$Id$
"""

import unittest
import re
import os
import sys
import time
import logging
from StringIO import StringIO
from zope.interface import moduleProvides
from zope.interface import directlyProvides, directlyProvidedBy
from zope.testing.doctestunit import DocTestSuite
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.interfaces import IModuleSetup, AuthenticationError

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


class ConfigStub:
    event_logging = False


class TestSite(unittest.TestCase):

    def test(self):
        from schooltool.main import Site
        db = object()
        rootName = 'foo'
        viewFactory = object()
        logs = [object()]
        authenticator = lambda c, u, p: None
        site = Site(db, rootName, viewFactory, authenticator, logs)
        self.assert_(site.db is db)
        self.assert_(site.viewFactory is viewFactory)
        self.assert_(site.rootName is rootName)
        self.assert_(site.authenticate is authenticator)
        self.assertEqual(site.conflictRetries, 5)
        self.assertEqual(site.exception_logs, logs)

    def test_buildProtocol(self):
        from schooltool.main import Site, Request
        db = object()
        rootName = 'foo'
        viewFactory = object()
        authenticator = lambda c, u, p: None
        site = Site(db, rootName, viewFactory, authenticator)
        addr = None
        channel = site.buildProtocol(addr)
        self.assert_(channel.requestFactory is Request)
        self.assert_(channel.site is site)


class TestAcceptParsing(unittest.TestCase):

    def test_parseAcept(self):
        from schooltool.main import parseAccept as p
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
        from schooltool.main import splitQuoted
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
        from schooltool.main import validToken
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
        from schooltool.main import validMediaType
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
        from schooltool.main import qualityOf as q
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
        from schooltool.main import chooseMediaType
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

    def test_reset(self):
        from schooltool.main import Request
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
        from schooltool.main import Request, SERVER_VERSION
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
        rq.process()
        self.assertEqual(rq.code, 400)

    def test_process_vh(self):
        from schooltool.main import Request
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.reactor_hook = ReactorStub()
        rq.path = '/++vh++https:www.example.com:443/foo/ba%72'
        rq.process()
        self.assertEqual(rq.postpath, ['foo', 'bar'])
        self.assertEqual(rq.getHost(), ('SSL', 'www.example.com', 443))

        rq = Request(channel, True)
        rq.reactor_hook = ReactorStub()
        rq.path = '/++vh++https:www.example.com/schooltool/foo/ba%72'
        rq.process()
        self.assertEqual(rq.code, 400)

    def test_handleVh(self):
        from schooltool.main import Request
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.host = ('INET', 'localhost', 80)
        rq.reactor_hook = ReactorStub()
        rq.postpath = ['++vh++https:host:443', 'groups', 'teachers']
        rq._handleVh()
        self.assertEqual(rq.postpath, ['groups', 'teachers'])
        self.assertEqual(rq.getHost(), ('SSL', 'host', 443))

        # No vh directive
        rq = Request(channel, True)
        rq.host = ('INET', 'localhost', 80)
        rq.reactor_hook = ReactorStub()
        rq.postpath = ['groups', 'teachers']
        rq._handleVh()
        self.assertEqual(rq.postpath, ['groups', 'teachers'])
        self.assertEqual(rq.getHost(), ('INET', 'localhost', 80))

    def test_handleVh_errors(self):
        from schooltool.main import Request
        channel = ChannelStub()
        rq = Request(channel, True)
        rq.host = ('INET', 'localhost', 80)
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
        from schooltool.main import Request
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
        transaction = TransactionStub()
        rq.get_transaction_hook = lambda: transaction
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
        self.assertEquals(len(called), 2)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))

        self.assertEquals(transaction.history, 'C')

        self.assertEquals(transaction._note, "GET %s" % path)
        self.assertEquals(transaction._user, user)

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
        self.assertEquals(len(called), 2)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))

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
        self.assertEquals(len(called), 3)
        self.assertEquals(called[1], (rq.write, error_msg))
        self.assertEquals(called[2], (rq.finish, ))

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
        self.assertEquals(len(called), 3)
        self.assertEquals(called[1], (rq.write, error_msg))
        self.assertEquals(called[2], (rq.finish, ))

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
        self.assertEquals(len(called), 2)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))

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

    # _handle_exception is tested indirectly, in test__process_on_exception
    # and test__process_many_conflict_errors

    def test_traverse(self):
        from schooltool.main import Request

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
        from schooltool.main import Request
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
        from schooltool.main import Request
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
        from schooltool.main import Request
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
        from schooltool.main import Request
        rq = Request(None, True)

        class ResourceStub:
            def render(self, request):
                return 42

        resource = ResourceStub()
        self.assertRaises(AssertionError, rq.render, resource)

    def test_logHit(self):
        from schooltool.main import Request
        buffer = StringIO()
        hitlogger = logging.getLogger('access')
        hitlogger.addHandler(logging.StreamHandler(buffer))
        hitlogger.setLevel(logging.INFO)
        hitlogger.propagate = 0

        rq = Request(None, True)
        rq.user = 'manager'
        rq.uri = '/foo/bar'
        rq.client = ("INET", "192.193.194.195", 123)
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


class TestServer(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpRegistries()
        self.original_path = sys.path[:]
        if sys.platform[:3] == 'win': # ZConfig does this
            self.defaulthost = 'localhost'
        else:
            self.defaulthost = ''

    def tearDown(self):
        sys.path[:] = self.original_path
        self.tearDownRegistries()

    def getConfigFileName(self, filename='sample.conf'):
        dirname = os.path.dirname(__file__)
        return os.path.join(dirname, filename)

    def test_loadConfig(self):
        from schooltool.main import Server
        server = Server()
        server.notifyConfigFile = lambda x: None
        config_file = self.getConfigFileName()
        config = server.loadConfig(config_file)
        self.assertEquals(config.thread_pool_size, 42)
        self.assertEquals(config.listen,
                          [(self.defaulthost, 123), ('10.20.30.40', 9999)])
        self.assert_(config.database is not None)
        self.assertEquals(config.path, ['/xxxxx', '/yyyyy/zzzzz'])
        self.assertEquals(config.module, ['schooltool.tests.test_main'])

        # Check that loadConfig hasn't messed with sys.path.
        self.assertEquals(sys.path, self.original_path)

    def test_findDefaultConfigFile(self):
        from schooltool.main import Server
        server = Server()
        config_file = server.findDefaultConfigFile()
        self.assert_('schooltool.conf' in config_file)

    def test_configure(self):
        from schooltool.main import Server
        from schooltool.component import getView
        server = Server()
        server.notifyConfigFile = lambda x: None
        server.findDefaultConfigFile = lambda: self.getConfigFileName()
        server.configure([])
        self.assertEquals(server.config.thread_pool_size, 42)
        self.assertEquals(server.config.listen,
                          [(self.defaulthost, 123), ('10.20.30.40', 9999)])
        self.assert_(server.config.database is not None)
        self.assertEquals(server.config.path, ['/xxxxx', '/yyyyy/zzzzz'])
        self.assertEquals(server.config.pid_file, None)
        self.assertEquals(server.logfiles, [sys.stderr])
        # Check that module schooltool.main is added. This is the metadefault.
        self.assertEquals(server.config.module,
                          ['schooltool.main', 'schooltool.tests.test_main'])
        self.assertEquals(server.appname, 'schooltool')
        self.assertEquals(server.viewFactory, getView)
        self.assertEquals(server.appFactory, server.createApplication)
        # Check that configure does not change sys.path
        self.assertEquals(sys.path, self.original_path)

        hitlogger = logging.getLogger('access')
        self.assertEquals(hitlogger.propagate, False)
        # handlers[0] is implicitly created by the logging module
        self.assert_(isinstance(hitlogger.handlers[1], logging.StreamHandler))
        self.assertEquals(hitlogger.handlers[1].stream, sys.stdout)

    def test_configure_with_args(self):
        from schooltool.main import Server
        from schooltool.component import getView
        server = Server()
        server.notifyConfigFile = lambda x: None
        config_file = self.getConfigFileName()
        server.configure(['-c', config_file])
        self.assertEquals(server.config.thread_pool_size, 42)
        self.assertEquals(server.config.listen,
                          [(self.defaulthost, 123), ('10.20.30.40', 9999)])
        self.assert_(server.config.database is not None)
        self.assertEquals(server.appname, 'schooltool')
        self.assertEquals(server.viewFactory, getView)
        self.assertEquals(server.appFactory, server.createApplication)
        # Check that configure does not change sys.path
        self.assertEquals(sys.path, self.original_path)

        server.help = lambda: None
        self.assertRaises(SystemExit, server.configure, ['-h'])
        self.assertRaises(SystemExit, server.configure, ['--help'])

    def test_configure_bad_args(self):
        from schooltool.main import Server, ConfigurationError
        server = Server()
        self.assertRaises(ConfigurationError, server.configure, ['-x'])
        self.assertRaises(ConfigurationError, server.configure, ['xyzzy'])

    def test_configure_no_storage(self):
        from schooltool.main import Server
        server = Server()
        server.noStorage = lambda: None
        config_file = self.getConfigFileName('empty.conf')
        server.findDefaultConfigFile = lambda: config_file
        server.notifyConfigFile = lambda x: None
        self.assertRaises(SystemExit, server.configure, ['-c', config_file])

    def test_main(self):
        from schooltool.main import Server
        stdout = StringIO()
        stderr = StringIO()
        server = Server(stdout, stderr)
        server.run = lambda: None
        server.main(['--invalid-arg'])
        self.assert_(stderr.getvalue() != '')

    def testNoIModuleSetup_run(self):
        from schooltool.main import Server
        stdout = StringIO()
        stderr = StringIO()
        server = Server(stdout, stderr)
        config_file = self.getConfigFileName()
        server.configure(['-c', config_file])
        import schooltool.tests.test_main as thismodule
        thismodule_provides = directlyProvidedBy(thismodule)
        directlyProvides(thismodule, thismodule_provides - IModuleSetup)
        self.assert_(not IModuleSetup.providedBy(thismodule))
        # Cannot set up module because it does not provide IModuleSetup
        try:
            self.assertRaises(TypeError, server.run)
        finally:
            directlyProvides(thismodule, thismodule_provides)

    def test_run(self):
        # make sure we have a clean fresh transaction
        from transaction import get_transaction
        get_transaction().abort()

        from schooltool.main import Server
        from schooltool.component import getView

        class ThreadableStub:
            def init(self):
                self._initialized = True

        server = Server()
        server.threadable_hook = threadable = ThreadableStub()
        server.reactor_hook = reactor = ReactorStub()
        server.notifyConfigFile = lambda x: None
        server.notifyServerStarted = lambda x, y: None
        server.notifyShutdown = lambda: None
        config_file = self.getConfigFileName()
        server.configure(['-c', config_file])

        # cleanly replace the setUp function in this module
        was_set_up = []
        def setUpThisModule():
            was_set_up.append(True)
        global setUp
        old_setUp = setUp
        setUp = setUpThisModule
        try:
            server.run()
        finally:
            setUp = old_setUp
        self.assert_(was_set_up)

        self.assert_(threadable._initialized)
        self.assert_(reactor._main_loop_running)
        # these should match sample.conf
        self.assertEquals(sys.path,
                          ['/xxxxx', '/yyyyy/zzzzz'] + self.original_path)
        self.assert_(reactor._suggested_thread_pool_size, 42)
        self.assertEqual(len(reactor._tcp_listeners), 2)
        self.assertEquals(reactor._tcp_listeners[0][0], 123)
        self.assertEquals(reactor._tcp_listeners[0][2], self.defaulthost)
        self.assertEquals(reactor._tcp_listeners[1][0], 9999)
        self.assertEquals(reactor._tcp_listeners[1][2], '10.20.30.40')
        site = reactor._tcp_listeners[0][1]
        self.assertEquals(site.rootName, 'schooltool')
        self.assert_(site.viewFactory is getView)

        from schooltool.component import getRelationshipHandlerFor
        from schooltool.uris import ISpecificURI, URIMembership
        # make sure relationships.setUp was called
        x = getRelationshipHandlerFor(ISpecificURI)
        y = getRelationshipHandlerFor(URIMembership)
        self.assertNotEquals(x, y, "schooltool.membership.setUp not called")

    def test_prepareDatabase(self):
        from schooltool.main import Server
        server = Server()
        transaction = TransactionStub()
        server.get_transaction_hook = lambda: transaction
        server.db = DbStub()
        server.appname = 'app'
        server.config = ConfigStub()
        server.prepareDatabase()
        self.assertEquals(len(server.db._connections), 1)
        conn = server.db._connections[0]
        self.assert_(conn.closed)
        self.assert_(conn.root()['app'] is ConnectionStub.app)
        self.assertEquals(transaction.history, 'C')

    def test_prepareDatabase_creates(self):
        from schooltool.main import Server
        server = Server()
        transaction = TransactionStub()
        server.get_transaction_hook = lambda: transaction
        cookie = AppStub()
        server.appFactory = lambda: cookie
        server.db = DbStub()
        server.appname = 'foo'
        server.config = ConfigStub()
        server.prepareDatabase()
        self.assertEquals(len(server.db._connections), 1)
        conn = server.db._connections[0]
        self.assert_(conn.closed)
        self.assert_(conn.root()['app'] is ConnectionStub.app)
        self.assert_(conn.root()['foo'] is cookie)
        self.assertEquals(transaction.history, 'CC')

    def test_prepareDatabase_eventlog(self):
        from schooltool.main import Server
        server = Server()
        transaction = TransactionStub()
        server.get_transaction_hook = lambda: transaction
        server.db = DbStub()
        server.appname = 'app'
        server.config = ConfigStub()
        server.config.event_logging = True
        server.prepareDatabase()
        event_log = ConnectionStub.app.utilityService['eventlog']
        self.assertEquals(event_log.enabled, True)
        server.config.event_logging = False
        server.prepareDatabase()
        self.assertEquals(event_log.enabled, False)

    def test_createApplication(self):
        from schooltool.interfaces import IEvent, IAttendanceEvent
        from schooltool.uris import URIGroup
        from schooltool.main import Server
        from schooltool.model import Person, Group, Resource
        from schooltool.component import getRelatedObjects
        from schooltool import relationship, membership
        relationship.setUp()
        membership.setUp()

        server = Server()
        app = server.createApplication()
        root = app['groups']['root']
        managers = app['groups']['managers']
        manager = app['persons']['manager']
        self.assert_(manager.checkPassword('schooltool'))
        self.assertEquals(getRelatedObjects(manager, URIGroup), [managers])
        self.assertEquals(getRelatedObjects(managers, URIGroup), [root])

        person = app['persons'].new()
        self.assert_(isinstance(person, Person))

        group = app['groups'].new()
        self.assert_(isinstance(group, Group))

        resource = app['resources'].new()
        self.assert_(isinstance(resource, Resource))

        event_log = app.utilityService['eventlog']
        event_service = app.eventService
        self.assert_((event_log, IEvent) in event_service.listSubscriptions())

        absence_tracker = app.utilityService['absences']
        self.assert_((absence_tracker, IAttendanceEvent)
                     in event_service.listSubscriptions())

    def test_authenticate(self):
        from schooltool.main import Server
        from schooltool import relationship, membership
        relationship.setUp()
        membership.setUp()
        app = Server.createApplication()
        john = app['persons'].new("john", title="John Smith")
        john.setPassword('secret')
        auth = Server.authenticate
        self.assertRaises(AuthenticationError, auth, app, 'foo', 'bar')
        self.assertRaises(AuthenticationError, auth, app, '', '')
        self.assertRaises(AuthenticationError, auth, app, 'john', 'wrong')
        self.assertEquals(auth(app, 'john', 'secret'), john)
        self.assertEquals(auth(john, 'john', 'secret'), john)


class TestSetUpModules(unittest.TestCase):

    def testDoesNotImplementIModuleSetup(self):
        from schooltool.main import setUpModules
        import schooltool.tests.test_main as thismodule
        thismodule_provides = directlyProvidedBy(thismodule)
        directlyProvides(thismodule, thismodule_provides - IModuleSetup)
        self.assert_(not IModuleSetup.providedBy(thismodule))
        # Cannot set up module because it does not provide IModuleSetup
        try:
            self.assertRaises(TypeError, setUpModules,
                              ['schooltool.tests.test_main'])
        finally:
            directlyProvides(thismodule, thismodule_provides)

    def test(self):
        from schooltool.main import setUpModules
        import schooltool.tests.test_main as thismodule
        self.assert_(IModuleSetup.providedBy(thismodule))

        # cleanly replace the setUp function in this module
        was_set_up = []
        def setUpThisModule():
            was_set_up.append(True)
        global setUp
        old_setUp = setUp
        setUp = setUpThisModule
        try:
            setUpModules(['schooltool.tests.test_main'])
        finally:
            setUp = old_setUp
        self.assert_(was_set_up)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.main'))
    suite.addTest(unittest.makeSuite(TestSite))
    suite.addTest(unittest.makeSuite(TestAcceptParsing))
    suite.addTest(unittest.makeSuite(TestRequest))
    suite.addTest(unittest.makeSuite(TestServer))
    suite.addTest(unittest.makeSuite(TestSetUpModules))
    return suite

if __name__ == '__main__':
    unittest.main()
