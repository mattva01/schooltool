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
The schooltool.browser package.
"""

import os

from schooltool.interfaces import AuthenticationError
from schooltool.views import View as _View
from schooltool.views import Template, read_file        # reexport
from schooltool.views import absoluteURL, absolutePath  # reexport
from schooltool.views import notFoundPage               # XXX temporary
from schooltool.browser.auth import PublicAccess
from schooltool.browser.auth import globalTicketService


__metaclass__ = type


class View(_View):
    """View for the web application.

    Subclasses can provide the following methods and attributes:

        template    Attribute that contains a Template instance for rendering.
                    It will be used by the default do_GET implementation.
                    Subclasses that override do_GET do not need this attribute.
        _traverse   Method that should return a view for a contained object
                    or raise a KeyError.
        do_FOO      Method that processes HTTP requests FOO for various values
                    of FOO.  Its signature should match render.  It can return
                    either an 8-bit string or a Unicode object (which will be
                    converted to UTF-8 by render).  It must set the
                    Content-Type header in the request.

    """

    macros_template = Template('www/macros.pt')
    redirect_template = Template('www/redirect.pt')

    macros = property(lambda self: self.macros_template.macros)

    def render(self, request):
        """Process the request.

        Hooks in the usual request processing to perform cookie-based
        authentication and override request.authenticated_user before
        authorization takes place.
        """
        auth_cookie = request.getCookie('auth')
        if auth_cookie:
            try:
                credentials = globalTicketService.verifyTicket(auth_cookie)
                request.authenticate(*credentials)
            except AuthenticationError:
                pass
        return _View.render(self, request)

    def unauthorized(self, request):
        """Render an unauthorized page."""
        return self.redirect('/?expired=1&url=%s' % request.uri, request)

    def do_POST(self, request):
        """Process an HTTP POST.

        The default implementation simply delegates the processing to the
        do_GET method.
        """
        return self.do_GET(request)

    def getChild(self, name, request):
        """Traverse to a child view."""
        if name == '': # trailing slash in the URL
            return self
        else:
            return _View.getChild(self, name, request)

    def redirect(self, url, request):
        """Redirect to a URL and return a html page explaining the redirect."""
        if '://' not in url:
            if not url.startswith('/'):
                url = '/' + url
            scheme = request.isSecure() and 'https' or 'http'
            hostname = request.getRequestHostname()
            port = request.getHost().port
            url = '%s://%s:%s%s' % (scheme, hostname, port, url)
        request.redirect(url)
        return self.redirect_template(request, destination=url)


class StaticFile(View):
    """View that returns static content from a file."""

    authorization = PublicAccess

    def __init__(self, filename, content_type):
        View.__init__(self, None)
        self.filename = filename
        self.content_type = content_type

    def do_GET(self, request):
        request.setHeader('Content-Type', self.content_type)
        return read_file(self.filename, os.path.dirname(__file__))

