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
The views for the schooltool content objects.

$Id$
"""

import os
from zope.interface import moduleProvides
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from twisted.web.resource import Resource
from schooltool.interfaces import IModuleSetup
from schooltool.component import getView, getPath
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


#
# Helpers
#

def getURL(request, obj, suffix='', absolute=True):
    """Returns the URL of an object."""
    if request.getHost()[0] == 'SSL':
        scheme = 'https'
    else:
        scheme = 'http'
    hostname = request.getRequestHostname()
    port = request.getHost()[2]
    url = request.virtualpath + getPath(obj)
    if suffix:
        if not url.endswith('/'):
            url += '/'
        url += suffix
    if absolute:
        return '%s://%s:%s%s' % (scheme, hostname, port, url)
    else:
        return url


def absolutePath(request, obj, suffix=''):
    """Return the absolute path of an object in context of request.

    Example:

      >>> from schooltool.views.tests import LocatableStub, setPath
      >>> root, obj = LocatableStub(), LocatableStub()
      >>> setPath(root, '/')
      >>> setPath(obj, '/obj')
      >>> from schooltool.views.tests import RequestStub
      >>> request = RequestStub()

      >>> absolutePath(request, root)
      '/'
      >>> absolutePath(request, obj)
      '/obj'

    The essential difference from schooltool.component.getPath is that
    absolutePath considers request.virtualpath.

      >>> request.virtualpath = '/virtual/path'
      >>> absolutePath(request, root)
      '/virtual/path'
      >>> absolutePath(request, obj)
      '/virtual/path/obj'

    Sometimes you want to construct references to subobjects that are not
    traversible or do not exist as application objects.

      >>> absolutePath(request, root, 'subobject')
      '/virtual/path/subobject'
      >>> absolutePath(request, obj, 'subobject/subsubobject')
      '/virtual/path/obj/subobject/subsubobject'

    """
    path = request.virtualpath.split('/')
    path += getPath(obj).split('/')
    path += suffix.split('/')
    return '/' + '/'.join(filter(None, path))


def read_file(fn):
    """Return the contents of the specified file.

    Filename is relative to the directory this module is placed in.
    """
    basedir = os.path.dirname(__file__)
    f = file(os.path.join(basedir, fn))
    try:
        return f.read()
    finally:
        f.close()


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

    ugettext_hook = _

    def __init__(self, filename, content_type='text/html', charset='UTF-8',
                       _prefix=None):
        _prefix = self.get_path_from_prefix(_prefix)
        PageTemplateFile.__init__(self, filename, _prefix)
        self.content_type = content_type
        self.charset = charset

    def __call__(self, request, **kw):
        """Renders the page template.

        Any keyword arguments passed to this function will be accessible
        in the page template namespace.
        """
        if self.content_type is not None:
            if self.charset is None:
                request.setHeader('Content-Type', self.content_type)
            else:
                request.setHeader('Content-Type', '%s; charset=%s' %
                                        (self.content_type, self.charset))
        context = self.pt_getContext()
        context['request'] = request
        context.update(kw)
        body = self.pt_render(context)
        if self.charset is None:
            return body
        else:
            return body.encode(self.charset, 'xmlcharrefreplace')

    def pt_getEngineContext(self, *args, **kwargs):
        """Get the engine context.

        Gets the engine context and adds our translation method to the
        object before returning it.
        """
        engine = PageTemplateFile.pt_getEngineContext(*args, **kwargs)
        engine.translate = self.translate
        return engine

    def translate(self, msgid, mapping=None, context=None,
                        target_language=None, default=None):
        """Return the translation for the message referred to by msgid.

        Translates the msgid according to the current locale of the server.
        """
        translation = self.ugettext_hook(msgid)
        if translation == msgid:
            return default
        else:
            return translation


#
# HTTP view infrastructure
#

def textErrorPage(request, message, code=400, reason=None):
    """Renders a simple error page and sets the HTTP status code and reason.

    Since textErrorPage is used in low-level parts of schooltool.main.Request,
    it cannot rely on the Unicode processing happening in View.render and must
    always return an 8-bit string with the appropriate charset set in the
    Content-Type header.
    """
    request.setResponseCode(code, reason)
    request.setHeader('Content-Type', 'text/plain; charset=UTF-8')
    return unicode(message).encode('UTF-8')


def notFoundPage(request):
    """Renders a simple 'not found' error page."""
    return textErrorPage(request, _('Not found: %s') % request.uri, code=404)


class View(Resource):
    """View for a content component.

    A View is a kind of a Resource in twisted.web sense, but it is
    really just a view for the actual resource, which is a content
    component.

    Rendering and traversal happens in a separate worker thread.  It
    is incorrect to call request.write or request.finish, or other
    non-thread-safe methods.  You can read more in Twisted
    documentation section about threading.

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
        authorization
                    Callable that takes a context and a request and returns
                    True if that request is authorized.  See also,
                    schooltool.views.auth

    Subclasses must provide authorization and either do_GET or template.

    """

    __super = Resource
    __super_init = __super.__init__

    def __init__(self, context):
        self.__super_init()
        self.context = context
        self.request = None

    def getChild(self, name, request):
        if name == '': # trailing slash in the URL
            if request.path == '/':
                return self
            else:
                return NotFoundView()
        try:
            return self._traverse(name, request)
        except KeyError:
            return NotFoundView()

    def _traverse(self, name, request):
        raise KeyError(name)

    def render(self, request):
        request.setHeader('Allow', ', '.join(self.allowedMethods()))
        handler = getattr(self, 'do_%s' % request.method, None)
        if handler is None:
            body = textErrorPage(request, _("Method Not Allowed"), code=405)
            culprit = 'textErrorPage'
        elif not self.authorization(self.context, request):
            request.setHeader('WWW-Authenticate', 'basic realm="SchoolTool"')
            body = textErrorPage(request, _("Bad username or password"),
                                 code=401)
            culprit = 'textErrorPage'
        else:
            self.request = request
            body = handler(request)
            self.request = None
            culprit = 'do_%s' % request.method

        # Twisted's http.Request keeps outgoing headers in a dict keyed by
        # lower-cased header name.
        ctype = request.headers.get('content-type', None)
        if ctype is None:
            raise AssertionError("%s did not set the Content-Type"
                                 " header" % culprit)
        if isinstance(body, str):
            return body
        elif isinstance(body, unicode):
            if not ctype.startswith('text/'):
                raise AssertionError("%s returned an unicode string for"
                                     " a non-text MIME type (%s)"
                                     % (culprit, ctype))
            if ';' not in ctype:
                ctype += '; charset=UTF-8'
                request.setHeader('Content-Type', ctype)
            elif not ctype.endswith('; charset=UTF-8'):
                raise AssertionError("%s returned an unicode string but"
                                     " specified a non-UTF-8 charset in"
                                     " Content-Type (%s)"
                                     % (culprit, ctype))
            return body.encode('UTF-8')
        else:
            raise AssertionError("%s did not return a string" % culprit)

    def allowedMethods(self):
        """Lists all allowed methods."""
        return [name[3:] for name in dir(self)
                         if name.startswith('do_')
                             and name[3:].isalpha()
                             and name[3:].isupper()]

    def do_GET(self, request):
        return self.template(request, view=self, context=self.context)

    def do_HEAD(self, request):
        body = self.do_GET(request)
        request.setHeader('Content-Length', len(body))
        return ""


class NotFoundView(View):
    """View that always returns a 404 error page."""

    def __init__(self):
        View.__init__(self, None)

    do_GET = staticmethod(notFoundPage)

    def authorization(self, context, request):
        return True


class ItemTraverseView(View):
    """A view that supports traversing with __getitem__."""

    def _traverse(self, name, request):
        return getView(self.context[name])


class TraversableView(View):
    """A view that supports traversing of ITraversable contexts."""

    def _traverse(self, name, request):
        return getView(self.context.traverse(name))


def setUp():
    """See IModuleSetup."""
    import schooltool.views.app
    import schooltool.views.model
    import schooltool.views.facet
    import schooltool.views.utility
    import schooltool.views.absence
    import schooltool.views.eventlog
    import schooltool.views.timetable
    import schooltool.views.cal
    import schooltool.views.infofacets
    schooltool.views.app.setUp()
    schooltool.views.model.setUp()
    schooltool.views.facet.setUp()
    schooltool.views.utility.setUp()
    schooltool.views.absence.setUp()
    schooltool.views.eventlog.setUp()
    schooltool.views.timetable.setUp()
    schooltool.views.cal.setUp()
    schooltool.views.infofacets.setUp()

