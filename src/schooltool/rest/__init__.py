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
from zope.tales.tales import ExpressionEngine
from zope.tales.expressions import PathExpr, StringExpr, NotExpr, DeferExpr
from zope.tales.expressions import SimpleModuleImporter
from zope.tales.pythonexpr import PythonExpr
from zope.i18n import interpolate
from twisted.web.resource import Resource
from schooltool.interfaces import IModuleSetup
from schooltool.component import getView, getPath, getRelatedObjects
from schooltool.uris import URINotation
from schooltool.common import UnicodeAwareException
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


#
# Helpers
#

def absoluteURL(request, obj, suffix=''):
    """Return the absolute URL of an object.

    Example:

      >>> from schooltool.rest.tests import LocatableStub, setPath
      >>> root, obj = LocatableStub(), LocatableStub()
      >>> setPath(root, '/')
      >>> setPath(obj, '/obj')
      >>> from schooltool.rest.tests import RequestStub
      >>> request = RequestStub('http://example.org:7001/')

      >>> absoluteURL(request, root)
      'http://example.org:7001/'
      >>> absoluteURL(request, obj)
      'http://example.org:7001/obj'

    Virtual hosting is supported:

      >>> request.setHost('example.com', 443, ssl=True)

      >>> absoluteURL(request, root)
      'https://example.com:443/'
      >>> absoluteURL(request, obj)
      'https://example.com:443/obj'

    Sometimes you want to construct references to subobjects that are not
    traversible or do not exist as application objects.  This is best done
    by passing the suffix argument:

      >>> absoluteURL(request, root, 'subobject/or/two')
      'https://example.com:443/subobject/or/two'
      >>> absoluteURL(request, obj, 'subobject')
      'https://example.com:443/obj/subobject'

    """
    if request.isSecure():
        scheme = 'https'
    else:
        scheme = 'http'
    hostname = request.getRequestHostname()
    port = request.getHost().port
    url = absolutePath(request, obj, suffix)
    return '%s://%s:%s%s' % (scheme, hostname, port, url)


def absolutePath(request, obj, suffix=''):
    """Return the absolute path of an object in context of request.

    The difference between schooltool.component.getPath and absolutePath
    is that the former works with "physical", application-space paths while
    the latter works with URL-space paths.  Currently the mapping is nearly
    one-to-one, but this might change in the future (e.g. virtual hosting
    directives might strip some initial path elements and add some virtual
    elements in their place).

    Example:

      >>> from schooltool.rest.tests import LocatableStub, setPath
      >>> root, obj = LocatableStub(), LocatableStub()
      >>> setPath(root, '/')
      >>> setPath(obj, '/obj')
      >>> from schooltool.rest.tests import RequestStub
      >>> request = RequestStub()

      >>> absolutePath(request, root)
      '/'
      >>> absolutePath(request, obj)
      '/obj'

    Sometimes you want to construct references to subobjects that are not
    traversible or do not exist as application objects.  This is best done
    by passing the suffix argument:

      >>> absolutePath(request, root, 'subobject')
      '/subobject'
      >>> absolutePath(request, obj, 'subobject/subsubobject')
      '/obj/subobject/subsubobject'

    """
    path = getPath(obj).split('/')
    path += suffix.split('/')
    return '/' + '/'.join(filter(None, path))


def read_file(fn, basedir=None):
    """Return the contents of the specified file.

    Filename is relative to basedir.  If basedir is none, then filename is
    relative to the directory this module is placed in.
    """
    if basedir is None:
        basedir = os.path.dirname(__file__)
    f = file(os.path.join(basedir, fn), 'rb')
    try:
        return f.read()
    finally:
        f.close()


#
# Page templates
#

_marker = object()


def schooltoolTraverse(object, path_items, econtext):
    """A SchoolTool traverser for TALES expressions.

    Honours the special names useful in SchoolTool page templates:

    object/@@absolute_url    -- returns the absolute URL of the object
    object/@@absolute_path   -- returns the path part of the absolute URL
    object/@@path            -- returns the path on the object in ZODB.

    See also zope.tal.expressions.simpleTraverse
    """
    for name in path_items:
        next = getattr(object, name, _marker)
        if next is not _marker:
            object = next
        elif name == '@@absolute_url':
            request = econtext.vars['request']
            return absoluteURL(request, object)
        elif name == '@@absolute_path':
            request = econtext.vars['request']
            return absolutePath(request, object)
        elif name == '@@path':
            return getPath(object)
        elif hasattr(object, '__getitem__'):
            object = object[name]
        else:
            raise NameError, name
    return object


class SchoolToolPathExpr(PathExpr):
    """Path expressions with schooltoolTraverse"""

    def __init__(self, name, expr, engine):
        PathExpr.__init__(self, name, expr, engine, schooltoolTraverse)


def _Engine():
    """This is zope.tal.engine.Engine with SchoolToolPathExpr"""
    e = ExpressionEngine()
    reg = e.registerType
    for pt in SchoolToolPathExpr._default_type_names:
        reg(pt, SchoolToolPathExpr)
    reg('string', StringExpr)
    reg('python', PythonExpr)
    reg('not', NotExpr)
    reg('defer', DeferExpr)
    e.registerBaseName('modules', SimpleModuleImporter())
    return e

_Engine = _Engine()


class Template(PageTemplateFile):
    """Page template file.

    Character set for rendered pages can be set by changing the 'charset'
    attribute.  You should not change the default (UTF-8) without a good
    reason.  If the page template contains characters not representable
    in the output charset, a UnicodeError will be raised when rendering.
    """

    # Hook for unit tests.
    ugettext_hook = staticmethod(_)

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
        if self.content_type is not None and request is not None:
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
        engine = _Engine.getContext(*args, **kwargs)
        engine.translate = self.translate
        return engine

    def pt_getEngine(self):
        return _Engine

    def translate(self, msgid, domain=None, mapping=None, default=None):
        """Return the translation for the message referred to by msgid.

        Translates the msgid according to the current locale of the server.
        """
        translation = self.ugettext_hook(msgid)
        if translation == msgid:
            translation = default
        return interpolate(translation, mapping)


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


class Unauthorized(Exception):
    """Unauthorized exception.

    A view's do_xxx method may raise Unauthorized to indicate that the
    authenticated user is not allowed to do whatever he tried to do.  Use this
    when view.authorization cannot tell in advance if the user is allowed to
    perform the request or not.
    """


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
                    Content-Type header in the request.  If do_FOO raises
                    Unauthorized, an authorization challenge will be returned
                    to the user in the same way as if authorization (see below)
                    returned False.
        authorization
                    Callable that takes a context and a request and returns
                    True if that request is authorized.  See also,
                    schooltool.rest.auth

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
            child = self._traverse(name, request)
            assert child is not None, ("%s._traverse returned None"
                                       % self.__class__.__name__)
            return child
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
            culprit = 'unauthorized'
            body = self.unauthorized(request)
        else:
            culprit = 'do_%s' % request.method
            self.request = request
            try:
                body = handler(request)
            except Unauthorized:
                culprit = 'unauthorized'
                body = self.unauthorized(request)
            self.request = None

        # Twisted's http.Request keeps outgoing headers in a dict keyed by
        # lower-cased header name.
        ctype = request.headers.get('content-type', None)
        if ctype is None and body != "":
            raise AssertionError("%s did not set the Content-Type"
                                 " header" % culprit)
        if isinstance(body, str) or body == u"":
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

    def unauthorized(self, request):
        """Render an unauthorized page."""
        request.setHeader('WWW-Authenticate', 'basic realm="SchoolTool"')
        return textErrorPage(request, _("Bad username or password"), code=401)

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

    def getNotes(self):
        user = self.request.authenticated_user
        # We should really just check to see if the object implements
        # IRelatable
        try:
            list = [(obj.title, obj)
                    for obj in getRelatedObjects(self.context, URINotation)]
            list.sort()
            return [obj for title, obj in list if obj.owner == user]
            #return [obj for title, obj in list]
        except AttributeError:
            return []


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


class ViewError(UnicodeAwareException):
    """User error.

    Used internally by some views to pass an error message until it can be
    rendered.
    """


def setUp():
    """See IModuleSetup."""
    import schooltool.rest.app
    import schooltool.rest.model
    import schooltool.rest.facet
    import schooltool.rest.utility
    import schooltool.rest.absence
    import schooltool.rest.eventlog
    import schooltool.rest.timetable
    import schooltool.rest.cal
    import schooltool.rest.infofacets
    schooltool.rest.app.setUp()
    schooltool.rest.model.setUp()
    schooltool.rest.facet.setUp()
    schooltool.rest.utility.setUp()
    schooltool.rest.absence.setUp()
    schooltool.rest.eventlog.setUp()
    schooltool.rest.timetable.setUp()
    schooltool.rest.cal.setUp()
    schooltool.rest.infofacets.setUp()

