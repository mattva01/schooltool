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
import os
import sys
import logging
from StringIO import StringIO

from zope.interface import moduleProvides
from zope.interface import directlyProvides, directlyProvidedBy
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.interfaces import IModuleSetup, AuthenticationError

__metaclass__ = type

moduleProvides(IModuleSetup)


def setUp():
    """Empty setUp. This is replaced by a unit test below."""


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

    def listenSSL(self, port, site, SSLContextFactory, interface=None):
        self._tcp_listeners.append((port, site, interface))

    def run(self):
        self._main_loop_running = True


class EventLogStub:
    enabled = False


class AppStub:

    def __init__(self, old_version=False):
        self.utilityService = {'eventlog': EventLogStub()}
        if not old_version:
            self.ticketService = None


class ConnectionStub:

    app = AppStub()
    old_app = AppStub(True)

    def __init__(self, old_version=False):
        if old_version:
            app = self.old_app
        else:
            app = self.app
        self._root = {'app': app}
        self.closed = False

    def root(self):
        return self._root

    def close(self):
        self.closed = True


class DbStub:

    def __init__(self, old_version=False):
        self._connections = []
        self.old_version = old_version

    def open(self):
        conn = ConnectionStub(self.old_version)
        self._connections.append(conn)
        return conn


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


class ConfigStub:
    event_logging = False


class OpenSSLContextFactoryStub:

    def setup(self, key, cert):
        self.key = key
        self.cert = cert


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

        for name in ['ZODB', 'ZODB.lock_file', 'txn', 'libxml2',
                     'schooltool.rest_access', 'schooltool.web_access',
                     'schooltool.app', 'schooltool.error',
                     'schooltool.server']:
            logger = logging.getLogger(name)
            del logger.handlers[:]
            logger.propagate = True
            logger.disabled = False
            logger.setLevel(0)

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
        from schooltool.app import create_application
        server = Server()

        # Set up the setCatalog hook
        hook = server.setCatalog_hook
        catalog = []
        def setCatalog(domain, languages, catalog=catalog):
            catalog.append(domain)
            catalog.append(languages)
            hook(domain, languages)
        server.setCatalog_hook = setCatalog

        server.notifyConfigFile = lambda x: None
        server.findDefaultConfigFile = lambda: self.getConfigFileName()
        server.configure([])
        self.assertEquals(server.config.thread_pool_size, 42)
        self.assertEquals(server.config.listen,
                          [(self.defaulthost, 123), ('10.20.30.40', 9999)])
        self.assert_(server.config.database is not None)
        self.assertEquals(server.config.path, ['/xxxxx', '/yyyyy/zzzzz'])
        self.assertEquals(server.config.pid_file, None)
        # Check that module schooltool.main is added. This is the metadefault.
        self.assertEquals(server.config.module,
                          ['schooltool.main', 'schooltool.tests.test_main'])
        self.assertEquals(server.appname, 'schooltool')
        self.assertEquals(server.viewFactory, getView)
        self.assertEquals(server.appFactory, create_application)
        # Check that configure does not change sys.path
        self.assertEquals(sys.path, self.original_path)

        hitlogger = logging.getLogger('schooltool.rest_access')
        self.assertEquals(hitlogger.propagate, False)
        self.assertEquals(len(hitlogger.handlers), 1)
        self.assert_(isinstance(hitlogger.handlers[0], logging.StreamHandler))
        self.assertEquals(hitlogger.handlers[0].stream, server.stdout)

        hitlogger = logging.getLogger('schooltool.web_access')
        self.assertEquals(hitlogger.propagate, False)
        self.assertEquals(len(hitlogger.handlers), 1)
        self.assert_(isinstance(hitlogger.handlers[0], logging.StreamHandler))
        self.assertEquals(hitlogger.handlers[0].stream, server.stdout)

        # Make sure the translations have been set up
        self.assertEqual(catalog, ['schoolbell', ['en_US', 'lt_LT']])

    def test_configure_with_args(self):
        from schooltool.main import Server
        from schooltool.component import getView
        from schooltool.app import create_application
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
        self.assertEquals(server.appFactory, create_application)
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

    def test_configureSSL(self):
        from schooltool.main import Server, ConfigurationError
        server = Server()
        server.OpenSSLContextFactory_hook = OpenSSLContextFactoryStub().setup 
        config_file = self.getConfigFileName('badssl.conf')
        server.findDefaultConfigFile = lambda: config_file
        server.notifyConfigFile = lambda x: None
        self.assertRaises(ConfigurationError, server.configure, ['-c', config_file])

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
        import transaction
        transaction.abort()

        from schooltool.main import Server
        from schooltool.http import Request
        from schooltool.component import getView
        from schooltool.browser import BrowserRequest
        from schooltool.browser.app import RootView

        class ThreadableStub:
            def init(self):
                self._initialized = True

        server = Server()
        server.threadable_hook = threadable = ThreadableStub()
        server.reactor_hook = reactor = ReactorStub()
        contextfactory = OpenSSLContextFactoryStub()
        server.OpenSSLContextFactory_hook = contextfactory.setup
        server.notifyConfigFile = lambda x: None
        server.notifyServerStarted = lambda x, y, ssl=False: None
        server.notifyWebServerStarted = lambda x, y, ssl=False: None
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
        self.assertEqual(len(reactor._tcp_listeners), 5)
        self.assertEquals(reactor._tcp_listeners[0][0], 123)
        self.assertEquals(contextfactory.cert, 'moon.pem')
        self.assertEquals(reactor._tcp_listeners[0][2], self.defaulthost)
        self.assertEquals(reactor._tcp_listeners[1][0], 9999)
        self.assertEquals(reactor._tcp_listeners[1][2], '10.20.30.40')
        self.assertEquals(reactor._tcp_listeners[2][0], 10000)
        self.assertEquals(reactor._tcp_listeners[2][2], '10.20.30.41')
        self.assertEquals(reactor._tcp_listeners[3][0], 48080)
        self.assertEquals(reactor._tcp_listeners[3][2], self.defaulthost)
        self.assertEquals(reactor._tcp_listeners[4][0], 48081)
        self.assertEquals(reactor._tcp_listeners[4][2], self.defaulthost)
        site = reactor._tcp_listeners[0][1]
        self.assertEquals(site.rootName, 'schooltool')
        self.assert_(site.viewFactory is getView)
        self.assert_(site.requestFactory is Request)
        site = reactor._tcp_listeners[2][1]
        self.assertEquals(site.rootName, 'schooltool')
        self.assert_(site.viewFactory is getView)
        self.assert_(site.requestFactory is Request)
        site = reactor._tcp_listeners[3][1]
        self.assertEquals(site.rootName, 'schooltool')
        self.assert_(site.viewFactory is RootView)
        self.assert_(site.requestFactory is BrowserRequest)
        site = reactor._tcp_listeners[4][1]
        self.assertEquals(site.rootName, 'schooltool')
        self.assert_(site.viewFactory is RootView)
        self.assert_(site.requestFactory is BrowserRequest)

        from schooltool.component import getRelationshipHandlerFor
        from schooltool.uris import URIMembership
        # make sure relationships.setUp was called
        x = getRelationshipHandlerFor(None)
        y = getRelationshipHandlerFor(URIMembership)
        self.assertNotEquals(x, y, "schooltool.membership.setUp not called")

    def test_prepareDatabase(self):
        from schooltool.main import Server
        server = Server()
        transaction = server.transaction_hook = TransactionStub()
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
        transaction = server.transaction_hook = TransactionStub()
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
        server.transaction_hook = TransactionStub()
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

    def test_prepareDatabase_oldversion(self):
        from schooltool.main import Server, SchoolToolError
        server = Server()
        transaction = server.transaction_hook = TransactionStub()
        server.db = DbStub(True)
        server.appname = 'app'
        server.config = ConfigStub()
        self.assertRaises(SchoolToolError, server.prepareDatabase)
        self.assertEquals(len(server.db._connections), 1)
        conn = server.db._connections[0]
        self.assert_(conn.closed)
        self.assert_(conn.root()['app'] is ConnectionStub.old_app)
        self.assertEquals(transaction.history, 'A')

    def test_authenticate(self):
        from schooltool.main import Server
        from schooltool import relationship, membership, teaching
        from schooltool.app import create_application
        relationship.setUp()
        membership.setUp()
        teaching.setUp()
        app = create_application()
        john = app['persons'].new("john", title="John Smith")
        john.setPassword('secret')
        auth = Server.authenticate
        self.assertRaises(AuthenticationError, auth, app, 'foo', 'bar')
        self.assertRaises(AuthenticationError, auth, app, '', '')
        self.assertRaises(AuthenticationError, auth, app, 'john', 'wrong')
        self.assertEquals(auth(app, 'john', 'secret'), john)
        self.assertEquals(auth(john, 'john', 'secret'), john)

    def test_getApplicationLogPath(self):
        from schooltool.main import Server
        server = Server()
        class ConfigStub: pass
        server.config = ConfigStub()
        server.config.app_log_file = ['STDOUT', 'STDERR', 'foo', 'bar']
        self.assertEquals(server.getApplicationLogPath(), 'foo')
        server.config.app_log_file = ['STDERR', 'STDOUT']
        self.assertEquals(server.getApplicationLogPath(), None)
        server.config.app_log_file = []
        self.assertEquals(server.getApplicationLogPath(), None)


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
    suite.addTest(unittest.makeSuite(TestServer))
    suite.addTest(unittest.makeSuite(TestSetUpModules))
    return suite


if __name__ == '__main__':
    unittest.main()
