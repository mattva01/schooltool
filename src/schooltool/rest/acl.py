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
The views for the ACL objects.

$Id$
"""

import libxml2
from schooltool.interfaces import Everybody
from schooltool.component import traverse, getPath
from schooltool.rest import View, Template, textErrorPage
from schooltool.rest import read_file
from schooltool.rest.auth import SystemAccess
from schooltool.schema.rng import validate_against_schema
from schooltool.translation import ugettext as _
from schooltool.common import to_unicode

__metaclass__ = type


class ACLView(View):
    """A view on ACLs"""

    authorization = SystemAccess
    template = Template("www/acl.pt", content_type="text/xml")
    schema = read_file("../schema/acl.rng")

    def listPerms(self):
        return ([{'path': getPath(principal),
                  'title': principal.title,
                  'perm': perm}
                 for (principal, perm) in self.context
                 if principal != Everybody ] +
                [{'path': 'Everybody',
                  'title': 'Everybody',
                  'perm': perm}
                for (principal, perm) in self.context
                if principal == Everybody ])

    def do_PUT(self, request):
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
            perms  = xpathctx.xpathEval('/m:acl/m:allow')

            self.context.clear()
            for perm in perms:
                path = to_unicode(perm.nsProp('principal', None))
                permission = perm.nsProp('permission', None)
                if path == Everybody:
                    principal = path
                else:
                    try:
                        principal = traverse(self.context, path)
                    except TypeError:
                        return textErrorPage(request, _("Bad path %r") % path)
                self.context.add((principal, permission))
        finally:
            doc.freeDoc()
            xpathctx.xpathFreeContext()

        request.setResponseCode(200)
        request.setHeader('Content-Type', 'text/plain')
        return _("ACL saved")

