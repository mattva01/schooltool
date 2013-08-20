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
import zope.component.zcml
import zope.configuration.fields
from zope.interface import Interface
from zope.security.zcml import Permission

from schooltool.skin.flourish.breadcrumbs import IBreadcrumb
from schooltool.skin.flourish.breadcrumbs import Breadcrumbs
from schooltool.skin.flourish.breadcrumbs import PageBreadcrumbs
from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish.zcml import IContentOrientedDirective
from schooltool.skin.flourish.zcml_content import handle_security
from schooltool.skin.flourish.zcml_content import IContentDirective
from schooltool.skin.flourish.zcml_content import contentDirective


class IBreadcrumbDirectiveBase(Interface):

    crumb_parent = zope.configuration.fields.GlobalObject(
        title=u"Crumb parent",
        description=u"Getter of the crumb parent.",
        required=False,
        )

    follow_crumb = zope.configuration.fields.GlobalObject(
        title=u"Follow crumb",
        description=u"The breadcrumb factory.",
        required=False,
        )


class IBreadcrumbDirective(IContentOrientedDirective,
                           IBreadcrumbDirectiveBase):
    """Define the SchoolTool content provider."""

    title = zope.configuration.fields.MessageID(
        title=u"Title",
        required=False,
        )

    class_ = zope.configuration.fields.GlobalObject(
        title=u"Class",
        description=u"The breadcrumb view class.",
        required=False,
        default=Breadcrumbs,
        )


IBreadcrumbDirective.setTaggedValue('keyword_arguments', True)


class IPageBreadcrumbsDirective(IContentDirective):
    """Define breadcrumbs content for a page."""

    name = zope.schema.TextLine(
        title=u"The name of the content provider.",
        required=False,
        default=u'breadcrumbs')

    permission = Permission(
        title=u"Permission",
        description=u"The permission needed to use the view.",
        required=False,
        )

    crumb_parent = zope.configuration.fields.GlobalObject(
        title=u"Crumb parent",
        description=u"Getter of the crumb parent.",
        required=False,
        )

    follow_crumb = zope.configuration.fields.GlobalObject(
        title=u"Follow crumb",
        description=u"The breadcrumb factory.",
        required=False,
        )

    show_page_title = zope.configuration.fields.Bool(
        title=u"Show page title",
        required=False,
        default=True)


IPageBreadcrumbsDirective.setTaggedValue('keyword_arguments', True)


def breadcrumbDirective(
    _context,
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPage,
    crumb_parent=None, follow_crumb=None,
    class_=Breadcrumbs,
    **kwargs):

    class_dict = dict(kwargs)

    bases = (class_, )
    if not IBreadcrumb.implementedBy(class_):
        bases = bases + (Breadcrumbs, )

    if crumb_parent is not None:
        class_dict['crumb_parent'] = property(
            lambda crumb: crumb_parent(crumb.context))

    if follow_crumb is not None:
        class_dict['follow_crumb'] = property(
            lambda crumb: follow_crumb(
                crumb.crumb_parent, crumb.request, crumb.view))

    class_ = type(class_.__name__, bases, class_dict)

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


def pageBreadcrumbsDirective(
    _context, name=u'breadcrumbs', permission=u'zope.Public',
    for_=Interface, layer=interfaces.IFlourishLayer, view=interfaces.IPage,
    class_=None, show_page_title=True,
    **kwargs):

    if class_ is None:
        if show_page_title:
            class_ = PageBreadcrumbs
        else:
            class_ = Breadcrumbs

    kwargs = dict(kwargs)
    _crumb_parent_factory = kwargs.get('crumb_parent')
    _follow_crumb_factory = kwargs.get('follow_crumb')

    if _crumb_parent_factory is not None:
        kwargs['crumb_parent'] = property(
            lambda crumb: _crumb_parent_factory(crumb.context))

    if _follow_crumb_factory is not None:
        kwargs['follow_crumb'] = property(
            lambda crumb: _follow_crumb_factory(
                crumb.crumb_parent, crumb.request, crumb.view))

    contentDirective(
        _context, name, permission,
        for_=for_, layer=layer, view=view,
        class_=class_, **kwargs)
