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

from zope.browserpage import ViewPageTemplateFile
from zope.interface import Interface
from zope.configuration.exceptions import ConfigurationError
from zope.component import zcml
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserView
from zope.security import checker
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

ISchoolToolContentDirective.setTaggedValue('keyword_arguments', True)


def createContentProviderClass(name, base, template=None, extra_attrs=None):
    attrs = extra_attrs and dict(extra_attrs) or {}

    attrs['__name__'] = name

    if template is not None:
        attrs['template'] = ViewPageTemplateFile(template)
        base_render = getattr(base, 'render', ContentProvider.render)
        if base_render == ContentProvider.render:
            def renderTemplate(self, *args, **kw):
                return self.template(*args, **kw)
            attrs['render'] = renderTemplate

    if ISchoolToolContentProvider.implementedBy(base):
        bases = (base,)
    else:
        bases = (base, ContentProvider)

    NewContentProvider = type(base.__name__, bases, attrs)
    return NewContentProvider


def contentDirective(
    _context, name, permission,
    for_=Interface, layer=ISchoolToolLayer, view=IBrowserView,
    class_=ContentProvider, template=None,
    allowed_interface=None, allowed_attributes=None,
    **kwargs):

    permission = _handle_permission(_context, permission)

    if template is not None:
        template = os.path.abspath(str(_context.path(template)))
        if not os.path.isfile(template):
            raise ConfigurationError("No such file", template)

    new_class = createContentProviderClass(
        name, class_, template=template, extra_attrs=kwargs)

    required = dict.fromkeys(ISchoolToolContentProvider, permission)

    _handle_allowed_interface(
        _context, (ISchoolToolContentProvider,), permission, required)

    if allowed_interface is not None:
        _handle_allowed_interface(
            _context, allowed_interface, permission, required)

    if allowed_attributes is not None:
        _handle_allowed_attributes(
            _context, allowed_attributes, permission, required)

    _handle_for(_context, for_)
    zcml.interface(_context, view)

    checker.defineChecker(new_class, checker.Checker(required))

    _context.action(
        discriminator = ('content', for_, layer, view, name),
        callable = zcml.handler,
        args = ('registerAdapter',
                new_class,
                (for_, layer, view),
                ISchoolToolContentProvider,
                name,
                _context.info),)
