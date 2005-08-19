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
Main SchoolTool script.

This module is not necessary if you use SchoolTool as a Zope 3 content object.
It is only used by the standalone SchoolTool executable.

$Id$
"""
import os
import sys
import time
import getopt
import locale
import gettext
import logging
import errno

import ZConfig
import transaction
import zope.app.component.hooks
import zope.configuration.config
import zope.configuration.xmlconfig
from zope.interface import directlyProvides, implements
from zope.component import provideAdapter, adapts
from zope.event import notify
from zope.server.taskthreads import ThreadedTaskDispatcher
from zope.publisher.interfaces.http import IHTTPRequest
from zope.i18n.interfaces import IUserPreferredLanguages
from zope.app.server.main import run
from zope.app.server.http import http
from zope.app.appsetup import DatabaseOpened, ProcessStarting
from zope.app.publication.zopepublication import ZopePublication
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.component.site import LocalSiteManager
from zope.app.securitypolicy.interfaces import IPrincipalRoleManager
from zope.app.container.contained import ObjectAddedEvent

from schooltool.app.app import SchoolToolApplication
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.person.person import Person
from schooltool.app.security import setUpLocalAuth
from schooltool.app.rest import restServerType
from schooltool.app.browser import pdfcal


locale_charset = locale.getpreferredencoding()

localedir = os.path.join(os.path.dirname(__file__), '..', 'locales')
catalog = gettext.translation('schooltool', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us).encode(locale_charset, 'replace')

st_usage_message = _("""
Usage: %s [options]
Options:
  -c, --config xxx       use this configuration file instead of the default
  -h, --help             show this help message
  -d, --daemon           go to background after starting
  -r, --restore-manager  restore the manager user with the default password
""").strip()


st_no_storage_error_msg = _("""
No storage defined in the configuration file.

If you're using the default configuration file, please edit it now and
uncomment one of the ZODB storage sections.
""").strip()


st_incompatible_db_error_msg = _("""
This is not a SchoolTool 0.10 database file, aborting.
""").strip()


st_old_db_error_msg = _("""
This is not a SchoolTool 0.10 database file, aborting.

Please run the standalone database upgrade script.
""").strip()


class OldDatabase(Exception):
    pass


class IncompatibleDatabase(Exception):
    pass


def die(message, exitcode=1):
    print >> sys.stderr, message
    sys.exit(exitcode)


class Options(object):
    config_filename = 'schooltool.conf'
    daemon = False
    quiet = False
    config = None
    restore_manager = False

    def __init__(self):
        dirname = os.path.dirname(__file__)
        dirname = os.path.normpath(os.path.join(dirname, '..', '..', '..'))
        self.config_file = os.path.join(dirname, self.config_filename)
        if not os.path.exists(self.config_file):
            self.config_file = os.path.join(dirname,
                                            self.config_filename + '.in')

def setLanguage(lang):
    """Set the language for the user interface."""
    if lang == 'auto':
        return # language is negotiated at runtime through Accept-Language.

    class SinglePreferredLanguage(object):

        adapts(IHTTPRequest)
        implements(IUserPreferredLanguages)

        def __init__(self, context):
            pass

        def getPreferredLanguages(self):
            return (lang, )

    # Replace the default adapter with one that always asks for the language
    # specified in the configuration file.
    provideAdapter(SinglePreferredLanguage)


class StreamWrapper(object):
    r"""Unicode-friendly wrapper for writable file-like objects.

    Here the terms 'encoding' and 'charset' are used interchangeably.

    The main use case for StreamWrapper is wrapping sys.stdout and sys.stderr
    so that you can forget worrying about charsets of your data.

        >>> from StringIO import StringIO
        >>> import schooltool.app.main
        >>> old_locale_charset = schooltool.app.main.locale_charset
        >>> schooltool.app.main.locale_charset = 'UTF-8'

        >>> sw = StreamWrapper(StringIO())
        >>> print >> sw, u"Hello, world! \u00b7\u263b\u00b7"
        >>> sw.stm.getvalue()
        'Hello, world! \xc2\xb7\xe2\x98\xbb\xc2\xb7\n'

    By default printing Unicode strings to stdout/stderr will raise Unicode
    errors if the stream encoding does not include some characters you are
    printing.  StreamWrapper will replace unconvertable characters to question
    marks, therefore you should only use it for informative messages where such
    loss of information is acceptable.

        >>> schooltool.app.main.locale_charset = 'US-ASCII'
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

        >>> schooltool.app.main.locale_charset = old_locale_charset

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
        print _("Going to background, daemon pid %d" % pid)
        sys.exit(0)

    os.close(0)
    os.close(1)
    os.close(2)
    os.open('/dev/null', os.O_RDWR)
    os.dup(0)
    os.dup(0)


LOCALIZED_PRINCIPALS = u"""\
<?xml version="1.0" encoding="utf-8"?>
<configure xmlns="http://namespaces.zope.org/zope">

  <unauthenticatedPrincipal id="zope.anybody" title="%(unauth_user)s" />
  <unauthenticatedGroup id="zope.Anybody" title="%(unauth_users)s" />
  <authenticatedGroup id="zope.Authenticated" title="%(auth_users)s" />
  <everybodyGroup id="zope.Everybody" title="%(all_users)s" />

</configure>
""" % {'unauth_user': catalog.ugettext("Unauthenticated User"),
       'unauth_users': catalog.ugettext("Unauthenticated Users"),
       'auth_users': catalog.ugettext("Authenticated Users"),
       'all_users': catalog.ugettext("All Users")}

# Mark strings for i18n extractor
_("Unauthenticated User"), _("Unauthenticated Users")
_("Authenticated Users"), _("All Users")

LOCALIZED_PRINCIPALS = LOCALIZED_PRINCIPALS.encode('utf-8')


class StandaloneServer(object):

    ZCONFIG_SCHEMA = os.path.join(os.path.dirname(__file__),
                                  'config-schema.xml')

    LOCALIZED_PRINCIPALS = LOCALIZED_PRINCIPALS

    usage_message = st_usage_message
    no_storage_error_msg = st_no_storage_error_msg
    incompatible_db_error_msg = st_incompatible_db_error_msg
    old_db_error_msg = st_old_db_error_msg

    system_name = "SchoolTool"

    Options = Options

    devmode = False

    def configure(self):
        """Configure Zope 3 components."""
        # Hook up custom component architecture calls
        zope.app.component.hooks.setHooks()
        context = zope.configuration.config.ConfigurationMachine()
        if self.devmode:
            context.provideFeature('devmode')
        zope.configuration.xmlconfig.registerCommonDirectives(context)
        context = zope.configuration.xmlconfig.file(
            self.siteConfigFile, context=context)
        zope.configuration.xmlconfig.string(self.LOCALIZED_PRINCIPALS, context)

        # Store the configuration context
        from zope.app.appsetup import appsetup
        appsetup.__dict__['__config_context'] = context

    def load_options(self, argv):
        """Parse the command line and read the configuration file."""
        options = self.Options()

        # Parse command line
        progname = os.path.basename(argv[0])
        try:
            opts, args = getopt.gnu_getopt(argv[1:], 'c:hdr',
                                           ['config=', 'help', 'daemon',
                                            'restore-manager'])
        except getopt.error, e:
            print >> sys.stderr, _("%s: %s") % (progname, e)
            print >> sys.stderr, _("Run %s -h for help.") % progname
            sys.exit(1)
        for k, v in opts:
            if k in ('-h', '--help'):
                print self.usage_message % progname
                sys.exit(0)
            if k in ('-c', '--config'):
                options.config_file = v
            if k in ('-d', '--daemon'):
                if not hasattr(os, 'fork'):
                    print >> sys.stderr, _("%s: daemon mode not supported on"
                                           " your operating system.")
                    sys.exit(1)
                else:
                    options.daemon = True
            if k in ('-r', '--restore-manager'):
                options.restore_manager = True

        # Read configuration file
        schema = ZConfig.loadSchema(self.ZCONFIG_SCHEMA)
        print _("Reading configuration from %s") % options.config_file
        try:
            options.config, handler = ZConfig.loadConfig(schema,
                                                         options.config_file)
        except ZConfig.ConfigurationError, e:
            print >> sys.stderr, _("%s: %s") % (progname, e)
            sys.exit(1)
        if options.config.database.config.storage is None:
            print >> sys.stderr, _("%s: %s") % (progname,
                                                self.no_storage_error_msg)
            sys.exit(1)

        return options

    def bootstrapSchoolTool(self, db):
        """Bootstrap SchoolTool database."""
        connection = db.open()
        root = connection.root()
        if root.get('schooltool'):
            transaction.abort()
            connection.close()
            raise OldDatabase('old database')
        app_obj = root.get(ZopePublication.root_name)
        if app_obj is None:
            app = SchoolToolApplication()
            directlyProvides(app, IContainmentRoot)
            root[ZopePublication.root_name] = app
            notify(ObjectAddedEvent(app))
            self.restoreManagerUser(app)
        elif not ISchoolToolApplication.providedBy(app_obj):
            transaction.abort()
            connection.close()
            raise IncompatibleDatabase('incompatible database')
        transaction.commit()
        connection.close()

    def restoreManagerUser(self, app):
        """Ensure there is a manager user

        Create a user if needed, set password to default, grant
        manager permissions
        """
        _('%s Manager') # mark for l10n
        manager_title = catalog.ugettext('%s Manager') % self.system_name
        if 'manager' not in app['persons']:
            manager = Person('manager', manager_title)
            app['persons']['manager'] = manager
        manager = app['persons']['manager']
        manager.setPassword(self.system_name.lower())
        roles = IPrincipalRoleManager(app)
        roles.assignRoleToPrincipal('zope.Manager', 'sb.person.manager')

    def main(self, argv=sys.argv):
        """Start the SchoolTool server."""
        t0, c0 = time.time(), time.clock()
        options = self.load_options(argv)
        self.setup(options)
        t1, c1 = time.time(), time.clock()
        print _("Startup time: %.3f sec real, %.3f sec CPU") % (t1 - t0,
                                                                c1 - c0)
        run()
        if options.config.pid_file:
            os.unlink(options.config.pid_file)

    def setup(self, options):
        """Configure SchoolTool."""
        setUpLogger(None, options.config.error_log_file,
                    "%(asctime)s %(message)s")
        setUpLogger('accesslog', options.config.web_access_log_file)

        # Shut up ZODB lock_file, because it logs tracebacks when unable
        # to lock the database file, and we don't want that.
        logging.getLogger('ZODB.lock_file').disabled = True

        # Determine whether we are in developer's mode:
        self.devmode = options.config.devmode

        # Process ZCML
        self.siteConfigFile = options.config.site_definition
        self.configure()

        # Set language specified in the configuration
        setLanguage(options.config.lang)

        # Configure reportlab.
        self.configureReportlab(options.config.reportlab_fontdir)

        # Open the database
        db_configuration = options.config.database
        try:
           db = db_configuration.open()
        except IOError, e:
            print >> sys.stderr, _("Could not initialize the database:\n%s" %
                                   (e, ))
            if e.errno == errno.EAGAIN: # Resource temporarily unavailable
                print >> sys.stderr, _("\nPerhaps another %s instance"
                                       " is using it?" % self.system_name)
            sys.exit(1)

        try:
            self.bootstrapSchoolTool(db)
        except IncompatibleDatabase:
            print >> sys.stderr, self.incompatible_db_error_msg
            sys.exit(1)
        except OldDatabase:
            print >> sys.stderr, self.old_db_error_msg
            sys.exit(1)

        notify(DatabaseOpened(db))

        if options.restore_manager:
            connection = db.open()
            root = connection.root()
            app = root[ZopePublication.root_name]
            self.restoreManagerUser(app)
            transaction.commit()
            connection.close()

        if options.daemon:
            daemonize()

        task_dispatcher = ThreadedTaskDispatcher()
        task_dispatcher.setThreadCount(options.config.thread_pool_size)

        for ip, port in options.config.web:
            http.create('HTTP', task_dispatcher, db, port=port, ip=ip)

        for ip, port in options.config.rest:
            restServerType.create('REST', task_dispatcher, db,
                                  port=port, ip=ip)

        # TODO BBB: remove the folowing lines after a while.
        # respecting options.config.listen is depreciated and for
        # compatibility only.
        for ip, port in options.config.listen:
            restServerType.create('REST', task_dispatcher, db,
                                  port=port, ip=ip)

        notify(ProcessStarting())

        if options.config.pid_file:
            pidfile = file(options.config.pid_file, "w")
            print >> pidfile, os.getpid()
            pidfile.close()

        return db

    def configureReportlab(self, fontdir):
        """Configure reportlab given a path to TrueType fonts.

        Disables PDF support in SchoolTool if fontdir is empty.
        Outputs a warning to stderr in case of errors.
        """
        if not fontdir:
            return

        try:
            import reportlab
        except ImportError:
            print >> sys.stderr, _("Warning: could not find the reportlab"
                                   " library.\nPDF support disabled.")
            return

        if not os.path.isdir(fontdir):
            print >> sys.stderr, (_("Warning: font directory '%s' does"
                                    " not exist.\nPDF support disabled.")
                                  % fontdir)
            return

        for font_file in pdfcal.font_map.values():
            font_path = os.path.join(fontdir, font_file)
            if not os.path.exists(font_path):
                print >> sys.stderr, _("Warning: font '%s' does not exist.\n"
                                       "PDF support disabled.") % font_path
                return

        pdfcal.setUpMSTTCoreFonts(fontdir)


if __name__ == '__main__':
    StandaloneServer().main()
