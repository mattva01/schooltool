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

from zc.table import table
from zope import schema
from zope.app.form.browser.interfaces import ITerms
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtilitiesFor
from zope.component import getUtility

from zope.component import queryAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.formlib import form
from zope.interface import Interface
from zope.interface import implements, providedBy
from zope.component import adapts
from zope.publisher.browser import BrowserView
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.schema.interfaces import IVocabularyFactory

from schooltool.app.browser.app import BaseEditView
from schooltool.app.interfaces import ISchoolToolApplication
from zc.table.column import GetterColumn

from schooltool.resource.interfaces import (IBaseResourceContained,
             IResourceContainer, IResourceFactoryUtility,
             IResourceTypeInformation, IResourceTypeSource, IResourceSubTypes,
             IResource, IEquipment, ILocation)
from schooltool.resource.types import EquipmentFactoryUtility
from schooltool.skin.interfaces import IFilterWidget
from schooltool.skin.table import CheckboxColumn
from schooltool.skin.table import FilterWidget
from schooltool.skin.table import LabelColumn

from schooltool import SchoolToolMessage as _


class IResourceTypeSchema(Interface):
    """Schema for resource container view forms."""

    type = schema.Choice(title=_(u"Type"),
                         description=_("Type of Resource"),
                         source="resource_types"
                         )


class ResourceContainerView(form.FormBase):
    """A Resource Container view."""

    __used_for__ = IResourceContainer

    index_title = _("Resource index")

    prefix = "resources"
    form_fields = form.Fields(IResourceTypeSchema)
    searchActions = form.Actions(
        form.Action('Search', success='handle_search_action'),)

    actions = form.Actions(
                form.Action('Delete', success='handle_delete_action'),)
    template = ViewPageTemplateFile("resourcecontainer.pt")
    delete_template = ViewPageTemplateFile('container_delete.pt')

    resourceType = None

    def __init__(self, context, request):
        form.FormBase.__init__(self, context, request)
        self.resourceType = self.request.get('resources.type','|').split('|')[0]
        self.filter_widget = queryMultiAdapter((self.getResourceUtility(),
                                                self.request), IFilterWidget)
        self.typeVocabulary = queryUtility(IVocabularyFactory,
                                           name="resource_types")(self.context)

        if 'resources.actions.delete' in self.request:
            self.template = self.delete_template

    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)

    def handle_delete_action(self, action, data):
        pass

    def handle_search_action(self, action, data):
        pass

    def getResourceUtility(self):
        return queryUtility(IResourceFactoryUtility,
                            name=self.resourceType, default=None)

    def columns(self):
        return self.getResourceUtility().columns()

    def sortOn(self):
        return (('title', False), )

    def filter(self, values):
        items = [resource for resource in values
                 if IResourceTypeInformation(resource).id == self.resourceType]
        return self.filter_widget.filter(items)

    def renderResourceTable(self):
        columns = [CheckboxColumn(prefix="delete", name='delete', title=u'')]
        available_columns = self.columns()
        from schooltool.skin.table import URLColumn
        available_columns[0] = URLColumn(available_columns[0], self.request)

        columns.extend(available_columns)
        formatter = table.StandaloneFullFormatter(
            self.context, self.request, self.filter(self.context.values()),
            columns=columns,
            sort_on=self.sortOn(),
            prefix="available")
        formatter.cssClasses['table'] = 'data'
        return formatter()


class EquipmentTypeFilter(FilterWidget):
    """Equipment Type Filter"""

    def filter(self, list):
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in list
                       if (searchstr in item.title.lower() and
                           self.request.get('resources.type','|').split('|')[1] ==
        item.type)]
        else:
            self.request.form['SEARCH'] = ''
            results = list

        return results

class LocationTypeFilter(FilterWidget):
    """Location Type Filter"""


class ResourceTypeFilter(FilterWidget):
    """Resource Type Filter"""


class ResourceView(form.DisplayFormBase):
    """A Resource info view."""

    __used_for__ = IResource

    form_fields = form.Fields(IResource)

    template = ViewPageTemplateFile("resource.pt")

    def __init__(self, context, request):
        self.context = context
        self.request = request

class LocationView(ResourceView):
    """A location info view."""
    __used_for__ = ILocation
    form_fields = form.Fields(ILocation)
class EquipmentView(ResourceView):
    """A equipment info view."""
    __used_for__ = IEquipment
    form_fields = form.Fields(IEquipment)

class ResourceEditView(BaseEditView):
    """A view for editing resource info."""

    __used_for__ = IBaseResourceContained


class ResourceTypeSource(object):
    """Source that displays all the available resoure types."""

    implements(IResourceTypeSource)

    def __init__(self, context):
        self.context = context
        utilities = sorted(getUtilitiesFor(IResourceFactoryUtility))
        self.types = []
        for name, utility in utilities:
            if IResourceSubTypes.providedBy(utility):
                subTypeAdapter = utility
            else:
                subTypeAdapter = queryAdapter(utility, IResourceSubTypes,
                                          default=None)
                if subTypeAdapter != None:
                    subTypeAdapter = subTypeAdapter()
            typeHeader = [name,name,'clickable']
            self.types.append(typeHeader)
            if subTypeAdapter:
                typeHeader[2] = 'unclickable'
                subTypes = subTypeAdapter
                for type in subTypes.types():
                    self.types.append([name, type,'clickable'])

    def __contains__(self, value):
        return value in self.types

    def __len__(self):
        len(self.types)

    def __iter__(self):
        return iter(self.types)

class ResourceTypeTerm(object):
    """Term for displaying of a resource type."""

    implements(ITitledTokenizedTerm)

    def __init__(self, value, title):
        self.value = value
        self.token = value
        self.title = title


class ResourceTypeTerms(object):
    """Terms implementation for resource types."""

    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getTerm(self, value):
        if value not in self.context:
            raise LookupError(value)
        return ResourceTypeTerm('%s|%s' % (value[0],value[1]),
                                value[1])

    def getValue(self, token):
        if token not in self.context:
            raise LookupError(token)
        return token
