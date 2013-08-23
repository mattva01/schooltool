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
SchoolTool flourish zcml directives.
"""
import zope.browserpage.metadirectives
import zope.component.zcml
import zope.configuration.fields
import zope.schema
import zope.security.checker
import zope.viewlet.metadirectives
from zope.interface import Interface, classImplements
from zope.configuration.exceptions import ConfigurationError
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IBrowserView

from schooltool.skin.flourish.zcml_content import contentDirective
from schooltool.skin.flourish.zcml_content import subclass_content
from schooltool.skin.flourish.zcml_content import template_specs, update_specs
from schooltool.skin.flourish.zcml_content import handle_interfaces
from schooltool.skin.flourish.zcml_content import handle_security
from schooltool.skin.flourish.zcml_content import TemplatePath
from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish.page import Page
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManager


class IRenderOverrides(Interface):

    update = zope.configuration.fields.PythonIdentifier(
        title=u"The name of the view attribute implementing content update.",
        required=False,
        )

    render = zope.configuration.fields.PythonIdentifier(
        title=u"The name of the view attribute that renders the content.",
        required=False,
        )


class IViewletOrder(Interface):

    after = zope.configuration.fields.Tokens(
        title=u"Display this viewlet after the specified viewlets.",
        value_type=zope.schema.TextLine(
            title=u"Names of viewlets",
            required=True),
        required=False)

    before = zope.configuration.fields.Tokens(
        title=u"Display this viewlet before the specified viewlets.",
        value_type=zope.schema.TextLine(
            title=u"Names of viewlets",
            required=True),
        required=False)


class IViewletDirective(zope.viewlet.metadirectives.IViewletDirective,
                        IRenderOverrides,
                        IViewletOrder):
    """A viewlet directive."""

    template = TemplatePath(
        title=u"Content-generating template.",
        required=False)

    manager = zope.configuration.fields.GlobalObject(
        title=u"The viewlet Manager",
        required=True)

    title = zope.configuration.fields.MessageID(
        title=u"Title of this viewlet",
        required=False,
        )


class IViewletFactoryDirective(zope.component.zcml.IAdapterDirective):

    for_ = zope.configuration.fields.GlobalObject(
        title=u"The interface or class this view is for",
        required=False,
        default=Interface,
        )

    factory = zope.configuration.fields.GlobalObject(
        title=u"The adapter factory",
        required=False,
        )

    provides = zope.configuration.fields.GlobalInterface(
        title=u"Interface the component provides",
        required=False,
        default=interfaces.IViewlet,
        )

    view = zope.configuration.fields.GlobalObject(
        title=u"The view the content provider is registered for.",
        description=u"""
        The view can either be an interface or a class. By
        default the provider is registered for all views,
        the most common case.""",
        required=False,
        default=IBrowserView,
        )

    layer = zope.configuration.fields.GlobalInterface(
        title=u"The layer the view is in",
        required=False,
        default=interfaces.IFlourishLayer,
        )

    manager = zope.configuration.fields.GlobalObject(
        title=u"The viewlet manager this viewlet is in",
        required=False,
        default=interfaces.IViewletManager,
        )


# Arbitrary keys and values are allowed to be passed to the viewlet.
IViewletDirective.setTaggedValue('keyword_arguments', True)


class IManagerDirective(zope.viewlet.metadirectives.IViewletManagerDirective,
                        IViewletOrder):
    """Viewlet manager directive."""


# Arbitrary keys and values are allowed to be passed to the manager.
IManagerDirective.setTaggedValue('keyword_arguments', True)


class IPageDirective(zope.browserpage.metadirectives.IPagesDirective,
                     IRenderOverrides):

    name = zope.schema.TextLine(
        title=u"The name of the page (view)",
        required=True,
        )

    title = zope.configuration.fields.MessageID(
        title=u"Title of this page",
        required=False,
        )

    subtitle = zope.configuration.fields.MessageID(
        title=u"Subitle of this page",
        description=u"""
        A very short description of this page.
        """,
        required=False,
        )

    template = TemplatePath(
        title=u"Main template",
        description=u"""
        Change the main template that renders everything.
        """,
        required=False,
        )

    page_template = TemplatePath(
        title=u"Template for the page",
        description=u"""
        Change template that renders the page part between the header
        and the footer.
        """,
        required=False,
        )

    content_template = TemplatePath(
        title=u"Template for the main page content.",
        description=u"""
        Set template that renders main content for this page.
        """,
        required=False,
        )


# Arbitrary keys and values are allowed to be passed to the manager.
IPageDirective.setTaggedValue('keyword_arguments', True)


class IContentOrientedDirective(Interface):

    for_ = zope.configuration.fields.GlobalObject(
        title=u"The interface or class this viewlet is active in",
        required=False,
        )

    layer = zope.configuration.fields.GlobalInterface(
        title=u"The layer",
        required=False,
        )

    view = zope.configuration.fields.GlobalObject(
        title=u"The view",
        required=False,
        )


class IActiveViewletDirective(IContentOrientedDirective):

    name = zope.schema.TextLine(
        title=u"The name of the active viewlet",
        required=False,
        )

    factory = zope.configuration.fields.GlobalObject(
        title=u"The adapter name of the active viewlet",
        required=False,
        )

    manager = zope.configuration.fields.GlobalObject(
        title=u"The viewlet manager",
        required=True,
        )


def viewletManager(
    _context, name, permission,
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPageBase,
    provides=interfaces.IViewletManager,
    class_=ViewletManager, template=None,
    update='update', render='render',
    allowed_interface=(), allowed_attributes=(),
    **kwargs):

    bases = (class_, )
    if not interfaces.IViewletManager.implementedBy(class_):
        bases = bases + (ViewletManager, )
    class_ = type(class_.__name__, bases, {})

    allowed_interface = (tuple(allowed_interface) +
                         (interfaces.IViewletManager, ))

    if not provides.implementedBy(class_):
        classImplements(class_, provides)

    contentDirective(
        _context, name, permission,
        for_=for_, layer=layer, view=view,
        class_=class_, template=template,
        update=update, render=render,
        allowed_interface=allowed_interface,
        allowed_attributes=allowed_attributes,
        **kwargs)


def viewlet(
    _context, name, permission,
    for_=Interface, layer=interfaces.IFlourishLayer, view=IBrowserView,
    manager=None,
    class_=Viewlet, template=None,
    update='update', render='render',
    allowed_interface=(), allowed_attributes=(),
    **kwargs):

    if not interfaces.IViewlet.implementedBy(class_):
        class_ = type(class_.__name__, (class_, Viewlet), {})
    allowed_interface = (tuple(allowed_interface) +
                         (interfaces.IViewlet, ))

    if (render == 'render' and
        class_.render == Viewlet.render):
        if template:
            render = 'template'
        else:
            raise ConfigurationError("When template and render not specified, "
                                     "class must implement 'render' method")

    class_ = subclass_content(
        class_, name,
        {'update': update, 'render': render},
        update_specs({'template': template}, view), kwargs)

    handle_interfaces(_context, (for_, view))
    handle_interfaces(_context, allowed_interface)

    handle_security(class_, permission,
                    allowed_interface, allowed_attributes)

    _context.action(
        discriminator=('schooltool.skin.flourish.viewlet',
                       for_, layer, view, manager, name),
        callable=zope.component.zcml.handler,
        args=('registerAdapter',
              class_,
              (for_, layer, view, manager),
              interfaces.IViewlet,
              name,
              _context.info),)


def viewletFactory(
    _context, factory, provides=interfaces.IViewlet,
    for_=Interface, permission=None,
    name='', trusted=True, locate=False,
    layer=interfaces.IFlourishLayer,
    view=IBrowserView,
    manager=interfaces.IViewletManager):

    wrapper = lambda c, r, v, m: factory(c, r, v, m, name)
    objects = [for_, layer, view, manager]
    zope.component.zcml.adapter(
        _context, [wrapper],
        provides=provides, for_=objects, permission=permission,
        name=name,
        trusted=trusted, locate=locate)


def page(_context, name, permission,
         for_=Interface, layer=interfaces.IFlourishLayer,
         title=None, subtitle=None,
         template=None, page_template=None, content_template=None,
         class_=Page,
         update='update', render='render',
         allowed_interface=(), allowed_attributes=(),
         **kwargs
         ):

    forward_methods = {
        'update': update,
        'render': render,
        }

    # BBB: add index to ease porting from old style views
    if (IBrowserView.implementedBy(class_) and
        getattr(class_, 'index', None) is None):
        forward_methods['index'] = render

    if not interfaces.IPage.implementedBy(class_):
        class_ = type(class_.__name__, (class_, Page), {})

    allowed_interface = (tuple(allowed_interface) +
                         (interfaces.IPage, ))

    class_dict = dict(kwargs)
    class_dict['__name__'] = name

    if title is not None:
        class_dict['title'] = title
    if subtitle is not None:
        class_dict['subtitle'] = subtitle

    # XXX: raise ConfigurationError if class_ is Page and
    #      no templates specified

    templates = template_specs({
        'template': template,
        'page_template': page_template,
        'content_template': content_template,
        }, content_type='html')

    class_ = subclass_content(
        class_, name,
        forward_methods,
        templates,
        class_dict,
        )

    handle_interfaces(_context, (for_,))
    handle_interfaces(_context, allowed_interface)

    handle_security(class_, permission,
                    allowed_interface, allowed_attributes)

    _context.action(
        discriminator=('view', for_, name, IBrowserRequest, layer),
        callable=zope.component.zcml.handler,
        args=('registerAdapter',
              class_, (for_, layer), Interface, name, _context.info),
        )


def activeViewlet(_context, name=None, factory=None,
                  for_=Interface, layer=interfaces.IFlourishLayer,
                  view=IBrowserView, manager=interfaces.IViewletManager):

    if name is not None and factory is not None:
        raise ConfigurationError("name and factory are mutually exclusive.")

    if name is not None:
        factory = lambda *args: name

    _context.action(
        discriminator=('flourish activeViewlet',
                       for_, layer, view, manager),
        callable=zope.component.zcml.handler,
        args=('registerAdapter',
              factory, (for_, layer, view, manager),
              interfaces.IActiveViewletName, '', _context.info),
        )
