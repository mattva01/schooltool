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

from zope.app.traversing.api import getPath, traverse, TraversalError
from schooltool.interfaces import Everybody
from schooltool.rest import View, Template, textErrorPage
from schooltool.rest import read_file
from schooltool.rest.auth import SystemAccess
from schooltool.rest.xmlparsing import XMLDocument, XMLError
from schooltool.translation import ugettext as _

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
            doc = XMLDocument(body, self.schema)
        except XMLError, e:
            return textErrorPage(request, e)
        try:
            doc.registerNs('m', 'http://schooltool.org/ns/model/0.1')
            doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')
            perms = doc.query('/m:acl/m:allow')

            # XXX bug: if a bad path is specified, a partial transaction is
            #          committed
            self.context.clear()
            for perm in perms:
                path = perm['principal']
                permission = perm['permission']
                if path == Everybody:
                    principal = path
                else:
                    try:
                        principal = traverse(self.context, path)
                    except TraversalError:
                        return textErrorPage(request, _("Bad path %r") % path)
                self.context.add((principal, permission))
        finally:
            doc.free()

        request.setResponseCode(200)
        request.setHeader('Content-Type', 'text/plain')
        return _("ACL saved")

