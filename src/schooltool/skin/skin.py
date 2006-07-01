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
SchoolTool skin.

$Id$
"""

from zope.component import adapts, getAdapter
from zope.interface import Interface, implements
from zope.schema import Object
from zope.publisher.interfaces.browser import ILayer, IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.viewlet.interfaces import IViewletManager
from zope.viewlet.manager import ViewletManagerBase
from zope.app import zapi

from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.interfaces import IBreadcrumbInfo

from schooltool.app.app import getSchoolToolApplication


class IJavaScriptManager(IViewletManager):
    """Provides a viewlet hook for the javascript link entries."""


class ICSSManager(IViewletManager):
    """Provides a viewlet hook for the CSS link entries."""


class IHeaderManager(IViewletManager):
    """Provides a viewlet hook for the header of a page."""


class INavigationManager(IViewletManager):
    """Provides a viewlet hook for the navigation section of a page."""


class IActionMenuManager(IViewletManager):
    """Provides a viewlet hook for the action menu."""

    def title():
        """Title that will be displayed before the action menu or submenu."""

    def subItems():
        """Sub items that will have their own menus in the main action menu.

        Returns a list of ISubMenuItem objects.
        """

class IActionMenuContext(Interface):
    """Schema for attributes required by ActionMenuViewletManager."""

    target = Object(Interface)


class OrderedViewletManager(ViewletManagerBase):
    """Viewlet manager that orders viewlets by their 'order' attribute.

    The order attribute can be a string, but it will be sorted numerically
    (i.e. '1' before '5' before '20').  The attribute is optional; viewlets
    without an ``order`` attribute will be sorted alphabetically by their
    ``title`` attribute, and placed below all the ordered viewlets.
    """

    def sort(self, viewlets):
        """Sort the viewlets.

        ``viewlets`` is a list of tuples of the form (name, viewlet).
        """

        def key_func((name, viewlet)):
            if hasattr(viewlet, 'order'):
                return (0, int(viewlet.order))
            elif hasattr(viewlet, 'title'):
                return (1, viewlet.title)
            else:
                raise AttributeError('%r viewlet has neither order nor title'
                                     % name)

        return sorted(viewlets, key=key_func)


class NavigationViewlet(object):
    """A navigation viewlet base class."""

    def actualContext(self):
        return ISchoolToolApplication(None)

    def appURL(self):
        return zapi.absoluteURL(getSchoolToolApplication(), self.request)


class TopLevelContainerNavigationViewlet(NavigationViewlet):
    """A base class of navigation viewlet for top level containers."""

    def actualContext(self):
        """Actual context is the container this viewlet links to."""
        return ISchoolToolApplication(None)[self.link]


class ISubMenuItem(Interface):
    """Marker interface for objects that will be displayed as items in submenus.
    """

class ActionMenuViewletManager(OrderedViewletManager):
    """Viewlet manager for displaying the action menu."""

    implements(IActionMenuContext, IActionMenuManager)

    def title(self):
        breadcrumb = zapi.getMultiAdapter((self.context, self.request),
                                          IBreadcrumbInfo)
        return breadcrumb.name

    def getSubItems(self, context):
        """Collect all items that should be displayed in the submenu of context.

        Submenu items are registered as subscribers with interface
        ISubMenuItem.
        """
        return [item for item in zapi.subscribers((context, ), ISubMenuItem)]

    def update(self):
        # set the right context for menu items that will be set up by
        # OrderedViewletManager.update
        self.context = self.target

        # We could just check for ISubMenuItem on self.context, though
        # that would be less reliable.
        in_submenu_of_parent = self.context in self.getSubItems(self.context.__parent__)
        displayed_in_submenu = IActionMenuManager.providedBy(self.__parent__)
        if (in_submenu_of_parent and not displayed_in_submenu):
            # display menu as if looking at the parent object
            self.context = self.context.__parent__
        self.orderedViewletManagerUpdate()

    def orderedViewletManagerUpdate(self):
        OrderedViewletManager.update(self)

    def subItems(self):
        """See zope.contentprovider.interfaces.IContentProvider"""
        return self.getSubItems(self.context)


class NavigationViewletCrowd(Crowd):
    """A crowd for navigation viewlets.

    Checks permissions on the actual context rather than the parent. Parents
    of viewlets are pretty useless in this case as NavigationViewlets
    are used in a global navigation menu.
    """

    def contains(self, principal):
        context = self.context.actualContext()
        crowd = getAdapter(context, ICrowd, name='schooltool.view')
        return crowd.contains(principal)


class ISchoolToolLayer(ILayer, IBrowserRequest):
    """SchoolTool layer."""


class ISchoolToolSkin(ISchoolToolLayer, IDefaultBrowserLayer):
    """The SchoolTool skin"""
