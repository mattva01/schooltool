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
Documentation for RESTive views

$Id$
"""
__docformat__ = 'restructuredtext'

import zope.interface
from zope.component.site import AdapterRegistration
from zope.publisher.interfaces.http import IHTTPRequest

from zope.app import zapi
from zope.app.apidoc import presentation, utilities
from zope.app.apidoc.classregistry import classRegistry
from zope.app.apidoc.interfaces import IDocumentationModule
from zope.app.content.interfaces import IContentType
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile
from zope.app.publisher.browser import BrowserView


def getViewRegistration(obj, type, name):
    gsm = zapi.getGlobalSiteManager()
    spec = zope.interface.implementedBy(obj)
    adapter = gsm.adapters.lookup((spec, type), zope.interface.Interface, name)
    if adapter is None:
        return

    for reg in gsm.registrations():
        if (isinstance(reg, AdapterRegistration) and reg.value == adapter):
            return reg

def getContainerClasses(obj):
    spec = zope.interface.implementedBy(obj)
    parentAttr = spec.get('__parent__')
    if parentAttr is None:
        return []
    if not hasattr(parentAttr, 'constraint'):
        return []
    gsm = zapi.getGlobalSiteManager()
    containerInterfaces = parentAttr.constraint.types
    result = []
    for ciface in containerInterfaces:
      result += list(classRegistry.getClassesThatImplement(ciface))
    return result


class RESTMenu(object):

    def listClasses(self):
        classModule = zapi.getUtility(IDocumentationModule, "Code")

        # (0) Make sure all classes are loaded.
        self.context.get('')

        # (1) Find schooltool content types:
        # TODO: This does not support third-party code.
        contentTypes = [iface
                        for name, iface in zapi.getUtilitiesFor(IContentType)
                        if name.startswith('schooltool')]

        # (2) Find classes that implement the content types:
        results = []
        for ct in contentTypes:
            for path, klass in classRegistry.getClassesThatImplement(ct):
                klass = zapi.traverse(classModule, path.replace('.', '/'))
                results.append(
                    {'path': path,
                     'url': zapi.absoluteURL(
                                klass, self.request)+'/@@restviews.html'
                     })

        results.sort(lambda x, y: cmp(x['path'], y['path']))
        return results


class RESTDocumentation(BrowserView):

    def getGETInfo(self):
        """Get the info dictionary of the GET RESTive view.

        If there is no such view, return None.
        """
        klass = classRegistry[self.context.getPath()]
        reg = getViewRegistration(klass, IHTTPRequest, 'GET')
        info = presentation.getViewInfoDictionary(reg)

        # Doctor up the info dict a little bit. This is easier than trying to
        # do the info dict from scratch.
        if hasattr(reg.value, 'factory'):
            # We deal with a zope.app.component.metaconfigure.ProxyView
            fn = reg.value.factory.template.filename
            info['factory']['template'] = presentation.relativizePath(fn)

            info.update(utilities.getPermissionIds(
                '__call__', checker=reg.value.checker))

        return info

    def getCreatePUTInfo(self):
        """Get the info dictionary of the PUT RESTive view.

        If there is no such view, return None.
        """
        klass = classRegistry[self.context.getPath()]
        gsm = zapi.getGlobalSiteManager()
        result = []
        for path, container in getContainerClasses(klass):
            cspec = zope.interface.implementedBy(container)
            factories = gsm.adapters.lookupAll((cspec,), IFileFactory)
            for name, factory in factories:
                if not hasattr(factory.factory, 'schema'):
                    import pdb; pdb.set_trace()
                result.append({
                    'object_name': zapi.getName(self.context),
                    'container_name': container.__name__,
                    'file_extension': name,
                    'factory': presentation.getViewFactoryData(
                                   factory.factory),
                    'schema': factory.factory.schema
                    })
        return result


    def getEditPUTInfo(self):
        """Get the info dictionary of the PUT RESTive view.

        If there is no such view, return None.
        """
        gsm = zapi.getGlobalSiteManager()
        klass = classRegistry[self.context.getPath()]
        spec = zope.interface.implementedBy(klass)
        factories = gsm.adapters.lookupAll((spec,), IWriteFile)
        result = []
        for name, factory in factories:
            result.append({
                'object_name': zapi.getName(self.context),
                'factory': presentation.getViewFactoryData(
                               factory.factory),
                })
        return result


    def getDELETEInfo(self):
        """Get the info dictionary of the DELETE RESTive view.

        If there is no such view, return None.
        """
        klass = classRegistry[self.context.getPath()]
        gsm = zapi.getGlobalSiteManager()
        result = []
        for path, container in getContainerClasses(klass):
            for name, factory in factories:
                result.append({
                    'object_name': zapi.getName(self.context),
                    'container_name': container.__name__,
                    })
        return result

