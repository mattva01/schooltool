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
Introspector

$Id$
"""
__docformat__ = 'restructuredtext'

import inspect
import types
import zope.interface
import zope.security.proxy

from zope.component.exceptions import ComponentLookupError
from zope.interface import directlyProvides, directlyProvidedBy

from zope.app import zapi, apidoc
from zope.app.component.interface import getInterface
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.interfaces import IPhysicallyLocatable

def getTypeLink(type):
    if type is types.NoneType:
        return None
    path = apidoc.utilities.getPythonPath(type)
    return path.replace('.', '/')


class Introspector(BrowserView):

    def __init__(self, context, request):
        super(Introspector, self).__init__(context, request)
        path = apidoc.utilities.getPythonPath(
            context.__class__).replace('.', '/')
        self.klassView = zapi.traverse(
            context, '/++apidoc++/Code/%s/@@index.html' %path, request=request)

    def parent(self):
        return zapi.getParent(self.context)

    def getBaseURL(self):
        return self.klassView.getBaseURL()

    def getDirectlyProvidedInterfaces(self):
        return [getPythonPath(iface)
                for iface in zope.interface.directlyProvidedBy(self.context)]

    def getImplementedInterfaces(self):
        return self.klassView.getInterfaces()

    def getBases(self):
        return self.klassView.getBases()

    def getAttributes(self):
        # remove the security proxy, so that `attr` is not proxied. We could
        # unproxy `attr` for each turn, but that would be less efficient.
        #
        # `getPermissionIds()` also expects the class's security checker not
        # to be proxied.
        klass = zope.security.proxy.removeSecurityProxy(self.klassView.context)
        obj = zope.security.proxy.removeSecurityProxy(self.context)

        for name in apidoc.utilities.getPublicAttributes(obj):
            value = getattr(obj, name)
            if inspect.ismethod(value) or inspect.ismethoddescriptor(value):
                continue
            entry = {
                'name': name,
                'value': `value`,
                'value_linkable': IPhysicallyLocatable(value, False) and True,
                'type': type(value).__name__,
                'type_link': getTypeLink(type(value)),
                'interface': apidoc.utilities.getInterfaceForAttribute(
                                 name, klass._Class__all_ifaces)
                }
            entry.update(apidoc.utilities.getPermissionIds(
                name, klass.getSecurityChecker()))
            yield entry

    def getMethods(self):
        return self.klassView.getMethods()

