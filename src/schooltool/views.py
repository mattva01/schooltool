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

import re
from zope.interface import moduleProvides
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from twisted.web.resource import Resource
from schooltool.interfaces import IGroup, IPerson, URIMember, URIGroup
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IUtilityService, IUtility, IFacet
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import ComponentLookupError
from schooltool.component import getPath, traverse, getRelatedObjects
from schooltool.component import getView, registerView, strURI, getURI
from schooltool.component import FacetManager, iterFacetFactories
from schooltool.component import getFacetFactory
from schooltool.debug import IEventLog, IEventLogUtility, IEventLogFacet

__metaclass__ = type


moduleProvides(IModuleSetup)

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
        return self.pt_render(context).encode(self.charset)


#
# HTTP view infrastructure
#

class ErrorView(Resource):
    """View for an error.

    Rendering this view will set the appropriate HTTP status code and reason.
    """

    __super = Resource
    __super_init = __super.__init__

    isLeaf = True

    template = Template('www/error.pt')

    def __init__(self, code, reason):
        self.__super_init()
        self.code = code
        self.reason = reason

    def render(self, request):
        request.setResponseCode(self.code, self.reason)
        return self.template(request, code=self.code, reason=self.reason)


class NotFoundView(ErrorView):
    """View for a not found error.

    This view should be used for HTTP status code 404.
    """

    __super = ErrorView
    __super_init = __super.__init__

    template = Template('www/notfound.pt')

    def __init__(self, code=404, reason='Not Found'):
        self.__super_init(code, reason)


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

        template    Attribute that contains a Template instance for rendering.
        _traverse   Method that should return a view for a contained object
                    or raise a KeyError.
        do_XXX      Method that processes HTTP requests XXX for various values
                    of XXX.  Its signature should match render.

    """

    __super = Resource
    __super_init = __super.__init__

    def __init__(self, context):
        self.__super_init()
        self.context = context

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
        handler = getattr(self, 'do_%s' % request.method, None)
        if handler is not None:
            return handler(request)
        else:
            request.setHeader('Allow', ', '.join(self.allowedMethods()))
            return errorPage(request, 405, "Method Not Allowed")

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


class ItemTraverseView(View):
    """A view that supports traversing with __getitem__."""

    def _traverse(self, name, request):
        return getView(self.context[name])


class TraversableView(View):
    """A view that supports traversing of ITraversable contexts."""

    def _traverse(self, name, request):
        return getView(self.context.traverse(name))


class ApplicationObjectTraverserView(View):
    """A view that supports traversing to facets and relationships."""

    def _traverse(self, name, request):
        if name == 'facets':
            return FacetManagementView(FacetManager(self.context))
        if name == 'relationships':
            return RelationshipsView(self.context)
        raise KeyError(name)


class XMLPseudoParser:
    """This is a temporary stub for validating XML parsing."""

    def extractKeyword(self, text, key):
        """Extracts values of key="value" format from a string.

        Throws a KeyError if key is not found.
        """
        pat = re.compile(r'\b%s="([^"]*)"' % key)
        match = pat.search(text)
        if match:
            return match.group(1)
        else:
            raise KeyError("%r not in text" % (key,))


#
# Concrete views
#

class GroupView(ApplicationObjectTraverserView):
    """The view for a group"""

    template = Template("www/group.pt", content_type="text/xml")

    def listItems(self):
        for item in getRelatedObjects(self.context, URIMember):
            yield {'title': item.title, 'path': getPath(item)}


class PersonView(ApplicationObjectTraverserView):
    """The view for a person object"""

    template = Template("www/person.pt", content_type="text/xml")

    def getGroups(self):
        return [{'title': group.title, 'path': getPath(group)}
                for group in getRelatedObjects(self.context, URIGroup)]


class ApplicationView(TraversableView):
    """The root view for the application"""

    template = Template("www/app.pt", content_type="text/xml")

    def getRoots(self):
        return [{'path': getPath(root), 'title': root.title}
                for root in self.context.getRoots()]

    def getContainers(self):
        base = getPath(self.context)
        if not base.endswith('/'):
            base += '/'
        return [{'path': '%s%s' % (base, key), 'title': key}
                for key in self.context.keys()]

    def getUtilities(self):
        return [{'path': getPath(utility), 'title': utility.title}
                for utility in self.context.utilityService.values()]


class ApplicationObjectCreator(XMLPseudoParser):
    """Mixin for adding new application objects"""

    def create(self, request, container, name=None):
        body = request.content.read()
        kw = {}
        if name is not None:
            kw['__name__'] = name
        try:
            kw['title'] = self.extractKeyword(body, 'title')
        except KeyError:
            pass
        obj = container.new(**kw)
        location = ('http://%s%s'
                    % (request.getRequestHostname(), getPath(obj)))
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Location', location)
        return "Object created: %s" % location


class ApplicationObjectContainerView(TraversableView, ApplicationObjectCreator):
    """The view for the application object containers"""

    template = Template("www/aoc.pt", content_type="text/xml")

    def getName(self):
        return self.context.__name__

    def items(self):
        c = self.context
        return [{'path': getPath(c[key]), 'title': c[key].title}
                for key in self.context.keys()]

    def _traverse(self, name, request):
        try:
            return TraversableView._traverse(self, name, request)
        except KeyError:
            return ApplicationObjectCreatorView(self.context, name)

    def do_POST(self, request):
        return self.create(request, self.context)


class ApplicationObjectCreatorView(View, ApplicationObjectCreator):
    """View for non-existing application objects"""

    template = Template('www/notfound.pt')
    code = 404
    reason = "Not Found"

    def __init__(self, container, name):
        View.__init__(self, None)
        self.container = container
        self.name = name

    def do_GET(self, request):
        request.setResponseCode(self.code, self.reason)
        return self.template(request, code=self.code, reason=self.reason)

    do_DELETE = do_GET

    def do_PUT(self, request):
        return self.create(request, self.container, self.name)


class UtilityServiceView(ItemTraverseView):
    """The view for the utility service"""

    template = Template("www/utilservice.pt", content_type="text/xml")

    def getName(self):
        return self.context.__name__

    def items(self):
        c = self.context
        return [{'path': getPath(utility), 'title': utility.title}
                for utility in self.context.values()]


class UtilityView(View):
    """View for utilities in general.

    Specific utilities should provide more informative views.
    """

    template = Template('www/utility.pt', content_type="text/xml")


class FacetView(View):
    """View for facets in general.

    Specific facets should provide more informative views.
    """

    template = Template('www/facet.pt', content_type="text/xml")

    def active(self):
        if self.context.active:
            return "active"
        else:
            return "inactive"

    def owned(self):
        if self.context.owner is not None:
            return "owned"
        else:
            return "unowned"

    def do_DELETE(self, request):
        if self.context.owner is not None:
            return errorPage(request, 400,
                             "Owned facets may not be deleted manually")
        FacetManager(self.context.__parent__).removeFacet(self.context)
        request.setHeader('Content-Type', 'text/plain')
        return "Facet removed"


class EventLogView(View):
    """View for EventLogFacet."""

    template = Template("www/eventlog.pt", content_type="text/xml")

    def items(self):
        return [{'timestamp': ts.isoformat(' '), 'event': event}
                for ts, event in self.context.received]

    def do_PUT(self, request):
        # XXX RFC 2616, section 9.6:
        #   The recipient of the entity MUST NOT ignore any Content-* (e.g.
        #   Content-Range) headers that it does not understand or implement
        #   and MUST return a 501 (Not Implemented) response in such cases.
        if request.content.read(1):
            return errorPage(request, 400, "Only PUT with an empty body"
                                           " is defined for event logs")
        n = len(self.context.received)
        self.context.clear()
        request.setHeader('Content-Type', 'text/plain')
        if n == 1:
            return "1 event cleared"
        else:
            return "%d events cleared" % n


class EventLogFacetView(EventLogView, FacetView):
    """A view for IEventLogFacet."""


class FacetManagementView(View, XMLPseudoParser):
    """A view of IFacetManager."""

    template = Template("www/facets.pt", content_type="text/xml")

    def _traverse(self, name, request):
        return getView(self.context.facetByName(name))

    def listFacets(self):
        activness = {False: 'inactive', True: 'active'}
        ownedness = {False: 'unowned', True: 'owned'}
        return [{'active': activness[bool(facet.active)],
                 'owned': ownedness[facet.owner is not None],
                 'title': facet.__name__,
                 'class_name': facet.__class__.__name__,
                 'path': 'facets/%s' % facet.__name__}
                for facet in self.context.iterFacets()]

    def listFacetFactories(self):
        return iterFacetFactories()

    def do_POST(self, request):
        body = request.content.read()

        try:
            factory_name = self.extractKeyword(body, 'factory')
        except KeyError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Could not find a needed param: %s" % e

        try:
            factory = getFacetFactory(factory_name)
        except KeyError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Factory does not exist: %s" % e

        facet = factory()
        self.context.setFacet(facet)

        location = ('http://%s%s/%s'
                    % (request.getRequestHostname(), request.path,
                       facet.__name__))
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Location', location)
        return "Facet created: %s" % location


class RelationshipsView(View, XMLPseudoParser):
    """A view of relationships on IRelatable which is also
    IRelationshipValencies.

    Lets the client see the relationships and valencies (GET),
    and create new relationships (POST).
    """

    template = Template("www/relationships.pt", content_type="text/xml")

    def listLinks(self):
        return [{'traverse': getPath(link.traverse()),
                 'title': link.title,
                 'type': strURI(link.reltype),
                 'role': strURI(link.role),
                 'path': getPath(link)}
                for link in self.context.listLinks()]

    def getValencies(self):
        return [{'type': strURI(type),
                 'role': strURI(role)}
                for type, role in self.context.getValencies()]

    def _traverse(self, name, request):
        link = self.context.getLink(name)
        return LinkView(link)

    def do_POST(self, request):
        body = request.content.read()

        try:
            type = self.extractKeyword(body, 'arcrole')
            role = self.extractKeyword(body, 'role')
            path = self.extractKeyword(body, 'href')
        except KeyError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Could not find a needed param: %s" % e

        try:
            type = getURI(type)
            role = getURI(role)
        except ComponentLookupError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Bad URI: %s" % e

        try:
            other = traverse(self.context, path)
        except TypeError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Nontraversable path: %s" % e

        try:
            val = self.context.getValencies()[type, role]
        except KeyError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Valency does not exist"
        kw = {val.this: self.context, val.other: other}
        links = val.schema(**kw)
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        # XXX HTTP/1.1, section 9.5:
        #     If a resource has been created on the origin server, the response
        #     SHOULD be 201 (Created) and contain an entity which describes the
        #     status of the request and refers to the new resource, and a
        #     Location header (see section 14.30).
        return "Relationship created"

class LinkView(View):

    template = Template("www/link.pt", content_type="text/xml")

    def info(self):
        return {'role': strURI(self.context.role),
                'arcrole': strURI(self.context.reltype),
                'title': self.context.title,
                'href': getPath(self.context.traverse())}

    def do_DELETE(self, request):
        self.context.unlink()
        request.setHeader('Content-Type', 'text/plain')
        return "Link removed"

def setUp():
    registerView(IPerson, PersonView)
    registerView(IGroup, GroupView)
    registerView(IApplication, ApplicationView)
    registerView(IApplicationObjectContainer, ApplicationObjectContainerView)
    registerView(IUtilityService, UtilityServiceView)
    registerView(IUtility, UtilityView)
    registerView(IEventLog, EventLogView)
    registerView(IEventLogUtility, EventLogView)
    registerView(IEventLogFacet, EventLogFacetView)
    registerView(IFacet, FacetView)

