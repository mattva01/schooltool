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
Functional tests for schooltool.restclient.

$Id$
"""


from schooltool.testing.functional import rest


class RestConnectionFactory(object):
    """Stub of httplib.HTTPConnectionFactory.

    Short-circuits real HTTP connections to the rest() function.
    """

    handle_errors = True

    def __init__(self, server, port):
        self._response = None
        self.server = server
        self.port = port

    def request(self, method, path, body, headers):
        if body is None:
            body = ''
        assert path.startswith('/'), path
        assert ' ' not in path, path
        path = '/++vh++http:localhost:7001/++' + path
        request = ["%s %s HTTP/1.1" % (method, path)]
        for hdr, value in headers.items():
            request.append("%s: %s" % (hdr, value))
        request_string = "\n".join(request) + "\n\n" + body
        self._response = rest(request_string, handle_errors=self.handle_errors)

    def getresponse(self):
        return RestResponse(self._response)

    def close(self):
        self._response = None


class RestResponse(object):
    """Adapter of Zope 3 response objects into httplib.HTTPResponse."""

    def __init__(self, zope3_response):
        self._zope3_response = zope3_response
        self.status = zope3_response.getStatus()
        status_and_reason = zope3_response.getStatusString()
        self.reason = status_and_reason.split(' ', 1)[1]

    def getheader(self, header):
        return self._zope3_response.getHeader(header)

    def read(self):
        return self._zope3_response.getBody()
