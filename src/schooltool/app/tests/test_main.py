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
Unit tests for schooltool.app.main.
"""

import os
import sys
import unittest
import doctest

from zope.component import getUtility
from zope.testing import cleanup
from zope.traversing.interfaces import IContainmentRoot
from zope.interface import directlyProvides

here = os.path.dirname(__file__)
ftesting_zcml = os.path.join(here, '..', 'ftesting.zcml')


def doctest_main():
    """Tests for main().

    Main does nothing more but configures SchoolTool, prints the startup time,
    and starts the main loop.

    Since we don't want to actually create disk files and start a web server in
    a test, we will set up some stubs.

        >>> from schooltool.app.main import Options
        >>> options = Options()
        >>> class ConfigStub:
        ...     pass
        >>> options.config = ConfigStub()

        >>> def load_options_stub(argv):
        ...     return options
        >>> def setup_stub(opts):
        ...     print "Performing setup..."
        ...     assert opts is options
        >>> from schooltool.app.main import SchoolToolServer
        >>> server = SchoolToolServer()
        >>> server.load_options = load_options_stub
        >>> server.setup = setup_stub

    Now we will run main().

        >>> server.main(['sb.py'])
        Performing setup...

    """


def doctest_load_options():
    """Tests for load_options().

        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()

    We will use a sample configuration file that comes with these tests.

        >>> import os
        >>> from schooltool.app import tests
        >>> test_dir = os.path.dirname(tests.__file__)
        >>> sample_config_file = os.path.join(test_dir, 'sample.conf')
        >>> empty_config_file = os.path.join(test_dir, 'empty.conf')

    load_options will report errors to stderr.  We need to temporarily
    redirect stderr to stdout, because otherwise doctests will not see the
    output.

        >>> old_stderr = sys.stderr
        >>> sys.stderr = sys.stdout

    Load options parses command line arguments and the configuration file.

        >>> from schooltool.app.main import SchoolToolServer
        >>> server = SchoolToolServer()
        >>> o = server.load_options(['st.py', '-c', sample_config_file])
        Reading configuration from ...sample.conf

    Some options come from the command line

        >>> o.config_file
        '...sample.conf'
        >>> o.pack
        False

    Some come from the config file

        >>> o.config.error_log_file
        ['/var/log/schooltool/schooltool.log', 'STDERR']
        >>> o.config.web_access_log_file
        ['/var/log/schooltool/web-access.log']
        >>> o.config.reportlab_fontdir
        '/fonts/liberation:/fonts/ubuntu'

    `load_options` can also give you a nice help message and exit with status
    code 0.

        >>> try:
        ...     o = server.load_options(['st.py', '-h'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Usage: st.py [options]
        Options:
          -c, --config xxx       use this configuration file
          -h, --help             show this help message
          --pack                 pack the database
          -r, --restore-manager password
                                 restore the manager user with the provided password
                                 (read password from the standart input if 'password'
                                 is '-')
        [exited with status 0]

    Here's what happens, when you use an unknown command line option.

        >>> try:
        ...     o = server.load_options(['st.py', '-q'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        st.py: option -q not recognized
        Run st.py -h for help.
        [exited with status 1]

    Here's what happens when the configuration file cannot be found

        >>> try:
        ...     o = server.load_options(['st.py', '-c', 'nosuchfile'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Reading configuration from nosuchfile
        st.py: error opening file ...nosuchfile: ...
        [exited with status 1]

    Here's what happens if you do not specify a storage section in the
    configuration file.

        >>> try:
        ...     o = server.load_options(['st.py', '-c', empty_config_file])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Reading configuration from ...empty.conf
        st.py: No storage defined in the configuration file.
        [exited with status 1]

    Cleaning up.

        >>> sys.stderr = old_stderr

        >>> setup.placelessTearDown()

    """


def doctest_configureReportlab():
    """Tests for configureReportlab.

        >>> from schooltool.app import pdf
        >>> from schooltool.app.main import SchoolToolServer

        >>> server = SchoolToolServer()

        >>> def setupStub(fontdir):
        ...     print 'reportlab set up: %s' % fontdir
        >>> realSetup = pdf.setUpFonts
        >>> pdf.setUpFonts = setupStub

        >>> old_stderr = sys.stderr
        >>> sys.stderr = sys.stdout

    First, if a null path is given, nothing happens (PDF support is
    left disabled):

        >>> server.configureReportlab(None)

    Now test the check that the font path is a directory:

        >>> server.configureReportlab(__file__)
        Warning: font directories '...test_main...' do not exist.
        PDF support disabled.

    We will cheat and temporarily override pdf.font_map:

        >>> pseudo_fontdir = os.path.dirname(__file__)
        >>> real_font_map = pdf.font_map
        >>> pdf.font_map = {'1': 'test_main.py', '2': 'nonexistent_file'}

        >>> server.configureReportlab(pseudo_fontdir)
        Warning: font '...nonexistent_file' does not exist...
        PDF support disabled.

    Now let's simulate a successful scenario:

        >>> del pdf.font_map['2']
        >>> server.configureReportlab(pseudo_fontdir)
        reportlab set up: ...tests...

    Cleaning up.

        >>> pdf.font_map = real_font_map
        >>> sys.stderr = old_stderr
        >>> pdf.setUpFonts = realSetup

    """


def doctest_setLanguage():
    """Tests for setLanguage.

        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()

    First, the 'automatic mode':

        >>> from schooltool.app.main import setLanguage
        >>> setLanguage('auto')

    The language adapter shouldn't have been installed:

        >>> from zope.i18n.interfaces import IUserPreferredLanguages
        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> IUserPreferredLanguages(request).getPreferredLanguages()
        []

    Now, if we specify a language, a language adapter should be set up:

        >>> setLanguage('lt')
        >>> IUserPreferredLanguages(request).getPreferredLanguages()
        ('lt',)

    If the language list contains more than one language, you get a
    cookie language selector:

        >>> from schooltool.app.interfaces import ICookieLanguageSelector
        >>> setLanguage('en, lt')
        >>> upl = IUserPreferredLanguages(request)
        >>> ICookieLanguageSelector.providedBy(upl)
        True

        >>> upl.getLanguageList()
        ['en', 'lt']

        >>> upl.getPreferredLanguages()
        ('en',)

    We're done.

        >>> setup.placelessTearDown()

    """


def doctest_setup():
    """Tests for setup()

        >>> cleanup.setUp()

    setup() does everything except enter the main application loop:

    - sets up loggers
    - configures Zope 3 components
    - opens the database (optionally packs it)

    It is difficult to unit test, but we'll try.

        >>> from schooltool.app.main import Options, SchoolToolServer
        >>> from ZODB.MappingStorage import MappingStorage
        >>> from ZODB.DB import DB
        >>> options = Options()
        >>> class DatabaseConfigStub:
        ...     def open(self):
        ...         return DB(MappingStorage())
        >>> class ConfigStub:
        ...     thread_pool_size = 1
        ...     database = DatabaseConfigStub()
        ...     pid_file = ''
        ...     error_log_file = ['STDERR']
        ...     web_access_log_file = ['STDOUT']
        ...     attendance_log_file = ['STDOUT']
        ...     lang = 'lt'
        ...     reportlab_fontdir = ''
        ...     devmode = False
        ...     site_definition = ftesting_zcml
        >>> options.config = ConfigStub()

    Workaround to fix a Windows failure:

        >>> import logging
        >>> del logging.getLogger(None).handlers[:]

    And go!

        >>> server = SchoolToolServer()
        >>> db = server.setup(options)
        >>> print db
        <ZODB.DB.DB object at ...>

    The root object is SchoolToolApplication:

        >>> connection = db.open()
        >>> root = connection.root()
        >>> from zope.app.publication.zopepublication import ZopePublication
        >>> app = root.get(ZopePublication.root_name)
        >>> app
        <schooltool.app.app.SchoolToolApplication object at ...>

    The manager is a SchoolTool person:

        >>> from schooltool.person.interfaces import IPerson
        >>> IPerson.providedBy(app['persons']['manager'])
        True

    A web access logger has been set up:

        >>> logger1 = logging.getLogger('accesslog')
        >>> logger1.propagate
        False
        >>> logger1.handlers
        [<logging.StreamHandler ...>]

    A generic access logger has been set up too:

        >>> logger2 = logging.getLogger(None)
        >>> logger2.handlers
        [<logging.StreamHandler ...>]

    The language adapter shouldn't have been installed:

        >>> from zope.i18n.interfaces import IUserPreferredLanguages
        >>> from zope.publisher.browser import TestRequest
        >>> request = TestRequest()
        >>> IUserPreferredLanguages(request).getPreferredLanguages()
        ('lt',)

    ZODB.lock_file has been shut up:

        >>> logging.getLogger('ZODB.lock_file').disabled
        True

    We better clean up logging before we leave:

        >>> logging.getLogger('ZODB.lock_file').disabled = False
        >>> for logger in [logger1, logger2]:
        ...     del logger.handlers[:]
        ...     logger.propagate = True
        ...     logger.disabled = False

        >>> for logger in [logger1]:
        ...     logger.setLevel(0)

        >>> cleanup.tearDown()

    """



class ConfigStub(object):

    devmode = False
    site_definition = None


class OptionsStub(object):

    config = ConfigStub()
    config_file = ''


def doctest_bootstrapSchoolTool():
    r"""Tests for bootstrapSchoolTool()

        >>> cleanup.setUp()

    Normally, bootstrapSchoolTool is called when Zope 3 is fully configured

        >>> from schooltool.app.main import SchoolToolServer
        >>> server = SchoolToolServer()
        >>> options = OptionsStub()
        >>> options.config.site_definition = ftesting_zcml
        >>> server.configureComponents(options)

    When we start with an empty database, bootstrapSchoolTool creates a
    SchoolTool application in it.

        >>> import transaction
        >>> from ZODB.DB import DB
        >>> from ZODB.MappingStorage import MappingStorage
        >>> db = DB(MappingStorage())

        >>> server.bootstrapSchoolTool(db)

    Let's take a look...

        >>> connection = db.open()
        >>> root = connection.root()
        >>> from zope.app.publication.zopepublication import ZopePublication
        >>> app = root.get(ZopePublication.root_name)
        >>> app
        <schooltool.app.app.SchoolToolApplication object at ...>

    This new application object is the containment root

        >>> IContainmentRoot.providedBy(app)
        True

    It is also a site

        >>> from zope.component.interfaces import ISite
        >>> ISite.providedBy(app)
        True

    It has a local authentication utility

        >>> from zope.authentication.interfaces import IAuthentication
        >>> getUtility(IAuthentication, context=app)
        <schooltool.app.security.SchoolToolAuthenticationUtility object at ...>

    It has an initial user (username 'manager', password 'schooltool')

        >>> manager = app['persons']['manager']
        >>> manager.checkPassword('schooltool')
        True

    bootstrapSchoolTool doesn't do anything if it finds the root object already
    present in the database.

        >>> from schooltool.person.person import Person
        >>> manager = app['persons']['user1'] = Person('user1')
        >>> transaction.commit()
        >>> connection.close()

        >>> server.bootstrapSchoolTool(db)

        >>> connection = db.open()
        >>> root = connection.root()
        >>> 'user1' in root[ZopePublication.root_name]['persons']
        True

    Clean up

        >>> transaction.abort()
        >>> connection.close()
        >>> cleanup.tearDown()
    """


def doctest_restoreManagerUser():
    r"""Unit test for SchoolToolServer.restoreManagerUser

        >>> cleanup.setUp()

    We need a configured server:

        >>> from schooltool.app.main import SchoolToolServer
        >>> server = SchoolToolServer()
        >>> options = OptionsStub()
        >>> options.config.site_definition = ftesting_zcml
        >>> server.configureComponents(options)

    We also need an application (we are doing the full set up in here
    because else person factory local utility is not being
    registered):

        >>> import transaction
        >>> from zope.lifecycleevent import ObjectAddedEvent
        >>> from schooltool.app.interfaces import ApplicationInitializationEvent
        >>> from zope.event import notify
        >>> from zope.app.publication.zopepublication import ZopePublication
        >>> from ZODB.DB import DB
        >>> from ZODB.MappingStorage import MappingStorage

        >>> db = DB(MappingStorage())
        >>> connection = db.open()
        >>> root = connection.root()

        >>> from schooltool.app.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> directlyProvides(app, IContainmentRoot)
        >>> root[ZopePublication.root_name] = app

        >>> save_point = transaction.savepoint(optimistic=True)
        >>> notify(ApplicationInitializationEvent(app))
        >>> notify(ObjectAddedEvent(app))

    Initially, there's no manager user in the database:

        >>> app['persons']['manager']
        Traceback (most recent call last):
          ...
        KeyError: 'manager'

    When we call restoreManagerUser, it gets created:

        >>> server.restoreManagerUser(app, 'schooltool')

        >>> manager = app['persons']['manager']
        >>> manager.checkPassword('schooltool')
        True

    Manager is by default a super user:

        >>> app['persons'].super_user is manager
        True

    To prevent this user from being deleted we add a dependency

        >>> from zope.app.dependable.interfaces import IDependable
        >>> IDependable(manager).dependents()
        (u'/persons/',)

    Let's break the manager user by forgetting his password:

        >>> marker = object()
        >>> manager.calendar = marker
        >>> manager.setPassword('randomrandom')

        >>> manager.checkPassword('schooltool')
        False

    If we call restoreManagerUser again, the object remains the same,
    but its password gets reset:

        >>> server.restoreManagerUser(app, 'schooltool')

        >>> manager = app['persons']['manager']
        >>> manager.checkPassword('schooltool')
        True

    The manager is the same:

        >>> manager.calendar is marker
        True

    Cleanup:

        >>> transaction.abort()
        >>> connection.close()
        >>> cleanup.tearDown()
    """


def test_setUpLogger():
    r"""Tests for setUpLogger.

    setUpLogger sets up a logger:

        >>> import logging
        >>> from schooltool.app.main import setUpLogger
        >>> setUpLogger('schooltool.just_testing',
        ...             ['STDERR', '_just_testing.log'],
        ...             '%(asctime)s %(message)s')

        >>> logger = logging.getLogger('schooltool.just_testing')
        >>> logger.propagate
        False
        >>> logger.handlers
        [<logging.StreamHandler ...>, <...UnicodeFileHandler ...>]
        >>> logger.handlers[0].stream is sys.stderr
        True
        >>> logger.handlers[0].formatter
        <logging.Formatter ...>
        >>> logger.handlers[0].formatter._fmt
        '%(asctime)s %(message)s'

    Let's clean up after ourselves (logging is messy):

        >>> del logger.handlers[:]
        >>> logger.propagate = True
        >>> logger.disabled = False
        >>> logger.setLevel(0)

        >>> import os
        >>> os.unlink('_just_testing.log')

    """



def doctest_CyclicPluginActionOrderException():
    """Tests for CyclicPluginActionOrderException.

    This exception converts a list of PluginDependency items to a human
    readable format.

       >>> from schooltool.app.main import PluginDependency
       >>> from schooltool.app.main import CyclicPluginActionOrderException

       >>> class PluginStub(object):
       ...     def __init__(self, name):
       ...         self.name = name
       ...     def __repr__(self):
       ...         return '<%s>' % self.name

       >>> dependencies = [
       ...     PluginDependency(PluginStub('alpha'), 'A',
       ...                      PluginStub('beta'), 'B'),
       ...     PluginDependency(PluginStub('gamma'), 'G',
       ...                      PluginStub('delta'), 'D',
       ...                      inverse=True),
       ...     PluginDependency(PluginStub('omega'), 'O')]

       >>> exception = CyclicPluginActionOrderException(dependencies)

       >>> print exception
       Cannot resolve plugin action order:
       <alpha> named "A" must be executed _before_ <beta> named "B".
       <gamma> named "G" must be executed _after_ <delta> named "D".
       <omega> named "O" must be executed _before_ another.

    """


def doctest_PluginActionSorter():
    """Tests for PluginActionSorter.

    The purpose of PluginActionSorter is to resolve the order in which
    the plugin actions should be executed.

        >>> from schooltool.app.main import PluginActionSorter

        >>> class ActionStub(object):
        ...     def __init__(self, exec_after, name, exec_before):
        ...         self.name = name
        ...         self.after = exec_after
        ...         self.before = exec_before
        ...     def __repr__(self):
        ...         return '<action %s>' % self.name

    The sorter takes a list of (adapter_name, factory) tuples that can be
    obtained with getAdapters.

        >>> actions = [
        ...     ActionStub([], 'C', []),
        ...     ActionStub([], 'A', ['B']),
        ...     ActionStub([], 'B', []),
        ...     ActionStub(['A'], 'Q', []),
        ...     ]

        >>> sorter = PluginActionSorter([(a.name, a) for a in actions])

    The sorter tries to maintain the original order of plugins if possible.

        >>> print sorter()
        [<action C>, <action A>, <action B>, <action Q>]

    When the order cannot be maintained, plugins are sorted by their
    execution dependencies.

        >>> actions = [
        ...     ActionStub([], 'A', []),
        ...     ActionStub([], 'B', []),
        ...     ActionStub(['D'], 'C', []),
        ...     ActionStub(['B'], 'D', ['A']),
        ...     ]

        >>> sorter = PluginActionSorter([(a.name, a) for a in actions])
        >>> print sorter()
        [<action B>, <action D>, <action A>, <action C>]

    In case of invalid dependencies, an exception is thrown.

        >>> actions = [
        ...     ActionStub([], 'A', []),
        ...     ActionStub(['A'], 'B', ['A']),
        ...     ]
        >>> sorter = PluginActionSorter([(a.name, a) for a in actions])
        >>> print sorter()
        Traceback (most recent call last):
        ...
        CyclicPluginActionOrderException: Cannot resolve plugin action order:
        <action A> named "A" must be executed _before_ <action B> named "B".
        <action A> named "A" must be executed _after_ <action B> named "B".

    The sorter also detects dependency cycles.

        >>> actions = [
        ...     ActionStub([], 'A', ['B']),
        ...     ActionStub([], 'B', []),
        ...     ActionStub(['B'], 'C', ['A']),
        ...     ]

        >>> sorter = PluginActionSorter([(a.name, a) for a in actions])
        >>> print sorter()
        Traceback (most recent call last):
        ...
        CyclicPluginActionOrderException: Cannot resolve plugin action order:
        <action B> named "B" must be executed _after_ <action A> named "A".
        <action B> named "B" must be executed _before_ <action C> named "C".
        <action A> named "A" must be executed _after_ <action C> named "C".

    """


def test_suite():
    # Override _ to not get translated test output
    import schooltool.app.main
    schooltool.app.main._ = lambda x: x

    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_NDIFF)
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.app.main',
                                     optionflags=optionflags),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
