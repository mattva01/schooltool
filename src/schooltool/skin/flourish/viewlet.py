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
SchoolTool flourish viewlets and viewlet managers.
"""
import zope.contentprovider.interfaces
import zope.event
import zope.security
import zope.viewlet.interfaces
from zope.component import adapts
from zope.interface import implements
from zope.proxy import removeAllProxies
from zope.proxy.decorator import SpecificationDecoratorBase
from zope.publisher.browser import BrowserPage

from schooltool.skin.flourish.content import ContentProvider
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin.flourish.interfaces import IViewlet, IViewletManager
from schooltool.skin.flourish.interfaces import IManagerViewlet
from schooltool.skin.flourish.sorting import dependency_sort


class Viewlet(BrowserPage):
    implements(IViewlet)

    _updated = False

    after = ()
    before = ()
    requires = ()

    def __init__(self, context, request, view, manager=None):
        BrowserPage.__init__(self, context, request)
        if manager is not None:
            self.manager = manager
        self.view = view

    @property
    def manager(self):
        return self.__parent__

    @manager.setter
    def manager(self, value):
        self.__parent__ = value

    def update(self):
        self._updated = True

    def render(self, *args, **kw):
        raise NotImplementedError(
            '`render` method must be implemented by subclass.')

    def __call__(self, *args, **kw):
        if not self._updated:
            event = zope.contentprovider.interfaces.BeforeUpdateEvent
            zope.event.notify(event(self, self.request))
            self.update()
        return self.render(*args, **kw)


class ViewletProxy(SpecificationDecoratorBase):
    """A viewlet proxy that turns a zope viewlet into flourish viewlet."""
    adapts(zope.viewlet.interfaces.IViewlet)
    implements(IViewlet)

    __slots__ = ('before', 'after', 'requires', '_updated')

    def __init__(self, *args, **kw):
        self.before = ()
        self.after = ()
        self.requires = ()
        self._updated = False
        super(ViewletProxy, self).__init__(*args, **kw)

    @property
    def view(self):
        unproxied = zope.proxy.getProxiedObject(self)
        return unproxied.__parent__

    @view.setter
    def view(self, value):
        unproxied = zope.proxy.getProxiedObject(self)
        unproxied.__parent__ = value

    @property
    def __parent__(self):
        return self.manager

    @__parent__.setter
    def __parent__(self, value):
        self.manager = value

    @zope.proxy.non_overridable
    def update(self):
        unproxied = zope.proxy.getProxiedObject(self)
        self._updated = True
        unproxied.update()

    @zope.proxy.non_overridable
    def __call__(self, *args, **kw):
        if not self._updated:
            event = zope.contentprovider.interfaces.BeforeUpdateEvent
            zope.event.notify(event(self, self.request))
            self.update()
        return self.render(*args, **kw)


class ViewletManagerBase(ContentProvider):
    implements(IViewletManager)

    cache = None
    order = None

    render = lambda self, *args, **kw: ''

    def collectViewlets(self):
        indirect = list(zope.component.getAdapters(
                (self.context, self.request, self.view, self),
                zope.viewlet.interfaces.IViewlet))
        adapted = [(v, IViewlet(a, None))
                   for (v, a) in indirect]

        result = dict(adapted)

        direct = list(zope.component.getAdapters(
                (self.context, self.request, self.view, self),
                IViewlet))
        result.update(dict(direct))

        # XXX: This is also a workaround Zope's bug - if an adapter
        #      has a specified a permission and returns None, instead
        #      of being filtered by getAdapters it returns a security
        #      proxied located instance of None.
        for name in list(result):
            if removeAllProxies(result[name]) is None:
                del result[name]

        for name, viewlet in result.items():
            unproxied = zope.security.proxy.removeSecurityProxy(viewlet)
            if unproxied.__name__ != name:
                unproxied.__name__ = name

        viewlets = dict(self.filterViewlets(result.items()))
        return viewlets

    def filterViewlets(self, viewlets):
        def can_access(item):
            name, viewlet = item
            try:
                return zope.security.canAccess(viewlet, 'render')
            except zope.security.interfaces.ForbiddenAttribute:
                return False
        viewlets = filter(can_access, viewlets)

        names = set([n for n, v in viewlets])
        has_required = lambda (n, v): set(v.requires).issubset(names)
        viewlets = filter(has_required, viewlets)

        return viewlets

    def presort(self, viewlet_dict):
        return sorted(viewlet_dict)

    def buildOrder(self, viewlet_dict):
        presort_order = self.presort(viewlet_dict)
        before = {}
        after = {}
        known_names = set(list(viewlet_dict)+['*'])
        for name, viewlet in viewlet_dict.items():
            before[name] = set(viewlet.before).intersection(known_names)
            after[name] = set(viewlet.after).intersection(known_names)
        names = dependency_sort(presort_order, before, after)
        return names

    def __getitem__(self, name):
        if self.cache is None:
            self.collect()
        return self.cache[name]

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def __contains__(self, name):
        if self.cache is None:
            self.collect()
        return name in self.cache

    @property
    def viewlets(self):
        if self.cache is None:
            self.collect()
        return [self[key] for key in self.order]

    def collect(self):
        self.cache = self.collectViewlets()
        self.order = self.buildOrder(self.cache)

    def update(self):
        event = zope.contentprovider.interfaces.BeforeUpdateEvent
        for viewlet in self.viewlets:
            zope.event.notify(event(viewlet, self.request))
            viewlet.update()


class ViewletManager(ViewletManagerBase):

    template = InlineViewPageTemplate("""
        <tal:block repeat="viewlet view/viewlets">
          <tal:block define="rendered viewlet;
                             stripped rendered/strip|nothing"
                     condition="stripped"
                     content="structure stripped">
          </tal:block>
        </tal:block>
    """)

    render = lambda self, *args, **kw: self.template(*args, **kw)


class ManagerViewlet(Viewlet, ViewletManager):
    implements(IManagerViewlet)
    view = None

    def __init__(self, context, request, view, manager=None):
        Viewlet.__init__(self, context, request, view, manager=manager)

    def update(self):
        return ViewletManager.update(self)

    def __call__(self, *args, **kw):
        return ViewletManager.__call__(self, *args, **kw)


def lookupViewlet(context, request, view, manager, name="", default=None):
    viewlet = zope.component.queryMultiAdapter(
        (context, request, view, manager),
        IViewlet, name=name, default=default)
    return viewlet
