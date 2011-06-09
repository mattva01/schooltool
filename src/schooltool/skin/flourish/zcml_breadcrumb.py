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
from zope.interface import Interface

from schooltool.skin.flourish.content import ContentProvider
from schooltool.skin.flourish.breadcrumbs import IBreadcrumb
from schooltool.skin.flourish.breadcrumbs import Breadcrumbs
from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish.zcml import IContentOrientedDirective
from schooltool.skin.flourish.zcml_content import handle_security


class IBreadcrumbDirective(IContentOrientedDirective):
    """Define the SchoolTool content provider."""

    class_ = zope.configuration.fields.GlobalObject(
        title=u"Class",
        description=u"The breadcrumb view class.",
        required=False,
        default=Breadcrumbs,
        )

IBreadcrumbDirective.setTaggedValue('keyword_arguments', True)


def breadcrumbDirective(
    _context,
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPage,
    class_=Breadcrumbs,
    **kwargs):

    bases = (class_, )
    if not IBreadcrumb.implementedBy(class_):
        bases = bases + (Breadcrumbs, )

    class_ = type(class_.__name__, (class_, ), kwargs)

    # XXX: I'm pretty sure security is not handled correctly here
    handle_security(class_, 'zope.Public', IBreadcrumb, ())

    _context.action(
        discriminator=('schooltool.skin.flourish.breadcrumb',
                       for_, layer, view),
        callable=zope.component.zcml.handler,
        args=('registerAdapter',
              class_,
              (for_, layer, view),
              IBreadcrumb,
              '',
              _context.info),
        )
