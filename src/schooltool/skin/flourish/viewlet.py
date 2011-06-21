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
SchoolTool flourish viewlets and viewlet managers.
"""
import zope.contentprovider.interfaces
import zope.event
import zope.security
import zope.viewlet.interfaces
from zope.cachedescriptors.property import Lazy
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

    manager = None
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


class ViewletManager(ContentProvider):
    implements(IViewletManager)

    template = InlineViewPageTemplate("""
        <tal:block repeat="viewlet view/viewlets"
                   content="structure viewlet" />
    """)

    render = lambda self, *args, **kw: self.template(*args, **kw)

    @Lazy
    def viewlet_dict(self):
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
            if viewlet.__name__ != name:
                unproxied = zope.security.proxy.removeSecurityProxy(viewlet)
                unproxied.__name__ = name

        result = dict(self.filter(result.items()))
        return result

    def filter(self, viewlets):
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

    @Lazy
    def order(self):
        viewlet_dict = self.viewlet_dict

        before = {}
        after = {}
        for viewlet in viewlet_dict.values():
            name = viewlet.__name__
            before[name] = set(viewlet.before)
            after[name] = set(viewlet.after)

        names = dependency_sort(sorted(viewlet_dict), before, after)
        return names

    @Lazy
    def viewlets(self):
        d = self.viewlet_dict
        return [d[key] for key in self.order]

    def __getitem__(self, name):
        return self.viewlet_dict[name]

    def get(self, name, default=None):
        return self.viewlet_dict.get(name, default)

    def __contains__(self, name):
        return name in self.viewlet_dict

    def update(self):
        event = zope.contentprovider.interfaces.BeforeUpdateEvent
        for viewlet in self.viewlets:
            zope.event.notify(event(viewlet, self.request))
            viewlet.update()


class ManagerViewlet(Viewlet, ViewletManager):
    implements(IManagerViewlet)
    view = None

    def update(self):
        return ViewletManager.update(self)

    def __call__(self, *args, **kw):
        return ViewletManager.__call__(self, *args, **kw)


def lookupViewlet(context, request, view, manager, name="", default=None):
    viewlet = zope.component.queryMultiAdapter(
        (context, request, view, manager),
        IViewlet, name=name, default=default)
    return viewlet
