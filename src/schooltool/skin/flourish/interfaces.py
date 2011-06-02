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
from zope.interface import Interface, Attribute
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserPage
from z3c.form.interfaces import IFormLayer

# XXX: move content providers to schooltool.skin
from schooltool.app.browser.content import ISchoolToolContentProvider
from schooltool.common import SchoolToolMessage as _


class IFlourishLayer(IDefaultBrowserLayer, IFormLayer):
    """SchoolTool flourish skin."""


class IViewletOrder(Interface):
    """Attributes to specify viewlet display order."""

    after = Attribute(
        _("Display this viewlet after the given list of viewlets."))

    before = Attribute(
        _("Display this viewlet before the given list of viewlets."))

    requires = Attribute(
        _("Display only if all specified viewlets are available."))


class IViewlet(zope.viewlet.interfaces.IViewlet,
               IBrowserPage,
               IViewletOrder):
    """A viewlet."""


class IViewletManager(zope.viewlet.interfaces.IViewletManager,
                      ISchoolToolContentProvider):
    """A viewlet manager."""


class IActiveViewletName(Interface):
    """Interface for adapter that returns the active viewlet name."""


class IPage(IBrowserPage):
    __name__ = zope.schema.TextLine(
        title=u"The name of the page",
        required=False,
        default=None)

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
