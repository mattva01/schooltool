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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for schoolbell.app.main.

$Id$
"""

import unittest
from zope.testing import doctest


def doctest_Options():
    """Tests for Options.

    The only interesting thing Options does is find the default configuration
    file.

        >>> import os
        >>> from schoolbell.app.main import Options
        >>> options = Options()
        >>> options.config_file
        '...schoolbell.conf...'

    """

def doctest_main():
    """Tests for main().

    Main does nothing more but configures SchoolTool, prints the startup time,
    and starts the main loop.

    Since we don't want to actually create disk files and start a web server in
    a test, we will set up some stubs.

        >>> from schoolbell.app.main import Options
        >>> options = Options()
        >>> class ConfigStub:
        ...     pid_file = ''
        >>> options.config = ConfigStub()

        >>> def load_options_stub(argv):
        ...     return options
        >>> def setup_stub(opts):
        ...     print "Performing setup..."
        ...     assert opts is options
        >>> def run_stub():
        ...     print "Running..."
        >>> from schoolbell.app import main
        >>> old_load_options = main.load_options
        >>> old_setup = main.setup
        >>> old_run = main.run
        >>> main.load_options = load_options_stub
        >>> main.setup = setup_stub
        >>> main.run = run_stub

    Now we will run main().

        >>> main.main(['sb.py', '-d'])
        Performing setup...
        Startup time: ... sec real, ... sec CPU
        Running...

    Clean up

        >>> main.load_options = old_load_options
        >>> main.setup = old_setup
        >>> main.run = old_run

    """


def doctest_load_options():
    """Tests for load_options().

    We will use a sample configuration file that comes with these tests.

        >>> import os
        >>> from schoolbell.app import tests
        >>> test_dir = os.path.dirname(tests.__file__)
        >>> sample_config_file = os.path.join(test_dir, 'sample.conf')
        >>> empty_config_file = os.path.join(test_dir, 'empty.conf')

    load_options will report errors to stderr.  We need to temporarily
    redirect stderr to stdout, because otherwise doctests will not see the
    output.

        >>> import sys
        >>> old_stderr = sys.stderr
        >>> sys.stderr = sys.stdout

    Load options parses command line arguments and the configuration file.
    Warnings about obsolete options are shown.

        >>> from schoolbell.app.main import load_options
        >>> o = load_options(['sb.py', '-c', sample_config_file])
        Reading configuration from ...sample.conf
        sb.py: warning: ignored configuration option 'module'
        sb.py: warning: ignored configuration option 'domain'
        sb.py: warning: ignored configuration option 'lang'
        sb.py: warning: ignored configuration option 'path'
        sb.py: warning: ignored configuration option 'app_log_file'


    Some options come from the command line

        >>> o.config_file
        '...sample.conf'
        >>> o.daemon
        False

    Some come from the config file

        >>> o.config.web
        [('', 48080)]
        >>> o.config.listen
        [('...', 123), ('10.20.30.40', 9999)]

    Note that "listen 123" in config.py produces ('localhost', 123) on
    Windows, but ('', 123) on other platforms.

    `load_options` can also give you a nice help message and exit with status
    code 0.

        >>> try:
        ...     o = load_options(['sb.py', '-h'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Usage: sb.py [options]
        Options:
          -c, --config xxx  use this configuration file instead of the default
          -h, --help        show this help message
          -d, --daemon      go to background after starting
        [exited with status 0]

    Here's what happens, when you use an unknown command line option.

        >>> try:
        ...     o = load_options(['sb.py', '-q'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        sb.py: option -q not recognized
        Run sb.py -h for help.
        [exited with status 1]

    Here's what happens when the configuration file cannot be found

        >>> try:
        ...     o = load_options(['sb.py', '-c', 'nosuchfile'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Reading configuration from nosuchfile
        sb.py: error opening file ...nosuchfile: ...
        [exited with status 1]

    Here's what happens if you do not specify a storage section in the
    configuration file.

        >>> try:
        ...     o = load_options(['sb.py', '-c', empty_config_file])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Reading configuration from ...empty.conf
        sb.py: No storage defined in the configuration file.
        <BLANKLINE>
        If you're using the default configuration file, please edit it now and
        uncomment one of the ZODB storage sections.
        [exited with status 1]

    Cleaning up.

        >>> sys.stderr = old_stderr

    """


def doctest_setup():
    """Tests for setup()

    setup() does everything except enter the main application loop:

    - sets up loggers
    - configures Zope 3 components
    - opens the database
    - starts tcp servers

    It is difficult to unit test, but we'll try.

        >>> from schoolbell.app.main import Options, setup
        >>> from ZODB.MappingStorage import MappingStorage
        >>> from ZODB.DB import DB
        >>> options = Options()
        >>> class DatabaseConfigStub:
        ...     def open(self):
        ...         return DB(MappingStorage())
        >>> class ConfigStub:
        ...     web = []
        ...     thread_pool_size = 1
        ...     database = DatabaseConfigStub()
        ...     pid_file = ''
        ...     path = []
        ...     error_log_file = ['STDERR']
        ...     web_access_log_file = ['STDOUT']
        >>> options.config = ConfigStub()

    Workaround to fix a Windows failure:

        >>> import logging
        >>> del logging.getLogger(None).handlers[:]

    And go!

        >>> setup(options)
        <ZODB.DB.DB object at ...>

    A web access logger has been set up:

        >>> logger1 = logging.getLogger('accesslog')
        >>> logger1.propagate
        False
        >>> logger1.handlers
        [<logging.StreamHandler instance at 0x...>]

    A generic access logger has been set up too:

        >>> logger2 = logging.getLogger(None)
        >>> logger2.handlers
        [<logging.StreamHandler instance at 0x...>]

    ZODB.lock_file has been shut up:

        >>> logging.getLogger('ZODB.lock_file').disabled
        True

    We better clean up logging before we leave:

        >>> logging.getLogger('ZODB.lock_file').disabled = False
        >>> for logger in [logger1, logger2]:
        ...     del logger.handlers[:]
        ...     logger1.propagate = True
        ...     logger1.disabled = False
        ...     logger1.setLevel(0)

        >>> from zope.app.testing import setup
        >>> setup.placelessTearDown()

    """


def doctest_bootstrapSchoolBell():
    r"""Tests for bootstrapSchoolBell()

    Normally, bootstrapSchoolBell is called when Zope 3 is fully configured

        >>> from schoolbell.app.main import configure
        >>> configure()

    When we start with an empty database, bootstrapSchoolBell creates a
    SchoolBell application in it.

        >>> import transaction
        >>> from ZODB.DB import DB
        >>> from ZODB.MappingStorage import MappingStorage
        >>> db = DB(MappingStorage())

        >>> from schoolbell.app.main import bootstrapSchoolBell
        >>> bootstrapSchoolBell(db)

    Let's take a look...

        >>> connection = db.open()
        >>> root = connection.root()
        >>> from zope.app.publication.zopepublication import ZopePublication
        >>> app = root.get(ZopePublication.root_name)
        >>> app
        <schoolbell.app.app.SchoolBellApplication object at ...>

    This new application object is the containment root

        >>> from zope.app.traversing.interfaces import IContainmentRoot
        >>> IContainmentRoot.providedBy(app)
        True

    It is also a site

        >>> from zope.app.component.interfaces import ISite
        >>> ISite.providedBy(app)
        True

    It has a local authentication utility

        >>> from zope.app import zapi
        >>> from zope.app.security.interfaces import IAuthentication
        >>> zapi.getUtility(IAuthentication, context=app)
        <schoolbell.app.security.SchoolBellAuthenticationUtility object at ...>

    It has an initial user (username 'manager', password 'schoolbell')

        >>> manager = app['persons']['manager']
        >>> manager.checkPassword('schoolbell')
        True

    This user has a grant for zope.Manager role

        >>> from zope.app.securitypolicy.interfaces import \
        ...     IPrincipalRoleManager
        >>> grants = IPrincipalRoleManager(app)
        >>> grants.getRolesForPrincipal('sb.person.manager')
        [('zope.Manager', PermissionSetting: Allow)]

    All users have a 'schoolbell.view' permission:

        >>> from zope.app.securitypolicy.interfaces import \
        ...     IPrincipalPermissionMap
        >>> grants = IPrincipalPermissionMap(app)
        >>> grants.getPermissionsForPrincipal('zope.Authenticated')
        [('schoolbell.view', PermissionSetting: Allow)]

    bootstrapSchoolBell doesn't do anything if it finds the root object already
    present in the database.

        >>> from schoolbell.app.app import Person
        >>> manager = app['persons']['user1'] = Person('user1')
        >>> transaction.commit()
        >>> connection.close()

        >>> bootstrapSchoolBell(db)

        >>> connection = db.open()
        >>> root = connection.root()
        >>> 'user1' in root[ZopePublication.root_name]['persons']
        True

    However it fails if the application root is not a schoolbell application

        >>> root[ZopePublication.root_name] = 'the object is strange'
        >>> transaction.commit()
        >>> connection.close()

        >>> bootstrapSchoolBell(db)
        Traceback (most recent call last):
          ...
        IncompatibleDatabase: incompatible database

    It also checks for the presence of an old data.

        >>> connection = db.open()
        >>> root = connection.root()
        >>> del root[ZopePublication.root_name]
        >>> root['schooltool'] = object()
        >>> transaction.commit()
        >>> connection.close()

        >>> bootstrapSchoolBell(db)
        Traceback (most recent call last):
          ...
        OldDatabase: old database

    Clean up

        >>> transaction.abort()
        >>> connection.close()

        >>> from zope.app.testing import setup
        >>> setup.placelessTearDown()

    """


def test_setUpLogger():
    r"""Tests for setUpLogger.

    setUpLogger sets up a logger:

        >>> import logging
        >>> from schoolbell.app.main import setUpLogger
        >>> setUpLogger('schoolbell.just_testing',
        ...             ['STDERR', '_just_testing.log'],
        ...             '%(asctime)s %(message)s')

        >>> logger = logging.getLogger('schoolbell.just_testing')
        >>> logger.propagate
        False
        >>> logger.handlers
        [<logging.StreamHandler instance ...>, <...UnicodeFileHandler ...>]
        >>> logger.handlers[0].stream
        <open file '<stderr>', mode 'w' at 0x...>
        >>> logger.handlers[0].formatter
        <logging.Formatter instance at ...>
        >>> logger.handlers[0].formatter._fmt
        '%(asctime)s %(message)s'

    Let's clean up after ourselves (logging is messy):

        >>> logger.handlers[1].close()
        >>> del logger.handlers[:]
        >>> logger.propagate = True
        >>> logger.disabled = False
        >>> logger.setLevel(0)

        >>> import os
        >>> os.unlink('_just_testing.log')

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schoolbell.app.main',
                                     optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
