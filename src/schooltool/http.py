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

import time
import urllib
import logging

from transaction import get_transaction
from ZODB.POSException import ConflictError
from twisted.web import resource
from twisted.internet import reactor
from twisted.protocols import http
from twisted.python import failure

from schooltool.rest import textErrorPage
from schooltool.interfaces import AuthenticationError
from schooltool.translation import ugettext as _


__metaclass__ = type


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
        self.applogger = logging.getLogger('schooltool.app')
        self.hit_time = formatHitTime()
        self.authenticated_user = None
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
            self.setResponseCode(400)
            body = self.renderRequestError(e)
            assert isinstance(body, str), \
                   "renderRequestError did not return a string"
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
        try:
            self.maybeAuthenticate()
        except AuthenticationError:
            body = self.renderAuthError()
            assert isinstance(body, str), \
                   "renderAuthError did not return a string"
            self.setHeader('Content-Length', len(body))
            return body

        # Traverse and render the resource
        resrc = self.traverse(app)
        body = self.render(resrc)
        return body

    def maybeAuthenticate(self):
        """Try to authenticate.

        Looks for HTTP basic authentication header.  If it is found, calls
        self.authenticate with the username and password extracted from the
        header.

        May raise an AuthenticationError.

        Subclasses may override this method to implement cookie-based
        authentication, for example.
        """
        if self.getUser():
            self.authenticate(self.getUser(), self.getPassword())

    def authenticate(self, username, password):
        """Try to authenticate with a given username and password.

        Sets the 'authenticated_user' attribute (to None if the authentication
        is not successful).

        Logs a message into the application log and raises AuthenticationError
        if the authentication is not successful.
        """
        root = self.zodb_conn.root()
        app = root[self.site.rootName]
        try:
            self.authenticated_user = self.site.authenticate(app, username,
                                                             password)
            self.user = username
        except AuthenticationError:
            self.authenticated_user = None
            self.user = ''
            self.applogger.warn(_("Failed login, username: %r") % username)
            raise

    def _printTraceback(self, reason):
        """Print a a traceback to the site log."""
        self.site.logger.error(reason.getTraceback(), exc_info=False)

    def _handle_exception(self, reason):
        """Generate an internal error page.

        'reason' is a twisted.python.failure.Failure object.

        twisted.web.server.Request.processFailure is very similar in purpose.

        This is called in a separate thread.
        """
        self.reactor_hook.callFromThread(self._printTraceback, reason)
        self.reset()
        self.setResponseCode(500)
        body = self.renderInternalError(reason)
        assert isinstance(body, str), \
               "renderInternalError did not return a string"
        self.setHeader('Content-Length', len(body))
        return body

    def traverse(self, app):
        """Locate the resource for this request.

        This is called in a separate thread.
        """
        rsc = self.site.viewFactory(app)
        return resource.getChildForRequest(rsc, self)

    def setHeader(self, header, value):
        """Set an HTTP response header.

        Header names and values must be convertible to 7-bit ASCII strings.
        """
        assert isinstance(header, str), "header name must be a string"
        assert isinstance(value, (str, int)), "header value must be a string"
        http.Request.setHeader(self, header, value)

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

    def renderRequestError(self, exception):
        """Render an error page for an ill-formed request."""
        return textErrorPage(self, exception)

    def renderInternalError(self, failure):
        """Render an error page for an internal server error.

        failure is an instance of twisted.pyton.failure.Failure.
        """
        self.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        return failure.getErrorMessage()

    def renderAuthError(self):
        """Render an authentication error page.

        The default implementation sends a basic HTTP authentication challenge
        for realm "SchoolTool" and returns a 401 (Unauthorized) HTTP status
        code.
        """
        self.setHeader('WWW-Authenticate', 'basic realm="SchoolTool"')
        return textErrorPage(self, _("Bad username or password"), code=401)

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

    def appLog(self, message, level=logging.INFO):
        """Add a log entry to the application log."""
        if self.authenticated_user is None:
            username = 'UNKNOWN'
        else:
            username = self.authenticated_user.username
        self.applogger.log(level, "(%s) %s" % (username, message))


class Site(http.HTTPFactory):
    """Site for serving requests based on ZODB"""

    __super = http.HTTPFactory
    __super___init__ = __super.__init__
    __super_buildProtocol = __super.buildProtocol

    conflictRetries = 5     # retry up to 5 times on ZODB ConflictErrors

    def __init__(self, db, rootName, viewFactory, authenticate, applog_path,
                 requestFactory=Request):
        """Create a site.

        Arguments:
          db                ZODB database
          rootName          name of the application object in the database
          viewFactory       factory for the application object views
          authenticate      authentication function (see IAuthenticator)
          applog_path       application audit log filename
          requestFactory    factory for requests
        """
        self.__super___init__(None)
        self.db = db
        self.viewFactory = viewFactory
        self.rootName = rootName
        self.authenticate = authenticate
        self.applog_path = applog_path
        self.logger = logging.getLogger('schooltool.error')
        self.requestFactory = requestFactory

    def buildProtocol(self, addr):
        channel = self.__super_buildProtocol(addr)
        channel.requestFactory = self.requestFactory
        channel.site = self
        return channel

