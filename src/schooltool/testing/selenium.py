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
import os
import string
import sys
import threading
import unittest
from StringIO import StringIO

from zope.app.wsgi import WSGIPublisherApplication
from zope.app.server.wsgi import ServerType
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



def extractJSONWireParams(cmd):
    t = string.Template(cmd)
    return [named
            for (excaped, named, braced, invalid)
            in t.pattern.findall(cmd)]


def extractJSONWireCommands(remote_connection):
    # XXX: hacky.
    for cmd, info in sorted(remote_connection._commands.items()):
        method, path = info
        params = extractJSONWireParams(path)
        yield cmd, params


class CommandExecutor(object):
    driver = None
    _commands = None

    def __init__(self, driver):
        self.driver = driver
        self._commands = {}

    def extractDriverCommands(self):
        """Extract commands / params from driver's command executor."""
        signatures = extractJSONWireCommands(self.driver.command_executor)
        for name, params in signatures:
            self.addDriverCommand(name, params)

    def addDriverCommand(self, name, params):
        """Add a method to this instance that executes corresponding
        command in the web driver."""
        def command(**keywords):
            if ('sessionId' in params and
                'sessionId' not in keywords):
                keywords['sessionId'] = self.driver.session_id
            return self.driver.execute(name, keywords)
        command.__doc__ = \
            '''%s(%s, ...)''' % (
            name, ', '.join(['%s=?' % p for p in params]))
        self._commands[name] = command

    def __getattr__(self, name):
        if name in self._commands:
            return self._commands[name]
        return object.__getattr__(self, name)

    def printDriverCommands(self):
        """Print configured commands."""
        for name in sorted(self._commands):
            print self._commands[name].__doc__


class Browser(object):

    driver = None
    execute = None

    def __init__(self, driver):
        self.driver = driver
        self.execute = CommandExecutor(self.driver)
        self.execute.extractDriverCommands()

    def printHTML(self, web_element):
        print self.getHTML(web_element)

    def getHTML(self, web_element):
        snippets = []
        if isinstance(web_element, list):
            for el in web_element:
                snippets.append(self.getHTML(el))
        else:
            snippets.append(self.driver.execute_script(
                'return document.createElement("div")'
                '.appendChild(arguments[0].cloneNode(true))'
                '.parentNode.innerHTML',
                web_element))
        html = '\n'.join(snippets)
        # XXX: format output nicely here -- or in the output checker
        return html

    def __getattr__(self, name):
        # XXX: temp proxy of driver methods
        return getattr(self.driver, name)


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
        driver = _browser_factory()
        self.browsers[name] = Browser(driver)
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


class SkippyDocTestRunner(doctest.DocTestRunner):
    """Mr. Skippy Runner"""

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        result = None
        try:
            result = doctest.DocTestRunner.run(
                self, test, compileflags=compileflags,
                out=out, clear_globs=clear_globs)
        finally:
            for example in test.examples:
                if '__old_options' in example.__dict__:
                    example.options = example.__dict__['__old_options']
                    del example.__dict__['__old_options']
        return result

    def report_failure(self, out, test, example, got):
        result = doctest.DocTestRunner.report_failure(
            self, out, test, example, got)
        if self.optionflags & doctest.REPORT_ONLY_FIRST_FAILURE:
            # For practical reasons, skip the rest of the test.
            # Selenium failures are slow enough as they are,
            # requiring to execute *all* examples in the test
            # is not an option considering the plausable implicit
            # waits on *each* failure.
            for example in test.examples:
                if '__old_options' not in example.__dict__:
                    example.__dict__['__old_options'] = example.options
                    example.options = example.options.copy()
                    example.options[doctest.SKIP] = True
                    del example.__dict__['__old_options']
        return result


class RepeatyDebugRunner(doctest.DebugRunner):
    """Mr. Repeaty Debugger"""

    # XXX: plug point for custom debug runner behaviour


class SeleniumDocFileCase(doctest.DocFileCase):

    def __init__(self, test,
                 optionflags=0,
                 setUp=None, tearDown=None,
                 checker=None):
        super(SeleniumDocFileCase, self).__init__(
            test, optionflags=optionflags,
            setUp=setUp, tearDown=tearDown, checker=checker)

    def debug(self):
        self.setUp()
        runner = RepeatyDebugRunner(optionflags=self._dt_optionflags,
                                    checker=self._dt_checker, verbose=False)
        runner.run(self._dt_test, clear_globs=False)
        self.tearDown()

    def runTest(self):
        test = self._dt_test
        old = sys.stdout
        new = StringIO()
        optionflags = self._dt_optionflags

        if not (optionflags & doctest.REPORTING_FLAGS):
            # The option flags don't include any reporting flags,
            # so add the default reporting flags
            optionflags |= doctest._unittest_reportflags

        runner = SkippyDocTestRunner(optionflags=optionflags,
                                     checker=self._dt_checker,
                                     verbose=False)

        try:
            runner.DIVIDER = "-"*70
            failures, tries = runner.run(
                test, out=new.write, clear_globs=False)
        finally:
            sys.stdout = old

        if failures:
            raise self.failureException(self.format_failure(new.getvalue()))


def SeleniumFileTest(path, module_relative=True, package=None,
                globs=None, parser=doctest.DocTestParser(),
                encoding=None, test_case_factory=SeleniumDocFileCase,
                **options):
    globs = globs and globs.copy() or {}
    if package and not module_relative:
        raise ValueError("Package may only be specified for module-"
                         "relative paths.")

    doc, path = doctest._load_testfile(path, package, module_relative)

    if "__file__" not in globs:
        globs["__file__"] = path

    test_name = os.path.basename(path)

    if encoding is not None:
        doc = doc.decode(encoding)

    test = parser.get_doctest(doc, globs, test_name, path, 0)
    return test_case_factory(test, **options)


def SeleniumDocFileSuite(layer, *paths, **kw):
    if kw.get('optionflags') is None:
        kw['optionflags'] = (doctest.ELLIPSIS |
                             doctest.REPORT_NDIFF |
                             doctest.NORMALIZE_WHITESPACE |
                             doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = unittest.TestSuite()
    for path in paths:
        suite.addTest(SeleniumFileTest(path, **kw))
    suite.layer = layer
    return suite


def collect_ftests(package=None, level=None, layer=None, filenames=None,
                   optionflags=None, test_case_factory=SeleniumDocFileCase):
    package = doctest._normalize_module(package)
    def make_suite(filename, package=None):
        suite = SeleniumDocFileSuite(layer, filename,
                                     package=package,
                                     optionflags=optionflags,
                                     globs={'browsers': layer.browsers},
                                     test_case_factory=test_case_factory)
        return suite
    assert isinstance(layer, SeleniumLayer)
    suite = collect_txt_ftests(package=package, level=level,
                               layer=layer, filenames=filenames,
                               suite_factory=make_suite)
    if not selenium_enabled:
        # XXX: should log that tests are skipped somewhere better
        print 'Selenium not configured, skipping', suite
        return unittest.TestSuite()
    return suite

