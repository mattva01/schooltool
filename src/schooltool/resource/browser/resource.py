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
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtilitiesFor
from zope.component import queryAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.formlib import form
from zope.app.zapi import absoluteURL
from zope.app.session.interfaces import ISession


from schooltool.app.browser.app import BaseEditView
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.resource.interfaces import (IBaseResourceContained,
             IResourceContainer, IResourceTypeInformation, IResourceSubTypes,
             IResource, IEquipment, ILocation)
from schooltool.skin.interfaces import IFilterWidget
from schooltool.skin.table import CheckboxColumn
from schooltool.skin.table import FilterWidget
from schooltool.person.browser.person import PersonFilterWidget
from schooltool.resource.interfaces import IResourceFactoryUtility

from schooltool import SchoolToolMessage as _


class ResourceContainerView(form.FormBase):
    """A Resource Container view."""

    __used_for__ = IResourceContainer

    index_title = _("Resource index")

    prefix = "resources"
    form_fields = form.Fields()
    searchActions = form.Actions(
        form.Action('Search', success='handle_search_action'),)

    actions = form.Actions(
                form.Action('Delete', success='handle_delete_action'),
                form.Action('Book', success='handle_book_action'))
    template = ViewPageTemplateFile("resourcecontainer.pt")
    delete_template = ViewPageTemplateFile('container_delete.pt')

    resourceType = None

    def __init__(self, context, request):
        form.FormBase.__init__(self, context, request)
        self.resourceType = self.request.get('resources.type','|').split('|')[0]
        self.filter_widget = queryMultiAdapter((self.getResourceUtility(),
                                                self.request), IFilterWidget)


    def getSubTypes(self):
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

            typeHeader = [name, utility.title, 'unclickable']
            self.types.append(typeHeader)
            for subtype in subTypeAdapter.types():
                self.types.append([name, subtype, 'clickable'])
        return self.types

    def listIdsForDeletion(self):
        return [key for key in self.context
                if "delete.%s" % key in self.request]

    def _listItemsForDeletion(self):
        return [self.context[key] for key in self.listIdsForDeletion()]

    itemsToDelete = property(_listItemsForDeletion)

    def handle_delete_action(self, action, data):
        self.template = self.delete_template

    def handle_search_action(self, action, data):
        pass

    def handle_book_action(self, action, data):
        sessionWrapper = ISession(self.request)
        session = sessionWrapper['schooltool.resource']
        session['bookingSelection'] = [''.join(key.split('.')[1:])
                                       for key in self.request
                                       if key.startswith('delete.')]
        url = absoluteURL(IBookingCalendar(self.context), self.request)
        return self.request.response.redirect(url)

    def getResourceUtility(self):
        return queryUtility(IResourceFactoryUtility,
                            name=self.resourceType, default=None)

    def columns(self):
        return self.getResourceUtility().columns()

    def sortOn(self):
        return (('title', False), )

    def filter(self, values):
        return self.filter_widget.filter(values)

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

class BaseTypeFilter(FilterWidget):
    """Base Type Filter"""

    def render(self):
        if 'CLEAR_SEARCH' in self.request:
            self.request.form['SEARCH'] = ''
        return self.template()

    def filter(self, list):
        resourceType = self.request.get('resources.type','|').split('|')[0]
        list = [resource for resource in list
                 if IResourceTypeInformation(resource).id == resourceType]
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in list
                       if (searchstr in item.title.lower() and
                           self.request.get('resources.type','|').split('|')[1] == item.type)]
        elif 'resources.type' in self.request:
            results = [item for item in list
                       if self.request.get('resources.type','|').split('|')[1] == item.type]
        else:
            results = list

        return results


class EquipmentTypeFilter(BaseTypeFilter):
    """Equipment Type Filter"""


class LocationTypeFilter(BaseTypeFilter):
    """Location Type Filter"""


class ResourceTypeFilter(BaseTypeFilter):
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


class ResourceContainerFilterWidget(PersonFilterWidget):

    template = ViewPageTemplateFile('resource_filter.pt')
    parameters = ['SEARCH_TITLE', 'SEARCH_TYPE']

    def types(self):
        utilities = sorted(getUtilitiesFor(IResourceFactoryUtility))
        types = []
        for name, utility in utilities:
            types.append({'title': utility.title,
                          'id': name})
        return types

    def filter(self, list):
        if 'CLEAR_SEARCH' in self.request:
            for parameter in self.parameters:
                self.request.form[parameter] = ''
            return list

        results = list

        if 'SEARCH_TITLE' in self.request:
            searchstr = self.request['SEARCH_TITLE'].lower()
            results = [item for item in results
                       if searchstr in item.title.lower()]

        if 'SEARCH_TYPE' in self.request:
            type = self.request['SEARCH_TYPE']
            if not type:
                return results

            results = [item for item in results
                       if IResourceTypeInformation(item).id == type]

        return results
