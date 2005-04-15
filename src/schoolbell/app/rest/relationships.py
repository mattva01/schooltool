#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
RESTive views for relationships
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager

$Id$
"""
from zope.app import zapi
from zope.component.interfaces import ComponentLookupError
from zope.component import getUtility
from zope.app.traversing.api import traverse
from zope.app.traversing.interfaces import TraversalError

from schoolbell.app.rest.errors import RestError
from schoolbell.relationship.annotatable import getRelationshipLinks
from schoolbell.relationship.uri import IURIObject
from schoolbell.app.browser.app import ACLViewBase, hasPermission
from schoolbell.app.rest import View, Template
from schoolbell.app.rest.errors import RestError
from schoolbell.app.rest.xmlparsing import XMLDocument
from schoolbell.app.rest.xmlparsing import XMLDocument
from schoolbell.relationship.interfaces import IRelationshipLinks
from schoolbell.relationship.interfaces import IRelationshipSchema
from schoolbell.relationship.relationship import relate, unrelate

from schoolbell import SchoolBellMessageID as _

class RelationshipsView(View):
    """A view of relationships on IRelatable which is also
    IRelationshipValencies.

    Lets the client see the relationships (GET),
    and create new relationships (POST).
    """

    template = Template("www/relationships.pt",
                        content_type="text/xml; charset=UTF-8")

    schema = """<?xml version="1.0" encoding="UTF-8"?>
    <!--
    RelaxNG grammar for a relationships
    -->
    <grammar xmlns="http://relaxng.org/ns/structure/1.0"
             xmlns:xlink="http://www.w3.org/1999/xlink"
             ns="http://schooltool.org/ns/model/0.1"
             datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
      <!-- parts of a simple xlink -->
      <define name="simplelinktype">
        <attribute name="xlink:type">
          <value>simple</value>
        </attribute>
      </define>
      <define name="href">
        <attribute name="xlink:href">
          <data type="anyURI"/>
        </attribute>
      </define>
      <define name="role">
        <attribute name="xlink:role">
          <data type="anyURI"/>
        </attribute>
      </define>
      <define name="arcrole">
        <attribute name="xlink:arcrole">
          <data type="anyURI"/>
        </attribute>
      </define>
      <define name="title">
        <attribute name="xlink:title">
          <text/>
        </attribute>
      </define>
      <define name="show">
        <attribute name="xlink:show">
          <choice>
            <value>new</value>
            <value>replace</value>
            <value>embed</value>
            <value>other</value>
            <value>none</value>
          </choice>
        </attribute>
      </define>
      <define name="actuate">
        <attribute name="xlink:actuate">
          <choice>
            <value>onLoad</value>
            <value>onRequest</value>
            <value>other</value>
            <value>none</value>
          </choice>
        </attribute>
      </define>
      <start>
        <element name="relationship">
          <ref name="simplelinktype"/>
          <ref name="href"/>
          <ref name="role"/>
          <ref name="arcrole"/>
          <optional>
            <ref name="title"/>
          </optional>
          <optional>
            <ref name="show"/>
          </optional>
          <optional>
            <ref name="actuate"/>
          </optional>
        </element>
      </start>
    </grammar>"""

    # It may be a bit counterintuitive that you need to have
    # ModifyPermission to add members to groups.

    def listLinks(self):
        return [{'traverse': zapi.getPath(link.target),
                 'type': link.rel_type.uri,
                 'role': link.my_role.uri,
                 'href': zapi.getPath(link)}
                for link in IRelationshipLinks(self.context)]

    def linkAbsoluteURL(self, link):
        return "%s/%s/%s" % (zapi.absoluteURL(self.context, self.request),
                             link.role.name,
                             link.target.__name__)

    def POST(self):
        body = self.request.bodyFile.read()
        response = self.request.response

        doc = XMLDocument(body, self.schema)
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')
            node = doc.query('/m:relationship')[0]
            rel_type = node['xlink:arcrole']
            target_role = node['xlink:role']
            path = node['xlink:href']
        finally:
            doc.free()

        try:
            schema = getUtility(IRelationshipSchema, rel_type)
            target_role = getUtility(IURIObject, target_role)
        except ComponentLookupError, e:
            raise RestError("Bad URI: %s" % e[1])


        try:
            target = traverse(self.context, path)
        except TraversalError, e:
            raise RestError("Bad URI: %s" % e[1])

        role1, role2 = schema.roles.values()
        if target_role == role1:
            my_role = role2
        else:
            my_role = role1

        rel_type = schema.rel_type
        relate(rel_type, (self.context, my_role), (target, target_role))

        link = getRelationshipLinks(self.context).find(my_role,
                                                       target,
                                                       target_role,
                                                       rel_type)
        location = zapi.getPath(link)

        response.setHeader('Location', location)
        response.setStatus(201)
        response.setHeader('Content-Type', 'text/plain; charset=UTF-8')
        return _("Relationship created: %s") % location


class LinkView(View):
    """A view on relationship links."""

    template = Template("www/link.pt", content_type="text/xml; charset=UTF-8")

    def info(self):
        return {'role': self.context.role.uri,
                'arcrole': self.context.rel_type.uri,
                'href': zapi.getPath(self.context.target)}

    def DELETE(self):
        unrelate(self.context.rel_type,
                 (self.context.__parent__.__parent__, self.context.my_role),
                 (self.context.target, self.context.role))

        response = self.request.response
        response.setStatus(201)
        response.setHeader('content-type', 'text/plain; charset=UTF-8')
        return _("Link removed")
