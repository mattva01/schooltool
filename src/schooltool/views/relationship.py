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

import libxml2
from schooltool.interfaces import ComponentLookupError
from schooltool.uris import strURI, getURI
from schooltool.component import traverse, getPath
from schooltool.views import View, Template, textErrorPage
from schooltool.views import read_file
from schooltool.views import absoluteURL, absolutePath
from schooltool.views.auth import PublicAccess
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _
from schooltool.common import to_unicode

__metaclass__ = type


class RelationshipsView(View):
    """A view of relationships on IRelatable which is also
    IRelationshipValencies.

    Lets the client see the relationships and valencies (GET),
    and create new relationships (POST).
    """

    template = Template("www/relationships.pt", content_type="text/xml")
    schema = read_file("../schema/relationship.rng")
    authorization = PublicAccess

    def listLinks(self):
        return [{'traverse': absolutePath(self.request, link.traverse()),
                 'title': link.title,
                 'type': strURI(link.reltype),
                 'role': strURI(link.role),
                 'href': absolutePath(self.request, link)}
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
            xlink = 'http://www.w3.org/1999/xlink'
            xpathctx.xpathRegisterNs('xlink', xlink)
            node = xpathctx.xpathEval('/m:relationship')[0]
            type = to_unicode(node.nsProp('arcrole', xlink))
            role = to_unicode(node.nsProp('role', xlink))
            path = to_unicode(node.nsProp('href', xlink))
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

        try:
            type = getURI(type)
            role = getURI(role)
        except ComponentLookupError, e:
            return textErrorPage(request, _("Bad URI: %s") % e)

        try:
            other = traverse(self.context, path)
        except TypeError, e:
            return textErrorPage(request, _("Nontraversable path: %s") % e)

        try:
            val = self.context.getValencies()[type, role]
        except KeyError, e:
            return textErrorPage(request, _("Valency does not exist"))

        kw = {val.this: self.context, val.other: other}
        try:
            links = val.schema(**kw)
        except ValueError, e:
            return textErrorPage(request,
                                 _("Cannot establish relationship: %s") % e)

        link = links[val.other]
        location = absoluteURL(request, link)
        request.site.logAppEvent(request.authenticated_user,
                                 "Relationship created: %s" % getPath(link))
        request.setHeader('Location', location)
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        return _("Relationship created: %s") % location


class LinkView(View):
    """A view on relationship links."""

    template = Template("www/link.pt", content_type="text/xml")
    authorization = PublicAccess

    def info(self):
        return {'role': strURI(self.context.role),
                'arcrole': strURI(self.context.reltype),
                'title': self.context.title,
                'href': absolutePath(self.request, self.context.traverse())}

    def do_DELETE(self, request):
        self.context.unlink()
        request.site.logAppEvent(request.authenticated_user,
                                 "Link removed: %s" % getPath(self.context))
        request.setHeader('Content-Type', 'text/plain')
        return _("Link removed")

