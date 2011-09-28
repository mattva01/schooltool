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
from __future__ import absolute_import
import asyncore
import doctest
import os
import string
import sys
import threading
import unittest
from StringIO import StringIO

import selenium.webdriver.common.keys
import selenium.webdriver.remote.webdriver
import selenium.webdriver.remote.webelement
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


class WebElementList(list):

    def __unicode__(self):
        return '\n'.join([unicode(el) for el in self])

    __str__ = lambda self: unicode(self).encode('utf-8')


def getWebElementHTML(driver, web_elements):
    """Get HTML of WebElement or a list of WebElement."""
    if isinstance(web_elements, list):
        snippets = []
        for el in web_elements:
            snippets.append(getWebElementHTML)
        html = u'\n'.join(snippets)
    else:
        html = driver.execute_script(
            'return document.createElement("div")'
            '.appendChild(arguments[0].cloneNode(true))'
            '.parentNode.innerHTML',
            web_elements)
    return html


class WebElement(selenium.webdriver.remote.webelement.WebElement):

    query = None
    query_all = None

    def __init__(self, *args):
        if len(args) == 1:
            web_element = args[0]
            assert isinstance(
                web_element, selenium.webdriver.remote.webelement.WebElement)
            parent, id_ = web_element.parent, web_element.id
        elif len(args) == 2:
            parent, id_ = args
        else:
            raise TypeError(
                "__init__() takes 1 (web_element) or 2 (parent, id) arguments"
                "(%d given)" % len(args))
        selenium.webdriver.remote.webelement.WebElement.__init__(
            self, parent, id_)
        self.query = WebElementQuery(self, single=True)
        self.query_all = WebElementQuery(self, single=False)

    def type(self, *value):
        return self.send_keys(*value)

    def getHTML(self):
        """Get HTML of WebElement."""
        return getWebElementHTML(self.parent, self)

    def __unicode__(self):
        return self.getHTML()

    __str__ = lambda self: unicode(self).encode('utf-8')


def proxy_find_element(name):
    def find_element(self, param):
        if self._single:
            method = getattr(self._target, "find_element_by_%s" % name)
        else:
            method = getattr(self._target, "find_elements_by_%s" % name)
        return self._wrap(method(param))
    return find_element


class WebElementQuery(object):

    _single = False
    _target = None

    def __init__(self, target, single=False):
        self._target = target
        self._single = single

    def _wrap(self, web_element):
        if isinstance(web_element, WebElement):
            return web_element # already wrapped
        elif isinstance(
            web_element, selenium.webdriver.remote.webelement.WebElement):
            return WebElement(web_element)
        elif isinstance(web_element, dict):
            return dict([(key, self._wrap(val))
                         for key, val in web_element.items()])
        elif isinstance(web_element, list):
            return WebElementList([self._wrap(el) for el in web_element])
        else:
            return web_element

    _link_text = proxy_find_element("link_text")
    _partial_link_text = proxy_find_element("partial_link_text")

    name = proxy_find_element("name")
    id = proxy_find_element("id")
    css = proxy_find_element("css_selector")
    tag = proxy_find_element("tag_name")
    xpath = proxy_find_element("xpath")

    def link(self, text=None, url=None, partial=False):
        if not ((url is not None) ^ (text is not None)):
            raise Exception("Must specify either url or link text")
        if partial:
            if url is not None:
                return self.xpath('//a[@href~="%s"]' % url)
            return self._partial_link_text(text)
        else:
            if url is not None:
                return self.xpath('//a[@href="%s"]' % url)
            return self._link_text(text)

    def button(self, text=None, name=None):
        if not ((text is not None) ^ (name is not None)):
            raise Exception("Must specify either button text or value")
        if name is not None:
            return self.xpath(
                '//input[@type="submit" and @name="%s"]' % name)
        return self.xpath(
            '//input[@type="submit" and contains(@value, "%s")]' % text)

    @property
    def active(self):
        """Return an active element."""
        target = self._target
        while not isinstance(
            target, selenium.webdriver.remote.webdriver.WebDriver):
            target = target.parent
        active = target.switch_to_active_element()
        if not self._single:
            active = [active]
        return self._wrap(active)

    def form(self, some_selectors=None):
        # XXX: return home-made wrapped form filler(s)
        raise NotImplemented()


class Browser(object):

    driver = None
    execute = None
    query = None
    query_all = None

    # helpers
    keys = None

    def __init__(self, pool, driver):
        self.pool = pool
        self.driver = driver
        self.execute = CommandExecutor(self.driver)
        self.execute.extractDriverCommands()
        self.query = WebElementQuery(self.driver, single=True)
        self.query_all = WebElementQuery(self.driver, single=False)
        self.keys = selenium.webdriver.common.keys.Keys()

    def open(self, url="http://localhost/"):
        """Open an URL."""
        server_url = self.pool.localhost[:-1]
        url = url.replace('http://localhost', server_url)
        return self.driver.get(url)

    def close(self):
        """Close the browser."""
        return self.driver.quit()

    def type(self, *keys):
        el = self.driver.switch_to_active_element()
        return el.send_keys(*keys)

    def execute_script(self, script, *args, **kw):
        async = kw.get('async', False)
        # XXX: missing:
        raise NotImplemented()

    # XXX: missing:
    #  - screenshots
    #  -
    #  - window handles, and more

    @property
    def url(self):
        return self.driver.current_url

    @property
    def title(self):
        return self.driver.title

    @property
    def contents(self):
        return self.driver.page_source

    def printHTML(self, web_element):
        """Print HTML of WebElement or a list of WebElement."""
        print self.getHTML(web_element)

    def getHTML(self, web_element):
        """Get HTML of WebElement or a list of WebElement."""
        return getWebElementHTML(self.driver, web_element)


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
        self.browsers[name] = Browser(self, driver)
        return self.browsers[name]

    def quit(self, name):
        self.browsers[name].close()
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
        print 'serving at http://%s:%s/' % (
            self.server.socket.getsockname())

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
    """Mr. Skippy Runner.

    When REPORT_ONLY_FIRST_FAILURE is specified, Mr. Skippy skips
    the rest of each test when an error is encountered.  Needless to say,
    tests that have cleanup at the end should *never* have
    REPORT_ONLY_FIRST_FAILURE set.
    """

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
    """Mr. Repeaty Debugger."""

    # XXX: plug point for custom debug runner behaviour


class SeleniumOutputChecker(doctest.OutputChecker):

    def __init__(self, layer, *args, **kw):
        self.layer = layer

    def _unify_got(self, got):
        if (isinstance(got, unicode) or
            isinstance(got, str)):
            localhost = self.layer.browsers.localhost
            got = got.replace(localhost, 'http://localhost/')
        return got

    def check_output(self, want, got, optionflags):
        return doctest.OutputChecker.check_output(
            self, want, self._unify_got(got), optionflags)

    def output_difference(self, example, got, optionflags):
        return doctest.OutputChecker.output_difference(
            self, example, self._unify_got(got), optionflags)


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
                checker=None,
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
    return test_case_factory(test, checker=checker, **options)


def SeleniumDocFileSuite(layer, *paths, **kw):
    if kw.get('optionflags') is None:
        kw['optionflags'] = (doctest.ELLIPSIS |
                             doctest.REPORT_NDIFF |
                             doctest.NORMALIZE_WHITESPACE |
                             doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = unittest.TestSuite()
    for path in paths:
        suite.addTest(SeleniumFileTest(
                path, checker=SeleniumOutputChecker(layer), **kw))
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

