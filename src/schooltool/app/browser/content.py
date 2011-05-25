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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Schooltool content providers.
"""

from zope.component import adapts, queryMultiAdapter
from zope.interface import implements
import zope.contentprovider.interfaces
from zope.contentprovider.interfaces import IContentProvider
from zope.contentprovider.interfaces import ContentProviderLookupError
from zope.contentprovider.tales import addTALNamespaceData
from zope.contentprovider.provider import ContentProviderBase
from zope.event import notify
from zope.location.interfaces import ILocation
from zope.proxy.decorator import SpecificationDecoratorBase
from zope.publisher.interfaces.browser import IBrowserPage
from zope.publisher.interfaces import NotFound
from zope.publisher.browser import BrowserPage
from zope.tales.interfaces import ITALESFunctionNamespace
from zope.traversing.interfaces import ITraversable


class IContentProviders(ITraversable):
    pass


class ISchoolToolContentProvider(IBrowserPage, IContentProvider):
    def __call__(*args, **kw):
        """Compute the response body."""


class ContentProvider(ContentProviderBase, BrowserPage):
    """Base SchoolTool content provider class."""

    implements(ISchoolToolContentProvider)

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


class SchoolToolContentProviderProxy(SpecificationDecoratorBase):
    """A content provider proxy that mimics behaviour of
    zope.contentrpovider.tales.TALESProviderExpression
    """
    adapts(IContentProvider)
    implements(ISchoolToolContentProvider)

    __slots__ = ('__call__', 'browserDefault', 'publishTraverse')

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
    implements(IContentProviders)

    def __init__(self, context, request, view):
        self.context = context
        self.request = request
        self.view = view
        self.cache = {}

    def __contains__(self, name):
        return self.cache.get(name) is not None

    def get(self, name, default=None):
        if name not in self.cache:
            self.cache[name] = self.lookup(name)
        ob = self.cache.get(name)
        if ob is None:
            return default
        return ob

    def __getitem__(self, name):
        ob = self.get(name, None)
        if ob is None:
            raise KeyError(name)
        return ob

    def lookup(self, name):
        provider = queryMultiAdapter(
            (self.context, self.request, self.view),
            ISchoolToolContentProvider, name)
        if provider is None:
            provider = queryMultiAdapter(
                (self.context, self.request, self.view),
                IContentProvider, name)
            if provider is not None:
                provider = ISchoolToolContentProvider(provider, None)
        if (provider is not None and
            ILocation.providedBy(provider)):
            provider.__name__ = name
        return provider

    def traverse(self, name, furtherPath):
        provider = self.get(name, None)
        if provider is None:
            raise ContentProviderLookupError(name)
        return provider


class TALESAwareContentProviders(ContentProviders):
    implements(ITALESFunctionNamespace)

    engine = None

    def setEngine(self, engine):
        self.engine = engine

    def traverse(self, name, furtherPath):
        provider = ContentProviders.traverse(self, name, furtherPath)
        if self.engine is not None:
            addTALNamespaceData(provider, self.engine)
        return provider
