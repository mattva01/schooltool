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

from zope.interface import moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IFacet
from schooltool.component import getPath
from schooltool.component import registerView, getView
from schooltool.component import FacetManager
from schooltool.component import getFacetFactory, iterFacetFactories
from schooltool.views import View, Template, textErrorPage
from schooltool.views import XMLPseudoParser
from schooltool.views import absoluteURL
from schooltool.views.auth import PublicAccess

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
                                 "Owned facets may not be deleted manually")
        FacetManager(self.context.__parent__).removeFacet(self.context)
        request.setHeader('Content-Type', 'text/plain')
        return "Facet removed"


class FacetManagementView(View, XMLPseudoParser):
    """A view of IFacetManager."""

    template = Template("www/facets.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        return getView(self.context.facetByName(name))

    def listFacets(self):
        activness = {False: 'inactive', True: 'active'}
        ownedness = {False: 'unowned', True: 'owned'}
        return [{'active': activness[bool(facet.active)],
                 'owned': ownedness[facet.owner is not None],
                 'title': facet.__name__,
                 'path': getPath(facet)}
                for facet in self.context.iterFacets()]

    def listFacetFactories(self):
        return iterFacetFactories()

    def do_POST(self, request):
        body = request.content.read()

        try:
            factory_name = self.extractKeyword(body, 'factory')
        except KeyError, e:
            return textErrorPage(request,
                                 "Could not find a needed param: %s" % e)

        try:
            factory = getFacetFactory(factory_name)
        except KeyError, e:
            return textErrorPage(request, "Factory does not exist: %s" % e)

        facet = factory()
        try:
            self.context.setFacet(facet, name=factory.facet_name)
        except ValueError, e:
            if factory.facet_name is not None:
                return textErrorPage(request,
                           "Facet '%s' already exists" % factory.facet_name)
            else:
                return textErrorPage(request,
                           "Could not create facet: %s" % e)

        location = absoluteURL(request,
                               '%s/%s' % (request.path, facet.__name__))
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Location', location)
        return "Facet created: %s" % location


def setUp():
    """See IModuleSetup."""
    registerView(IFacet, FacetView)

