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
from zope.component import getUtility
from zope.component.exceptions import ComponentLookupError
from zope.app.traversing.api import getPath, traverse, TraversalError
from schooltool.interfaces import ViewPermission
from schooltool.interfaces import ModifyPermission
from schooltool.interfaces import IURIObject
from schooltool.rest import View, Template, textErrorPage
from schooltool.rest import read_file
from schooltool.rest import absoluteURL, absolutePath
from schooltool.rest.auth import ACLAccess
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
    authorization = ACLAccess(get=ViewPermission, post=ModifyPermission)
    # It may be a bit counterintuitive that you need to have
    # ModifyPermission to add members to groups.

    def listLinks(self):
        return [{'traverse': absolutePath(self.request, link.traverse()),
                 'title': link.title,
                 'type': link.reltype.uri,
                 'role': link.role.uri,
                 'href': absolutePath(self.request, link)}
                for link in self.context.listLinks()]

    def getValencies(self):
        return [{'type': type.uri,
                 'role': role.uri}
                for type, role in self.context.getValencies()]

    def _traverse(self, name, request):
        link = self.context.getLink(name)
        return LinkView(link)

    def do_POST(self, request):
        body = request.content.read()

        # TODO: rewrite this using schooltool.rest.xmlparser.XMLDocument
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
            type = getUtility(IURIObject, type)
            role = getUtility(IURIObject, role)
        except ComponentLookupError, e:
            return textErrorPage(request, _("Bad URI: %s") % e[1])

        try:
            other = traverse(self.context, path)
        except TraversalError, e:
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
        request.appLog(_("Relationship '%s' between %s and %s created")
                       % (link.reltype.name, getPath(self.context),
                          getPath(other)))
        request.setHeader('Location', location)
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        return _("Relationship created: %s") % location


class LinkView(View):
    """A view on relationship links."""

    template = Template("www/link.pt", content_type="text/xml")
    authorization = ACLAccess(get=ViewPermission, delete=ModifyPermission)

    def info(self):
        return {'role': self.context.role.uri,
                'arcrole': self.context.reltype.uri,
                'title': self.context.title,
                'href': absolutePath(self.request, self.context.traverse())}

    def do_DELETE(self, request):
        msg = (_("Relationship '%s' between %s and %s removed") %
               (self.context.reltype.name,
                getPath(self.context.source),
                getPath(self.context.traverse())))
        self.context.unlink()
        request.appLog(msg)
        request.setHeader('Content-Type', 'text/plain')
        return _("Link removed")

