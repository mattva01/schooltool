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
Views for facets.

$Id$
"""

import libxml2
from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IFacet
from schooltool.component import registerView, getView
from schooltool.component import FacetManager
from schooltool.component import getFacetFactory, iterFacetFactories
from schooltool.component import getPath
from schooltool.views import View, Template, textErrorPage
from schooltool.views import read_file
from schooltool.views import absoluteURL, absolutePath
from schooltool.views.auth import PublicAccess
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _
from schooltool.common import to_unicode

__metaclass__ = type


moduleProvides(IModuleSetup)


class FacetView(View):
    """View for facets in general.

    Specific facets should provide more informative views.
    """

    template = Template('www/facet.pt', content_type="text/xml")
    authorization = PublicAccess

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
            return textErrorPage(request,
                                 _("Owned facets may not be deleted manually"))
        path = getPath(self.context)
        FacetManager(self.context.__parent__).removeFacet(self.context)
        request.site.logAppEvent(request.authenticated_user, path,
                                 "Facet removed")
        request.setHeader('Content-Type', 'text/plain')
        return _("Facet removed")


class FacetManagementView(View):
    """A view of IFacetManager."""

    template = Template("www/facets.pt", content_type="text/xml")
    schema = read_file("../schema/facet.rng")
    authorization = PublicAccess

    def _traverse(self, name, request):
        return getView(self.context.facetByName(name))

    def listFacets(self):
        activeness = {False: 'inactive', True: 'active'}
        ownedness = {False: 'unowned', True: 'owned'}
        return [{'active': activeness[bool(facet.active)],
                 'owned': ownedness[facet.owner is not None],
                 'title': facet.__name__,
                 'href': absolutePath(self.request, facet)}
                for facet in self.context.iterFacets()]

    def listFacetFactories(self):
        return iterFacetFactories()

    def do_POST(self, request):
        body = request.content.read()

        try:
            if not validate_against_schema(self.schema, body):
                return textErrorPage(request,
                            _("Document not valid according to schema"))
        except libxml2.parserError:
            return textErrorPage(request, _("Document not valid XML"))

        doc = libxml2.parseDoc(body)
        xpathctx = doc.xpathNewContext()
        try:
            ns = 'http://schooltool.org/ns/model/0.1'
            xpathctx.xpathRegisterNs('m', ns)
            nodes = xpathctx.xpathEval('/m:facet/@factory')
            if nodes:
                factory_name = to_unicode(nodes[0].content)
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

        try:
            factory = getFacetFactory(factory_name)
        except KeyError, e:
            return textErrorPage(request, _("Factory does not exist: %s") % e)

        facet = factory()
        try:
            self.context.setFacet(facet, name=factory.facet_name)
        except ValueError, e:
            if factory.facet_name is not None:
                return textErrorPage(request,
                           _("Facet '%s' already exists") % factory.facet_name)
            else:
                return textErrorPage(request,
                           _("Could not create facet: %s") % e)

        location = absoluteURL(request, facet)
        path = getPath(facet)
        request.site.logAppEvent(request.authenticated_user, path,
                                 "Facet created")
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Location', location)
        return _("Facet created: %s") % location


def setUp():
    """See IModuleSetup."""
    registerView(IFacet, FacetView)

