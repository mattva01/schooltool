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
import sets
import datetime
import libxml2
from zope.interface import moduleProvides
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from twisted.web.resource import Resource
from schooltool.interfaces import IGroup, IPerson, URIMember, URIGroup
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IUtilityService, IUtility, IFacet
from schooltool.interfaces import IModuleSetup, IAbsenceTrackerUtility
from schooltool.interfaces import IAbsenceTrackerFacet
from schooltool.interfaces import ComponentLookupError, Unchanged
from schooltool.component import getPath, traverse, getRelatedObjects
from schooltool.component import getView, registerView, strURI, getURI
from schooltool.component import FacetManager, iterFacetFactories
from schooltool.component import getFacetFactory
from schooltool.debug import IEventLog, IEventLogUtility, IEventLogFacet
from schooltool.model import AbsenceComment

__metaclass__ = type


moduleProvides(IModuleSetup)


#
# Helpers
#

def absoluteURL(request, path):
    """Returns the absulute URL of the object adddressed with path"""
    if not path.startswith('/'):
        raise ValueError("Path must be absolute")
    return 'http://%s%s' % (request.getRequestHostname(), path)


def parse_datetime(s):
    """Parses ISO 8601 date/time values.

    Only a small subset of ISO 8601 is accepted:

      YYYY-MM-DD HH:MM:SS
      YYYY-MM-DD HH:MM:SS.ssssss
      YYYY-MM-DDTHH:MM:SS
      YYYY-MM-DDTHH:MM:SS.ssssss

    Returns a datetime.datetime object without a time zone.
    """
    m = re.match("(\d+)-(\d+)-(\d+)[ T](\d+):(\d+):(\d+)([.](\d+))?$", s)
    if not m:
        raise ValueError("Bad datetime: %s" % s)
    ssssss = m.groups()[7]
    if ssssss:
        ssssss = int((ssssss + "00000")[:6])
    else:
        ssssss = 0
    y, m, d, hh, mm, ss = map(int, m.groups()[:6])
    return datetime.datetime(y, m, d, hh, mm, ss, ssssss)


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
        do_FOO      Method that processes HTTP requests FOO for various values
                    of FOO.  Its signature should match render.

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
            body = handler(request)
            assert isinstance(body, str), \
                   "do_%s did not return a string" % request.method
            return body
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

    def _traverse(self, name, request):
        if name == 'rollcall':
            return RollcallView(self.context)
        if name == 'tree':
            return TreeView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)

    def listItems(self):
        for item in getRelatedObjects(self.context, URIMember):
            yield {'title': item.title, 'path': getPath(item)}


class PersonView(ApplicationObjectTraverserView):
    """The view for a person object"""

    template = Template("www/person.pt", content_type="text/xml")

    def _traverse(self, name, request):
        if name == 'absences':
            return AbsenceManagementView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)

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
        location = absoluteURL(request, getPath(obj))
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Location', location)
        return "Object created: %s" % location


class ApplicationObjectContainerView(TraversableView,
                                     ApplicationObjectCreator):
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
                for ts, event in self.context.getReceived()]

    def do_PUT(self, request):
        # XXX RFC 2616, section 9.6:
        #   The recipient of the entity MUST NOT ignore any Content-* (e.g.
        #   Content-Range) headers that it does not understand or implement
        #   and MUST return a 501 (Not Implemented) response in such cases.
        if request.content.read(1):
            return errorPage(request, 400, "Only PUT with an empty body"
                                           " is defined for event logs")
        n = len(self.context.getReceived())
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
                 'path': getPath(facet)}
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

        location = absoluteURL(request,
                               '%s/%s' % (request.path, facet.__name__))
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
        try:
            links = val.schema(**kw)
        except ValueError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Cannot establish relationship: %s" % e

        link = links[val.other]
        location = absoluteURL(request, getPath(link))
        request.setHeader('Location', location)
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        return "Relationship created: %s" % location


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


class AbsenceCommentParser(XMLPseudoParser):

    def parseComment(self, request):
        """Parse and create an AbsenceComment from a given request body"""
        body = request.content.read()

        try:
            text = self.extractKeyword(body, 'text')
        except KeyError:
            raise ValueError("Text attribute missing")

        try:
            reporter_path = self.extractKeyword(body, 'reporter')
        except KeyError:
            raise ValueError("Reporter attribute missing")
        else:
            try:
                reporter = traverse(self.context, reporter_path)
            except KeyError:
                raise ValueError("Reporter not found: %s" % reporter_path)

        try:
            dt = self.extractKeyword(body, 'datetime')
        except KeyError:
            dt = None
        else:
            dt = parse_datetime(dt)

        try:
            absent_from_path = self.extractKeyword(body, 'absent_from')
        except KeyError:
            absent_from = None
        else:
            try:
                absent_from = traverse(self.context, absent_from_path)
            except KeyError:
                raise ValueError("Object not found: %s" % reporter_path)

        try:
            ended = self.extractKeyword(body, 'ended')
        except KeyError:
            ended = Unchanged
        else:
            d = {'ended': True, 'unended': False}
            if ended not in d:
                raise ValueError("Bad value for ended", ended)
            ended = d[ended]

        try:
            resolved = self.extractKeyword(body, 'resolved')
        except KeyError:
            resolved = Unchanged
        else:
            d = {'resolved': True, 'unresolved': False}
            if resolved not in d:
                raise ValueError("Bad value for resolved", resolved)
            resolved = d[resolved]

        try:
            expected_presence = self.extractKeyword(body, 'expected_presence')
        except KeyError:
            expected_presence = Unchanged
        else:
            if expected_presence == '':
                expected_presence = None
            else:
                expected_presence = parse_datetime(expected_presence)

        comment = AbsenceComment(reporter, text, absent_from=absent_from,
                                 dt=dt, ended=ended, resolved=resolved,
                                 expected_presence=expected_presence)

        return comment


class AbsenceListViewMixin:

    def _listAbsences(self, absences, titles):
        endedness = {False: 'unended', True: 'ended'}
        resolvedness = {False: 'unresolved', True: 'resolved'}
        person_title = None
        for absence in absences:
            expected_presence = None
            if absence.expected_presence is not None:
                expected_presence = absence.expected_presence.isoformat(' ')
            if titles:
                person_title = absence.person.title
            yield {'title': absence.__name__,
                   'path': getPath(absence),
                   'person_title': person_title,
                   'datetime': absence.comments[0].datetime.isoformat(' '),
                   'expected_presence': expected_presence,
                   'ended': endedness[absence.ended],
                   'resolved': resolvedness[absence.resolved]}


class AbsenceManagementView(View, AbsenceCommentParser, AbsenceListViewMixin):

    template = Template('www/absences.pt', content_type="text/xml")

    def _traverse(self, name, request):
        absence = self.context.getAbsence(name)
        return AbsenceView(absence)

    def listAbsences(self):
        return self._listAbsences(self.context.iterAbsences(), False)

    def do_POST(self, request):
        try:
            comment = self.parseComment(request)
        except ValueError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return str(e)
        absence = self.context.reportAbsence(comment)
        location = absoluteURL(request, getPath(absence))
        request.setHeader('Location', location)
        request.setHeader('Content-Type', 'text/plain')
        if len(absence.comments) == 1:
            request.setResponseCode(201, 'Created')
            return "Absence created: %s" % getPath(absence)
        else:
            request.setResponseCode(200, 'OK')
            return "Absence updated: %s" % getPath(absence)


class AbsenceView(View, AbsenceCommentParser):

    template = Template('www/absence.pt', content_type="text/xml")

    def ended(self):
        if self.context.ended:
            return "ended"
        else:
            return "unended"

    def resolved(self):
        if self.context.resolved:
            return "resolved"
        else:
            return "unresolved"

    def expected_presence(self):
        if self.context.expected_presence:
            return self.context.expected_presence.isoformat(' ')
        else:
            return None

    def person_href(self):
        return getPath(self.context.person)

    def person_title(self):
        return self.context.person.title

    def listComments(self):
        endedness = {Unchanged: None, False: 'unended', True: 'ended'}
        resolvedness = {Unchanged: None, False: 'unresolved', True: 'resolved'}
        for comment in self.context.comments:
            absent_from_title = absent_from_href = None
            if comment.absent_from is not None:
                absent_from_href = getPath(comment.absent_from)
                absent_from_title = comment.absent_from.title
            if comment.expected_presence is Unchanged:
                expected_presence = None
            elif comment.expected_presence is None:
                expected_presence = ''
            else:
                expected_presence = comment.expected_presence.isoformat(' ')
            yield {'datetime': comment.datetime.isoformat(' '),
                   'text': comment.text,
                   'reporter_title': comment.reporter.title,
                   'reporter_href': getPath(comment.reporter),
                   'absent_from_title': absent_from_title,
                   'absent_from_href': absent_from_href,
                   'ended': endedness[comment.ended],
                   'resolved': resolvedness[comment.resolved],
                   'expected_presence': expected_presence}

    def do_POST(self, request):
        try:
            comment = self.parseComment(request)
        except ValueError, e:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return str(e)
        try:
            self.context.addComment(comment)
        except ValueError:
            request.setResponseCode(400, 'Bad request')
            request.setHeader('Content-Type', 'text/plain')
            return "Cannot reopen an absence when another one is not ended"
        request.setHeader('Content-Type', 'text/plain')
        return "Comment added"


class RollcallView(View):

    template = Template('www/rollcall.pt', content_type="text/xml")

    def groupPath(self):
        return getPath(self.context)

    def listPersons(self, group=None, _already_added=None):
        if group is None:
            group = self.context
        if _already_added is None:
            _already_added = sets.Set()
        results = []
        for member in getRelatedObjects(group, URIMember):
            if (IPerson.isImplementedBy(member)
                and member not in _already_added):
                absence = member.getCurrentAbsence()
                if absence is None:
                    presence = "present"
                    expected_presence = None
                else:
                    presence = "absent"
                    expected_presence = absence.expected_presence
                    if expected_presence:
                        expected_presence = expected_presence.isoformat(' ')
                _already_added.add(member)
                results.append({'title': member.title, 'href': getPath(member),
                                'presence': presence,
                                'expected_presence': expected_presence})
            if IGroup.isImplementedBy(member):
                results.extend(self.listPersons(member, _already_added))
        return results

    def parseRollcall(self, request):
        """Parse roll call document.

        Returns (datetime, reporter, comment_text, items) where items is a list
        of (person, present).
        """
        body = request.content.read()
        try:
            doc = libxml2.parseDoc(body)
        except libxml2.parserError:
            raise ValueError("Bad roll call representation")
        ctx = doc.xpathNewContext()
        xlink = "http://www.w3.org/1999/xlink"
        try:
            ctx.xpathRegisterNs("xlink", xlink)

            res = ctx.xpathEval("/rollcall/@datetime")
            if res:
                dt = parse_datetime(res[0].content)
            else:
                dt = None

            res = ctx.xpathEval("/rollcall/reporter/@xlink:href")
            if not res:
                raise ValueError("Reporter not specified")
            path = res[0].content
            try:
                reporter = traverse(self.context, path)
            except KeyError:
                raise ValueError("Reporter not found: %s" % path)

            items = []
            presence = {'present': True, 'absent': False}
            resolvedness = {None: Unchanged, 'resolved': True,
                            'unresolved': False}
            seen = sets.Set()
            members = sets.Set([item['href'] for item in self.listPersons()])
            for node in ctx.xpathEval("/rollcall/person"):
                path = node.nsProp('href', xlink)
                if path is None:
                    raise ValueError("Person does not specify xlink:href")
                if path in seen:
                    raise ValueError("Person mentioned more than once: %s"
                                     % path)
                seen.add(path)
                if path not in members:
                    raise ValueError("Person %s is not a member of %s"
                                     % (path, getPath(self.context)))
                person = traverse(self.context, path)
                try:
                    present = presence[node.nsProp('presence', None)]
                except KeyError:
                    raise ValueError("Bad presence value for %s" % path)
                try:
                    resolved = resolvedness[node.nsProp('resolved', None)]
                except KeyError:
                    raise ValueError("Bad resolved value for %s" % path)
                if resolved is True and not present:
                    raise ValueError("Cannot resolve an absence for absent"
                                     " person %s" % path)
                text = node.nsProp('comment', None)
                items.append((person, present, resolved, text))
            if seen != members:
                missing = list(members - seen)
                missing.sort()
                raise ValueError("Persons not mentioned: %s"
                                 % ', '.join(missing))
            return dt, reporter, items
        finally:
            doc.freeDoc()
            ctx.xpathFreeContext()

    def do_POST(self, request):
        request.setHeader('Content-Type', 'text/plain')
        nabsences = npresences = 0
        try:
            dt, reporter, items = self.parseRollcall(request)
        except ValueError, e:
            request.setResponseCode(400, 'Bad request')
            return str(e)
        for person, present, resolved, text in items:
            if not present:
                person.reportAbsence(AbsenceComment(reporter, text, dt=dt,
                                                    absent_from=self.context))
                nabsences += 1
            if present and person.getCurrentAbsence() is not None:
                person.reportAbsence(AbsenceComment(reporter, text, dt=dt,
                                                    absent_from=self.context,
                                                    ended=True,
                                                    resolved=resolved))
                npresences += 1
        return ("%d absences and %d presences reported"
                % (nabsences, npresences))


class AbsenceTrackerView(View, AbsenceListViewMixin):

    template = Template('www/absences.pt', content_type='text/xml')
    template_html = Template('www/absences_html.pt', content_type='text/html')

    utcnow = datetime.datetime.utcnow

    def format_reason(self, reason):
        if reason is None:
            return ''
        else:
            return ' (%s)' % reason

    def format_date(self, date, now):
        if date.date() == now.date():
            return 'today'
        else:
            return date.strftime('%Y-%m-%d')

    def text_template(self, request):
        request.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        result = []
        now = self.utcnow()
        format_reason = self.format_reason
        format_date = self.format_date
        header = "Absences at %s" % (now.strftime("%H:%M%P %Y-%m-%d UTC"))
        result.append("%s\n%s\n" % (header, "=" * len(header)))
        result.append("Unexpected absences\n"
                      "-------------------\n")
        unexpected = self.unexpected(now)
        if not unexpected:
            result.append("None")
        else:
            for absence in unexpected:
                if absence.expected_presence:
                    when_expected = absence.expected_presence
                    age = now - when_expected
                    seconds_in_day = 86400
                    agestring = '%dh%dm' % divmod(
                        (age.days * seconds_in_day + age.seconds) / 60, 60)
                    reason = absence.comments[-1].text
                    result.append("%s expected %s ago, at %s %s%s" %
                                  (absence.person.title,
                                   agestring,
                                   when_expected.strftime("%I:%M%P"),
                                   format_date(when_expected, now),
                                   format_reason(reason)
                                   ))
                else:
                    start = absence.comments[0].datetime
                    age = now - start
                    seconds_in_day = 86400
                    agestring = '%dh%dm' % divmod(
                        (age.days * seconds_in_day + age.seconds) / 60, 60)
                    reason = absence.comments[-1].text
                    result.append("%s absent for %s, since %s %s%s" %
                                  (absence.person.title,
                                   agestring,
                                   start.strftime("%I:%M%P"),
                                   format_date(start, now),
                                   format_reason(reason)
                                   ))
        result.append("\n"
                      "Expected absences\n"
                      "-----------------\n")
        expected = self.expected(now)
        if not expected:
            result.append("None")
        else:
            for absence in expected:
                when_expected = absence.expected_presence
                age = when_expected - now
                seconds_in_day = 86400
                agestring = '%dh%dm' % divmod(
                    (age.days * seconds_in_day + age.seconds) / 60, 60)
                reason = absence.comments[-1].text
                result.append("%s expected in %s, at %s %s%s" %
                              (absence.person.title,
                               agestring,
                               when_expected.strftime("%I:%M%P"),
                               format_date(when_expected, now),
                               format_reason(reason)
                               ))
        result.append("")
        return "\n".join(result)

    def unexpected(self, now):
        L = [(absence.expected_presence or absence.comments[0].datetime,
              absence)
             for absence in self.context.absences
             if absence.expected_presence is None or
             absence.expected_presence < now]
        L.sort()
        return [absence for sortkey, absence in L]

    def expected(self, now):
        L = [(absence.expected_presence, absence)
             for absence in self.context.absences
             if absence.expected_presence is not None and
             absence.expected_presence >= now]
        L.sort()
        return [absence for sortkey, absence in L]

    def listAbsences(self):
        return self._listAbsences(self.context.absences, True)

    def do_GET(self, request):
        if 'text/plain' in [row[1] for row in request.accept]:
            return self.text_template(request)
        else:
            return self.template(request, view=self, context=self.context)


class AbsenceTrackerFacetView(AbsenceTrackerView, FacetView):
    pass


class TreeView(View):

    template = Template('www/tree.pt', content_type='text/xml')
    node_template = Template('www/tree_node.pt', content_type='text/xml')

    def generate(self, node, request):
        children = [child for child in getRelatedObjects(node, URIMember)
                    if IGroup.isImplementedBy(child)]
        res = self.node_template(request, title=node.title, href=getPath(node),
                                 children=children, generate=self.generate)
        return res.strip().replace('\n', '\n  ')


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
    registerView(IAbsenceTrackerUtility, AbsenceTrackerView)
    registerView(IAbsenceTrackerFacet, AbsenceTrackerFacetView)
    registerView(IFacet, FacetView)

