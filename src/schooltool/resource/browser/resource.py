#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
group views.

$Id$
"""

from zope.publisher.browser import BrowserView
from zope.formlib import form
from zope.interface import Interface
from zope import schema
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool import SchoolToolMessage as _
from schooltool.skin.containers import TableContainerView
from schooltool.app.browser.app import BaseAddView, BaseEditView
from zc.table.column import GetterColumn

from schooltool.resource.interfaces import IResourceContainer
from schooltool.resource.interfaces import IResourceContained
from schooltool import SchoolToolMessage as _

from schooltool.demographics.interfaces import SourceList

class IResourceTypeSchema(Interface):
    """Schema for resource container view forms."""

    type = schema.Choice(title=_(u"Type"),
                         description=_("Type of Resource"),
                         source=SourceList([_('Projector'),_('Computer Lab')])
                         )

class ResourceContainerView(form.FormBase):
    """A Resource Container view."""

    __used_for__ = IResourceContainer

    index_title = _("Resource index")

    prefix = "resources"
    form_fields = form.Fields(IResourceTypeSchema)
    actions = form.Actions(
        form.Action('Search', success='handle_search_action'))
    template = ViewPageTemplateFile("resourcecontainer.pt")

    def handle_search_action(self, action, data):
        self.resourceType = self.request.get('resources.type')

    def columns(self):
        return (GetterColumn(name='title',
                             title=u'Title',
                             getter=lambda i,f: getattr(i,'title',u''),
                             subsort=True),
                GetterColumn(name='type',
                             title=u'Type',
                             getter=lambda i,f: getattr(i,'type',u''),
                             subsort=True),
                GetterColumn(name='model',
                             title=u'Model',
                             getter=lambda i,f: getattr(i,'model',u''),
                             subsort=True),
                GetterColumn(name='manufacturer',
                             title=u'Manufacturer',
                             getter=lambda i,f: getattr(i,'manufacturer',u''),
                             subsort=True),
                )


class ResourceView(BrowserView):
    """A Resource info view."""

    __used_for__ = IResourceContained


class ResourceEditView(BaseEditView):
    """A view for editing resource info."""

    __used_for__ = IResourceContained
