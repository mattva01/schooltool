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

import re
import os
import datetime
import logging
import urllib

from schooltool.interfaces import AuthenticationError
from schooltool.interfaces import IApplicationObjectContainer, IRelatable
from schooltool.component import getTicketService, traverse, getRelatedObjects
from schooltool.rest import View as _View
from schooltool.rest import Unauthorized               # reexport
from schooltool.rest import Template, read_file        # reexport
from schooltool.rest import absoluteURL, absolutePath  # reexport
from schooltool.uris import URINotation
from schooltool.http import Request
from schooltool.browser.auth import PublicAccess
from schooltool.browser.auth import isManager, isTeacher
from schooltool.translation import ugettext as _, TranslatableString


__metaclass__ = type


# Time limit for session expiration
session_time_limit = datetime.timedelta(hours=5)


# Person username / group __name__ validation
# XXX Perhaps this constraint is a bit too strict.
#     If you change this constraint, be sure to update the error message in
#     TimetableSchemaWizard
#     See also http://issues.schooltool.org/issue96
#     Note that group names must not have spaces, or CSV import/export will
#     break.
valid_name = re.compile("^[-a-zA-Z0-9.,'()]+$").match


class BrowserRequest(Request):
    """Browser request.

    Customizes the schooltool.http.Request class by adding cookie-based
    authentication and HTML error messages.
    """

    error_template = Template('www/error.pt')

    def __init__(self, *args, **kwargs):
        Request.__init__(self, *args, **kwargs)
        self.hitlogger = logging.getLogger('schooltool.web_access')

    def maybeAuthenticate(self):
        """Try to authenticate if the authentication cookie is there."""
        auth_cookie = self.getCookie('auth')
        if auth_cookie:
            try:
                ticketService = getTicketService(self.getApplication())
                credentials = ticketService.verifyTicket(auth_cookie,
                                                         session_time_limit)
                self.authenticate(*credentials)
            except AuthenticationError:
                # Do nothing if the cookie has expired -- if the user is not
                # allowed to view the page, the normal authorization mechanism
                # will redirect him to a login page and say that her session
                # has expired.
                #
                # It would be nice to ask the browser to purge the cookie here.
                pass

    # We do not need to override renderAuthError here since maybeAuthenticate
    # never raises AuthenticationError.

    def renderInternalError(self, failure):
        return InternalErrorView(failure).do_GET(self)

    # TODO: override renderRequestError


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
        breadcrumbs
                    Method that returns a sequence of (title, url) breadcrumbs
                    to display in the navigation bar.

    """

    macros_template = Template('www/macros.pt')
    redirect_template = Template('www/redirect.pt')

    macros = property(lambda self: self.macros_template.macros)

    def listBreadcrumbs(self):
        # We use hasattr instead of defining a breadcrumbs method because this
        # makes it easier to define breadcrumbs in mixins without worrying
        # about method resolution order.
        if not hasattr(self, 'breadcrumbs'):
            return []
        return [{'url': url, 'title': title}
                for title, url in self.breadcrumbs()]

    def unauthorized(self, request):
        """Render an unauthorized page."""
        uri = urllib.quote(request.uri)
        if request.authenticated_user is None:
            return self.redirect('/?expired=1&url=%s' % uri, request)
        else:
            return self.redirect('/?forbidden=1&url=%s' % uri, request)

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
        try:
            child = self._traverse(name, request)
            assert child is not None, ("%s._traverse returned None"
                                       % self.__class__.__name__)
            return child
        except KeyError:
            return NotFoundView()

    def redirect(self, url, request):
        """Redirect to a URL and return a html page explaining the redirect."""
        if not url.startswith('http://') and not url.startswith('https://'):
            if not url.startswith('/'):
                url = '/' + url
            scheme = request.isSecure() and 'https' or 'http'
            hostname = request.getRequestHostname()
            port = request.getHost().port
            url = '%s://%s:%s%s' % (scheme, hostname, port, url)
        request.redirect(url)
        return self.redirect_template(request, destination=url, view=self,
                                      context=self.context)

    def isManager(self):
        """Check if the authenticated user is a manager.

        To be used from page templates (e.g. tal:condition="view/isManager").
        """
        return isManager(self.request.authenticated_user)

    def isTeacher(self):
        """Check if the authenticated user is a manager or a teacher.

        To be used from page templates (e.g. tal:condition="view/isTeacher").
        """
        return isTeacher(self.request.authenticated_user)

    def isRelatable(self):
        """Return True/False if the current context is relatable.

        This is a utility for use in tal, primarily for the note system
        """

        return IRelatable.providedBy(self.context)

    def getNotations(self, request):
        """Return a list of related notes

        XXX: refactor, remove passed request
        """

        user = request.authenticated_user
        # We should really just check to see if the object implements
        # IRelatable
        try:
            list = [(obj.title, obj)
                    for obj in getRelatedObjects(self.context, URINotation)]
            list.sort()
            return [obj for title, obj in list if obj.owner == user]
        except AttributeError:
            return []


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


class InternalErrorView(View):
    """View that always returns a 500 error page."""

    template = Template("www/error.pt")

    authorization = PublicAccess

    def do_GET(self, request):
        request.setResponseCode(500)
        return View.do_GET(self, request)

    def traceback(self):
        import cgi
        import linecache
        lines = []
        w = lines.append
        q = lambda s: cgi.escape(str(s), True)
        for method, filename, lineno, locals, globals in self.context.frames:
            w('File "<span class="filename">%s</span>",'
                    ' line <span class="lineno">%s</span>,'
                    ' in <span class="method">%s</span>\n'
              % (q(filename), q(lineno), q(method)))
            w('  <span class="source">%s</span>\n'
              % q(linecache.getline(filename, lineno).strip()))
            self._extra_info(w, dict(locals))
        return "".join(lines)

    def _extra_info(self, w, locals):
        import cgi
        q = lambda s: cgi.escape(str(s), True)
        if '__traceback_info__' in locals:
            tb_info = locals['__traceback_info__']
            w('Extra information: %s\n' % q(repr(tb_info)))
        if '__traceback_supplement__' in locals:
            tb_supplement = locals['__traceback_supplement__']
            tb_supplement = tb_supplement[0](*tb_supplement[1:])
            from zope.pagetemplate.pagetemplate import \
                    PageTemplateTracebackSupplement
            from zope.tales.tales import TALESTracebackSupplement
            if isinstance(tb_supplement, PageTemplateTracebackSupplement):
                source_file = tb_supplement.manageable_object.pt_source_file()
                if source_file:
                    w('Template "<span class="filename">%s</span>"\n'
                      % q(source_file))
            elif isinstance(tb_supplement, TALESTracebackSupplement):
                w('Template "<span class="filename">%s</span>",'
                  ' line <span class="lineno">%s</span>,'
                  ' column <span class="column">%s</span>\n'
                  % (q(tb_supplement.source_url), q(tb_supplement.line),
                     q(tb_supplement.column)))
                w('  Expression: <span class="expr">%s</span>\n'
                  % q(tb_supplement.expression))
            else:
                w('__traceback_supplement__ = %s\n'
                  % q(repr(tb_supplement)))


class NotFoundView(View):
    """View that always returns a 404 error page."""

    template = Template("www/notfound.pt")

    authorization = PublicAccess

    def __init__(self):
        View.__init__(self, None)

    def do_GET(self, request):
        request.setResponseCode(404)
        return View.do_GET(self, request)


def notFoundPage(request):
    """Render a simple 'not found' error page."""
    return NotFoundView().render(request)


class ToplevelBreadcrumbsMixin:
    """Mixin that produces a single breadcrumb pointing to the start page."""

    def breadcrumbs(self):
        if self.context is not None:
            app = traverse(self.context, '/')
            return [(_('Start'), absoluteURL(self.request, app, 'start'))]
        else:
            return []


class ContainerBreadcrumbsMixin(ToplevelBreadcrumbsMixin):
    """Breadcrumbs for application object container views."""

    _ = TranslatableString  # postpone translations

    _container_translations = {'groups': _('Groups'),
                               'persons': _('Persons'),
                               'resources': _('Resources'),
                               'notes': _('Notes')}

    del _ # go back to immediate translations

    def breadcrumbs(self):
        breadcrumbs = ToplevelBreadcrumbsMixin.breadcrumbs(self)
        container = self.context
        while not IApplicationObjectContainer.providedBy(container):
            container = container.__parent__
        title = unicode(self._container_translations[container.__name__])
        breadcrumbs.append((title, absoluteURL(self.request, container)))
        return breadcrumbs


class AppObjectBreadcrumbsMixin(ContainerBreadcrumbsMixin):
    """Mixin for application object views."""

    def breadcrumbs(self, context=None):
        breadcrumbs = ContainerBreadcrumbsMixin.breadcrumbs(self)
        if context is None:
            context = self.context

        obj = context
        while not IApplicationObjectContainer.providedBy(obj.__parent__):
            obj = obj.__parent__

        breadcrumbs.append((context.title, absoluteURL(self.request, context)))
        return breadcrumbs
