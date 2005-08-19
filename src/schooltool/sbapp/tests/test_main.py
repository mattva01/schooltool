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
Unit tests for schooltool.sbapp.main.

$Id$
"""
import os
import sys
import unittest
from zope.testing import doctest
from zope.app import zapi
from zope.interface.verify import verifyObject


def doctest_Options():
    """Tests for Options.

    The only interesting thing Options does is find the default configuration
    file.

        >>> from schooltool.sbapp.main import Options
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

        >>> from schooltool.sbapp.main import Options
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
        >>> from schooltool.app import main
        >>> from schooltool.sbapp.main import StandaloneServer
        >>> server = StandaloneServer()
        >>> old_run = main.run
        >>> server.load_options = load_options_stub
        >>> server.setup = setup_stub
        >>> main.run = run_stub

    Now we will run main().

        >>> server.main(['sb.py', '-d'])
        Performing setup...
        Startup time: ... sec real, ... sec CPU
        Running...

    Clean up

        >>> main.run = old_run

    """


def doctest_load_options():
    """Tests for load_options().

    We will use a sample configuration file that comes with these tests.

        >>> from schooltool.sbapp import tests
        >>> test_dir = os.path.dirname(tests.__file__)
        >>> sample_config_file = os.path.join(test_dir, 'sample.conf')
        >>> empty_config_file = os.path.join(test_dir, 'empty.conf')

    load_options will report errors to stderr.  We need to temporarily
    redirect stderr to stdout, because otherwise doctests will not see the
    output.

        >>> old_stderr = sys.stderr
        >>> sys.stderr = sys.stdout

    Load options parses command line arguments and the configuration file.
    Warnings about obsolete options are shown.

        >>> from schooltool.sbapp.main import StandaloneServer
        >>> server = StandaloneServer()
        >>> o = server.load_options(['sb.py', '-c', sample_config_file, '-r'])
        Reading configuration from ...sample.conf

    Some options come from the command line

        >>> o.config_file
        '...sample.conf'
        >>> o.daemon
        False
        >>> o.restore_manager
        True

    Some come from the config file

        >>> o.config.web in ([('', 48080)],          # Unix
        ...                  [('localhost', 48080)]) # Windows
        True
        >>> o.config.rest in ([('', 47001)],          # Unix
        ...                  [('localhost', 47001)])  # Windows
        True
        >>> o.config.listen
        [('...', 123), ('10.20.30.40', 9999)]

    Note that "listen 123" in config.py produces ('localhost', 123) on
    Windows, but ('', 123) on other platforms.

    The developer mode can also be turned on via the configuration file:  

        >>> o.config.devmode
        True

    `load_options` can also give you a nice help message and exit with status
    code 0.

        >>> try:
        ...     o = server.load_options(['sb.py', '-h'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Usage: sb.py [options]
        Options:
          -c, --config xxx       use this configuration file instead of the default
          -h, --help             show this help message
          -d, --daemon           go to background after starting
          -r, --restore-manager  restore the manager user with the default password
        [exited with status 0]

    Here's what happens, when you use an unknown command line option.

        >>> try:
        ...     o = server.load_options(['sb.py', '-q'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        sb.py: option -q not recognized
        Run sb.py -h for help.
        [exited with status 1]

    Here's what happens when the configuration file cannot be found

        >>> try:
        ...     o = server.load_options(['sb.py', '-c', 'nosuchfile'])
        ... except SystemExit, e:
        ...     print '[exited with status %s]' % e
        Reading configuration from nosuchfile
        sb.py: error opening file ...nosuchfile: ...
        [exited with status 1]

    Here's what happens if you do not specify a storage section in the
    configuration file.

        >>> try:
        ...     o = server.load_options(['sb.py', '-c', empty_config_file])
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

        >>> from schooltool.sbapp.main import Options, StandaloneServer
        >>> from ZODB.MappingStorage import MappingStorage
        >>> from ZODB.DB import DB
        >>> options = Options()
        >>> class DatabaseConfigStub:
        ...     def open(self):
        ...         return DB(MappingStorage())
        >>> class ConfigStub:
        ...     web = []
        ...     rest = []
        ...     listen = []
        ...     thread_pool_size = 1
        ...     database = DatabaseConfigStub()
        ...     pid_file = ''
        ...     path = []
        ...     error_log_file = ['STDERR']
        ...     web_access_log_file = ['STDOUT']
        ...     lang = 'lt'
        ...     reportlab_fontdir = ''
        ...     devmode = True
        >>> options.config = ConfigStub()

    Workaround to fix a Windows failure:

        >>> import logging
        >>> del logging.getLogger(None).handlers[:]

    And go!

        >>> server = StandaloneServer()
        >>> server.setup(options)
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

    A custom language adapter has been installed:

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
        ...     logger1.propagate = True
        ...     logger1.disabled = False
        ...     logger1.setLevel(0)

        >>> from zope.app.testing import setup
        >>> setup.placelessTearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
