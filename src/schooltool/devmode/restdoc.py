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
import types

import zope.interface
from zope.component.site import AdapterRegistration, SubscriptionRegistration
from zope.publisher.interfaces.http import IHTTPRequest

from zope.app import zapi
from zope.app.apidoc import presentation, utilities, component
from zope.app.apidoc.ifacemodule.browser import findAPIDocumentationRoot
from zope.app.apidoc.classregistry import classRegistry
from zope.app.apidoc.interfaces import IDocumentationModule
from zope.app.basicskin.standardmacros import StandardMacros
from zope.app.container.interfaces import IContainer
from zope.app.content.interfaces import IContentType
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile
from zope.app.http.put import FilePUT
from zope.app.publisher.browser import BrowserView

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.traverser.interfaces import ITraverserPlugin
from schooltool.traverser.traverser import AdapterTraverserPluginTemplate
from schooltool.traverser.traverser import NullTraverserPluginTemplate


def getHTTPViewRegistration(klass, name):
    """Return a view registration for the given object, type and name."""
    gsm = zapi.getGlobalSiteManager()
    spec = zope.interface.implementedBy(klass)
    adapter = gsm.adapters.lookup(
        (spec, IHTTPRequest), zope.interface.Interface, name)

    if adapter is None:
        return

    for reg in gsm.registrations():
        if (isinstance(reg, AdapterRegistration) and reg.value == adapter):
            return reg


def getContainerInterfaces(klass):
    """Get a list of interfaces that describe containers in which instances of
    the given class can be located.
    """
    spec = zope.interface.implementedBy(klass)
    parentAttr = spec.get('__parent__')

    if parentAttr is None or not hasattr(parentAttr, 'constraint'):
        # Custom hack to give schooltool containers a container interface
        if spec.isOrExtends(IContainer):
            return (ISchoolToolApplication,)
        return ()

    return parentAttr.constraint.types


def getAdapters(spec, provided):
    gsm = zapi.getGlobalSiteManager()
    factories = [
        factory
        for name, factory in gsm.adapters.lookupAll((spec,), provided)]
    return [
        reg
        for reg in gsm.registrations()
        if (isinstance(reg, AdapterRegistration) and reg.value in factories)]


def getNameTraversers(klass):
    gsm = zapi.getGlobalSiteManager()
    spec = zope.interface.implementedBy(klass)
    factories = [f for f in gsm.adapters.subscriptions((spec, IHTTPRequest),
                                                       ITraverserPlugin)]
    return [
        reg
        for reg in gsm.registrations()
        if (isinstance(reg, SubscriptionRegistration)
            and reg.value in factories)]


class RESTDocMacros(StandardMacros):
    """Page Template METAL macros for API Documentation"""
    macro_pages = ('restdoc_details_macros',)


class RESTMenu(object):

    def listContentClasses(self):
        # Make sure that the class registry is setup.
        self.context.get('')

        results = []
        for name, iface in zapi.getUtilitiesFor(IContentType):

            for path, klass in classRegistry.getClassesThatImplement(iface):
                if path.startswith('zope'):
                    continue
                results.append(
                    {'path': path.replace('schooltool', 'st'),
                     'url': path.replace('.', '/') + '/@@restviews.html'
                     })

        results.sort(lambda x, y: cmp(x['path'], y['path']))
        return results


class RESTDocumentation(BrowserView):

    def __init__(self, context, request):
        super(RESTDocumentation, self).__init__(context, request)
        try:
            self.apidocRoot = findAPIDocumentationRoot(context, request)
        except TypeError:
            # Probably context without location; it's a test
            self.apidocRoot = ''

        # Ensure that the class registry is populated
        zapi.getUtility(IDocumentationModule, 'Code').setup()

        # We need the naked class for introspection everywhere.
        self.klass = classRegistry[context.getPath()]
        self.name = zapi.getName(context)


    def getGETInfo(self):
        """Get the info dictionary of the GET RESTive view.

        If there is no such view, return None.
        """
        reg = getHTTPViewRegistration(self.klass, 'GET')

        if reg is None:
            return None

        info = presentation.getViewInfoDictionary(reg)

        # Doctor up the info dict a little bit. This is easier than trying to
        # do the info dict from scratch.
        factory = component.getRealFactory(reg.value)

        # We deal with a zope.app.component.metaconfigure.ProxyView
        if hasattr(factory, 'template'):
            fn = factory.template.filename
            info['factory']['template'] = presentation.relativizePath(fn)

        # In plain HTTP views, `__call__` is the right method to get perms
        # for.
        if hasattr(factory, 'checker'):
            info.update(
                utilities.getPermissionIds('__call__', checker=factory.checker))

        return info


    def getPOSTInfo(self):
        """Get the info dictionary of the POST RESTive view.

        If there is no such view, return None.
        """
        reg = getHTTPViewRegistration(self.klass, 'POST')
        if reg is None:
            return

        info = presentation.getViewInfoDictionary(reg)

        # In plain HTTP views, `__call__` is the right method to get perms for.
        if hasattr(reg.value, 'checker'):
            info.update(utilities.getPermissionIds(
                '__call__', checker=reg.value.checker))

        if hasattr(reg.value, 'factory'):
            # Try to find a schema
            schema  = getattr(reg.value.factory, 'schema', None)
            if schema:
                schema = utilities.dedentString(schema)
                info['schema'] = schema

            # We deal with a zope.app.component.metaconfigure.ProxyView
            if hasattr(reg.value.factory, 'template'):
                fn = reg.value.factory.template.filename
                info['factory']['template'] = presentation.relativizePath(fn)

        return info


    def getPUTInfo(self):
        """Get the info dictionary of the PUT RESTive view.

        If there is no such view, return None.
        """
        reg = getHTTPViewRegistration(self.klass, 'PUT')
        if reg is None:
            return

        info = presentation.getViewInfoDictionary(reg)

        # Doctor up the info dict a little bit. This is easier than trying to
        # do the info dict from scratch.
        schema  = getattr(reg.value.factory, 'schema', None)
        if schema:
            schema = utilities.dedentString(schema)
        info['schema'] = schema

        # Try to get the checker
        checker = getattr(reg.value, 'checker', None)
        if checker:
            info.update(utilities.getPermissionIds('PUT', checker=checker))

        # Generically Zope 3 supports putting files by extension using the
        # IWriteFile interface; so we have to collect all of this info here.
        if component.getRealFactory(reg.value.factory) is FilePUT:

            # The should be only one IWriteFile adapter too.
            spec = zope.interface.implementedBy(self.klass)
            reg = getAdapters(spec, IWriteFile)
            if reg:
                reg = reg[0]
                info['edit'] = component.getAdapterInfoDictionary(reg)

            # Usually there will be only one container per content type, so
            # only using the first found container is a good assumption
            container = getContainerInterfaces(self.klass)
            if not container:
                return info
            container = container[0]

            # Also, while we could have a file factory for various different
            # extensions of an object, SchoolTool commonly only uses the
            # default adapter without any extensions.
            reg = getAdapters(container, IFileFactory)
            if reg:
                reg = reg[0]
                info['create'] = component.getAdapterInfoDictionary(reg)
                cdict = component.getInterfaceInfoDictionary(container)
                info['create']['container'] = cdict

                factory = component.getRealFactory(reg.value)

                # Also, if we have a schema, show it.
                schema  = getattr(factory, 'schema', None)
                if schema:
                    schema = utilities.dedentString(schema)
                    info['schema'] = schema

        return info


    def getDELETEInfo(self):
        """Get the info dictionary of the DELETE RESTive view.

        If there is no such view, return None.
        """
        # Get the DELETE view registration
        reg = getHTTPViewRegistration(self.klass, 'DELETE')

        # If none was found (which should never happen), then return None
        if reg is None:
            return None

        info = presentation.getViewInfoDictionary(reg)

        # Retrieve better security information
        checker = getattr(reg.value, 'checker', None)
        if checker:
            info.update(utilities.getPermissionIds('DELETE', checker=checker))

        # Now look up the containers and create an entry for each.
        containers = []
        for container in getContainerInterfaces(self.klass):
            containers.append(component.getInterfaceInfoDictionary(container))
        info['containers'] = containers
        return info


    def getNameTraversers(self):
        """Get a list of all name traversers."""
        result = []
        for reg in getNameTraversers(self.klass):
            # Get rid of all sorts of security and location wrappers
            factory = component.getRealFactory(reg.value)

            if not hasattr(factory, 'traversalName'):
                continue

            info = {
                'name': factory.traversalName,
                'component': {'path': None, 'url': None, 'referencable': None}
                }

            # Does not work yet.
            info.update(utilities.getPermissionIds(
                'publishTraverse', klass=getattr(factory, 'factory', factory)))

            if isinstance(reg.doc, (str, unicode)):
                info['zcml'] = None
            else:
                info['zcml'] = component.getParserInfoInfoDictionary(reg.doc)

            adapter = None
            if AdapterTraverserPluginTemplate in factory.__bases__:
                gsm = zapi.getGlobalSiteManager()
                iface = factory.interface
                spec = zope.interface.implementedBy(self.klass)
                adapter = gsm.adapters.lookup(
                    (spec,), iface, name=factory.adapterName)

                adapter = component.getRealFactory(adapter)

                # Sometimes the adapters are functions, so we have to dig deeper
                if isinstance(adapter, types.FunctionType):
                    # Make a guess.
                    for n, k in classRegistry.getClassesThatImplement(iface):
                        adapter = k
                        break

            elif NullTraverserPluginTemplate in factory.__bases__:
                adapter = self.klass

            elif hasattr(factory, 'component'):
                adapter = factory.component

            if adapter:
                adapterClass = component.getRealFactory(adapter)

                path = utilities.getPythonPath(adapterClass)
                referencable = utilities.isReferencable(path)
                info['component'] = {
                    'path': path,
                    'referencable': referencable,
                    'url': referencable and path.replace('.', '/') or None}

            result.append(info)

        result.sort(lambda x, y: cmp(x['name'], y['name']))
        return result
