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
import ZConfig
import urllib
import copy
import getopt
from persistence import Persistent
from transaction import get_transaction
from zodb.interfaces import ConflictError
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from twisted.web import server, resource
from twisted.internet import reactor
from twisted.protocols import http
from twisted.python import threadable
from twisted.python import failure

__metaclass__ = type


#
# Some fake content
#

def readFile(filename):
    dirname = os.path.dirname(__file__)
    pathname = os.path.join(dirname, filename)
    f = open(pathname)
    data = f.read()
    f.close()
    return data


class FakePhoto:

    format = 'image/jpeg'
    data = readFile('photo.jpg')


class FakePerson:

    photo = FakePhoto()

    def __init__(self, name):
        self.name = name


class FakeApplication(Persistent):

    people = {'john': FakePerson('john'),
              'smith': FakePerson('smith'),
              'george': FakePerson('george')}

    counter = 0


#
# Page templates
#

class Template(PageTemplateFile):
    """Page template file.

    Character set for rendered pages can be set by changing the 'charset'
    attribute.  You should not change the default (UTF-8) without a good
    reason.  If the page template contains characters not representable
    in the output charset, a UnicodeError will be raised when rendering.
    """

    charset = 'UTF-8'

    def __call__(self, request, **kw):
        """Renders the page template.

        Any keyword arguments passed to this function will be accessible
        in the page template namespace.
        """
        request.setHeader('Content-Type',
                          'text/html; charset=%s' % self.charset)
        context = self.pt_getContext()
        context['request'] = request
        context.update(kw)
        return self.pt_render(context).encode(self.charset)


#
# HTTP view infrastructure
#

SERVER_VERSION = "SchoolTool/0.1"

class ErrorView(resource.Resource):
    """View for an error.

    Rendering this view will set the appropriate HTTP status code and reason.
    """

    __super = resource.Resource
    __super___init__ = __super.__init__

    isLeaf = True

    template = Template('www/error.pt')

    def __init__(self, code, reason):
        self.__super___init__()
        self.code = code
        self.reason = reason

    def render(self, request):
        request.setResponseCode(self.code, self.reason)
        return self.template(request, code=self.code, reason=self.reason)


class NotFoundView(ErrorView):
    """View for a not found error.

    This view should be used for HTTP status code 404.
    """

    template = Template('www/notfound.pt')


def errorPage(request, code, reason):
    """Renders a simple error page and sets the HTTP status code and reason."""
    return ErrorView(code, reason).render(request)


class View(resource.Resource):
    """View for a content component.

    A View is a kind of a Resource in twisted.web sense, but it is really just
    a view for the actual resource, which is a content component.

    Rendering and traversal happens in a separate worker thread.  It is
    incorrect to call request.write or request.finish, or other non-thread-safe
    methods.  You can read more in Twisted documentation section about
    threading.

    Subclasses could provide the following methods and attributes:

        template    attribute that contains a Template instance for rendering
        _traverse   method that should return a view for a contained object
                    or raise a KeyError

    """

    __super = resource.Resource
    __super___init__ = __super.__init__
    __super_getChild = __super.getChild

    def __init__(self, context):
        self.__super___init__()
        self.context = context

    def getChild(self, name, request):
        if name == '': # trailing slash in the URL?
            return self
        try:
            return self._traverse(name, request)
        except KeyError:
            return NotFoundView(404, "Not Found")
        return self.__super_getChild(name, request)

    def _traverse(self, name, request):
        raise KeyError(name)

    def render(self, request):
        if request.method == 'GET':
            return self.template(request, view=self, context=self.context)
        elif request.method == 'HEAD':
            body = self.template(request, view=self, context=self.context)
            request.setHeader('Content-Length', len(body))
            return ""
        else:
            request.setHeader('Allow', 'GET, HEAD')
            return errorPage(request, 405, "Method Not Allowed")


class Request(server.Request):
    """Threaded request processor, integrated with ZODB"""

    def process(self):
        """Process the request"""

        # Do all the things server.Request.process would do
        self.site = self.channel.site
        self.setHeader('Server', SERVER_VERSION)
        self.setHeader('Date', http.datetimeToString())
        self.setHeader('Content-Type', "text/html")
        self.prepath = []
        self.postpath = map(urllib.unquote, self.path[1:].split('/'))

        # But perform traversal and rendering in a separate worker thread
        reactor.callInThread(self._process)

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
                        txn = get_transaction()
                        txn.note(self.path)
                        txn.setUser(self.getUser()) # anonymous is ""
                        txn.commit()
                    except ConflictError:
                        if retries <= 0:
                            raise
                        retries -= 1
                        get_transaction().abort()
                        self.zodb_conn.close()
                        self.reset()
                    else:
                        break
            except:
                get_transaction().abort()
                reactor.callFromThread(self.processingFailed, failure.Failure())
            else:
                reactor.callFromThread(self.write, body)
                reactor.callFromThread(self.finish)
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

        if not isinstance(body, str):
            body = errorPage(self, 500, "render did not return a string")

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
# Actual views
#

class RootView(View):
    """View for the application root."""

    template = Template('www/root.pt')

    def counter(self):
        self.context.counter += 1
        return self.context.counter

    def _traverse(self, name, request):
        if name == 'people':
            return PeopleView(self.context)
        raise KeyError(name)


class PeopleView(View):
    """View for /people"""

    template = Template('www/people.pt')

    def listNames(self):
        """Lists the names of all persons known to the system.

        Names are sorted in alphabetical order.
        """
        people = self.context.people.items()
        people.sort()
        return [k for k, v in people]

    def _traverse(self, name, request):
        person = self.context.people[name]
        return PersonView(person)


class PersonView(View):
    """View for /people/person_name"""

    template = Template('www/person.pt')

    def _traverse(self, name, request):
        if name == 'photo':
            return PhotoView(self.context.photo)
        raise KeyError(name)


class PhotoView(View):
    """View for /people/person_name/photo"""

    def render(self, request):
        if request.method == 'GET':
            request.setHeader('Content-Type', self.context.format)
            return self.context.data
        elif request.method == 'HEAD':
            request.setHeader('Content-Type', self.context.format)
            request.setHeader('Content-Length', len(self.context.data))
            return ""
        else:
            request.setHeader('Allow', 'GET, HEAD')
            return errorPage(request, 405, "Method Not Allowed")


#
# Main loop
#

def main():
    """Starts the SchoolTool mockup HTTP server on port 8080."""

    # Tell Twisted we'll be using threads
    threadable.init()

    # Find a default configuration file
    dirname = os.path.dirname(__file__)
    dirname = os.path.normpath(os.path.join(dirname, '..', '..'))
    config_file = os.path.join(dirname, 'schooltool.conf')
    if not os.path.exists(config_file):
        config_file = os.path.join(dirname, 'schooltool.conf.in')

    # Check if a different config file is specified on the command line
    opts, args = getopt.getopt(sys.argv[1:], 'c:', ['config='])
    for k, v in opts:
        if k in ('-c', '--config'):
            config_file = v

    # Read configuration file
    dirname = os.path.dirname(__file__)
    schema = ZConfig.loadSchema(os.path.join(dirname, 'schema.xml'))
    print "Reading configuration from %s" % config_file
    config, handler = ZConfig.loadConfig(schema, config_file)

    # Apply misc. config settings
    reactor.suggestThreadPoolSize(config.thread_pool_size)

    # Open the database
    db = config.database.open()
    conn = db.open()
    root = conn.root()
    if root.get('schooltool') is None:
        root['schooltool'] = FakeApplication()
        get_transaction().commit()
    conn.close()

    # Start web servers
    site = Site(db, 'schooltool', RootView)
    for interface, port in config.listen:
        reactor.listenTCP(port, site, interface=interface)
        print "Started HTTP server on %s:%s" % (interface or "*", port)
    reactor.run()


if __name__ == '__main__':
    main()

