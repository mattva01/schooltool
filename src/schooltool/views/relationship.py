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
The views for the schooltool.relationship objects.

$Id: __init__.py 397 2003-11-21 11:38:01Z mg $
"""

from schooltool.interfaces import ComponentLookupError
from schooltool.uris import strURI, getURI
from schooltool.component import getPath, traverse
from schooltool.views import View, Template, textErrorPage
from schooltool.views import XMLPseudoParser
from schooltool.views import absoluteURL
from schooltool.views.auth import PublicAccess

__metaclass__ = type


class RelationshipsView(View, XMLPseudoParser):
    """A view of relationships on IRelatable which is also
    IRelationshipValencies.

    Lets the client see the relationships and valencies (GET),
    and create new relationships (POST).
    """

    template = Template("www/relationships.pt", content_type="text/xml")
    authorization = PublicAccess

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
            return textErrorPage(request,
                                 "Could not find a needed param: %s" % e)

        try:
            type = getURI(type)
            role = getURI(role)
        except ComponentLookupError, e:
            return textErrorPage(request, "Bad URI: %s" % e)

        try:
            other = traverse(self.context, path)
        except TypeError, e:
            return textErrorPage(request, "Nontraversable path: %s" % e)

        try:
            val = self.context.getValencies()[type, role]
        except KeyError, e:
            return textErrorPage(request, "Valency does not exist")

        kw = {val.this: self.context, val.other: other}
        try:
            links = val.schema(**kw)
        except ValueError, e:
            return textErrorPage(request,
                                 "Cannot establish relationship: %s" % e)

        link = links[val.other]
        location = absoluteURL(request, getPath(link))
        request.setHeader('Location', location)
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        return "Relationship created: %s" % location


class LinkView(View):
    """A view on relationship links."""

    template = Template("www/link.pt", content_type="text/xml")
    authorization = PublicAccess

    def info(self):
        return {'role': strURI(self.context.role),
                'arcrole': strURI(self.context.reltype),
                'title': self.context.title,
                'href': getPath(self.context.traverse())}

    def do_DELETE(self, request):
        self.context.unlink()
        request.setHeader('Content-Type', 'text/plain')
        return "Link removed"

