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
import logging

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

from schoolbell.app.app import SchoolBellApplication, Person
from schoolbell.app.security import setUpLocalAuth


ZCONFIG_SCHEMA = os.path.join(os.path.dirname(__file__), 'schema.xml')


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
    deprecated = ['module', 'test_mode', 'domain', 'lang', 'path']
    for setting in deprecated:
        if getattr(options.config, setting):
            print >> sys.stderr, ("%s: warning: the `%s` option is"
                                  " obsolete." % (progname, setting))
    # TODO: log

    return options


def setup(options):
    """Configure SchoolBell."""
    # TODO: configure logging as the config file says
    logging.basicConfig()

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

    bootstrapSchoolBell(db)

    notify(DatabaseOpened(db))

    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(options.config.thread_pool_size)

    for ip, port in options.config.web:
        print "Started HTTP server for web UI on %s:%d" % (ip or "*", port)
        http.create('HTTP', task_dispatcher, db, port=port, ip=ip)

    notify(ProcessStarting())

    if options.daemon:
        daemonize()

    if options.config.pid_file:
        pidfile = file(options.config.pid_file, "w")
        print >> pidfile, os.getpid()
        pidfile.close()

    return db


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
    if not root.get(ZopePublication.root_name):
        app = SchoolBellApplication()
        directlyProvides(app, IContainmentRoot)
        root[ZopePublication.root_name] = app
        setUpLocalAuth(app)
        manager = Person('manager', 'SchoolBell Manager')
        manager.setPassword('schoolbell')
        app['persons']['manager'] = manager
        IPrincipalRoleManager(app).assignRoleToPrincipal('zope.Manager',
                                                         'sb.person.manager')
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
