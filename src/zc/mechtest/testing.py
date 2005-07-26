##############################################################################
#
# Copyright (c) 2005 Zope Corporation. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Visible Source
# License, Version 1.0 (ZVSL).  A copy of the ZVSL should accompany this
# distribution.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import httplib
import urllib2
from cStringIO import StringIO

from zope.app.testing.functional import HTTPCaller

import private_mechanize


class PublisherConnection:

    def __init__(self, host):
        self.host = host
        self.caller = HTTPCaller()

    def set_debuglevel(self, level):
        pass

    def request(self, method, url, body=None, headers=None):
        header_chunks = []
        if body is None:
            body = ''

        if headers is not None:
            for header in headers.items():
                header_chunks.append('%s: %s' % header)
            headers = '\n'.join(header_chunks) + '\n'
        else:
            headers = ''

        request_string = (method + ' ' + url + ' HTTP/1.1\n'
                          + headers + '\n' + body)

        self.response = self.caller(request_string, handle_errors=False)

    def getresponse(self):
        headers = self.response.header_output.headersl
        real_response = self.response._response
        status = real_response.getStatus()
        reason = real_response._reason # XXX should add a getReason method
        output = (real_response.getHeaderText(real_response.getHeaders()) +
                  self.response.getBody())
        return PublisherResponse(output, status, reason)


class PublisherResponse:

    def __init__(self, content, status, reason):
        self.content = content
        self.status = status
        self.reason = reason
        self.msg = httplib.HTTPMessage(StringIO(content), 0)
        self.content_as_file = StringIO(content)

    def read(self, amt=None):
        return self.content_as_file.read(amt)


class PublisherHandler(urllib2.HTTPHandler):

    def http_open(self, req):
        return self.do_open(PublisherConnection, req)

    http_request = urllib2.AbstractHTTPHandler.do_request_


# hack the mechanize user agent class to talk to the publisher
private_mechanize.UserAgent.handler_classes['http'] = PublisherHandler

# the robots.txt handler tries to access the Internet, so we'll disable it
del private_mechanize.UserAgent.handler_classes['_robots']
private_mechanize.UserAgent.default_features.remove('_robots')

import browser

class Browser(browser.Browser):
    def __init__(self, url=None):
        super(Browser, self).__init__(
            url=url, mech_browser=private_mechanize.Browser())
