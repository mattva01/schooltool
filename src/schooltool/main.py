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

Usage: schooltool.py [options]
Options:

  -c, --config xxx  use this configuration file instead of the default
  -m, --mockup      start a mockup application
  -h, --help        show this help message

$Id$
"""

import os
import sys
import ZConfig
import urllib
import copy
import getopt
from transaction import get_transaction
from zodb.interfaces import ConflictError
from twisted.web import server, resource
from twisted.internet import reactor
from twisted.protocols import http
from twisted.python import threadable
from twisted.python import failure

from schooltool import mockup
from schooltool.model import RootGroup, Group, Person
from schooltool.views import GroupView, errorPage
from schooltool.relationships import setUp as setUpRelationship
from schooltool.membership import setUp as setUpMembership

__metaclass__ = type


#
# HTTP server
#

SERVER_VERSION = "SchoolTool/0.1"

class Request(server.Request):
    """Threaded request processor, integrated with ZODB.

    Another enhancement over Twisted's Request is that an attribute
    called 'accept' is available that lists all acceptable content types
    according to the provided HTTP Accept header.  See the docstring of
    _parseAccept for more information about its structure.

    Note that HTTP/1.1 allows the server to return responses which are
    not acceptable according to the accept headers.  See RFC 2616 section
    10.4.7 for more information.
    """

    reactor_hook = reactor
    get_transaction_hook = get_transaction

    def _parseAccept(self, value):
        """Parses HTTP Accept: header.

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

        split = self._split
        valid_token = self._valid_token
        valid_media_type = self._valid_media_type

        results = []
        for media in map(str.strip, split(value, ',')):
            if not media:
                continue
            items = split(media, ';')
            media_type = items[0].strip()
            if not valid_media_type(media_type):
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
                if not valid_token(key):
                    raise ValueError('Invalid parameter name: %s' % key)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                else:
                    if not valid_token(value):
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

    def _split(self, s, sep):
        """Splits s using sep as the separator.

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

    def _valid_token(self, s):
        """Checks wheter s is a syntactically valid token."""
        invalid_chars = list('()<>@,;:\\"/[]?={}\177') + map(chr, range(33))
        for c in s:
            if c in invalid_chars:
                return False
        return s != ''

    def _valid_media_type(self, s):
        """Checks wheter s is a syntactically valid media type."""
        if s.count('/') != 1:
            return False
        type, subtype = s.split('/')
        if not self._valid_token(type):
            return False
        if not self._valid_token(subtype):
            return False
        if type == '*' and subtype != '*':
            return False
        return True

    def process(self):
        """Process the request"""

        # Do all the things server.Request.process would do
        self.site = self.channel.site
        self.setHeader('Server', SERVER_VERSION)
        self.setHeader('Date', http.datetimeToString())
        self.setHeader('Content-Type', "text/html")
        self.prepath = []
        self.postpath = map(urllib.unquote, self.path[1:].split('/'))

        # Parse the HTTP 'Accept' header:
        try:
            self.accept = self._parseAccept(self.getHeader('Accept'))
        except ValueError, e:
            self.accept = []
            body = errorPage(self, 400, str(e))
            self.setHeader('Content-Length', len(body))
            self.write(body)
            self.finish()
            return

        # But perform traversal and rendering in a separate worker thread
        self.reactor_hook.callInThread(self._process)

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
                        resrc = self.traverse()
                        body = self.render(resrc)
                        txn = self.get_transaction_hook()
                        txn.note(self.path)
                        txn.setUser(self.getUser()) # anonymous is ""
                        txn.commit()
                    except ConflictError:
                        if retries <= 0:
                            raise
                        retries -= 1
                        self.get_transaction_hook().abort()
                        self.zodb_conn.close()
                        self.reset()
                    else:
                        break
            except:
                self.get_transaction_hook().abort()
                self.reactor_hook.callFromThread(self.processingFailed,
                                                 failure.Failure())
            else:
                self.reactor_hook.callFromThread(self.write, body)
                self.reactor_hook.callFromThread(self.finish)
        finally:
            if self.zodb_conn:
                self.zodb_conn.close()
                self.zodb_conn = None

    def reset(self):
        """Resets the state of the request.

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

    def traverse(self):
        """Locate the resource for this request.

        This is called in a separate thread.
        """

        # Do things usually done by Site.getResourceFor
        self.sitepath = copy.copy(self.prepath)
        self.acqpath = copy.copy(self.prepath)

        # Get a persistent application object from ZODB
        root = self.zodb_conn.root()
        app = root[self.site.rootName]
        resource = self.site.viewFactory(app)
        return resource.getChildForRequest(self)

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


class Site(server.Site):
    """Site for serving requests based on ZODB"""

    __super = server.Site
    __super___init__ = __super.__init__
    __super_buildProtocol = __super.buildProtocol

    conflictRetries = 5     # retry up to 5 times on ZODB ConflictErrors

    def __init__(self, db, rootName, viewFactory):
        """Creates a site.

        Arguments:
          db            ZODB database
          rootName      name of the application object in the database
          viewFactory   factory for the application object views
        """
        self.__super___init__(None)
        self.db = db
        self.viewFactory = viewFactory
        self.rootName = rootName

    def buildProtocol(self, addr):
        channel = self.__super_buildProtocol(addr)
        channel.requestFactory = Request
        return channel

#
# Main loop
#

class Server:
    """SchoolTool HTTP server."""

    threadable_hook = threadable
    reactor_hook = reactor
    get_transaction_hook = get_transaction

    def __init__(self, stdout=sys.stdout, stderr=sys.stderr):
        self.stdout = stdout
        self.stderr = stderr

    def main(self, args):
        """Starts the SchoolTool HTTP server.

        args contains command line arguments, usually it is sys.argv[1:].

        Returns zero on normal exit, nonzero on error.  Return value should
        be passed to sys.exit.
        """
        try:
            self.configure(args)
        except getopt.GetoptError, e:
            print >> self.stderr, "schooltool: %s" % e
            print >> self.stderr, "run schooltool -h for help"
            return 1
        except SystemExit, e:
            return e.args[0]
        else:
            self.run()
            return 0

    def configure(self, args):
        """Process command line arguments and configuration files.

        This is called automatically from run.

        The following attributes define server configuration and are set by
        this method:
          appname       name of the application instance in ZODB
          viewFactory   root view class
          appFactory    application object factory
          config        configuration loaded from a config file, contains the
                        following attributes (see schema.xml for the definitive
                        list):
                            thread_pool_size
                            listen
                            database
        """

        # Defaults
        config_file = self.findDefaultConfigFile()
        self.appname = 'schooltool'
        self.viewFactory = GroupView
        self.appFactory = self.createApplication

        # Process command line arguments
        opts, args = getopt.getopt(args, 'c:hm', ['config=', 'help', 'mockup'])

        for k, v in opts:
            if k in ('-h', '--help'):
                self.help()
                raise SystemExit(0)

        if args:
            raise getopt.GetoptError("too many arguments")

        # Read configuration file
        for k, v in opts:
            if k in ('-c', '--config'):
                config_file = v
        self.config = self.loadConfig(config_file)

        # Process any command line arguments that may override config file
        # settings here.
        for k, v in opts:
            if k in ('-m', '--mockup'):
                self.appname = 'mockup'
                self.viewFactory = mockup.RootView
                self.appFactory = mockup.FakeApplication

    def help(self):
        """Prints a help message."""
        message = __doc__.strip().splitlines()[:-1]
        print >> sys.stdout, "\n".join(message)

    def findDefaultConfigFile(self):
        """Returns the default config file pathname."""
        dirname = os.path.dirname(__file__)
        dirname = os.path.normpath(os.path.join(dirname, '..', '..'))
        config_file = os.path.join(dirname, 'schooltool.conf')
        if not os.path.exists(config_file):
            config_file = os.path.join(dirname, 'schooltool.conf.in')
        return config_file

    def loadConfig(self, config_file):
        """Loads configuration from a given config file."""
        dirname = os.path.dirname(__file__)
        schema = ZConfig.loadSchema(os.path.join(dirname, 'schema.xml'))
        self.notifyConfigFile(config_file)
        config, handler = ZConfig.loadConfig(schema, config_file)
        return config

    def run(self):
        """Start the HTTP server.

        Must be called after configure.
        """
        setUpRelationship()
        setUpMembership()

        db_configuration = self.config.database
        self.db = db_configuration.open()
        self.ensureAppExists(self.db, self.appname)

        self.threadable_hook.init()

        site = Site(self.db, self.appname, self.viewFactory)
        for interface, port in self.config.listen:
            self.reactor_hook.listenTCP(port, site, interface=interface)
            self.notifyServerStarted(interface, port)

        # Call suggestThreadPoolSize at the last possible moment, because it
        # will create a number of non-daemon threads and will prevent the
        # application from exitting on errors.
        self.reactor_hook.suggestThreadPoolSize(self.config.thread_pool_size)
        self.reactor_hook.run()

    def ensureAppExists(self, db, appname):
        """Makes sure the database has an application instance.

        Creates the application if necessary.
        """
        conn = db.open()
        root = conn.root()
        if root.get(appname) is None:
            root[appname] = self.appFactory(conn)
            self.get_transaction_hook().commit()
        conn.close()

    def createApplication(self, datamgr):
        """Instantiate a new application"""
        root = RootGroup("root")
        teachers = Group("teachers")
        students = Group("students")
        cleaners = Group("cleaners")
        root.add(teachers)
        root.add(students)
        root.add(cleaners)
        teachers.add(Person("Mark"))
        teachers.add(Person("Steve"))
        students.add(Person("Aiste"))
        cleaners.add(Person("Albertas"))
        cleaners.add(Person("Marius"))
        return root

    def notifyConfigFile(self, config_file):
        print >> self.stdout, "Reading configuration from %s" % config_file

    def notifyServerStarted(self, network_interface, port):
        print >> self.stdout, ("Started HTTP server on %s:%s"
                               % (network_interface or "*", port))


def main():
    """Starts the SchoolTool HTTP server."""
    sys.exit(Server().main(sys.argv[1:]))


if __name__ == '__main__':
    main()
