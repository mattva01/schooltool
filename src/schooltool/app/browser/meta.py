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
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserView
from zope.viewlet.metadirectives import ITemplatedContentProvider
from zope.viewlet.metaconfigure import _handle_permission
from zope.viewlet.metaconfigure import _handle_allowed_interface
from zope.viewlet.metaconfigure import _handle_allowed_attributes
from zope.viewlet.metaconfigure import _handle_for

from schooltool.app.browser.content import ISchoolToolContentProvider
from schooltool.app.browser.content import ContentProvider
from schooltool.skin import ISchoolToolLayer


class ISchoolToolContentDirective(ITemplatedContentProvider):
    """Define the SchoolTool content provider."""

    update = zope.configuration.fields.PythonIdentifier(
        title=u"The name of the view attribute implementing content update.",
        required=False,
        )

    render = zope.configuration.fields.PythonIdentifier(
        title=u"The name of the view attribute that renders the content.",
        required=False,
        )


ISchoolToolContentDirective.setTaggedValue('keyword_arguments', True)


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
                     update_attr, render_attr,
                     template_dict, class_dict):
    class_dict = dict(class_dict)
    class_dict['__name__'] = name
    class_dict['update'] = getattr(class_, update_attr)
    class_dict['render'] = getattr(class_, render_attr)
    for attr, template in template_dict.items():
        if template:
            class_dict[attr] = ViewPageTemplateFile(template)
    new_class = type('%s_%s' % (class_.__name__, name), (class_, ), class_dict)
    return new_class


def contentDirective(
    _context, name, permission,
    for_=Interface, layer=ISchoolToolLayer, view=IBrowserView,
    class_=ContentProvider, template=None,
    update='update', render='render',
    allowed_interface=(), allowed_attributes=(),
    **kwargs):

    if not ISchoolToolContentProvider.implementedBy(class_):
        class_ = type(name, (class_, ContentProvider), {})

    allowed_interface = (tuple(allowed_interface) +
                         (ISchoolToolContentProvider, ))

    if (render == 'render' and
        class_.render == ContentProvider.render):
        if template:
            render = 'template'
        else:
            raise ConfigurationError("When template and render not specified, class must implement 'render' method")

    class_ = subclass_content(
        class_, name, update, render,
        {'template': template}, kwargs)

    handle_interfaces(_context, (for_, view))
    handle_interfaces(_context, allowed_interface)

    handle_security(class_, permission,
                    allowed_interface, allowed_attributes)

    _context.action(
        discriminator = ('schooltool.skin.flourish.content',
                         for_, layer, view, name),
        callable = zope.component.zcml.handler,
        args = ('registerAdapter',
                class_,
                (for_, layer, view),
                ISchoolToolContentProvider,
                name,
                _context.info),)
