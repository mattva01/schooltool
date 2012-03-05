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
import cgi
import doctest
import linecache
import os
import re
import string
import sys
import threading
import time
import unittest
from StringIO import StringIO
from UserDict import DictMixin

import lxml.html
import lxml.doctestcompare
import lxml.etree

from zope.app.wsgi import WSGIPublisherApplication
from zope.app.server.wsgi import ServerType
from zope.server.taskthreads import ThreadedTaskDispatcher
from zope.server.http.commonaccesslogger import CommonAccessLogger
from zope.server.http.wsgihttpserver import WSGIHTTPServer


import schooltool.testing.registry
from schooltool.testing import mock
from schooltool.testing.functional import ZCMLLayer
from schooltool.testing.functional import collect_txt_ftests


BLACK_MAGIC = True # enable morally ambiguous monkeypatching

_browser_factory = None
selenium_enabled = False

IMPLICIT_WAIT = 5 # in seconds

try:
    if _browser_factory is None:
        import schooltool.devtools.selenium_recipe
        _browser_factory = schooltool.devtools.selenium_recipe.spawn_browser
        selenium_enabled = (
            schooltool.devtools.selenium_recipe.default_factory is not None)
        IMPLICIT_WAIT =  schooltool.devtools.selenium_recipe.implicit_wait
except ImportError:
    pass


try:
    # selenium on python2.5 throws a SyntaxError
    from selenium.webdriver.remote.webelement import WebElement \
            as SimpleWebElement

    if _browser_factory is None:
        import selenium.webdriver.firefox.webdriver
        def _browser_factory(factory_name='firefox'):
            assert factory_name == 'firefox'
            return selenium.webdriver.firefox.webdriver.WebDriver()
        selenium_enabled = True

except (ImportError, SyntaxError):
    SimpleWebElement = object

try:
    from selenium.common.exceptions import NoSuchElementException
    from selenium.common.exceptions import TimeoutException
except ImportError:
    pass


_Browser_UI_ext = None
_Element_UI_ext = None


class ExtensionGroup(object):
    def __init__(self):
        self._handlers = {}

    def __repr__(self):
        return '<ExtensionGroup (%d ext)>: %s' % (
            len(self._handlers), list(self._handlers))

    def __getitem__(self, name):
        if name not in self:
            raise KeyError(name)
        return self._handlers[name]

    def __iter__(self):
        return iter(self._handlers)

    def __setitem__(self, name, handler):
        if name in self._handlers:
            raise KeyError(name)
        self._handlers[name] = handler

    def __delitem__(self, name, handler):
        del self._handlers[name]

    def __contains__(self, name):
        return name in self._handlers


class BoundExtension(object):

    _extension = None
    _name = None
    _target = None

    def __init__(self, extension, name, target):
        self._extension = extension
        self._name = name
        self._target = target
        if isinstance(extension, ExtensionGroup):
            for ext_n in extension:
                # Lazy man's dynamic attr marker
                setattr(self, ext_n, None)

    def __getattribute__(self, name):
        extension = object.__getattribute__(self, '_extension')
        if (name in BoundExtension.__dict__ or
            name not in extension):
            return object.__getattribute__(self, name)
        return BoundExtension(
                extension[name],
                '%s.%s' % (object.__getattribute__(self, '_name'), name),
                object.__getattribute__(self, '_target'))

    def __call__(self, *args, **kw):
        return self._extension(self._target, *args, **kw)

    def __repr__(self):
        return '<BoundExtension %s (%r)>' % (self._name, self._target)


def registerExtension(target, name, handler):
    """Register UI extension for web elements."""
    path = filter(None, [s.strip() for s in name.split('.')])
    if not path:
        raise ValueError(name)
    while len(path) > 1:
        part = path.pop(0)
        if part not in target:
            target[part] = ExtensionGroup()
            target = target[part]
    target[path[0]] = handler


def registerBrowserUI(name, handler):
    registerExtension(_Browser_UI_ext, name, handler)


def registerElementUI(name, handler):
    registerExtension(_Element_UI_ext, name, handler)


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

    def __init__(self, driver, browser=None):
        self.driver = driver
        self.browser = browser
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


class SortedDict(DictMixin):

    def __init__(self, dict):
        self.dict = dict

    def __getitem__(self, k):
        return self.dict.__getitem__(k)

    def __setitem__(self, k, v):
        return self.dict.__setitem__(k)

    def __delitem__(self, k):
        return self.dict.__delitem__(k)

    def keys(self):
        return sorted(self.dict)


class DocTestHtmlElement(object):

    @property
    def attrib(self):
        return SortedDict(super(DocTestHtmlElement, self).attrib)

    def keys(self):
        u"""keys(self)

        Gets a list of attribute names.  The names are returned in an
        arbitrary order (just like for an ordinary Python dictionary).
        """
        return sorted(super(DocTestHtmlElement, self).keys())

    def values(self):
        u"""values(self)

        Gets element attribute values as a sequence of strings.  The
        attributes are returned in an arbitrary order.
        """
        return sorted(super(DocTestHtmlElement, self).values())

    def items(self):
        u"""items(self)
        Gets element attributes, as a sequence. The attributes are returned in
        an arbitrary order.
        """
        return sorted(super(DocTestHtmlElement, self).items())


class HtmlElement(DocTestHtmlElement, lxml.html.HtmlElement):
    pass


class DocTestHtmlElementClassLookup(lxml.html.HtmlElementClassLookup):

    def lookup(self, node_type, document, namespace, name):
        if node_type == 'element':
            return self._element_classes.get(name.lower(), HtmlElement)
        return lxml.html.HtmlElementClassLookup.lookup(
            self, node_type, document, namespace, name)


class DocTestHTMLParser(lxml.etree.HTMLParser):
    def __init__(self, **kwargs):
        super(DocTestHTMLParser, self).__init__(**kwargs)
        self.set_element_class_lookup(
            DocTestHtmlElementClassLookup(
                mixins=[('*', DocTestHtmlElement)],
                ))


class DocTestXHTMLParser(lxml.etree.XMLParser):
    def __init__(self, **kwargs):
        super(DocTestHTMLParser, self).__init__(**kwargs)
        self.set_element_class_lookup(
            DocTestHtmlElementClassLookup(
                mixins=[('*', DocTestHtmlElement)],
                ))


shared_html_parser = DocTestHTMLParser(
    recover=True, remove_blank_text=False)

shared_xhtml_parser = DocTestHTMLParser(
    recover=True, remove_blank_text=False)


class HTMLSerializer(object):

    container_node = None

    empty_tags = (
        'param', 'img', 'area', 'br', 'basefont', 'input',
        'base', 'meta', 'link', 'col')

    def __init__(self, doc=None, parser=shared_html_parser):
        self.parser = parser
        if isinstance(doc, basestring):
            self.doc = self.parse(doc)
        elif isinstance(doc, lxml.etree.ElementBase):
            self.doc = doc
        else:
            raise NotImplemented('doc must be html string or lxml element,'
                                 ' got: %r' % doc)

    def _fix_ns(self, text):
        # Do some guesswork to remove the namespace for now.
        # XXX: regex or something would be better
        if isinstance(text, basestring):
            if text[0] == '{':
                return text.split('}')[-1]
        return text

    def parse(self, html, **kw):
        self.container_node = None
        start = html[:200].lstrip().lower()
        inject_html = bool(not '<html>' in start)
        inject_body = bool(not '<body>' in start)
        template = '%s'
        if inject_body:
            template = '<body>' + template + '</body>'
        if inject_html:
            template = '<html>' + template + '</html>'
        if template != '%s':
            html = template % html
        doc = lxml.etree.fromstring(html, parser=self.parser, **kw)

        if inject_body:
            bodies = doc.xpath('//body')
            assert len(bodies) == 1, bodies
            self.container_node = bodies[0]
        elif inject_html:
            htmls = doc.xpath('//html')
            assert len(htmls) == 1, htmls
            self.container_node = htmls[0]

    def format_doc(self, indent=0):
        stream = StringIO()
        self.print_doc(stream=stream, indent=indent)
        return stream.getvalue()

    def print_doc(self, stream=sys.stdout, indent=0):
        if self.container_node is None:
            self.print_node(self.doc, stream=stream, indent=indent)
        else:
            for node in self.container_node:
                self.print_node(node, stream=stream, indent=indent)

    def print_node(self, node, stream=sys.stdout, indent=0):
        for base, method in self.formatters:
            if isinstance(node, base):
                return method(self, node, stream=stream, indent=indent)
        raise NotImplemented(repr(node))

    def print_text(self, text, stream=sys.stdout, indent=0):
        if text is None:
            return
        text = text.strip()
        if not text:
            return
        text = (indent*' ' + '\n').join(text.splitlines())
        stream.write(indent*' '+cgi.escape(text, True)+'\n')

    def print_comment(self, node, stream=sys.stdout, indent=0):
        stream.write(indent*' ' + '<!--\n')
        self.print_text(node.text, stream=stream, indent=indent+2)
        stream.write(indent*' ' + '-->\n')

    def print_tag(self, node, stream=sys.stdout, indent=0):
        has_contents = bool(len(node) or node.text)
        # Only auto-close node if it correctly has no children or text
        if (self._fix_ns(node.tag).lower() in self.empty_tags and
            not has_contents):
            self.auto_tag(node, stream=stream, indent=indent)
        else:
            self.open_tag(node, stream=stream, indent=indent)
            self.print_text(node.text, stream=stream, indent=indent+2)
            for child in node:
                self.print_node(child, stream=stream, indent=indent+2)
            self.close_tag(node, stream=stream, indent=indent)
            self.print_text(node.tail, stream=stream, indent=indent)

    def print_attribs(self, node, stream=sys.stdout):
        process = lambda t: t and cgi.escape(unicode(t), True) or ""
        stream.write(' ' .join(['%s="%s"' % (self._fix_ns(n), process(v))
                                for n, v in node.attrib.items()]))

    def auto_tag(self, node, stream=sys.stdout, indent=0):
        stream.write(indent*' ' + '<'+self._fix_ns(node.tag).lower())
        if node.attrib:
            stream.write(' ')
            self.print_attribs(node, stream=stream)
        stream.write(' />\n')

    def open_tag(self, node, stream=sys.stdout, indent=0):
        stream.write(indent*' ' + '<'+self._fix_ns(node.tag).lower())
        if node.attrib:
            stream.write(' ')
            self.print_attribs(node, stream=stream)
        stream.write('>\n')

    def close_tag(self, node, stream=sys.stdout, indent=0):
        stream.write(indent*' ' + '</' + self._fix_ns(node.tag).lower() + '>\n')

    def skip(self, *args, **kw):
        pass

    formatters = (
            (lxml.etree.CommentBase, print_comment),
            (lxml.etree.ElementBase, print_tag),
            (lxml.etree.PIBase, skip),
            )


class PrintablesList(list):

    def __unicode__(self):
        return '\n'.join([unicode(el).rstrip() for el in self])

    __str__ = lambda self: unicode(self).encode('utf-8')


class ForwardingMethodsList(PrintablesList):

    fwd_methods = ()
    fwd_attrs = ()

    def __getattr__(self, name):
        if (name in self.fwd_methods or
            name in self.fwd_attrs):
            attrs = []
            for web_el in self:
                method = getattr(web_el, name, None)
                if method is None:
                    attrs.append(None)
                    continue
                if hasattr(method, '__call__'):
                    attrs.append(method)
                else:
                    attrs.append(method)
            if name in self.fwd_attrs:
                return PrintablesList(attrs)
            def multi_element_method(*args, **kw):
                results = []
                for attr in attrs:
                    if hasattr(method, '__call__'):
                        results.append(attr(*args, **kw))
                    else:
                        results.append(attr)
                return PrintablesList(results)
            return multi_element_method
        return PrintablesList.__getattr__(self, name)


class WebElementList(ForwardingMethodsList):

    fwd_methods = (
        'get_attribute', 'is_selected', 'is_enabled',
        'value_of_css_property',
        )

    fwd_attrs = (
        'tag_name', 'text', 'size', 'location',
        )


def sanitizeHTML(html):
    if html.strip():
        serializer = HTMLSerializer(html)
        return serializer.format_doc()
    return html


def getWebElementHTML(driver, web_elements):
    """Get HTML of WebElement or a list of WebElement."""
    if isinstance(web_elements, list):
        snippets = []
        for el in web_elements:
            snippets.append(getWebElementHTML(driver, el))
        html = u'\n'.join(snippets)
    else:
        html = driver.execute_script(
            'return document.createElement("div")'
            '.appendChild(arguments[0].cloneNode(true))'
            '.parentNode.innerHTML',
            web_elements)
    if html:
        html = sanitizeHTML(html)
    return html


class WebElement(SimpleWebElement):

    browser = None
    query = None
    query_all = None

    def __init__(self, *args):
        browser = None
        if len(args) == 1:
            web_element = args[0]
            assert isinstance(web_element, SimpleWebElement)
            parent, id_ = web_element.parent, web_element.id
        elif len(args) == 2:
            parent, id_ = args
        elif len(args) == 3:
            parent, id_, browser = args
        else:
            raise TypeError(
                "__init__() takes 1 (web_element) or 2 (parent, id) arguments"
                "(%d given)" % len(args))
        SimpleWebElement.__init__(self, parent, id_)
        self.browser = browser
        self.query = WebElementQuery(self, single=True, browser=browser)
        self.query_all = WebElementQuery(self, single=False, browser=browser)

    @property
    def expired(self):
        try:
            from selenium.common.exceptions import StaleElementReferenceException
            self.tag_name
        except StaleElementReferenceException:
            return True
        return False

    @property
    def ui(self):
        return BoundExtension(_Element_UI_ext, 'element.ui', self)

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
    _browser = None

    def __init__(self, target, single=False, browser=None):
        self._target = target
        self._single = single
        self._browser = browser

    def _wrap(self, web_element):
        if isinstance(web_element, WebElement):
            return web_element # already wrapped
        elif isinstance(web_element, SimpleWebElement):
            return WebElement(web_element.parent, web_element.id, self._browser)
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
        import selenium.webdriver.remote.webdriver
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

    WAIT_FEW_SECONDS = max(5, min(IMPLICIT_WAIT, 30))
    WAIT_FEW_MINUTES = max(120, min(IMPLICIT_WAIT*12, 600))
    WAIT_LONG = max(300, min(IMPLICIT_WAIT*80, 3600))

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
        self.query = WebElementQuery(
            self.driver, single=True, browser=self)
        self.query_all = WebElementQuery(
            self.driver, single=False, browser=self)
        import selenium.webdriver.common.keys
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
        return sanitizeHTML(self.driver.page_source)

    def printHTML(self, web_element):
        """Print HTML of WebElement or a list of WebElement."""
        print self.getHTML(web_element)

    def getHTML(self, web_element):
        """Get HTML of WebElement or a list of WebElement."""
        return getWebElementHTML(self.driver, web_element)

    @property
    def ui(self):
        return BoundExtension(_Browser_UI_ext, 'browser.ui', self)

    def wait(self, checker, wait=None, no_element_result=False):
        if wait is None:
            wait = self.WAIT_FEW_SECONDS
        start = time.time()
        ts = 0.3
        while True:
            try:
                result = checker()
            except NoSuchElementException:
                result = no_element_result
            if result:
                break
            now = time.time()
            if now >= start+wait:
                raise TimeoutException()
            time.sleep(ts)
            ts = min(50, ts*1.01)

    def wait_no(self, checker, wait=None):
        return self.wait(lambda: not checker(), wait=wait, no_element_result=True)

    def wait_few_minutes(self, checker):
        return self.wait(checker, wait=self.WAIT_FEW_MINUTES)

    def wait_long(self, checker):
        return self.wait(checker, wait=self.WAIT_LONG)


class BrowserPool(object):

    layer = None
    browsers = None

    def __init__(self, layer):
        self.layer = layer
        self.browsers = {}

    def __getattr__(self, name):
        if (name.startswith('_') or
            name == 'trait_names'): # for IPdb.
            raise AttributeError(name)
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

DOCTEST_EXAMPLE_FILENAME_RE = re.compile(r'<doctest (?P<name>.+)\[(?P<examplenum>\d+)\]>$')


def make_doctest_getlines_patch(test):
    orig_getlines = linecache.getlines
    def getlines(filename, module_globals=None):
        m = DOCTEST_EXAMPLE_FILENAME_RE.match(filename)
        if m and m.group('name') == test.name:
            example = test.examples[int(m.group('examplenum'))]
            source = example.source
            if isinstance(source, unicode):
                source = source.encode('ascii', 'backslashreplace')
            return source.splitlines(True)
        else:
            return orig_getlines(filename, module_globals)
    return getlines


def make_doctest_compile_patch(test):
    def compile_example(source, filename, mode, *args):
        match = DOCTEST_EXAMPLE_FILENAME_RE.match(filename)
        example_n = int(match.group('examplenum'))
        example = test.examples[example_n]
        line = example.lineno
        return compile('\n'*(line)+source, test.filename, mode, *args)
    return compile_example


def walk_the_traceback(traceback, test):
    """Try to find the traceback for this test."""
    try:
        test_filename = test.filename
    except AttributeError:
        return traceback

    while traceback.tb_next is not None:
        try:
            tb_filename = traceback.tb_frame.f_code.co_filename
            if tb_filename == test_filename:
                return traceback
        except AttributeError:
            pass
        traceback = traceback.tb_next

    return traceback


def acquire_testrunner_traceback(exc_info):
    ex_type, err, traceback = exc_info

    if isinstance(err, doctest.UnexpectedException):
        exc_info = err.exc_info
        traceback = exc_info[2]
    elif isinstance(err, doctest.DocTestFailure):
        try:
            last_line = max(0, len(err.example.source.splitlines())+err.example.lineno-1)
            throw_source = '\n'*(last_line) +\
                           'raise ValueError'\
                           '("Expected and actual output are different")'
            exec compile(throw_source, err.test.filename, 'single') in err.test.globs
        except:
            exc_info = sys.exc_info()
            traceback = exc_info[2]

    if isinstance(err, (doctest.DocTestFailure, doctest.UnexpectedException)):
        traceback = walk_the_traceback(traceback, err.test)

    return traceback


def walk_frames_to_find_output():
    from zope.testrunner.runner import TestResult
    ff = sys._getframe()
    while ff.f_back is not None:
        ff = ff.f_back
        if isinstance(ff.f_locals.get('self'), TestResult):
            testresult = ff.f_locals['self']
            return testresult.options.output



def report_testrunner_real_exception(exc_info):
    ex_type, err, traceback = exc_info
    if not isinstance(err, doctest.UnexpectedException):
        return # nothing to report
    try:
        import zope.testrunner.runner
    except ImportError:
        return # no testrunner
    exc_info = err.exc_info
    traceback = exc_info[2]
    traceback = walk_the_traceback(traceback, err.test)
    output = walk_frames_to_find_output()
    if output is not None:
        output.print_traceback(
            "Test failure:", (exc_info[0], exc_info[1], traceback))


def make_ipdb_testrunner_postmortem(test):
    import ipdb
    import zope.testrunner.interfaces
    def interactive_post_mortem(exc_info):
        report_testrunner_real_exception(exc_info)
        tb = acquire_testrunner_traceback(exc_info)
        ipdb.__main__.update_stdout()
        ipdb.__main__.BdbQuit_excepthook.excepthook_ori = sys.excepthook
        sys.excepthook = ipdb.__main__.BdbQuit_excepthook
        p = ipdb.__main__.Pdb(ipdb.__main__.def_colors)
        p.reset()
        p.botframe = tb.tb_frame
        p.interaction(tb.tb_frame, tb)
        raise zope.testrunner.interfaces.EndRun()
    return interactive_post_mortem


def make_pdb_testrunner_postmortem(test):
    import pdb
    import zope.testrunner.interfaces
    def interactive_post_mortem(exc_info):
        report_testrunner_real_exception(exc_info)
        tb = acquire_testrunner_traceback(exc_info)
        p = pdb.Pdb()
        p.reset()
        p.botframe = tb.tb_frame
        p.interaction(tb.tb_frame, tb)
        raise zope.testrunner.interfaces.EndRun()
    return interactive_post_mortem


def make_testrunner_postmortem_patch(test):
    try:
        return make_ipdb_testrunner_postmortem(test)
    except ImportError:
        pass

    try:
        return make_pdb_testrunner_postmortem(test)
    except ImportError:
        return None
    return None


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
        if BLACK_MAGIC:
            self.patches = mock.ModulesSnapshot()

    def setUp(self):
        global _Browser_UI_ext
        global _Element_UI_ext
        _Browser_UI_ext = ExtensionGroup()
        _Element_UI_ext = ExtensionGroup()
        schooltool.testing.registry.setupSeleniumHelpers()
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
        global _Browser_UI_ext
        global _Element_UI_ext
        _Browser_UI_ext = None
        _Element_UI_ext = None

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
        if BLACK_MAGIC:
            self.patches.restore()


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

    def honour_only_first_failure_flag(self, test):
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

    def report_unexpected_exception(self, out, test, example, exc_info):
        result = doctest.DocTestRunner.report_unexpected_exception(
            self, out, test, example, exc_info)
        self.honour_only_first_failure_flag(test)
        return result

    def report_failure(self, out, test, example, got):
        result = doctest.DocTestRunner.report_failure(
            self, out, test, example, got)
        self.honour_only_first_failure_flag(test)
        return result


class RepeatyDebugRunner(doctest.DebugRunner, SkippyDocTestRunner):
    """Mr. Repeaty Debugger."""


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


class DiffTemplate(object):

    class ExampleStub(object):
        pass

    def __init__(self, checker, optionflags=None):
        self.checker = checker
        self.optionflags = optionflags

    def prettifyDiff(self, diff):
        output = walk_frames_to_find_output()
        if output is None:
            return diff
        old_stdout = sys.stdout
        result = StringIO()
        sys.stdout = result
        try:
            output.print_doctest_failure(diff)
        finally:
            sys.stdout = old_stdout
        return result.getvalue()

    def __mod__(self, params):
        file, line, name, source, want, got = params
        result = 'File "%s", line %s, in %s' % (file, line, name)
        result += '\n\n>>> '+'\n...'.join(source.splitlines())+'\n\n'
        example = self.ExampleStub()
        example.want = want
        diff = self.checker.output_difference(example, got, self.optionflags)
        result += self.prettifyDiff(diff)
        return result


def make_pretty_diff_template(*args, **kw):
    try:
        import zope.testrunner.formatter
    except ImportError:
        return None
    return DiffTemplate(*args, **kw)


class SeleniumDocFileCase(doctest.DocFileCase):

    def __init__(self, test,
                 optionflags=0,
                 setUp=None, tearDown=None,
                 checker=None):
        super(SeleniumDocFileCase, self).__init__(
            test, optionflags=optionflags,
            setUp=setUp, tearDown=tearDown, checker=checker)

    if BLACK_MAGIC:
        def patch(self, patches):
            self._layer.patches.mock(
                dict(filter(lambda (a, m): m is not None, patches.items())))

    def run(self, *args, **kw):
        if BLACK_MAGIC:
            test = self._dt_test
            patches = {
                'doctest.compile':
                    make_doctest_compile_patch(test),
                }
            self.patch(patches)
        return doctest.DocFileCase.run(self, *args, **kw)

    def debug(self):
        if BLACK_MAGIC:
            test = self._dt_test
            patches = {
                'doctest.compile':
                    make_doctest_compile_patch(test),
                #'linecache.getlines':
                #    make_doctest_getlines_patch(test),
                'zope.testrunner.debug.post_mortem':
                    make_testrunner_postmortem_patch(test),
                'zope.testrunner.formatter.doctest_template':
                    make_pretty_diff_template(self._dt_checker,
                                              optionflags=self._dt_optionflags),
                }
            self.patch(patches)
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
        if BLACK_MAGIC:
            def layer_setting_factory(*args, **kw):
                test_case = test_case_factory(*args, **kw)
                test_case._layer = layer
                return test_case
            suite_test_case_factory = layer_setting_factory
        else:
            suite_test_case_factory = test_case_factory
        suite = SeleniumDocFileSuite(layer, filename,
                                     package=package,
                                     optionflags=optionflags,
                                     globs={'browsers': layer.browsers},
                                     test_case_factory=suite_test_case_factory)
        return suite
    assert isinstance(layer, SeleniumLayer)
    suite = collect_txt_ftests(package=package, level=level,
                               layer=layer, filenames=filenames,
                               suite_factory=make_suite)
    if not selenium_enabled:
        # XXX: should log that tests are skipped somewhere better
        print >> sys.stderr, 'Selenium not configured, skipping', package.__name__
        return unittest.TestSuite()
    return suite


class PreferNoLanguage(object):

    def __init__(self, context):
        pass

    def getPreferredLanguages(self):
        return ()
