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
Unit tests for the schooltool.rest package.
"""

import logging
from StringIO import StringIO
from zope.interface import implements, directlyProvides
from twisted.protocols import http
from twisted.internet.address import IPv4Address
from schooltool.interfaces import ITraversable, IContainmentRoot, IUtility
from schooltool.interfaces import ILocation
from schooltool.security import SecurityPolicy

__metaclass__ = type


class RequestStub:

    code = 200
    reason = 'OK'

    def __init__(self, uri='', method='GET', body='', headers=None,
                 authenticated_user=None, accept=(), args=None, cookies=None):
        self.uri = uri
        self.method = method
        self.path = ''
        self.content = StringIO(body)
        self.authenticated_user = authenticated_user
        self.security = SecurityPolicy(authenticated_user)
        self.headers = {}
        self.args = {}
        if args:
            for k, v in args.items():
                if not isinstance(v, list):
                    v = [v]
                self.args[k] = v
        if body:
            self.request_headers = {'content-length': len(body)}
        else:
            self.request_headers = {'content-length': 0}
        if headers:
            for k, v in headers.items():
                self.request_headers[k.lower()] = v
        self._cookies = {}
        if cookies:
            self._cookies.update(cookies)
        self._outgoing_cookies = {}
        self.accept = list(accept)
        self.path = uri
        self._secure = False
        self._hostname = 'localhost'
        self._port = 7001
        if '://' in uri:
            # XXX This is bogus: twisted's request.uri does not contain http://
            #     etc.
            start = uri.find('/', uri.find('://')+3)
            if start < 0:
                start = len(uri)
            self.path = uri[start:]
            if uri.startswith('https://'):
                self._secure = True
            host_and_port = uri[uri.index('://')+3:start]
            if ':' not in host_and_port:
                host_and_port += ':7001'
            self._hostname, port = host_and_port.split(':')
            self._port = int(port)
        self.applog = []
        self.path = self.path.split('?')[0]

    def getRequestHostname(self):
        return self._hostname

    def getHost(self):
        return IPv4Address('TCP', self._hostname, self._port, 'INET')

    def setHost(self, hostname, port, ssl=False):
        self._hostname = hostname
        self._port = port
        self._secure = ssl

    def isSecure(self):
        return self._secure

    def getHeader(self, header):
        # Twisted's getHeader returns None when the header does not exist
        return self.request_headers.get(header.lower())

    def getContentType(self):
        ctype = self.getHeader('Content-Type')
        if ctype and ';' in ctype:
            ctype = ctype.split(';', 1)[0]
        return ctype

    def setHeader(self, header, value):
        self.headers[header.lower()] = value

    def getCookie(self, key):
        # Twisted's getCookie returns None when the cookie does not exist
        return self._cookies.get(key)

    def addCookie(self, key, value, expires=None, path=None):
        self._outgoing_cookies[key] = {'value': value,
                                       'path': path,
                                       'expires': expires}

    def clearCookie(self, key, value='', **kw):
        self.addCookie(key, value, expires='Www, DD-Mmm-YYYY HH:MM:SS UTC',
                       **kw)

    def setResponseCode(self, code, reason=None):
        self.code = code
        if reason is None:
            self.reason = http.RESPONSES.get(code, 'Unknown Status')
        else:
            self.reason = reason

    def redirect(self, url):
        self.setResponseCode(302)
        self.setHeader("location", url)

    def chooseMediaType(self, supported_types):
        from schooltool.http import chooseMediaType
        return chooseMediaType(supported_types, self.accept)

    def appLog(self, message, level=logging.INFO):
        self.applog.append((self.authenticated_user, message, level))


class TraversableStub:

    implements(ITraversable)

    def __init__(self, **kw):
        self.children = kw

    def traverse(self, name):
        return self.children[name]


class TraversableRoot(TraversableStub):

    implements(IContainmentRoot)


class LocatableStub:
    pass


def setPath(obj, path, root=None):
    """Trick getPath(obj) into returning path."""
    assert path.startswith('/')
    obj.__name__ = path[1:]
    if root is None:
        directlyProvides(obj, ILocation)
        obj.__parent__ = TraversableRoot()
    else:
        assert IContainmentRoot.providedBy(root)
        obj.__parent__ = root


class Libxml2ErrorLogger:

    def __init__(self):
        self.log = []

    def __call__(self, ctx, error):
        self.log.append(error)


class UtilityStub:

    implements(IUtility)

    __parent__ = None
    __name__ = None

    def __init__(self, title):
        self.title = title


def viewClass(iface):
    """Return the view class registered for an interface."""
    from schooltool.component import getView
    cls = type(iface.getName(), (), {})
    obj = cls()
    directlyProvides(obj, iface)
    return getView(obj).__class__
