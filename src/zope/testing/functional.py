##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Functional testing framework for Zope 3.

There should be a file 'ftesting.zcml' in the current directory.

$Id: functional.py,v 1.19 2004/03/19 12:00:11 jim Exp $
"""

import logging
import sys
import traceback
import unittest

from StringIO import StringIO

from transaction import get_transaction
from ZODB.DB import DB
from ZODB.DemoStorage import DemoStorage
from zope.publisher.browser import BrowserRequest
from zope.publisher.http import HTTPRequest
from zope.publisher.publish import publish
from zope.exceptions import Forbidden, Unauthorized

from zope.app import Application
from zope.app.publication.zopepublication import ZopePublication
from zope.app.publication.http import HTTPPublication

__metaclass__ = type


class HTTPTaskStub(StringIO):

    pass


class ResponseWrapper:
    """A wrapper that adds several introspective methods to a response."""

    def __init__(self, response, outstream, path):
        self._response = response
        self._outstream = outstream
        self._path = path

    def getOutput(self):
        """Returns the full HTTP output (headers + body)"""
        return self._outstream.getvalue()

    def getBody(self):
        """Returns the response body"""
        output = self._outstream.getvalue()
        idx = output.find('\r\n\r\n')
        if idx == -1:
            return None
        else:
            return output[idx+4:]

    def getPath(self):
        """Returns the path of the request"""
        return self._path

    def __getattr__(self, attr):
        return getattr(self._response, attr)


class FunctionalTestSetup:
    """Keeps shared state across several functional test cases."""

    __shared_state = { '_init': False }

    def __init__(self, config_file=None):
        """Initializes Zope 3 framework.

        Creates a volatile memory storage.  Parses Zope3 configuration files.
        """
        self.__dict__ = self.__shared_state

        if not self._init:
            if not config_file:
                config_file = 'ftesting.zcml'
            self.log = StringIO()
            # Make it silent but keep the log available for debugging
            logging.root.addHandler(logging.StreamHandler(self.log))
            self.base_storage = DemoStorage("Memory Storage")
            self.db = DB(self.base_storage)
            self.app = Application(self.db, config_file)
            self.connection = None
            self._config_file = config_file
            self._init = True
        elif config_file and config_file != self._config_file:
            # Running different tests with different configurations is not
            # supported at the moment
            raise NotImplementedError('Already configured'
                                      ' with a different config file')

    def setUp(self):
        """Prepares for a functional test case."""
        # Tear down the old demo storage (if any) and create a fresh one
        self.db.close()
        storage = DemoStorage("Demo Storage", self.base_storage)
        self.db = self.app.db = DB(storage)

    def tearDown(self):
        """Cleans up after a functional test case."""
        get_transaction().abort()
        if self.connection:
            self.connection.close()
            self.connection = None
        self.db.close()

    def getRootFolder(self):
        """Returns the Zope root folder."""
        if not self.connection:
            self.connection = self.db.open()
        root = self.connection.root()
        return root[ZopePublication.root_name]

    def getApplication(self):
        """Returns the Zope application instance."""
        return self.app


class FunctionalTestCase(unittest.TestCase):
    """Functional test case."""

    def setUp(self):
        """Prepares for a functional test case."""
        super(FunctionalTestCase, self).setUp()
        FunctionalTestSetup().setUp()

    def tearDown(self):
        """Cleans up after a functional test case."""
        FunctionalTestSetup().tearDown()
        super(FunctionalTestCase, self).tearDown()

    def getRootFolder(self):
        """Returns the Zope root folder."""
        return FunctionalTestSetup().getRootFolder()

    def commit(self):
        get_transaction().commit()

    def abort(self):
        get_transaction().abort()

class BrowserTestCase(FunctionalTestCase):
    """Functional test case for Browser requests."""

    def makeRequest(self, path='', basic=None, form=None, env={},
                    outstream=None):
        """Creates a new request object.

        Arguments:
          path   -- the path to be traversed (e.g. "/folder1/index.html")
          basic  -- basic HTTP authentication credentials ("user:password")
          form   -- a dictionary emulating a form submission
                    (Note that field values should be Unicode strings)
          env    -- a dictionary of additional environment variables
                    (You can emulate HTTP request header
                       X-Header: foo
                     by adding 'HTTP_X_HEADER': 'foo' to env)
          outstream -- a stream where the HTTP response will be written
        """
        if outstream is None:
            outstream = HTTPTaskStub()
        environment = {"HTTP_HOST": 'localhost',
                       "HTTP_REFERER": 'localhost'}
        environment.update(env)
        app = FunctionalTestSetup().getApplication()
        request = app._request(path, '', outstream,
                               environment=environment,
                               basic=basic, form=form,
                               request=BrowserRequest)
        return request

    def publish(self, path, basic=None, form=None, env={},
                handle_errors=False):
        """Renders an object at a given location.

        Arguments are the same as in makeRequest with the following exception:
          handle_errors  -- if False (default), exceptions will not be caught
                            if True, exceptions will return a formatted error
                            page.

        Returns the response object enhanced with the following methods:
          getOutput()    -- returns the full HTTP output as a string
          getBody()      -- returns the full response body as a string
          getPath()      -- returns the path used in the request
        """
        outstream = HTTPTaskStub()
        request = self.makeRequest(path, basic=basic, form=form, env=env,
                                   outstream=outstream)
        response = ResponseWrapper(request.response, outstream, path)
        publish(request, handle_errors=handle_errors)
        return response

    def checkForBrokenLinks(self, body, path, basic=None):
        """Looks for broken links in a page by trying to traverse relative
        URIs.
        """
        if not body: return

        from htmllib import HTMLParser
        from formatter import NullFormatter
        class SimpleHTMLParser(HTMLParser):
            def __init__(self, fmt, base):
                HTMLParser.__init__(self, fmt)
                self.base = base
            def do_base(self, attrs):
                self.base = dict(attrs).get('href', self.base)

        parser = SimpleHTMLParser(NullFormatter(), path)
        parser.feed(body)
        parser.close()
        base = parser.base
        while not base.endswith('/'):
            base = base[:-1]
        if base.startswith('http://localhost/'):
            base = base[len('http://localhost/') - 1:]

        errors = []
        for a in parser.anchorlist:
            if a.startswith('http://localhost/'):
                a = a[len('http://localhost/') - 1:]
            elif a.find(':') != -1:
                # Assume it is an external link
                continue
            elif not a.startswith('/'):
                a = base + a
            if a.find('#') != -1:
                a = a[:a.index('#') - 1]
            # XXX what about queries (/path/to/foo?bar=baz&etc)?
            request = None
            try:
                try:
                    request = self.makeRequest(a, basic=basic)
                    publication = request.publication
                    request.processInputs()
                    publication.beforeTraversal(request)
                    object = publication.getApplication(request)
                    object = request.traverse(object)
                    publication.afterTraversal(request, object)
                except (KeyError, NameError, AttributeError, Unauthorized, Forbidden):
                    e = traceback.format_exception_only(*sys.exc_info()[:2])[-1]
                    errors.append((a, e.strip()))
            finally:
                # Bad Things(TM) related to garbage collection and special
                # __del__ methods happen if request.close() is not called here
                if request:
                    request.close()
        if errors:
            self.fail("%s contains broken links:\n" % path
                      + "\n".join(["  %s:\t%s" % (a, e) for a, e in errors]))


class HTTPTestCase(FunctionalTestCase):
    """Functional test case for HTTP requests."""

    def makeRequest(self, path='', basic=None, form=None, env={},
                    instream=None, outstream=None):
        """Creates a new request object.

        Arguments:
          path   -- the path to be traversed (e.g. "/folder1/index.html")
          basic  -- basic HTTP authentication credentials ("user:password")
          form   -- a dictionary emulating a form submission
                    (Note that field values should be Unicode strings)
          env    -- a dictionary of additional environment variables
                    (You can emulate HTTP request header
                       X-Header: foo
                     by adding 'HTTP_X_HEADER': 'foo' to env)
          instream  -- a stream from where the HTTP request will be read
          outstream -- a stream where the HTTP response will be written
        """
        if outstream is None:
            outstream = HTTPTaskStub()
        if instream is None:
            instream = ''
        environment = {"HTTP_HOST": 'localhost',
                       "HTTP_REFERER": 'localhost'}
        environment.update(env)
        app = FunctionalTestSetup().getApplication()
        request = app._request(path, instream, outstream,
                               environment=environment,
                               basic=basic, form=form,
                               request=HTTPRequest, publication=HTTPPublication)
        return request

    def publish(self, path, basic=None, form=None, env={},
                handle_errors=False, request_body=''):
        """Renders an object at a given location.

        Arguments are the same as in makeRequest with the following exception:
          handle_errors  -- if False (default), exceptions will not be caught
                            if True, exceptions will return a formatted error
                            page.

        Returns the response object enhanced with the following methods:
          getOutput()    -- returns the full HTTP output as a string
          getBody()      -- returns the full response body as a string
          getPath()      -- returns the path used in the request
        """
        outstream = HTTPTaskStub()
        request = self.makeRequest(path, basic=basic, form=form, env=env,
                                   instream=request_body, outstream=outstream)
        response = ResponseWrapper(request.response, outstream, path)
        publish(request, handle_errors=handle_errors)
        return response

#
# Sample functional test case
#

class SampleFunctionalTest(BrowserTestCase):

    def testRootPage(self):
        response = self.publish('/')
        self.assertEquals(response.getStatus(), 200)

    def testRootPage_preferred_languages(self):
        response = self.publish('/', env={'HTTP_ACCEPT_LANGUAGE': 'en'})
        self.assertEquals(response.getStatus(), 200)

    def testNotExisting(self):
        response = self.publish('/nosuchthing', handle_errors=True)
        self.assertEquals(response.getStatus(), 404)

    def testLinks(self):
        response = self.publish('/')
        self.assertEquals(response.getStatus(), 200)
        self.checkForBrokenLinks(response.getBody(), response.getPath())


def sample_test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SampleFunctionalTest))
    return suite


if __name__ == '__main__':
    unittest.main()
