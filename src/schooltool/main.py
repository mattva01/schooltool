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
import time
import urllib
import getopt
import libxml2
import logging
import ZConfig
from zope.interface import moduleProvides
from transaction import get_transaction
from ZODB.POSException import ConflictError
from twisted.web import resource
from twisted.internet import reactor
from twisted.protocols import http
from twisted.python import threadable
from twisted.python import failure
import twisted.python.runtime

from schooltool.app import Application, ApplicationObjectContainer
from schooltool import model, absence
from schooltool.views import textErrorPage
from schooltool.component import getView, traverse
from schooltool.membership import Membership
from schooltool.eventlog import EventLogUtility
from schooltool.interfaces import IEvent, IAttendanceEvent, IModuleSetup
from schooltool.interfaces import AuthenticationError
from schooltool.common import StreamWrapper, UnicodeAwareException
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


#
# HTTP server
#

SERVER_VERSION = "SchoolTool/0.6"


def parseAccept(value):
    """Parse HTTP Accept: header.

    See RFC 2616, section 14.1 for a formal grammar.

    Returns a list of tuples
      (qvalue, media_type, media_params, accept_params)

    qvalue is a float in range 0..1 (inclusive)
    media_type is a string "type/subtype", it can be "type/*" or "*/*"
    media_params is a dict
    accept_params is a dict
    """
    if not value:
         return []

    results = []
    for media in map(str.strip, splitQuoted(value, ',')):
        if not media:
            continue
        items = splitQuoted(media, ';')
        media_type = items[0].strip()
        if not validMediaType(media_type):
            raise ValueError('Invalid media type: %s' % media_type)
        params = media_params = {}
        accept_params = {}
        q = 1.0
        for item in items[1:]:
            try:
                key, value = item.split('=', 1)
            except ValueError:
                raise ValueError('Invalid parameter: %s' % item)
            key = key.lstrip()
            value = value.rstrip()
            if not validToken(key):
                raise ValueError('Invalid parameter name: %s' % key)
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            else:
                if not validToken(value):
                    raise ValueError('Invalid parameter value: %s'
                                     % value)
            if key in ('q', 'Q'):
                try:
                    q = float(value)
                except ValueError:
                    raise ValueError('Invalid qvalue: %s' % q)
                else:
                    if q < 0 or q > 1:
                        raise ValueError('Invalid qvalue: %s' % q)
                params = accept_params
            else:
                params[key] = value
        results.append((q, media_type, media_params, accept_params))
    return results


def splitQuoted(s, sep):
    """Split s using sep as the separator.

    Does not split when sep occurs within a quoted string.
    """
    assert len(sep) == 1
    results = []
    start = 0
    state = 0
    for i, c in enumerate(s):
        if state == 0 and c == sep:
            results.append(s[start:i])
            start = i + 1
        elif state == 0 and c == '"':
            state = 1
        elif state == 1 and c == '"':
            state = 0
        elif state == 1 and c == '\\':
            state = 2
        elif state == 2:
            state = 1
    results.append(s[start:])
    return results


def validToken(s):
    """Checks whether s is a syntactically valid token."""
    invalid_chars = list('()<>@,;:\\"/[]?={}\177') + map(chr, range(33))
    for c in s:
        if c in invalid_chars:
            return False
    return s != ''


def validMediaType(s):
    """Check whether s is a syntactically valid media type."""
    if s.count('/') != 1:
        return False
    type, subtype = s.split('/')
    if not validToken(type):
        return False
    if not validToken(subtype):
        return False
    if type == '*' and subtype != '*':
        return False
    return True


def matchMediaType(media_type, params, pattern, pattern_params):
    """Match the media type with a pattern and return the precedence level.

    Returns -1 if the media type does not match the pattern.

    >>> matchMediaType('text/css', {'level': '2'}, '*/*', {})
    1
    >>> matchMediaType('text/css', {'level': '2'}, 'text/*', {})
    2
    >>> matchMediaType('text/css', {'level': '2'}, 'text/css', {})
    3
    >>> matchMediaType('text/css', {'level': '2'}, 'text/css', {'level': '2'})
    4
    >>> matchMediaType('text/css', {'level': '2'}, 'text/css', {'level': '1'})
    -1
    >>> matchMediaType('text/plain', {}, '*/*', {})
    1
    >>> matchMediaType('text/plain', {}, 'text/*', {})
    2
    >>> matchMediaType('text/plain', {}, 'text/plain', {})
    4
    >>> matchMediaType('text/plain', {}, 'text/plain', {'level': '2'})
    -1
    >>> matchMediaType('text/plain', {}, 'text/html', {})
    -1
    >>> matchMediaType('text/plain', {}, 'image/png', {})
    -1
    >>> matchMediaType('text/plain', {}, 'image/*', {})
    -1
    """
    if media_type == pattern and params == pattern_params:
        return 4
    elif media_type == pattern and not pattern_params:
        return 3
    elif pattern.endswith('/*') and media_type.startswith(pattern[:-1]):
        return 2
    elif pattern == '*/*':
        return 1
    else:
        return -1


def qualityOf(media_type, params, accept_list):
    """Calculate the media quality value for a given media type.

    See RFC 2616 section 14.1 for details.

    The accept list is in the same format as returned by parseAccept.
    """
    if not accept_list:
        return 1
    best_qv = 0
    best_precedence = 0
    for qv, pattern, mparams, aparams in accept_list:
        precedence = matchMediaType(media_type, params, pattern, mparams)
        if precedence > best_precedence:
            best_precedence = precedence
            best_qv = qv
    return best_qv


def chooseMediaType(supported_types, accept_list):
    """Choose the best matching media type.

    supported_types should be a sequence of media types.  Media type can
    be a string or a tuples of (media_type, params_dict).

    The accept list is in the same format as returned by parseAccept.

    Returns the media type that has the largest quality value as calculated
    by qualityOf.  If the largest quality value is 0, returns None.
    """
    best = None
    best_q = 0
    for choice in supported_types:
        if isinstance(choice, tuple):
            media_type, params = choice
        else:
            media_type, params = choice, {}
        q = qualityOf(media_type, params, accept_list)
        if q > best_q:
            best_q = q
            best = choice
    return best


def formatHitTime(seconds=None):
    """Format the time stamp for Apache-style HTTP hit logs.

    Example result (assuming your timezone is UTC+03:00):

      '29/Apr/2004:18:05:24 +0300'

    """
    if seconds is None:
        seconds = time.time()
    tt = time.localtime(seconds)
    if tt.tm_isdst:
        tzoffset = -time.altzone / 60
    else:
        tzoffset = -time.timezone / 60
    if tzoffset < 0:
        sign = '-'
    else:
        sign = '+'
    hoffs, moffs = divmod(abs(tzoffset), 60)
    timezone = '%c%02d%02d' % (sign, hoffs, moffs)
    return time.strftime('%d/%b/%Y:%H:%M:%S ', tt) + timezone


class Request(http.Request):
    """Threaded request processor, integrated with ZODB.

    The bulk of the processing is done in a separate thread -- it seems to
    be the only way to integrate Twisted no-blocking requirement with blocking
    operation of ZODB.

    A number of attributes not provided by Twisted's Request are available
    when render is called:

      - 'accept' lists all acceptable content types according to the provided
        HTTP Accept header.  See the docstring of parseAccept for more
        information about its structure.  It is simpler to use chooseMediaType
        instead.

        Note that HTTP/1.1 allows the server to return responses which are
        not acceptable according to the accept headers.  See RFC 2616 section
        10.4.7 for more information.

      - 'authenticated_user' is the user object derived from basic HTTP
        authentication information (None for anonymous access).
    """

    reactor_hook = reactor

    def __init__(self, *args, **kwargs):
        self.get_transaction_hook = get_transaction
        self.hitlogger = logging.getLogger('schooltool.access')
        self.hit_time = formatHitTime()
        http.Request.__init__(self, *args, **kwargs)

    def reset(self):
        """Reset the state of the request.

        Clears all cookies, headers.  In other words, undoes any changes
        caused by calling setHeader, addCookie, setResponseCode, redirect,
        setLastModified, setETag.

        Limitation: this method does not undo changes made by calling setHost.

        You may not call reset if the response is already partially written
        to the transport.
        """

        # should not happen
        assert not self.startedWriting, 'cannot reset at this state'

        self.cookies = []
        self.headers = {}
        self.lastModified = None
        self.etag = None
        self.setResponseCode(http.OK)

    def process(self):
        """Process the request."""

        # Do all the things twisted.web.server.Request.process would do
        self.site = self.channel.site
        self.setHeader('Server', SERVER_VERSION)
        self.setHeader('Date', http.datetimeToString())
        self.setHeader('Content-Type', "text/plain")
        self.prepath = []
        self.postpath = map(urllib.unquote, self.path[1:].split('/'))

        try:
            self._handleVh()
            self.accept = parseAccept(self.getHeader('Accept'))
        except ValueError, e:
            self.accept = []
            body = textErrorPage(self, e)
            self.setHeader('Content-Length', len(body))
            self.write(body)
            self.finish()
            self.logHit()
            return

        # But perform traversal and rendering in a separate worker thread
        self.reactor_hook.callInThread(self._process)

    def _handleVh(self):
        """Handle the virtual hosting directive in the path.

        The directive should start at the beginning of the path and
        have the following form:

          /++vh++proto:host:port/real/path

        In this case, /real/path is in ZODB or is traversed by views, and the
        absolute URLs generated by the application will have the form

          proto://host:port/real/path

        Does nothing if there is no virtual hosting directive.

        Raises a ValueError if the directive is not well formed.
        """

        if self.postpath and self.postpath[0].startswith('++vh++'):
            dir = self.postpath.pop(0)

            try:
                proto, host, port = dir[6:].split(':')
            except ValueError:
                raise ValueError(_('There should be two colons in the '
                                   'virtual hosting directive'), dir)
            secure = (proto == 'https')
            port = int(port)

            self.setHost(host, port, secure)

    def _process(self):
        """Process the request in a separate thread.

        Every request gets a separate transaction and a separate ZODB
        connection.
        """
        self.zodb_conn = None
        try:
            try:
                retries = self.site.conflictRetries
                while True:
                    try:
                        self.zodb_conn = self.site.db.open()
                        body = self._generate_response()
                        txn = self.get_transaction_hook()
                        if self.code >= 400:
                            txn.abort()
                        else:
                            txn.note("%s %s" % (self.method, self.uri))
                            txn.setUser(self.getUser()) # anonymous is ""
                            txn.commit()
                    except ConflictError:
                        if retries <= 0:
                            raise
                        retries -= 1
                        self.get_transaction_hook().abort()
                        self.zodb_conn.close()
                        self.zodb_conn = None
                        self.reset()
                    else:
                        break
            except:
                self.get_transaction_hook().abort()
                body = self._handle_exception(failure.Failure())
            self.reactor_hook.callFromThread(self.write, body)
            self.reactor_hook.callFromThread(self.finish)
            self.reactor_hook.callFromThread(self.logHit)
        finally:
            if self.zodb_conn:
                self.zodb_conn.close()
                self.zodb_conn = None

    def _generate_response(self):
        """Generate the response.

        This is called in a separate thread.
        """
        # Get a persistent application object from ZODB
        root = self.zodb_conn.root()
        app = root[self.site.rootName]

        # Find out the authenticated user
        self.authenticated_user = None
        if self.getUser():
            try:
                self.authenticated_user = self.site.authenticate(app,
                        self.getUser(), self.getPassword())
            except AuthenticationError:
                self.site.logAppEvent(None, "",
                                      _("Failed login, username: %r")
                                      % self.getUser(), logging.WARNING)
                body = textErrorPage(self, _("Bad username or password"),
                                     code=401)
                self.setHeader('Content-Length', len(body))
                self.setHeader('WWW-Authenticate', 'basic realm="SchoolTool"')
                return body

        # Traverse and render the resource
        resrc = self.traverse(app)
        body = self.render(resrc)
        return body

    def _printTraceback(self, reason):
        """Print a timestamp preceding a traceback to the site log."""
        # XXX Do we really need a separate method here?
        self.site.logger.error(reason.getTraceback(), exc_info=False)

    def _handle_exception(self, reason):
        """Generate an internal error page.

        'reason' is a twisted.python.failure.Failure object.

        twisted.web.server.Request.processFailure is very similar in purpose.

        This is called in a separate thread.
        """
        self.reactor_hook.callFromThread(self._printTraceback, reason)
        body = reason.getErrorMessage()
        self.reset()
        self.setResponseCode(500)
        self.setHeader('Content-Type', 'text/plain')
        self.setHeader('Content-Length', len(body))
        return body

    def traverse(self, app):
        """Locate the resource for this request.

        This is called in a separate thread.
        """
        rsc = self.site.viewFactory(app)
        return resource.getChildForRequest(rsc, self)

    def render(self, resrc):
        """Render a resource.

        This is called in a separate thread.
        """
        body = resrc.render(self)
        assert isinstance(body, str), "render did not return a string"

        if self.method == "HEAD":
            if len(body) > 0:
                self.setHeader('Content-Length', len(body))
            return ''
        else:
            self.setHeader('Content-Length', len(body))
            return body

    def chooseMediaType(self, supported_types):
        """Choose a media type for presentation according to Accept: header."""
        return chooseMediaType(supported_types, self.accept)

    def logHit(self):
        """Log a hit into an access log in Apache combined log format."""
        self.hitlogger.info('%s - %s [%s] "%s" %s %s "%s" "%s"' %
                (self.getClientIP() or '-',
                self.getUser() or '-',
                self.hit_time,
                '%s %s %s' % (self.method, self.uri, self.clientproto),
                self.code,
                self.sentLength or "-",
                self.getHeader("referer") or "-",
                self.getHeader("user-agent") or "-"))


class Site(http.HTTPFactory):
    """Site for serving requests based on ZODB"""

    __super = http.HTTPFactory
    __super___init__ = __super.__init__
    __super_buildProtocol = __super.buildProtocol

    conflictRetries = 5     # retry up to 5 times on ZODB ConflictErrors

    def __init__(self, db, rootName, viewFactory, authenticate, applog_path):
        """Create a site.

        Arguments:
          db               ZODB database
          rootName         name of the application object in the database
          viewFactory      factory for the application object views
          authenticate     authentication function (see IAuthenticator)
        """
        self.__super___init__(None)
        self.db = db
        self.viewFactory = viewFactory
        self.rootName = rootName
        self.authenticate = authenticate
        self.applog_path = applog_path
        self.logger = logging.getLogger('schooltool.error')
        self.applogger = logging.getLogger('schooltool.app')

    def buildProtocol(self, addr):
        channel = self.__super_buildProtocol(addr)
        channel.requestFactory = Request
        channel.site = self
        return channel

    def logAppEvent(self, user, path, message, level=logging.INFO):
        """Add a log entry to the application log."""
        if user is None:
            username = 'UNKNOWN'
        else:
            username = user.username
        self.applogger.log(level, "(%s) [%s] %s" % (username, path, message))


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
        self.logger.info(_("Started HTTP server on %s:%s"),
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
        'schooltool.views',
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
