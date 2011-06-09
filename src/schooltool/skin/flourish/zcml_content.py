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


class IContentDirective(ITemplatedContentProvider):
    """Define the SchoolTool content provider."""

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


IContentDirective.setTaggedValue('keyword_arguments', True)


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


def subclass_content(class_, name,
                     forward_call_dict,
                     template_dict, class_dict):
    class_dict = dict(class_dict)
    class_dict['__name__'] = name
    for attr, base_attr in forward_call_dict.items():
        if attr != base_attr:
            method = getattr(class_, base_attr)
            class_dict[attr] = lambda *a, **kw: method(*a, **kw)
    for attr, template in template_dict.items():
        if template:
            class_dict[attr] = ViewPageTemplateFile(template)
    classname = (u'%s_%s' % (class_.__name__, name)).encode('ASCII')
    new_class = type(classname, (class_, ), class_dict)
    return new_class


def contentDirective(
    _context, name, permission,
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPage,
    class_=ContentProvider, template=None,
    update='update', render='render',
    allowed_interface=(), allowed_attributes=(),
    **kwargs):

    if not interfaces.IContentProvider.implementedBy(class_):
        class_ = type(name, (class_, ContentProvider), {})

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

    class_ = subclass_content(
        class_, name,
        {'update': update, 'render': render},
        {'template': template}, kwargs)

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
