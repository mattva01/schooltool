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

import z3c.form
from z3c.form import form, field, button, subform, validator, widget
from z3c.form.interfaces import DISPLAY_MODE, HIDDEN_MODE, NO_VALUE, IActionHandler
from zc.table import table

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapter, adapts
from zope.component import getUtilitiesFor
from zope.component import queryAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.component import getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.event import notify
from zope.formlib import form as oldform
from zope.interface import implementer, implements, implementsOnly
from zope.lifecycleevent import ObjectCreatedEvent
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.session.interfaces import ISession
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL

from schooltool.app.browser.app import BaseEditView
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.browser.demographics import DemographicsView
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.resource.interfaces import (IBaseResourceContained,
             IResourceContainer, IResourceTypeInformation, IResourceSubTypes,
             IResource, IEquipment, ILocation, IResourceDemographicsFields)
from schooltool.resource.resource import Resource, Location, Equipment
from schooltool.table.interfaces import IFilterWidget
from schooltool.table.table import url_cell_formatter
from schooltool.table.table import CheckboxColumn
from schooltool.table.table import FilterWidget
from schooltool.person.browser.person import PersonFilterWidget
from schooltool.resource.interfaces import IResourceFactoryUtility

from schooltool.common import SchoolToolMessage as _


class ResourceContainerView(oldform.FormBase):
    """A Resource Container view."""

    __used_for__ = IResourceContainer

    index_title = _("Resource index")

    prefix = "resources"
    form_fields = oldform.Fields()
    searchActions = oldform.Actions(
        oldform.Action('Search', success='handle_search_action'),)

    actions = oldform.Actions(
                oldform.Action('Delete', success='handle_delete_action'),
                oldform.Action('Book', success='handle_book_action'))
    template = ViewPageTemplateFile("resourcecontainer.pt")
    delete_template = ViewPageTemplateFile('container_delete.pt')

    resourceType = None

    def __init__(self, context, request):
        oldform.FormBase.__init__(self, context, request)
        self.resourceType = self.request.get('SEARCH_TYPE','|').split('|')[0]
        self.filter_widget = queryMultiAdapter((self.getResourceUtility(),
                                                self.request), IFilterWidget)


    def getSubTypes(self):
        utilities = sorted(getUtilitiesFor(IResourceFactoryUtility))

        types = []
        for name, utility in utilities:
            if IResourceSubTypes.providedBy(utility):
                subTypeAdapter = utility
            else:
                subTypeAdapter = queryAdapter(utility, IResourceSubTypes,
                                          default=None)
                if subTypeAdapter != None:
                    subTypeAdapter = subTypeAdapter()

            typeHeader = [name, utility.title, 'unclickable']
            subTypes = subTypeAdapter.types()
            if subTypes:
                types.append(typeHeader)
                for subtype in subTypes:
                    types.append([name, subtype, 'clickable'])
        return types

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
        available_columns[0].cell_formatter = url_cell_formatter

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
        resourceType = self.request.get('SEARCH_TYPE','|').split('|')[0]
        list = [resource for resource in list
                 if IResourceTypeInformation(resource).id == resourceType]
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            results = [item for item in list
                       if (searchstr in item.title.lower() and
                           self.request.get('SEARCH_TYPE','|').split('|')[1] == item.type)]
        elif 'SEARCH_TYPE' in self.request:
            results = [item for item in list
                       if self.request.get('SEARCH_TYPE','|').split('|')[1] == item.type]
        else:
            results = list

        return results


class EquipmentTypeFilter(BaseTypeFilter):
    """Equipment Type Filter"""


class LocationTypeFilter(BaseTypeFilter):
    """Location Type Filter"""


class ResourceTypeFilter(BaseTypeFilter):
    """Resource Type Filter"""


class IResourceSubTypeWidget(z3c.form.interfaces.ITextWidget):
    pass


class ResourceSubTypeWidget(z3c.form.browser.text.TextWidget):
    implementsOnly(IResourceSubTypeWidget)

    utility = None

    def __init__(self, request, utility=None):
        super(ResourceSubTypeWidget, self).__init__(request)
        self.utility = utility

    def freeTextValue(self):
        if self.value in self.subTypes():
            return ''
        return self.value

    def subTypes(self):
        util = queryUtility(IResourceFactoryUtility,
                            name=self.utility,
                            default=None)
        if IResourceSubTypes.providedBy(util):
            subtypes = util
        else:
            subtypes = queryAdapter(util, IResourceSubTypes, default=None)
        if subtypes is not None:
            return subtypes.types()
        return []

    def hasInput(self):
        return self.request.get(self.name,None) != '' or self.request.get(self.name+'.newSubType',None)

    def extract(self, default=NO_VALUE):
        subType = self.request.get(self.name, default)
        newSubType = self.request.get(self.name+'.newSubType', default)
        if subType and subType != default:
            return subType
        return newSubType or default


def ResourceSubTypeFieldWidget(field, request):
    utility_name = 'resource'
    if not field.interface is None:
        # XXX: this is what we get for using named utilities
        if issubclass(field.interface, IEquipment):
            utility_name = 'equipment'
        elif issubclass(field.interface, ILocation):
            utility_name = 'location'
    return widget.FieldWidget(
        field,
        ResourceSubTypeWidget(request, utility=utility_name)
        )


class ResourceContainerFilterWidget(PersonFilterWidget):

    template = ViewPageTemplateFile('resource_filter.pt')
    parameters = ['SEARCH_TITLE', 'SEARCH_TYPE']

    def types(self):
        utilities = sorted(getUtilitiesFor(IResourceFactoryUtility))
        types = []
        for name, utility in utilities:
            if IResourceSubTypes.providedBy(utility):
                subTypeAdapter = utility
            else:
                subTypeAdapter = queryAdapter(utility, IResourceSubTypes,
                                          default=None)
                if subTypeAdapter != None:
                    subTypeAdapter = subTypeAdapter()

            typeHeader = {'id':name,
                          'title':utility.title,
                          'clickable':False}
            types.append(typeHeader)
            for subtype in subTypeAdapter.types():
                types.append({'id':name, 'title':subtype, 'clickable':True})
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
            type = type.split('|')[0]
            utility = queryUtility(IResourceFactoryUtility,
                                   name=type, default=None)
            filter_widget = queryMultiAdapter((utility,self.request), IFilterWidget)
            if filter_widget:
                results = filter_widget.filter(results)

        return results


class ResourceDemographicsFieldsAbsoluteURLAdapter(BrowserView):

    adapts(IResourceDemographicsFields, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/resource_demographics'

    __call__ = __str__


class ResourceDemographicsView(DemographicsView):

    title = _('Resource Demographics Container')


##########  Base class of all resource views (uses self.resource_type) #########
class ResourceFieldGenerator(object):

    def makeRows(self, fields, cols=1):
        rows = []
        while fields:
            rows.append(fields[:cols])
            fields = fields[cols:]
        return rows

    def makeFieldSet(self, fieldset_id, legend, fields, cols=1):
        result = {
            'id': fieldset_id,
            'legend': legend,
            }
        result['rows'] = self.makeRows(fields, cols)
        return result

    def fieldsets(self):
        result = []
        sources = [
            (self.base_id, self.base_legend, list(self.getBaseFields())),
            (self.demo_id, self.demo_legend, list(self.getDemoFields())),
            ]
        for fieldset_id, legend, fields in sources:
            result.append(self.makeFieldSet(fieldset_id, legend, fields, 2))
        return result

    def getDemoFields(self):
        fields = field.Fields()
        dfs = IResourceDemographicsFields(ISchoolToolApplication(None))
        for field_desc in dfs.filter_key(self.resource_type):
            fields += field_desc.makeField()
        return fields


###############  Resource view (group determined by base class) #################
class BaseResourceView(form.Form, ResourceFieldGenerator):

    template = ViewPageTemplateFile('templates/resource_view.pt')
    mode = DISPLAY_MODE
    id = 'resource-view'

    @property
    def label(self):
        return self.context.title

    def update(self):
        self.fields = self.getBaseFields()
        self.fields += self.getDemoFields()
        self.subforms = []
        super(BaseResourceView, self).update()

    def __call__(self):
        self.update()
        return self.render()

    def updateWidgets(self):
        super(BaseResourceView, self).updateWidgets()
        for widget in self.widgets:
            if not self.widgets[widget].value:
                self.widgets[widget].mode = HIDDEN_MODE


class ResourceView(BaseResourceView):
    """A location info view."""

    resource_type = 'resource'

    def getBaseFields(self):
        return field.Fields(IResource)


class LocationView(BaseResourceView):
    """A location info view."""

    resource_type = 'location'

    def getBaseFields(self):
        return field.Fields(ILocation)


class EquipmentView(BaseResourceView):
    """A equipment info view."""

    resource_type = 'equipment'

    def getBaseFields(self):
        return field.Fields(IEquipment)


###############  Base classes of all resource add/edit views ################
class BaseResourceAddView(form.AddForm, ResourceFieldGenerator):

    id = 'resource-form'
    template = ViewPageTemplateFile('templates/resource_form.pt')

    def getBaseFields(self):
        return field.Fields(IResource)

    def groupViewURL(self):
        return '%s/%s.html' % (absoluteURL(self.context, self.request),
                               self.group_id)

    def updateActions(self):
        super(BaseResourceAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'))
    def handleAdd(self, action):
        super(BaseResourceAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.groupViewURL())

    def createAndAdd(self, data):
        resource = self._factory()
        resource.title = data.get('title')
        chooser = INameChooser(self.context)
        resource.__name__ = chooser.chooseName('', resource)
        form.applyChanges(self, resource, data)
        notify(ObjectCreatedEvent(resource))
        self.context[resource.__name__] = resource
        return resource

    def update(self):
        self.fields = self.getBaseFields()
        self.fields += self.getDemoFields()
        self.updateWidgets()
        self.updateActions()
        self.actions.execute()

    def updateWidgets(self):
        super(BaseResourceAddView, self).updateWidgets()

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class BaseResourceEditView(form.EditForm, ResourceFieldGenerator):

    id = 'resource-form'
    template = ViewPageTemplateFile('templates/resource_form.pt')

    def update(self):
        self.fields = self.getBaseFields()
        self.fields += self.getDemoFields()
        super(BaseResourceEditView, self).update()

    @button.buttonAndHandler(_('Apply'))
    def handle_apply_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @property
    def label(self):
        return _(u'Change information for ${fullname}',
                 mapping={'fullname': self.context.title})

    def updateActions(self):
        super(BaseResourceEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


###############  Resource add/edit views ################
class BaseResourceForm(object):

    resource_type = 'resource'
    base_id = 'base-data'
    base_legend = _('Resource identification')
    demo_id = 'demo-data'
    demo_legend = _('Resource demographics')

    def getBaseFields(self):
        return field.Fields(IResource).omit('type')


class ResourceAddView(BaseResourceForm, BaseResourceAddView):

    label = _('Add new resource')
    _factory = Resource


class ResourceEditView(BaseResourceForm, BaseResourceEditView):

    label = _('Edit resource')


###############  Location add/edit views ################
class BaseLocationForm(object):

    resource_type = 'location'
    base_id = 'base-data'
    base_legend = _('Location identification')
    demo_id = 'demo-data'
    demo_legend = _('Location demographics')

    def getBaseFields(self):
        fields = field.Fields(ILocation)
        return fields


class LocationAddView(BaseLocationForm, BaseResourceAddView):

    label = _('Add new location')
    _factory = Location


class LocationEditView(BaseLocationForm, BaseResourceEditView):

    label = _('Edit location')


###############  Equipment add/edit views ################
class BaseEquipmentForm(object):

    resource_type = 'equipment'
    base_id = 'base-data'
    base_legend = _('Equipment identification')
    demo_id = 'demo-data'
    demo_legend = _('Equipment demographics')

    def getBaseFields(self):
        fields = field.Fields(IEquipment)
        return fields


class EquipmentAddView(BaseEquipmentForm, BaseResourceAddView):

    label = _('Add new equipment')
    _factory = Equipment


class EquipmentEditView(BaseEquipmentForm, BaseResourceEditView):

    label = _('Edit equipment')

