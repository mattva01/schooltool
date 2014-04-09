#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Functional Testing Utilities
"""

import os
import unittest
import doctest

from zope.testbrowser.testing import Browser
from zope.testing.server import startServer
from zope.app.testing.functional import HTTPCaller
from zope.app.testing.functional import ZCMLLayer as _ZCMLLayer
from zope.app.testing.functional import FunctionalDocFileSuite
from zope.app.appsetup.interfaces import IDatabaseOpenedEvent
import zope.event

from schooltool.testing.analyze import queryHTML
from schooltool.testing import analyze


def find_ftesting_zcml():
    """Find ftesting.zcml to be used for SchoolTool functional tests."""
    dir = os.path.abspath(os.path.dirname(__file__))
    while True:
        filename = os.path.join(dir, 'etc', 'ftesting.zcml')
        if os.path.exists(filename):
            return filename # We are testing in an instance
        dir = os.path.dirname(dir)
        if dir == os.path.dirname(dir): # we're looping at the filesystem root
            raise RuntimeError("I can't find ftesting.zcml!")


class ZCMLLayer(_ZCMLLayer):

    def __init__(self, *args, **kwargs):
        kwargs['allow_teardown'] = True
        _ZCMLLayer.__init__(self, *args, **kwargs)

    def setUp(self):
        # SchoolTool needs to bootstrap the database first, before the Zope 3
        # IDatabaseOpenedEvent gets a chance to create its own root folder and
        # stuff.  Unfortunatelly, we cannot install a IDatabaseOpenedEvent
        # subscriber via ftesting.zcml and ensure it will get called first.
        # Instead we place our own subscriber directly into zope.event.subscribers,
        # where it gets a chance to intercept IDatabaseOpenedEvent before the
        # Zope 3 event dispatcher sees it.

        def install_db_bootstrap_hook():
            """Install schooltool_db_setup into zope.event.subscribers."""
            zope.event.subscribers.insert(0, schooltool_db_setup)

        def uninstall_db_bootstrap_hook():
            """Remove schooltool_db_setup from zope.event.subscribers."""
            zope.event.subscribers.remove(schooltool_db_setup)

        def schooltool_db_setup(event):
            """IDatabaseOpenedEvent handler that bootstraps SchoolTool."""
            if IDatabaseOpenedEvent.providedBy(event):
                import schooltool.app.main
                server = schooltool.app.main.SchoolToolServer()
                server.initializePreferences = lambda app: None
                server.bootstrapSchoolTool(event.database)
                server.startApplication(event.database)

        install_db_bootstrap_hook()
        try:
            _ZCMLLayer.setUp(self)
        finally:
            uninstall_db_bootstrap_hook()


class TestBrowser(Browser):

    username = None
    password = None

    def __init__(self, username=None, password=None, url='http://localhost/'):
        super(TestBrowser, self).__init__()
        self.username = username
        self.password = password
        if username and password:
            self.addHeader('Authorization',
                           'Basic %s:%s' % (self.username, self.password))
        self.handleErrors = False
        self.open(url)

    def serve(self, url=None, port=8000):
        if url is None:
            url = self.url
        startServer(HTTPCaller(), url, self.username, self.password, port=port)

    def queryHTML(self, query):
        return queryHTML(query, self.contents)

    def printQuery(self, query, skip_inner_blank=False):
        for item in queryHTML(query, self.contents):
            if item.strip():
                if skip_inner_blank:
                    result = str(item.strip()).splitlines()
                    for line in result:
                        line = line.strip()
                        if line:
                            print line
                else:
                    print item.strip()


def collect_txt_ftests(package=None, level=None, layer=None, filenames=None,
                       suite_factory=None):
    """Collect all functional doctest files in a given package.

    If `package` is None, looks up the call stack for the right module.

    Returns a unittest.TestSuite.
    """
    testdir = os.path.dirname(package.__file__)
    if filenames is None:
        filenames = [fn for fn in os.listdir(testdir)
                     if fn.endswith('.txt') and not fn.startswith('.')]
    suites = []
    for filename in filenames:
        suite = suite_factory(
            filename, package=package)
        if level is not None:
            suite.level = level
        if layer is None:
            raise ValueError("ftests must specify an ftesting.zcml.")
        suite.layer = layer
        suites.append(suite)
    return unittest.TestSuite(suites)


def collect_ftests(package=None, level=None, layer=None, filenames=None,
                   extra_globs=None):
    package = doctest._normalize_module(package)
    extra_globs = extra_globs or {}
    extra_globs.update({'analyze': analyze,
                        'Browser': TestBrowser})
    def make_suite(filename, package=None):
        optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                       doctest.NORMALIZE_WHITESPACE |
                       doctest.REPORT_ONLY_FIRST_FAILURE)
        suite = FunctionalDocFileSuite(filename, package=package,
                                       optionflags=optionflags,
                                       globs=extra_globs)
        return suite
    return collect_txt_ftests(package=package, level=level,
                              layer=layer, filenames=filenames,
                              suite_factory=make_suite)
