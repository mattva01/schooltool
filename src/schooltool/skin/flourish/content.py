#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Schooltool content providers.
"""
from zope.component import adapts, adapter, queryMultiAdapter, getAdapter
from zope.interface import implements, implementer
import zope.contentprovider.interfaces
from zope.contentprovider.interfaces import ContentProviderLookupError
from zope.contentprovider.tales import addTALNamespaceData
from zope.contentprovider.provider import ContentProviderBase
from zope.event import notify
from zope.location import ILocation
from zope.proxy.decorator import SpecificationDecoratorBase
from zope.publisher.interfaces import NotFound
from zope.publisher.browser import BrowserPage
from zope.security.proxy import removeSecurityProxy
from zope.tales.interfaces import ITALESFunctionNamespace

from schooltool.skin.flourish import interfaces
from schooltool.securitypolicy.interfaces import ICrowd


class ContentProvider(ContentProviderBase, BrowserPage):
    """Base SchoolTool content provider class."""

    implements(interfaces.IContentProvider)

    @property
    def view(self):
        return self.__parent__

    @view.setter
    def view(self, value):
        self.__parent__ = value

    def __call__(self, *args, **kw):
        event = zope.contentprovider.interfaces.BeforeUpdateEvent
        notify(event(self, self.request))
        self.update()
        return self.render(*args, **kw)


class ContentProviderProxy(SpecificationDecoratorBase):
    """A content provider proxy that mimics behaviour of
    zope.contentprovider.tales.TALESProviderExpression
    """
    adapts(zope.contentprovider.interfaces.IContentProvider)
    implements(interfaces.IContentProvider)

    @property
    def view(self):
        return self.__parent__

    def browserDefault(self, request):
        return self, ()

    def publishTraverse(self, request, name):
        raise NotFound(self, name, request)

    def __call__(self, *args, **kw):
        event = zope.contentprovider.interfaces.BeforeUpdateEvent
        notify(event(self, self.request))
        self.update()
        return self.render(*args, **kw)


class ContentProviders(object):
    implements(interfaces.IContentProviders)

    def __init__(self, context, request, view):
        self.context = context
        self.request = request
        self.view = view
        self.cache = {}

    def __contains__(self, name):
        return self.get(name) is not None

    def get(self, name, default=None):
        if name not in self.cache:
            self[name] = self.lookup(name)
        ob = self.cache.get(name)
        if ob is None:
            return default
        return ob

    def __getitem__(self, name):
        ob = self.get(name, None)
        if ob is None:
            raise KeyError(name)
        return ob

    def __setitem__(self, name, provider):
        self.cache[name] = provider

    def lookup(self, name):
        provider = queryMultiAdapter(
            (self.context, self.request, self.view),
            interfaces.IContentProvider, name)
        if provider is None:
            provider = queryMultiAdapter(
                (self.context, self.request, self.view),
                zope.contentprovider.interfaces.IContentProvider, name)
            if provider is not None:
                provider = interfaces.IContentProvider(provider, None)
        if (provider is not None and
            ILocation.providedBy(provider)):
            unproxied = removeSecurityProxy(provider)
            unproxied.__name__ = name
        return provider

    def get_providers(self, direct=True, adapted=True):
        """Get all content providers.
        Use this for debugging purposes only.
        """
        if direct:
            direct_providers = list(zope.component.getAdapters(
                    (self.context, self.request, self.view),
                    interfaces.IContentProvider))
        else:
            direct_providers = []
        if adapted:
            indirect = list(zope.component.getAdapters(
                    (self.context, self.request, self.view),
                    zope.contentprovider.interfaces.IContentProvider))
            adapted_providers = [
                (name, interfaces.IContentProvider(provider, None))
                for name, provider in indirect]
        else:
            adapted_providers = []
        result = dict(adapted_providers)
        result.update(dict(direct_providers))
        return result

    def traverse(self, name, furtherPath):
        provider = self.get(name, None)
        if provider is None:
            raise ContentProviderLookupError(self.context, name)
        return provider


class TALESAwareContentProviders(ContentProviders):
    implements(ITALESFunctionNamespace)

    engine = None

    def setEngine(self, engine):
        self.engine = engine

    def traverse(self, name, furtherPath):
        provider = ContentProviders.traverse(self, name, furtherPath)
        if self.engine is not None:
            unproxied = removeSecurityProxy(provider)
            addTALNamespaceData(unproxied, self.engine)
        return provider


def queryContentProvider(context, request, view, name):
    provider = queryMultiAdapter(
        (context, request, view),
        interfaces.IContentProvider,
        name)
    if provider is not None:
        return provider

    zope_provider = queryMultiAdapter(
        (context, request, view),
        zope.contentprovider.interfaces.IContentProvider,
        name)
    if zope_provider is None:
        return None
    provider = interfaces.IContentProvider(provider, None)
    return provider


@adapter(interfaces.IContentProvider)
@implementer(ICrowd)
def providerViewCrowd(provider):
    return getAdapter(provider.context, ICrowd, name="schooltool.view")


@adapter(interfaces.IContentProvider)
@implementer(ICrowd)
def providerEditCrowd(provider):
    return getAdapter(provider.context, ICrowd, name="schooltool.edit")


@adapter(interfaces.IContentProvider)
@implementer(ICrowd)
def providerManageAppCrowd(provider):
    return getAdapter(provider.context, ICrowd, name="zope.ManageApplication")
