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
from schooltool.component import getView

__metaclass__ = type


moduleProvides(IModuleSetup)


#
# Helpers
#

def absoluteURL(request, path, scheme='http'):
    """Returns the absulute URL of the object adddressed with path"""
    if not path.startswith('/'):
        raise ValueError("Path must be absolute")
    hostname = request.getRequestHostname()
    port = request.getHost()[2]
    return '%s://%s:%s%s' % (scheme, hostname, port, path)


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

    def __init__(self, filename, content_type='text/html', charset='UTF-8',
                       _prefix=None):
        _prefix = self.get_path_from_prefix(_prefix)
        PageTemplateFile.__init__(self, filename, _prefix)
        self.content_type = content_type
        self.charset = charset

    def pt_getEngineContext(self, *args, **kwargs):
        engine = PageTemplateFile.pt_getEngineContext(*args, **kwargs)
        engine.translate = self.translate
        return engine

    def __call__(self, request, **kw):
        """Renders the page template.

        Any keyword arguments passed to this function will be accessible
        in the page template namespace.
        """
        request.setHeader('Content-Type',
                          '%s; charset=%s' % (self.content_type, self.charset))
        context = self.pt_getContext()
        context['request'] = request
        context.update(kw)
        body = self.pt_render(context)
        return body.encode(self.charset, 'xmlcharrefreplace')
    
    domain = "schooltool"
    # XXX should we state that we implement ITranslationDomain?
    def translate(self, msgid, mapping=None, context=None,
                        target_language=None, default=None):
        """Return the translation for the message referred to by msgid.

        For now this simply translates msgid according to the current locale
        of the server without regard to other arguments.
        """
        return _(msgid)

#
# HTTP view infrastructure
#

def textErrorPage(request, message, code=400, reason=None):
    """Renders a simple error page and sets the HTTP status code and reason."""
    request.setResponseCode(code, reason)
    request.setHeader('Content-Type', 'text/plain')
    return str(message)


def notFoundPage(request):
    """Renders a simple 'not found' error page."""
    return textErrorPage(request, 'Not found: %s' % request.uri, code=404)


class View(Resource):
    """View for a content component.

    A View is a kind of a Resource in twisted.web sense, but it is
    really just a view for the actual resource, which is a content
    component.

    Rendering and traversal happens in a separate worker thread.  It
    is incorrect to call request.write or request.finish, or other
    non-thread-safe methods.  You can read more in Twisted
    documentation section about threading.

    Subclasses could provide the following methods and attributes:

        template    Attribute that contains a Template instance for rendering.
        _traverse   Method that should return a view for a contained object
                    or raise a KeyError.
        do_FOO      Method that processes HTTP requests FOO for various values
                    of FOO.  Its signature should match render.
        authorization
                    Callable that takes a context and a request and returns
                    True if that request is authorized.  See also,
                    schooltool.views.auth

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
        if handler is not None:
            if not self.authorization(self.context, request):
                request.setHeader('WWW-Authenticate',
                                  'basic realm="SchoolTool"')
                return textErrorPage(request, "Bad username or password",
                                     code=401)
            self.request = request
            body = handler(request)
            self.request = None
            assert isinstance(body, str), \
                   "do_%s did not return a string" % request.method
            return body
        else:
            return textErrorPage(request, "Method Not Allowed", code=405)

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
    import schooltool.translation
    schooltool.views.app.setUp()
    schooltool.views.model.setUp()
    schooltool.views.facet.setUp()
    schooltool.views.utility.setUp()
    schooltool.views.absence.setUp()
    schooltool.views.eventlog.setUp()
    schooltool.views.timetable.setUp()
    schooltool.views.cal.setUp()
    schooltool.views.infofacets.setUp()
    schooltool.translation.setUp()

