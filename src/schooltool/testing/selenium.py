#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Selenium testing.
"""
import asyncore
import doctest
import threading
import unittest

from zope.app.wsgi import WSGIPublisherApplication
from zope.app.server.wsgi import ServerType
from zope.app.testing.functional import FunctionalDocFileSuite
from zope.server.taskthreads import ThreadedTaskDispatcher
from zope.server.http.commonaccesslogger import CommonAccessLogger
from zope.server.http.wsgihttpserver import WSGIHTTPServer

from schooltool.testing.functional import ZCMLLayer
from schooltool.testing.functional import collect_txt_ftests


_browser_factory = None
selenium_enabled = False

try:
    if _browser_factory is None:
        import schooltool.devtools.selenium_recipe
        _browser_factory = schooltool.devtools.selenium_recipe.spawn_browser
        selenium_enabled = (
            schooltool.devtools.selenium_recipe.default_factory is not None)
except ImportError:
    pass


try:
    if _browser_factory is None:
        import selenium.webdriver.firefox.webdriver
        def _browser_factory(factory_name='firefox'):
            assert factory_name == 'firefox'
            return selenium.webdriver.firefox.webdriver.WebDriver()
        selenium_enabled = True
except ImportError:
    pass


class BrowserPool(object):

    layer = None
    browsers = None

    def __init__(self, layer):
        self.layer = layer
        self.browsers = {}

    def __getattr__(self, name):
        if name not in self.browsers:
            return self.start(name)
        return self.browsers[name]

    def start(self, name):
        if name in self.browsers:
            self.quit(name)
        self.browsers[name] = _browser_factory()
        return self.browsers[name]

    def quit(self, name):
        self.browsers[name].quit()
        del self.browsers[name]

    def reset(self):
        for name in list(self.browsers):
            self.quit(name)

    @property
    def localhost(self):
        assert self.layer.serving
        return 'http://%s:%s/' % self.layer.server.socket.getsockname()


class FTestWSGIHTTPServer(WSGIHTTPServer):

    def bind(self, addr):
        ip, port = addr
        super(FTestWSGIHTTPServer, self).bind(addr)
        if port == 0:
            ip, port = self.socket.getsockname()
            self.port = port


HTTPServerFactory = ServerType(FTestWSGIHTTPServer,
                               WSGIPublisherApplication,
                               CommonAccessLogger,
                               0, True)


class SeleniumLayer(ZCMLLayer):

    server_factory = HTTPServerFactory
    thread_count = 1
    ip = "127.0.0.1"
    port = 0
    serving = False

    browsers = None

    def __init__(self, *args, **kw):
        ZCMLLayer.__init__(self, *args, **kw)
        self.browsers = BrowserPool(self)

    def setUp(self):
        ZCMLLayer.setUp(self)
        dispatcher = ThreadedTaskDispatcher()
        dispatcher.setThreadCount(self.thread_count)
        self.server = self.server_factory.create(
            'WSGI-HTTP', dispatcher, self.setup.db,
            ip=self.ip, port=self.port)
        self.thread = threading.Thread(target=self.poll_server)
        self.thread.setDaemon(True)
        self.thread.start()
        print 'serving at', repr("%s:%s" % self.server.socket.getsockname())

    def tearDown(self):
        self.serving = False
        self.thread.join()
        self.browsers.reset()
        ZCMLLayer.tearDown(self)

    def poll_server(self):
        self.serving = True
        while self.serving:
            asyncore.poll(0.1)
        self.server.close()

    def testSetUp(self):
        self.browsers.reset()
        self.setup.setUp()

        application = self.server.application
        factory = type(application.requestFactory)
        application.requestFactory = factory(self.setup.db)

    def testTearDown(self):
        self.setup.tearDown()
        self.browsers.reset()


def collect_ftests(package=None, level=None, layer=None, filenames=None):
    package = doctest._normalize_module(package)
    def make_suite(filename, package=None):
        optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                       doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_ONLY_FIRST_FAILURE)

        suite = FunctionalDocFileSuite(filename, package=package,
                                       optionflags=optionflags,
                                       globs={'browsers': layer.browsers})
        return suite
    suite = collect_txt_ftests(package=package, level=level,
                               layer=layer, filenames=filenames,
                               suite_factory=make_suite)
    if not selenium_enabled:
        # XXX: should log that tests are skipped somewhere better
        print 'Selenium not configured, skipping', suite
        return unittest.TestSuite()
    return suite

