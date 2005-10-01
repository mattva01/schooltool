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
from zope.interface import directlyProvidedBy
from zope.app import zapi, apidoc, annotation
from zope.app.location import location
from zope.app.publisher.browser import BrowserView
from zope.app.traversing.interfaces import IPhysicallyLocatable


def getTypeLink(type):
    if type is types.NoneType:
        return None
    path = apidoc.utilities.getPythonPath(type)
    return path.replace('.', '/')


class annotationsNamespace(object):
    """Used to traverse to the annotations of an object."""

    def __init__(self, ob, request=None):
        self.context = ob

    def traverse(self, name, ignore):
        # This is pretty unsafe, so this should really just be available in
        # devmode.
        naked = zope.security.proxy.removeSecurityProxy(self.context)
        annotations = annotation.interfaces.IAnnotations(naked)
        obj = name and annotations[name] or annotations
        if not IPhysicallyLocatable(obj, False):
            obj = location.LocationProxy(
                obj, self.context, '++annotations++'+name)
        return obj


class sequenceItemsNamespace(object):
    """Used to traverse to the values of a sequence."""

    def __init__(self, ob, request=None):
        self.context = ob

    def traverse(self, name, ignore):
        obj = self.context[int(name)]
        if not IPhysicallyLocatable(obj, False):
            obj = location.LocationProxy(obj, self.context, '++items++'+name)
        return obj


class mappingItemsNamespace(object):
    """Used to traverse to the values of a mapping.

    Important: This might seem like overkill, but we do not know that (1)
    every mapping has a traverser and (2) whether the location is available. A
    location might not be available, if we have a mapping in the annotations,
    for example.
    """

    def __init__(self, ob, request=None):
        self.context = ob

    def traverse(self, name, ignore):
        obj = self.context[name]
        if not IPhysicallyLocatable(obj, False):
            obj = location.LocationProxy(obj, self.context, '++items++'+name)
        return obj


class Introspector(BrowserView):

    def __init__(self, context, request):
        super(Introspector, self).__init__(context, request)
        path = apidoc.utilities.getPythonPath(
            context.__class__).replace('.', '/')
        self.klassView = zapi.traverse(
            zapi.getSiteManager(),
            '/++apidoc++/Code/%s/@@index.html' %path, request=request)

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
        # remove the security proxy, so that `attr` is not proxied. We could
        # unproxy `attr` for each turn, but that would be less efficient.
        #
        # `getPermissionIds()` also expects the class's security checker not
        # to be proxied.
        klass = zope.security.proxy.removeSecurityProxy(self.klassView.context)
        obj = zope.security.proxy.removeSecurityProxy(self.context)

        for name in apidoc.utilities.getPublicAttributes(obj):
            val = getattr(obj, name)
            if not (inspect.ismethod(val) or inspect.ismethoddescriptor(val)):
                continue
            if inspect.ismethod(val):
                signature = apidoc.utilities.getFunctionSignature(val)
            else:
                signature = '(...)'

            entry = {
                'name': name,
                'signature': signature,
                'doc': apidoc.utilities.renderText(
                     val.__doc__ or '',
                     zapi.getParent(self.klassView.context).getPath()),
                'interface': apidoc.utilities.getInterfaceForAttribute(
                     name, klass._Class__all_ifaces)}

            entry.update(apidoc.utilities.getPermissionIds(
                name, klass.getSecurityChecker()))

            yield entry

    def isSequence(self):
        return zope.interface.common.sequence.IExtendedReadSequence.providedBy(
            self.context)

    def getSequenceItems(self):
        ann = []
        # Make the object naked, so that we can inspect the value types.
        naked = zope.security.proxy.removeSecurityProxy(self.context)
        for index in xrange(0, len(self.context)):
            value = naked[index]
            ann.append({
                'index': index,
                'value': `value`,
                'value_type': type(value).__name__,
                'value_type_link': getTypeLink(type(value))
                })
        return ann

    def isMapping(self):
        return zope.interface.common.mapping.IEnumerableMapping.providedBy(
            self.context)

    def getMappingItems(self):
        ann = []
        # Make the object naked, so that we can inspect the value types.
        naked = zope.security.proxy.removeSecurityProxy(self.context)
        for key, value in naked.items():
            ann.append({
                'key': key,
                'key_string': `key`,
                'value': `value`,
                'value_type': type(value).__name__,
                'value_type_link': getTypeLink(type(value))
                })
        return ann

    def isAnnotatable(self):
        return annotation.interfaces.IAnnotatable.providedBy(self.context)

    def getAnnotationsInfo(self):
        # We purposefully strip the security here; this is the introspector,
        # so we want to see things that we usually cannot see
        naked = zope.security.proxy.removeSecurityProxy(self.context)
        annotations = annotation.interfaces.IAnnotations(naked)
        if not hasattr(annotations, 'items'):
            return
        ann = []
        for key, value in annotations.items():
            ann.append({
                'key': key,
                'key_string': `key`,
                'value': `value`,
                'value_type': type(value).__name__,
                'value_type_link': getTypeLink(type(value))
                })
        return ann
