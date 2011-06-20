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
SchoolTool flourish skin interfaces.
"""

import zope.schema
import zope.viewlet.interfaces
import zope.contentprovider.interfaces
from zope.interface import Interface, Attribute
from zope.location.interfaces import ILocation
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserPage
from zope.traversing.interfaces import ITraversable
from z3c.form.interfaces import IFormLayer

from schooltool.common import SchoolToolMessage as _


class IFlourishLayer(IDefaultBrowserLayer, IFormLayer):
    """SchoolTool flourish skin."""


class IContentProviders(ITraversable):
    """Traversable collection of content providers."""


class IContentProvider(
    IBrowserPage, zope.contentprovider.interfaces.IContentProvider):

    def __call__(*args, **kw):
        """Compute the response body."""


class IViewletOrder(Interface):
    """Attributes to specify viewlet display order."""

    after = Attribute(
        _("Display this viewlet after the given list of viewlets."))

    before = Attribute(
        _("Display this viewlet before the given list of viewlets."))

    requires = Attribute(
        _("Display only if all specified viewlets are available."))


class IViewlet(zope.viewlet.interfaces.IViewlet,
               ILocation,
               IBrowserPage,
               IViewletOrder):
    """A viewlet."""


class IViewletManager(zope.viewlet.interfaces.IViewletManager,
                      ILocation,
                      IContentProvider):
    """A viewlet manager."""


class IManagerViewlet(IViewlet, IViewletManager):
    """A viewlet that is also a manager."""


class IActiveViewletName(Interface):
    """Interface for adapter that returns the active viewlet name."""


class IPage(IBrowserPage, ILocation):
    title = zope.schema.TextLine(
        title=_("Page title"), required=False)

    subtitle = zope.schema.TextLine(
        title=_("Page subtitle"), required=False)

    template = Attribute(
        _("""Main page template, renders the whole browser page,
        including header and footer.
        """))

    page_template = Attribute(
        _("Template that renders all contents between header and footer."))

    content_template = Attribute(
        _("Template that renders the main content."))

    def update(self):
        pass

    def render(*args, **kw):
        pass
