#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Schooltool HTTP server.

$Id$
"""

import os
import sys
import getopt
import libxml2
import logging

import ZConfig
from zope.interface import moduleProvides
from transaction import get_transaction
from twisted.internet import reactor
from twisted.python import threadable
import twisted.python.runtime

from schooltool.app import Application, ApplicationObjectContainer
from schooltool import model, absence
from schooltool.component import getView, traverse
from schooltool.membership import Membership
from schooltool.eventlog import EventLogUtility
from schooltool.interfaces import IEvent, IAttendanceEvent, IModuleSetup
from schooltool.interfaces import AuthenticationError
from schooltool.common import StreamWrapper, UnicodeAwareException
from schooltool.translation import ugettext as _
from schooltool.browser.app import RootView
from schooltool.http import Site


__metaclass__ = type


moduleProvides(IModuleSetup)


#
# Misc
#

def profile(fn, extension='prof'):
    """Profiling hook.

    To profile a function call, wrap it in a call to this function.
    For example, to profile
      self.foo(bar, baz)
    write
      profile(lambda: self.foo(bar, baz))

    The 'extension' argument gives the extension of the filename to use for
    saving the profiling data.
    """
    import hotshot, random, time
    filename = '%s_%03d' % (time.strftime('%DT%T'), random.randint(0, 1000))
    filename = filename.replace('/', '-').replace(':', '-')
    prof = hotshot.Profile('%s.%s' % (filename, extension))
    result = []

    def doit():
        result.append(fn())

    prof.runcall(doit)
    prof.close()
    return result[0]


#
# Main loop
#

no_storage_error_msg = _("""\
No storage defined in the configuration file.  Unable to start the server.

If you're using the default configuration file, please edit it now and
uncomment one of the ZODB storage sections.""")

usage_msg = _("""\
Usage: %s [options]
Options:

  -c, --config xxx  use this configuration file instead of the default
  -h, --help        show this help message
  -d, --daemon      go to background after starting""")


class ConfigurationError(UnicodeAwareException):
    pass


class SchoolToolError(UnicodeAwareException):
    pass


class Server:
    """SchoolTool HTTP server."""

    threadable_hook = threadable
    reactor_hook = reactor

    def __init__(self, stdout=sys.stdout, stderr=sys.stderr):
        self.stdout = StreamWrapper(stdout)
        self.stderr = StreamWrapper(stderr)
        self.get_transaction_hook = get_transaction
        self.logger = logging.getLogger('schooltool.server')

    def main(self, args):
        """Start the SchoolTool HTTP server.

        args contains command line arguments, usually it is sys.argv[1:].

        Returns zero on normal exit, nonzero on error.  Return value should
        be passed to sys.exit.
        """
        try:
            self.configure(args)
            self.run()
        except ConfigurationError, e:
            print >> self.stderr, u"schooltool: %s" % unicode(e)
            print >> self.stderr, _("run schooltool -h for help")
            return 1
        except SchoolToolError, e:
            print >> self.stderr, unicode(e)
            return 1
        except SystemExit, e:
            return e.args[0]
        else:
            return 0

    def configure(self, args):
        """Process command line arguments and configuration files.

        This is called automatically from run.

        The following attributes define server configuration and are set by
        this method:
          appname       name of the application instance in ZODB
          viewFactory   root view class
          appFactory    application object factory
          config_file   file name of the config file
          config        configuration loaded from a config file, contains the
                        following attributes (see schema.xml for the definitive
                        list):
                            thread_pool_size
                            listen
                            database
                            event_logging
                            pid_file
                            error_log_file
                            access_log_file
                            app_log_file
        """
        # Defaults
        config_file = self.findDefaultConfigFile()
        self.appname = 'schooltool'
        self.viewFactory = getView
        self.appFactory = self.createApplication
        self.daemon = False

        # Process command line arguments
        try:
            opts, args = getopt.getopt(args, 'c:hmd',
                                       ['config=', 'help', 'daemon'])
        except getopt.error, e:
            raise ConfigurationError(str(e))

        for k, v in opts:
            if k in ('-h', '--help'):
                self.help()
                raise SystemExit(0)

        if args:
            raise ConfigurationError(_("too many arguments"))

        # Read configuration file
        for k, v in opts:
            if k in ('-c', '--config'):
                config_file = v
        self.config_file = config_file
        self.config = self.loadConfig(config_file)

        db_configuration = self.config.database
        if db_configuration.config.storage is None:
            self.noStorage()
            raise SystemExit(1)

        # Insert the metadefault for 'modules'
        self.config.module.insert(0, 'schooltool.main')

        # Set up logging
        self.setUpLogger('schooltool.server', self.config.error_log_file,
                         "%(asctime)s %(message)s")
        self.setUpLogger('schooltool.error', self.config.error_log_file,
                         "--\n%(asctime)s\n%(message)s")
        self.setUpLogger('schooltool.access', self.config.access_log_file)
        self.setUpLogger('schooltool.app', self.config.app_log_file,
                         "%(asctime)s %(levelname)s %(message)s")

        # Shut up ZODB lock_file, because it logs tracebacks when unable
        # to lock the database file, and we don't want that.
        logging.getLogger('ZODB.lock_file').disabled = True

        # ZODB and libxml2 should have a way to complain in case of trouble
        for logger_name in ['ZODB', 'txn', 'libxml2']:
            self.setUpLogger(logger_name, self.config.error_log_file,
                             "%(asctime)s [%(name)s] %(message)s")

        # Process any command line arguments that may override config file
        # settings here.

        for k, v in opts:
            if k in ('-d', '--daemon'):
                if twisted.python.runtime.platformType == 'posix':
                    self.daemon = True
                else:
                    sys.exit(_("Daemon mode is not supported on your"
                               " operating system"))

    def setUpLogger(self, name, filenames, format=None):
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
                handler = logging.StreamHandler(self.stdout)
            elif filename == 'STDERR':
                handler = logging.StreamHandler(self.stderr)
            else:
                handler = UnicodeFileHandler(filename)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    def help(self):
        """Print a help message."""
        progname = os.path.basename(sys.argv[0])
        print >> self.stdout, usage_msg % progname

    def noStorage(self):
        """Print an informative message when the config file does not define a
        storage."""
        print >> self.stderr, no_storage_error_msg

    def findDefaultConfigFile(self):
        """Return the default config file pathname.

        Looks for a file called 'schooltool.conf' in the directory two levels
        above the location of this module.  In the extracted source archive
        this will be the project root.
        """
        dirname = os.path.dirname(__file__)
        dirname = os.path.normpath(os.path.join(dirname, '..', '..'))
        config_file = os.path.join(dirname, 'schooltool.conf')
        if not os.path.exists(config_file):
            config_file = os.path.join(dirname, 'schooltool.conf.in')
        return config_file

    def loadConfig(self, config_file):
        """Load configuration from a given config file."""
        dirname = os.path.dirname(__file__)
        schema = ZConfig.loadSchema(os.path.join(dirname, 'schema.xml'))
        self.notifyConfigFile(config_file)
        config, handler = ZConfig.loadConfig(schema, config_file)
        return config

    def run(self):
        """Start the HTTP server.

        Must be called after configure.
        """
        # Add directories to the pythonpath
        path = self.config.path[:]
        path.reverse()
        for dir in path:
            sys.path.insert(0, dir)

        setUpModules(self.config.module)

        # Log libxml2 complaints
        libxml2.registerErrorHandler(
                lambda logger, error: logger.error(error.strip()),
                logging.getLogger('libxml2'))

        # This must be called here because we use threads
        libxml2.initParser()

        db_configuration = self.config.database
        try:
            self.db = db_configuration.open()
        except IOError, e:
            msg = _("Could not initialize the database:\n  ") + unicode(e)
            if e[0] == 11: # Resource temporarily unavailable
                msg += "\n"
                msg += _("Perhaps another SchoolTool instance is using it?")
            raise SchoolToolError(msg)
        self.prepareDatabase()

        self.threadable_hook.init()

        site = Site(self.db, self.appname, self.viewFactory, self.authenticate,
                    self.getApplicationLogPath())
        for interface, port in self.config.listen:
            self.reactor_hook.listenTCP(port, site, interface=interface)
            self.notifyServerStarted(interface, port)

        site = Site(self.db, self.appname, RootView, self.authenticate,
                    self.getApplicationLogPath())
        for interface, port in self.config.web:
            self.reactor_hook.listenTCP(port, site, interface=interface)
            self.notifyWebServerStarted(interface, port)

        if self.daemon:
            self.daemonize()

        if self.config.pid_file:
            pidfile = file(self.config.pid_file, "w")
            print >> pidfile, os.getpid()
            pidfile.close()

        # Call suggestThreadPoolSize at the last possible moment, because it
        # will create a number of non-daemon threads and will prevent the
        # application from exitting on errors.
        self.reactor_hook.suggestThreadPoolSize(self.config.thread_pool_size)
        self.reactor_hook.run()

        # Cleanup on signals TERM, INT and BREAK
        self.notifyShutdown()
        if self.config.pid_file:
            os.unlink(self.config.pid_file)

    def daemonize(self):
        """Daemonize with a double fork and close the standard IO."""
        pid = os.fork()
        if pid:
            sys.exit(0)
        os.setsid()
        os.umask(077)

        pid = os.fork()
        if pid:
            self.notifyDaemonized(pid)
            sys.exit(0)

        os.close(0)
        os.close(1)
        os.close(2)
        os.open('/dev/null', os.O_RDWR)
        os.dup(0)
        os.dup(0)

    def prepareDatabase(self):
        """Prepare the database.

        Makes sure the database has an application instance.

        Creates the application if necessary.

        This is the place to perform object schema upgrades, if necessary.
        """
        conn = self.db.open()
        root = conn.root()

        # Create the application if it does not yet exist
        if root.get(self.appname) is None:
            root[self.appname] = self.appFactory()
            self.get_transaction_hook().commit()
        app = root[self.appname]

        # Enable or disable global event logging
        eventlog = app.utilityService['eventlog']
        eventlog.enabled = self.config.event_logging
        self.get_transaction_hook().commit()

        conn.close()

    def createApplication():
        """Instantiate a new application."""
        app = Application()

        event_log = EventLogUtility()
        app.utilityService['eventlog'] = event_log
        app.eventService.subscribe(event_log, IEvent)

        absence_tracker = absence.AbsenceTrackerUtility()
        app.utilityService['absences'] = absence_tracker
        app.eventService.subscribe(absence_tracker, IAttendanceEvent)

        app['groups'] = ApplicationObjectContainer(model.Group)
        app['persons'] = ApplicationObjectContainer(model.Person)
        app['resources'] = ApplicationObjectContainer(model.Resource)
        Person = app['persons'].new
        Group = app['groups'].new

        root = Group("root", title=_("Root Group"))
        app.addRoot(root)

        managers = Group("managers", title=_("System Managers"))
        manager = Person("manager", title=_("Manager"))
        manager.setPassword('schooltool')
        Membership(group=managers, member=manager)
        Membership(group=root, member=managers)

        return app

    createApplication = staticmethod(createApplication)

    def authenticate(context, username, password):
        """See IAuthenticator."""
        try:
            persons = traverse(context, '/persons')
        except (TypeError, KeyError):
            # Perhaps log somewhere that authentication is not possible in
            # this context, otherwise it might be hard to debug
            raise AuthenticationError(_("Invalid login"))
        try:
            person = persons[username]
        except KeyError:
            pass
        else:
            if person.checkPassword(password):
                return person
        raise AuthenticationError(_("Invalid login"))

    authenticate = staticmethod(authenticate)

    def notifyConfigFile(self, config_file):
        self.logger.info(_("Reading configuration from %s"), config_file)

    def notifyServerStarted(self, network_interface, port):
        self.logger.info(_("Started HTTP server for RESTive API on %s:%s"),
                         network_interface or "*", port)

    def notifyWebServerStarted(self, network_interface, port):
        self.logger.info(_("Started HTTP server for web UI on %s:%s"),
                         network_interface or "*", port)

    def notifyDaemonized(self, pid):
        self.logger.info(_("Going to background, daemon pid %d"), pid)

    def notifyShutdown(self):
        self.logger.info(_("Shutting down"))

    def getApplicationLogPath(self):
        for name in self.config.app_log_file:
            if name not in ('STDOUT', 'STDERR'):
                return name
        return None


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


def setUpModules(module_names):
    """Set up the modules named in the given list."""
    for name in module_names:
        assert isinstance(name, basestring)
        module = __import__(name)
        components = name.split('.')
        for component in components[1:]:
            module = getattr(module, component)
        if IModuleSetup.providedBy(module):
            module.setUp()
        else:
            raise TypeError('Cannot set up module because it does not'
                            ' provide IModuleSetup', module)


def setUp():
    """Set up the SchoolTool application."""
    setUpModules([
        'schooltool.relationship',
        'schooltool.membership',
        'schooltool.absence',
        'schooltool.rest',
        'schooltool.eventlog',
        'schooltool.uris',
        'schooltool.teaching',
        'schooltool.timetable',
        ])


def main():
    """Start the SchoolTool HTTP server."""
    sys.exit(Server().main(sys.argv[1:]))


if __name__ == '__main__':
    main()
