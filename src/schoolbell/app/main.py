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
Main SchoolBell script.

This module is not necessary if you use SchoolBell as a Zope 3 content object.
It is only used by the standalone SchoolBell executable.
"""

import os
import sys
import time
import getopt
import locale
import logging
import errno

import ZConfig
import transaction
import zope.app.component.hooks
from zope.interface import directlyProvides
from zope.event import notify
from zope.configuration import xmlconfig
from zope.server.taskthreads import ThreadedTaskDispatcher
from zope.app.server.main import run
from zope.app.server.http import http
from zope.app.appsetup import DatabaseOpened, ProcessStarting
from zope.app.publication.zopepublication import ZopePublication
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.component.site import LocalSiteManager
from zope.app.securitypolicy.interfaces import IPrincipalRoleManager
from zope.app.container.contained import ObjectAddedEvent

from schoolbell.app.app import SchoolBellApplication, Person
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.security import setUpLocalAuth


ZCONFIG_SCHEMA = os.path.join(os.path.dirname(__file__), 'config-schema.xml')


locale_charset = locale.getpreferredencoding()


usage_message = """
Usage: %s [options]
Options:
  -c, --config xxx  use this configuration file instead of the default
  -h, --help        show this help message
  -d, --daemon      go to background after starting
""".strip()


no_storage_error_msg = """
No storage defined in the configuration file.

If you're using the default configuration file, please edit it now and
uncomment one of the ZODB storage sections.
""".strip()


incompatible_db_error_msg = """
This is not a SchoolBell 1.0 database file, aborting.
""".strip()


old_db_error_msg = """
This is not a SchoolBell 1.0 database file, aborting.

Please run the standalone database upgrade script.
""".strip()


class OldDatabase(Exception):
    pass


class IncompatibleDatabase(Exception):
    pass


class Options(object):
    """SchoolBell process options."""

    config_file = 'schoolbell.conf'
    daemon = False
    quiet = False
    config = None

    def __init__(self):
        dirname = os.path.dirname(__file__)
        dirname = os.path.normpath(os.path.join(dirname, '..', '..', '..'))
        self.config_file = os.path.join(dirname, 'schoolbell.conf')
        if not os.path.exists(self.config_file):
            self.config_file = os.path.join(dirname, 'schoolbell.conf.in')


def main(argv=sys.argv):
    """Start the SchoolBell server."""
    t0, c0 = time.time(), time.clock()
    options = load_options(argv)
    setup(options)
    t1, c1 = time.time(), time.clock()
    print "Startup time: %.3f sec real, %.3f sec CPU" % (t1-t0, c1-c0)
    run()
    if options.config.pid_file:
        os.unlink(options.config.pid_file)


def load_options(argv):
    """Parse the command line and read the configuration file."""
    options = Options()

    # Parse command line
    progname = os.path.basename(argv[0])
    try:
        opts, args = getopt.gnu_getopt(argv[1:], 'c:hd',
                                       ['config=', 'help', 'daemon'])
    except getopt.error, e:
        print >> sys.stderr, "%s: %s" % (progname, e)
        print >> sys.stderr, "Run %s -h for help." % progname
        sys.exit(1)
    for k, v in opts:
        if k in ('-h', '--help'):
            print usage_message % progname
            sys.exit(0)
        if k in ('-c', '--config'):
            options.config_file = v
        if k in ('-d', '--daemon'):
            if not hasattr(os, 'fork'):
                print >> sys.stderr, ("%s: daemon mode not supported on your"
                                      " operating system.")
                sys.exit(1)
            else:
                options.daemon = True

    # Read configuration file
    schema = ZConfig.loadSchema(ZCONFIG_SCHEMA)
    print "Reading configuration from %s" % options.config_file
    try:
        options.config, handler = ZConfig.loadConfig(schema,
                                                     options.config_file)
    except ZConfig.ConfigurationError, e:
        print >> sys.stderr, "%s: %s" % (progname, e)
        sys.exit(1)
    if options.config.database.config.storage is None:
        print >> sys.stderr, "%s: %s" % (progname, no_storage_error_msg)
        sys.exit(1)

    # Complain about obsolete options.  This section should be removed
    # in later SchoolBell versions.
    deprecated = ['module', 'test_mode', 'domain', 'lang',
                  'path', 'app_log_file']
    for setting in deprecated:
        if getattr(options.config, setting):
            print >> sys.stderr, ("%s: warning: ignored configuration option"
                                  " '%s'" % (progname, setting))
    return options


def setup(options):
    """Configure SchoolBell."""
    setUpLogger(None, options.config.error_log_file,
                "%(asctime)s %(message)s")
    setUpLogger('accesslog', options.config.web_access_log_file)

    # Shut up ZODB lock_file, because it logs tracebacks when unable
    # to lock the database file, and we don't want that.
    logging.getLogger('ZODB.lock_file').disabled = True

    # Process ZCML
    configure()

    # Open the database
    db_configuration = options.config.database
    try:
       db = db_configuration.open()
    except IOError, e:
        print >> sys.stderr, ("Could not initialize the database:\n%s" % (e, ))
        if e.errno == errno.EAGAIN: # Resource temporarily unavailable
            print >> sys.stderr, ("\nPerhaps another SchoolBell instance"
                                  " is using it?")
        sys.exit(1)

    try:
        bootstrapSchoolBell(db)
    except IncompatibleDatabase:
        print >> sys.stderr, incompatible_db_error_msg
        sys.exit(1)
    except OldDatabase:
        print >> sys.stderr, old_db_error_msg
        sys.exit(1)

    notify(DatabaseOpened(db))

    if options.daemon:
        daemonize()

    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(options.config.thread_pool_size)

    for ip, port in options.config.web:
        http.create('HTTP', task_dispatcher, db, port=port, ip=ip)

    notify(ProcessStarting())

    if options.config.pid_file:
        pidfile = file(options.config.pid_file, "w")
        print >> pidfile, os.getpid()
        pidfile.close()

    return db


class StreamWrapper(object):
    r"""Unicode-friendly wrapper for writable file-like objects.

    Here the terms 'encoding' and 'charset' are used interchangeably.

    The main use case for StreamWrapper is wrapping sys.stdout and sys.stderr
    so that you can forget worrying about charsets of your data.

        >>> from StringIO import StringIO
        >>> import schoolbell.app.main
        >>> old_locale_charset = schoolbell.app.main.locale_charset
        >>> schoolbell.app.main.locale_charset = 'UTF-8'

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! \xc2\xb7\xe2\x98\xbb\xc2\xb7\n'

    By default printing Unicode strings to stdout/stderr will raise Unicode
    errors if the stream encoding does not include some characters you are
    printing.  StreamWrapper will replace unconvertable characters to question
    marks, therefore you should only use it for informative messages where such
    loss of information is acceptable.

        >>> schoolbell.app.main.locale_charset = 'US-ASCII'
        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! ???\n'

    StreamWrapper converts all unicode strings that are written to it to the
    encoding defined in the wrapped stream's 'encoding' attribute, or, if that
    is None, to the locale encoding.  Typically the stream's encoding attribute
    is set when the stream is connected to a console device, and None when the
    stream is connected to a file.  On Unix systems the console encoding
    matches the locale charset, but on Win32 systems they differ.

        >>> s = StringIO()
        >>> s.encoding = 'ISO-8859-1'
        >>> sw = StreamWrapper(s)
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! \xb7?\xb7\n'

    You can print other kinds of objects:

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, 1, 2,
        >>> print >> sw, 3
        >>> sw.stm.getvalue()
        '1 2 3\n'

    but not 8-bit strings:

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, "\xff"
        Traceback (most recent call last):
          ...
        UnicodeDecodeError: 'ascii' codec can't decode byte 0xff in position 0: ordinal not in range(128)

    In addition to 'write', StreamWrapper provides 'flush' and 'writelines'

        >>> sw = StreamWrapper(StringIO())
        >>> sw.write('xyzzy\n')
        >>> sw.flush()
        >>> sw.writelines(['a', 'b', 'c', 'd'])
        >>> sw.stm.getvalue()
        'xyzzy\nabcd'

    Clean up:

        >>> schoolbell.app.main.locale_charset = old_locale_charset

    """

    def __init__(self, stm):
        self.stm = stm
        self.encoding = getattr(stm, 'encoding', None)
        if self.encoding is None:
            self.encoding = locale_charset

    def write(self, obj):
        self.stm.write(obj.encode(self.encoding, 'replace'))

    def flush(self):
        self.stm.flush()

    def writelines(self, seq):
        for obj in seq:
            self.write(obj)

    def close(self):
        self.stm.close()


class UnicodeFileHandler(logging.StreamHandler):
    """A handler class which writes records to disk files.

    This class differs from logging.FileHandler in that it can handle Unicode
    strings with graceful degradation.
    """

    def __init__(self, filename):
        stm = StreamWrapper(open(filename, 'a'))
        logging.StreamHandler.__init__(self, stm)

    def close(self):
        self.stream.close()


def setUpLogger(name, filenames, format=None):
    """Set up a named logger.

    Sets up a named logger to log into filenames with the given format.
    Two filenames are special: 'STDOUT' means sys.stdout and 'STDERR'
    means sys.stderr.
    """
    formatter = logging.Formatter(format)
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.INFO)
    for filename in filenames:
        if filename == 'STDOUT':
            handler = logging.StreamHandler(sys.stdout)
        elif filename == 'STDERR':
            handler = logging.StreamHandler(sys.stderr)
        else:
            handler = UnicodeFileHandler(filename)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def daemonize():
    """Daemonize with a double fork and close the standard IO."""
    pid = os.fork()
    if pid:
        sys.exit(0)
    os.setsid()
    os.umask(077)

    pid = os.fork()
    if pid:
        print "Going to background, daemon pid %d" % pid
        sys.exit(0)

    os.close(0)
    os.close(1)
    os.close(2)
    os.open('/dev/null', os.O_RDWR)
    os.dup(0)
    os.dup(0)


def bootstrapSchoolBell(db):
    """Bootstrap SchoolBell database."""
    connection = db.open()
    root = connection.root()
    if root.get('schooltool'):
        transaction.abort()
        connection.close()
        raise OldDatabase('old database')
    app_obj = root.get(ZopePublication.root_name)
    if app_obj is None:
        app = SchoolBellApplication()
        directlyProvides(app, IContainmentRoot)
        root[ZopePublication.root_name] = app
        notify(ObjectAddedEvent(app))
        manager = Person('manager', 'SchoolBell Manager')
        manager.setPassword('schoolbell')
        app['persons']['manager'] = manager
        IPrincipalRoleManager(app).assignRoleToPrincipal('zope.Manager',
                                                         'sb.person.manager')
    elif not ISchoolBellApplication.providedBy(app_obj):
        transaction.abort()
        connection.close()
        raise IncompatibleDatabase('incompatible database')
    transaction.commit()
    connection.close()


def configure():
    """Configure Zope 3 components."""
    # Hook up custom component architecture calls
    zope.app.component.hooks.setHooks()
    context = xmlconfig.string(SITE_DEFINITION)


SITE_DEFINITION = """
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:browser="http://namespaces.zope.org/browser">

  <include package="zope.app" />
  <include package="zope.app.securitypolicy" file="meta.zcml" />

  <include package="zope.app.session" />
  <include package="zope.app.server" />

  <!-- Workaround to shut down a DeprecationWarning that appears because we do
       not include zope.app.onlinehelp and the rotterdam skin tries to look for
       this menu -->
  <browser:menu id="help_actions" />

  <include package="schoolbell.app" />

  <include package="zope.app.securitypolicy" />

  <unauthenticatedPrincipal id="zope.anybody" title="Unauthenticated User" />
  <unauthenticatedGroup id="zope.Anybody" title="Unauthenticated Users" />
  <authenticatedGroup id="zope.Authenticated" title="Authenticated Users" />
  <everybodyGroup id="zope.Everybody" title="All Users" />

</configure>
"""


if __name__ == '__main__':
    main()
