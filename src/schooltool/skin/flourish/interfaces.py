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
SchoolTool flourish skin interfaces.
"""

import zope.interface.interfaces
import zope.schema
import zope.schema.interfaces
import zope.viewlet.interfaces
import zope.contentprovider.interfaces
from zope.interface import Interface, Attribute
from zope.location.interfaces import ILocation
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserPage
from zope.traversing.interfaces import ITraversable
from z3c.form.interfaces import IFormLayer


class IFlourishLayer(IFormLayer):
    """SchoolTool flourish skin."""


class IFlourishBrowserLayer(IFlourishLayer, IDefaultBrowserLayer):
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


class IPageBase(IBrowserPage, ILocation):

    template = Attribute(
        """Main page template, often used to render the page""")

    def update(self):
        pass

    def render(*args, **kw):
        pass


class IPage(IPageBase):
    title = zope.schema.TextLine(
        title=u"Page title", required=False)

    subtitle = zope.schema.TextLine(
        title=u"Page subtitle", required=False)

    page_template = Attribute(
        u"Template that renders all contents between header and footer.")

    content_template = Attribute(
        u"Template that renders the main content.")


IPage.setTaggedValue('flourish.template_content_type', 'html')


class IRMLTemplated(Interface):

    template = Attribute("""The template, renders RML""")

    def render(*args, **kw):
        """Render the RML."""


IRMLTemplated.setTaggedValue('flourish.template_content_type', 'xml')


class IPDFPage(IRMLTemplated, IPageBase):

    title = zope.schema.TextLine(
        title=u"PDF title", required=False)

    author = zope.schema.TextLine(
        title=u"PDF author", required=False)

    filename = zope.schema.TextLine(
        title=u"PDF file name", required=False)

    inline = zope.schema.Bool(
        title=u"Render inline", required=False)

    page_size = zope.schema.Tuple(
        title=u"Page size",
        value_type = zope.schema.Float(title=u"Size in pt (1/72 inch)"),
        required=False
        )

    rotation = zope.schema.Float(
        title=u"Page rotation",
        required=False
        )

    render_invariant = zope.schema.Bool(
        title=u"Render invariant",
        description=u"Render without influence form environment, like current time.",
        required=False)

    render_debug = zope.schema.Bool(
        title=u"Render debug",
        description=u"Render with debug information.",
        required=False)

    inline = zope.schema.Bool(
        title=u"Render inline", required=False)

    content_template = Attribute(
        u"Template that renders the main content.")


IPDFPage.setTaggedValue('flourish.template_content_type', 'xml')


class IPDFPart(IRMLTemplated, IViewlet):
    """A viewlet for RML."""


IPDFPart.setTaggedValue('flourish.template_content_type', 'xml')


class ITemplateSlots(ILocation):

    context = Attribute("The context object the view renders")
    request = Attribute("The request object driving the view")
    view = Attribute("The view")
    template = Attribute("A viewlet that renders a PDF <template>")


class IPageTemplate(IViewlet):

    slots = zope.schema.Object(
        title=u"Slot data",
        schema=ITemplateSlots,
        required=True)

    slots_interface = zope.schema.Object(
        title=u"Slot inteface",
        schema=zope.interface.interfaces.ISpecification,
        required=False)


class IFromPublication(IPublishTraverse):

    fromPublication = zope.schema.Bool(
        title=u'Accessed from publication',
        description=u'A flag that specifies if this part was built '
                     'by publication.',
        default=False,
        required=False)


class IAJAXParts(IViewletManager, IFromPublication):
    """AJAX parts of the view."""


class IAJAXPart(IViewlet, IFromPublication):
    """An ajax part of a view."""

    ignoreRequest = zope.schema.Bool(
        title=u'Ignore request',
        description=u'A flag that specifies if the request should be '
                     'regarded as unreliable (for example, part '
                     'was not obtained via publication).',
        default=True,
        required=False)
