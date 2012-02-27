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
from zope.publisher.interfaces import IPublishTraverse
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

    view = zope.interface.Attribute(
        """The view the provider appears in.

        The view is the third discriminator of the content provider. It allows
        that the content can be controlled for different views.

        Having it stored as the parent is also very important for the security
        context to be kept.
        """)

    def __call__(*args, **kw):
        """Compute the response body."""


class IViewletOrder(Interface):
    """Attributes to specify viewlet display order."""

    after = Attribute(
        u"Display this viewlet after the given list of viewlets.")

    before = Attribute(
        u"Display this viewlet before the given list of viewlets.")

    requires = Attribute(
        u"Display only if all specified viewlets are available.")


class IViewlet(IContentProvider,
               ILocation,
               IBrowserPage,
               IViewletOrder):
    """A viewlet."""

    manager = zope.interface.Attribute(
        """The Viewlet Manager

        The viewlet manager for which the viewlet is registered. The viewlet
        manager will contain any additional data that was provided by the
        view, for example the TAL namespace attributes.
        """)


class IViewletManager(zope.viewlet.interfaces.IViewletManager,
                      ILocation,
                      IContentProvider):
    """A viewlet manager."""

    def collect():
        """Collect the viewlets and deduce their order."""


class IManagerViewlet(IViewlet, IViewletManager):
    """A viewlet that is also a manager."""


class IActiveViewletName(Interface):
    """Interface for adapter that returns the active viewlet name."""


class IPage(IBrowserPage, ILocation):
    title = zope.schema.TextLine(
        title=u"Page title", required=False)

    subtitle = zope.schema.TextLine(
        title=u"Page subtitle", required=False)

    template = Attribute(
        """Main page template, renders the whole browser page,
        including header and footer.
        """)

    page_template = Attribute(
        u"Template that renders all contents between header and footer.")

    content_template = Attribute(
        u"Template that renders the main content.")

    def update(self):
        pass

    def render(*args, **kw):
        pass


class IFromPublication(IPublishTraverse):

    fromPublication = zope.schema.Bool(
        title=_('Accessed from publication'),
        description=_('A flag that specifies if this part was built '
                      'by publication.'),
        default=False,
        required=False)


class IAJAXParts(IViewletManager, IFromPublication):
    """AJAX parts of the view."""


class IAJAXPart(IViewlet, IFromPublication):
    """An ajax part of a view."""

    ignoreRequest = zope.schema.Bool(
        title=_('Ignore request'),
        description=_('A flag that specifies if the request should be '
                      'regarded as unreliable (for example, part '
                      'was not obtained via publication).'),
        default=True,
        required=False)
