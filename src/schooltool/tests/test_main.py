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

__metaclass__ = type


# RFC 2616, section 3.3
http_date_rx = re.compile(r'(Sun|Mon|Tue|Wed|Thu|Fri|Sat), \d{2}'
                          r' (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
                          r' \d{4} \d{2}:\d{2}:\d{2} GMT')


class ReactorStub:
    def __init__(self):
        self._called_in_thread = []
        self._called_from_thread = []

    def callInThread(self, callback):
        self._called_in_thread.append(callback)

    def callFromThread(self, *args):
        self._called_from_thread.append(args)

class ConnectionStub:
    def __init__(self):
        self.closed = False

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
    def __init__(self):
        self.conflictRetries = 5
        self.db = DbStub()

class ChannelStub:
    site = SiteStub()


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


class TestSite(unittest.TestCase):

    def test(self):
        from schooltool.main import Site
        db = object()
        rootName = 'foo'
        viewFactory = object()
        site = Site(db, rootName, viewFactory)
        self.assert_(site.db is db)
        self.assert_(site.viewFactory is viewFactory)
        self.assert_(site.rootName is rootName)
        self.assertEqual(site.conflictRetries, 5)

    def test_buildProtocol(self):
        from schooltool.main import Site, Request
        db = object()
        rootName = 'foo'
        viewFactory = object()
        site = Site(db, rootName, viewFactory)
        addr = None
        channel = site.buildProtocol(addr)
        self.assert_(channel.requestFactory is Request)


class TestRequest(unittest.TestCase):

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
        self.assertEqual(rq.headers['content-type'], 'text/html')
        self.assertEqual(rq.reactor_hook._called_in_thread, [rq._process])

    def do_test__process(self, path, render_stub, user=None):
        from schooltool.main import Request

        transaction = TransactionStub()

        channel = None
        rq = Request(channel, True)
        rq.path = path
        rq.site = SiteStub()
        rq.reactor_hook = ReactorStub()
        rq.get_transaction_hook = lambda: transaction
        rq.traverse = lambda: path
        rq.render = render_stub
        if user is not None:
            rq.user = user
        rq._process()

        self.assert_(rq.zodb_conn is None)
        self.assert_(len(rq.site.db._connections) > 0)
        for connection in rq.site.db._connections:
            self.assert_(connection.closed)

        return rq, transaction

    def test__process(self):
        from twisted.python import failure

        path = '/foo'
        body = 'spam and eggs'
        user = 'john'

        def render_stub(resource):
            assert resource is path
            return body

        rq, transaction = self.do_test__process(path, render_stub, user=user)

        self.assertEquals(transaction.history, 'C')

        self.assertEquals(transaction._note, path)
        self.assertEquals(transaction._user, user)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 2)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))

    def test__process_on_exception(self):
        from twisted.python import failure

        path = '/foo'
        error_type = RuntimeError
        error_msg = 'Testing exception handling'

        def render_stub(resource):
            assert resource is path
            raise error_type(error_msg)

        rq, transaction = self.do_test__process(path, render_stub)

        self.assertEquals(transaction.history, 'A')

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 1)
        self.assertEquals(len(called[0]), 2)
        self.assertEquals(called[0][0], rq.processingFailed)
        self.assert_(isinstance(called[0][1], failure.Failure))
        self.assert_(called[0][1].type is error_type)
        self.assertEquals(called[0][1].value.args, (error_msg, ))

    def test__process_many_conflict_errors(self):
        from twisted.python import failure
        from zodb.interfaces import ConflictError

        path = '/foo'
        error_type = ConflictError
        error_msg = 'Testing exception handling'

        def render_stub(resource):
            assert resource is path
            raise error_type(error_msg)

        rq, transaction = self.do_test__process(path, render_stub)

        retries = rq.site.conflictRetries + 1
        self.assertEquals(transaction.history, 'A' * retries)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 1)
        self.assertEquals(len(called[0]), 2)
        self.assertEquals(called[0][0], rq.processingFailed)
        self.assert_(isinstance(called[0][1], failure.Failure))
        self.assert_(called[0][1].type is error_type)

        self.assertEquals(len(rq.site.db._connections),
                          1 + rq.site.conflictRetries)

    def test__process_some_conflict_errors(self):
        from twisted.python import failure
        from zodb.interfaces import ConflictError

        path = '/foo'
        body = 'spam and eggs'
        user = 'john'
        retries = 3
        counter = [retries]

        def render_stub(resource):
            assert resource is path
            if counter[0] > 0:
                counter[0] -= 1
                raise ConflictError
            return body

        rq, transaction = self.do_test__process(path, render_stub, user=user)

        # these checks are a bit coarse...
        self.assertEquals(transaction.history, 'A' * retries + 'C')

        self.assertEquals(transaction._note, path)
        self.assertEquals(transaction._user, user)

        called = rq.reactor_hook._called_from_thread
        self.assertEquals(len(called), 2)
        self.assertEquals(called[0], (rq.write, body))
        self.assertEquals(called[1], (rq.finish, ))

        self.assertEquals(len(rq.site.db._connections),
                          1 + retries)

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

    def test_traverse(self):
        from schooltool.main import Request

        app = object()

        class ConnectionStub:
            _root = {'app': app}

            def root(self):
                return self._root

        class ResourceStub:
            def getChildForRequest(self, request):
                return request

        class SiteStub:
            rootName = 'app'

            def viewFactory(self, context):
                assert context is app
                return ResourceStub()

        rq = Request(None, True)
        rq.zodb_conn = ConnectionStub()
        rq.site = SiteStub()
        rq.prepath = ['some', 'thing']
        self.assertEquals(rq.traverse(), rq)
        self.assertEquals(rq.sitepath, rq.prepath)
        self.assert_(rq.sitepath is not rq.prepath)
        self.assertEquals(rq.acqpath, rq.prepath)
        self.assert_(rq.acqpath is not rq.prepath)

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


# XXX: test main (tricky)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSite))
    suite.addTest(unittest.makeSuite(TestRequest))
    return suite

if __name__ == '__main__':
    unittest.main()
