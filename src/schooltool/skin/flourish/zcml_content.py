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
Meta directives and their handlers.
"""
import os

import zope.component.zcml
import zope.configuration.fields
from zope.security.checker import defineChecker, Checker, CheckerPublic
from zope.browserpage import ViewPageTemplateFile
from zope.interface import Interface
from zope.configuration.exceptions import ConfigurationError
from zope.component import zcml
from zope.viewlet.metadirectives import ITemplatedContentProvider

from schooltool.skin.flourish.content import ContentProvider
from schooltool.skin.flourish import interfaces


TEMPLATE_CONTENT_TYPES = {
    'xml': 'text/xml',
    'html': 'text/html',
}


class TemplatePath(zope.configuration.fields.Path):

    def fromUnicode(self, u):
        parts = u.split(':')
        content_type = None
        if len(parts) > 1:
            content_type_part = parts[0].strip().lower()
            if content_type_part in TEMPLATE_CONTENT_TYPES:
                content_type = TEMPLATE_CONTENT_TYPES.get(content_type_part)
                parts.pop(0)
        path = super(TemplatePath, self).fromUnicode(':'.join(parts))
        return content_type, path


class IContentDirective(ITemplatedContentProvider):
    """Define the SchoolTool content provider."""

    template = TemplatePath(
        title=u"Content-generating template.",
        required=False)

    update = zope.configuration.fields.PythonIdentifier(
        title=u"The name of the view attribute implementing content update.",
        required=False,
        )

    render = zope.configuration.fields.PythonIdentifier(
        title=u"The name of the view attribute that renders the content.",
        required=False,
        )

    provides = zope.configuration.fields.GlobalInterface(
        title=u"Interface the component provides",
        required=False,
        default=interfaces.IContentProvider,
        )

    title = zope.configuration.fields.MessageID(
        title=u"Title of this page",
        required=False,
        )


IContentDirective.setTaggedValue('keyword_arguments', True)


class IContentFactoryDirective(zope.component.zcml.IAdapterDirective):

    for_ = zope.configuration.fields.GlobalObject(
        title=u"The interface or class this view is for.",
        required=False,
        default=Interface,
        )

    factory = zope.configuration.fields.GlobalObject(
        title=u"The adapter factory.",
        required=True,
        )

    provides = zope.configuration.fields.GlobalInterface(
        title=u"Interface the component provides",
        required=False,
        default=interfaces.IContentProvider,
        )

    view = zope.configuration.fields.GlobalObject(
        title=u"The view the content provider is registered for.",
        description=(u"The view can either be an interface or a class. By "
                     "default the provider is registered for all views, "
                     "the most common case."),
        required=False,
        default=interfaces.IPageBase,
        )

    layer = zope.configuration.fields.GlobalInterface(
        title=(u"The layer the view is in."),
        required=False,
        default=interfaces.IFlourishLayer,
        )


def handle_security(class_, permission, interfaces, attributes):
    required = set(attributes)
    for ifc in interfaces:
        required.update(set(ifc))

    if permission == 'zope.Public':
        permission = CheckerPublic

    defineChecker(class_, Checker(dict.fromkeys(required, permission)))


def handle_interfaces(_context, interfaces):
    for ifc in interfaces:
        if ifc is not None:
            zope.component.zcml.interface(_context, ifc)


def template_specs(template_dict, content_type=None):
    content_type = TEMPLATE_CONTENT_TYPES.get(content_type, content_type)
    result = dict(template_dict)
    for var in result:
        if (result[var] is not None and
            result[var][0] is None):
            result[var] = (content_type, result[var][1])
    return result


_undefined = object()

def update_specs(template_dict, target):
    types = []
    if issubclass(target, Interface):
        types.append(
            target.queryTaggedValue('flourish.template_content_type', _undefined))
    implemented = getattr(target, '__implemented__', None)
    if implemented:
        for ifc in implemented.interfaces():
            types.append(
                ifc.queryTaggedValue('flourish.template_content_type', _undefined))
    types = filter(lambda p: p is not _undefined, types)
    if types:
        return template_specs(template_dict, types[0])
    return dict(template_dict)


def subclass_content(class_, name,
                     forward_call_dict,
                     template_dict, class_dict):
    class_dict = dict(class_dict)
    class_dict['__name__'] = name
    for attr, template_spec in template_dict.items():
        if not template_spec:
            continue
        content_type, template = template_spec
        if not template:
            continue
        class_dict[attr] = ViewPageTemplateFile(
            template, content_type=content_type)
    classname = (u'%s_%s' % (class_.__name__, name)).encode('ASCII')
    new_class = type(classname, (class_, ), class_dict)
    for attr, base_attr in forward_call_dict.items():
        if attr != base_attr:
            method = getattr(new_class, base_attr)
            setattr(new_class, attr, lambda *a, **kw: method(*a, **kw))
    return new_class


def contentDirective(
    _context, name, permission,
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPageBase,
    class_=ContentProvider, template=None,
    update='update', render='render',
    allowed_interface=(), allowed_attributes=(),
    **kwargs):

    if not interfaces.IContentProvider.implementedBy(class_):
        class_ = type(class_.__name__, (class_, ContentProvider), {})

    allowed_interface = (tuple(allowed_interface) +
                         (interfaces.IContentProvider, ))

    if (render == 'render' and
        class_.render == ContentProvider.render):
        if template:
            render = 'template'
        else:
            raise ConfigurationError(
                "When template and render not specified, "
                "class must implement 'render' method")

    templates = update_specs({'template': template}, view)
    class_ = subclass_content(
        class_, name,
        {'update': update, 'render': render},
        templates, kwargs)

    handle_interfaces(_context, (for_, view))
    handle_interfaces(_context, allowed_interface)

    handle_security(class_, permission,
                    allowed_interface, allowed_attributes)

    _context.action(
        discriminator=('schooltool.skin.flourish.content',
                       for_, layer, view, name),
        callable=zope.component.zcml.handler,
        args=('registerAdapter',
              class_,
              (for_, layer, view),
              interfaces.IContentProvider,
              name,
              _context.info),
        )


def contentFactory(
    _context, factory, name='', permission=None,
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPageBase,
    provides=interfaces.IContentProvider,
    trusted=True, locate=False):

    wrapper = lambda c, r, v: factory(c, r, v, name)
    objects = [for_, layer, view]
    zope.component.zcml.adapter(
        _context, [wrapper],
        provides=provides,
        for_=objects, permission=permission,
        name=name,
        trusted=trusted, locate=locate)
