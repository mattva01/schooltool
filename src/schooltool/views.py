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

from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from twisted.web.resource import Resource
from schooltool.interfaces import IGroup, IPerson

__metaclass__ = type


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

class ErrorView(Resource):
    """View for an error.

    Rendering this view will set the appropriate HTTP status code and reason.
    """

    __super = Resource
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

        template    attribute that contains a Template instance for rendering
        _traverse   method that should return a view for a contained object
                    or raise a KeyError

    """

    __super = Resource
    __super___init__ = __super.__init__

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


class GroupView(View):
    """The view for a group"""

    template = Template("www/group.pt")

    def _traverse(self, name, request):
        item = self.context[int(name)]
        if IGroup.isImplementedBy(item):
            return GroupView(item)
        elif IPerson.isImplementedBy(item):
            return PersonView(item)
        else:
            # XXX: This shouldn't really be KeyError -- this is a
            # ViewForObjectNotFound error
            raise KeyError


class PersonView(View):
    """The view for a person object"""
    
