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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Resource views
"""
from collections import defaultdict
from datetime import datetime

import z3c.form
import z3c.form.browser.text
import zc.table.table
from z3c.form import form, field, button, widget
from z3c.form.interfaces import DISPLAY_MODE, HIDDEN_MODE, NO_VALUE
from zc.table.column import GetterColumn

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import adapter, adapts
from zope.component import getUtilitiesFor
from zope.component import queryAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.component import getMultiAdapter
from zope.container.interfaces import INameChooser
from zope.event import notify
from zope.formlib import form as oldform
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.interface import implementer, implements, implementsOnly
from zope.lifecycleevent import ObjectCreatedEvent
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.security.checker import canAccess
from zope.session.interfaces import ISession
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.browser.app import EditRelationships
from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.browser.app import RelationshipRemoveTableMixin
from schooltool.basicperson.browser.demographics import (
    DemographicsView,
    FlourishDemographicsView, FlourishReorderDemographicsView)
from schooltool.basicperson.interfaces import IAddEditViewTitle
from schooltool.basicperson.interfaces import ILimitKeysLabel
from schooltool.basicperson.interfaces import ILimitKeysHint
from schooltool.common.inlinept import InheritTemplate, InlineViewPageTemplate
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.resource.interfaces import (
             IResourceContainer, IResourceTypeInformation, IResourceSubTypes,
             IResource, IEquipment, ILocation, IResourceDemographicsFields)
from schooltool.report.browser.report import RequestRemoteReportDialog
from schooltool.resource.resource import Resource, Location, Equipment
from schooltool.person.browser.person import PersonFilterWidget
from schooltool.resource.interfaces import IResourceFactoryUtility
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.skin import flourish
from schooltool import table

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
        self.filter_widget = queryMultiAdapter(
            (self.getResourceUtility(), self.request),
            table.interfaces.IFilterWidget)


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
        columns = [table.column.CheckboxColumn(
                       prefix="delete", name='delete', title=u'')]
        available_columns = self.columns()
        available_columns[0].cell_formatter = table.table.url_cell_formatter

        columns.extend(available_columns)
        formatter = zc.table.table.StandaloneFullFormatter(
            self.context, self.request, self.filter(self.context.values()),
            columns=columns,
            sort_on=self.sortOn(),
            prefix="available")
        formatter.cssClasses['table'] = 'data'
        return formatter()


class FlourishResourcesView(flourish.page.Page):

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
    ''')


class ResourcesTable(table.ajax.Table):

    def columns(self):
        default = table.ajax.Table.columns(self)
        description = GetterColumn(
            name='description',
            title=_(u'Description'),
            getter=lambda i, f: i.description or '')
        return default + [description]


class ResourceListTable(ResourcesTable):

    @property
    def source(self):
        return ISchoolToolApplication(None)['resources']

    def items(self):
        return self.context


class LocationListTable(ResourceListTable):

    def items(self):
        return [r for r in self.context
                if ILocation(r, None) is not None]


class EquipmentListTable(ResourceListTable):

    def items(self):
        return [r for r in self.context
                if IEquipment(r, None) is not None]


class EditResourceRelationships(EditRelationships):

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['resources']


class EditLocationRelationships(EditResourceRelationships):
    pass


class EditEquipmentRelationships(EditResourceRelationships):
    pass


class LocationAddRelationshipTable(RelationshipAddTableMixin,
                                   ResourcesTable):
    pass


class LocationRemoveRelationshipTable(RelationshipRemoveTableMixin,
                                      ResourcesTable):
    pass


class EquipmentAddRelationshipTable(RelationshipAddTableMixin,
                                    ResourcesTable):
    pass


class EquipmentRemoveRelationshipTable(RelationshipRemoveTableMixin,
                                       ResourcesTable):
    pass


class BaseTypeFilter(table.table.FilterWidget):
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
            filter_widget = queryMultiAdapter((utility,self.request),
                                              table.interfaces.IFilterWidget)
            if filter_widget:
                results = filter_widget.filter(results)

        return results


class FlourishResourceContainerFilterWidget(ResourceContainerFilterWidget):

    template = ViewPageTemplateFile('templates/f_resource_filter.pt')

    search_title_id = 'SEARCH_TITLE'
    search_type_id = 'SEARCH_TYPE'

    def types(self):
        options = [
            {'id': 'equipment',
             'title': _('Equipment')},
            {'id': 'location',
             'title': _('Location')},
            {'id': 'resource',
             'title': _('Resource')},
            ]
        return options

    def filter(self, results):
        if self.search_title_id in self.request:
            searchstr = self.request[self.search_title_id].lower()
            results = [item for item in results
                       if searchstr in item.title.lower() or
                       (item.description and searchstr in item.description.lower())]
        if self.search_type_id in self.request:
            type = self.request[self.search_type_id]
            if not type:
                return results
            results = [resource for resource in results
                       if IResourceTypeInformation(resource).id == type]
        return results


class ResourcesTableFilter(table.ajax.TableFilter,
                           FlourishResourceContainerFilterWidget):

    template = ViewPageTemplateFile('templates/f_resource_table_filter.pt')

    @property
    def search_title_id(self):
        return self.manager.html_id+"-title"

    @property
    def search_group_id(self):
        return self.manager.html_id+"-group"

    def filter(self, results):
        if self.ignoreRequest:
            return results
        return FlourishResourceContainerFilterWidget.filter(self, results)


class ResourceContainerLinks(flourish.page.RefineLinksViewlet):
    """Resource container links viewlet."""


class ResourceImportLinks(flourish.page.RefineLinksViewlet):
    """Resource import links viewlet."""


class ResourceDemographicsFieldsAbsoluteURLAdapter(BrowserView):

    adapts(IResourceDemographicsFields, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/resource_demographics'

    __call__ = __str__


class ResourceDemographicsView(DemographicsView):

    title = _('Resource Attributes')


class FlourishResourceDemographicsView(FlourishDemographicsView):

    container_class = 'container'

    keys = [('resource', _('Res.')),
            ('location', _('Locat.')),
            ('equipment', _('Equip.'))]


class FlourishReorderResourceDemographicsView(FlourishReorderDemographicsView):
    pass


@adapter(IResourceDemographicsFields)
@implementer(IAddEditViewTitle)
def getAddEditViewTitle(context):
    return _('Resource attributes')


@adapter(IResourceDemographicsFields)
@implementer(ILimitKeysLabel)
def getLimitKeysLabel(context):
    return _('Limit to resource type(s)')


@adapter(IResourceDemographicsFields)
@implementer(ILimitKeysHint)
def getLimitKeysHint(context):
    return _(u"If you select one or more resource types below, this field "
              "will only be displayed in forms and reports for "
              "resources of the selected types.")


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


class FlourishBaseResourceView(flourish.page.Page, BaseResourceView):

    def update(self):
        BaseResourceView.update(self)

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    def has_leaders(self):
        return bool(list(self.context.leaders))


class ResourceView(BaseResourceView):
    """A location info view."""

    resource_type = 'resource'

    def getBaseFields(self):
        return field.Fields(IResource)


class FlourishResourceView(FlourishBaseResourceView, ResourceView):

    def getBaseFields(self):
        return field.Fields(IResource).select('title', 'description')


class LocationView(BaseResourceView):
    """A location info view."""

    resource_type = 'location'

    def getBaseFields(self):
        return field.Fields(ILocation)


class FlourishLocationView(FlourishBaseResourceView, LocationView):

    def getBaseFields(self):
        return field.Fields(ILocation).select('title', 'description')


class EquipmentView(BaseResourceView):
    """A equipment info view."""

    resource_type = 'equipment'

    def getBaseFields(self):
        return field.Fields(IEquipment)


class FlourishEquipmentView(FlourishBaseResourceView, EquipmentView):

    def getBaseFields(self):
        return field.Fields(IEquipment).select('title', 'description')


###############  Base classes of all resource add/edit views ################
# XXX: move this to a generic form base class
#      it's also duplicated in basicperson.browser.person.PersonForm
class ErrorMessageBase(object):

    formErrorsMessage = _('Please correct the marked fields below.')


class BaseResourceAddView(ErrorMessageBase, form.AddForm,
                          ResourceFieldGenerator):

    id = 'resource-form'
    template = ViewPageTemplateFile('templates/resource_form.pt')

    def getBaseFields(self):
        return field.Fields(IResource)

    def updateActions(self):
        super(BaseResourceAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'))
    def handleAdd(self, action):
        super(BaseResourceAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


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


class BaseResourceEditView(ErrorMessageBase, form.EditForm,
                           ResourceFieldGenerator):

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


class BaseFlourishResourceAddForm(flourish.form.AddForm):

    template = InheritTemplate(flourish.page.Page.template)
    label = None

    def createAndAdd(self, data):
        resource = self._factory()
        resource.title = data.get('title')
        chooser = INameChooser(self.context)
        resource.__name__ = chooser.chooseName('', resource)
        form.applyChanges(self, resource, data)
        notify(ObjectCreatedEvent(resource))
        self.context[resource.__name__] = resource
        self._resource = resource
        return resource

    def nextURL(self):
        return absoluteURL(getattr(self, '_resource', None) or self.context,
                           self.request)


###############  Resource add/edit views ################
class BaseResourceForm(object):

    resource_type = 'resource'
    base_id = 'base-data'
    base_legend = _('Resource identification')
    demo_id = 'demo-data'
    demo_legend = _('Resource attributes')

    def getBaseFields(self):
        return field.Fields(IResource).omit('type', 'notes')


class ResourceAddView(BaseResourceForm, BaseResourceAddView):

    label = _('Add new resource')
    _factory = Resource


class FlourishResourceAddView(BaseFlourishResourceAddForm, ResourceAddView):
    pass


class ResourceEditView(BaseResourceForm, BaseResourceEditView):

    label = _('Edit resource')


class FlourishResourceEditView(flourish.page.Page, ResourceEditView):

    label = None

    def update(self):
        ResourceEditView.update(self)


###############  Location add/edit views ################
class BaseLocationForm(object):

    resource_type = 'location'
    base_id = 'base-data'
    base_legend = _('Location identification')
    demo_id = 'demo-data'
    demo_legend = _('Location attributes')

    def getBaseFields(self):
        fields = field.Fields(ILocation).select('title', 'description')
        return fields


class LocationAddView(BaseLocationForm, BaseResourceAddView):

    label = _('Add new location')
    _factory = Location


class FlourishLocationAddView(BaseFlourishResourceAddForm, LocationAddView):
    pass


class LocationEditView(BaseLocationForm, BaseResourceEditView):

    label = _('Edit location')


class FlourishLocationEditView(flourish.page.Page, LocationEditView):

    label = None

    def update(self):
        LocationEditView.update(self)


###############  Equipment add/edit views ################
class BaseEquipmentForm(object):

    resource_type = 'equipment'
    base_id = 'base-data'
    base_legend = _('Equipment identification')
    demo_id = 'demo-data'
    demo_legend = _('Equipment attributes')

    def getBaseFields(self):
        fields = field.Fields(IEquipment).select('title', 'description')
        return fields


class EquipmentAddView(BaseEquipmentForm, BaseResourceAddView):

    label = _('Add new equipment')
    _factory = Equipment


class FlourishEquipmentAddView(BaseFlourishResourceAddForm, EquipmentAddView):
    pass


class EquipmentEditView(BaseEquipmentForm, BaseResourceEditView):

    label = _('Edit equipment')


class FlourishEquipmentEditView(flourish.page.Page, EquipmentEditView):

    label = None

    def update(self):
        EquipmentEditView.update(self)


class FlourishResourceContainerTableFormatter(table.table.SchoolToolTableFormatter):

    def makeFormatter(self):
        formatter = table.table.SchoolToolTableFormatter.makeFormatter(self)
        formatter.cssClasses['table'] = 'resources-table'
        return formatter


class ResourceLinks(flourish.page.RefineLinksViewlet):

    @property
    def title(self):
        return self.context.title


class ResourceActions(flourish.page.RefineLinksViewlet): pass


class FlourishBookResourceView(BrowserView):

    def __call__(self):
        sessionWrapper = ISession(self.request)
        session = sessionWrapper['schooltool.resource']
        session['bookingSelection'] = [self.context.__name__]
        url = absoluteURL(IBookingCalendar(self.context), self.request)
        self.request.response.redirect(url)


class FlourishResourceDeleteView(flourish.form.DialogForm, form.Form):

    dialog_submit_actions = ('delete',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.buttonAndHandler(_('Delete'))
    def handle_delete_action(self, action):
        parent = self.context.__parent__
        parent_url = absoluteURL(parent, self.request)
        context_name = self.context.__name__.encode('utf-8')
        url = '%s/delete.html?delete.%s&CONFIRM' % (parent_url, context_name)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishResourceDeleteView, self).updateActions()
        self.actions['delete'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishResourceDeleteLink(flourish.page.ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Delete ${resource_title}',
                  mapping={'resource_title': self.context.title})
        return translate(title, context=self.request)


class FlourishManageResourcesOverview(flourish.page.Content,
                                      ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_resources_overview.pt')

    @property
    def resources(self):
        return self.context['resources']

    @Lazy
    def resource_types(self):
        types = defaultdict(lambda:dict(amount=0, title=None, id=None))
        for resource in self.resources.values():
            info = IResourceTypeInformation(resource)
            if types[info.id]['title'] is None:
                types[info.id]['title'] = info.title
            if types[info.id]['id'] is None:
                types[info.id]['id'] = info.id
            types[info.id]['amount'] += 1
        return types

    def resources_url(self):
        return self.url_with_schoolyear_id(self.context,
                                           view_name='resources')


class FlourishRequestResourceReportView(RequestRemoteReportDialog):

    report_builder='resource_report.pdf'


class ResourceReportPDFView(flourish.report.PlainPDFPage):

    name = _("Resource Report")

    message_title = _("resource report")

    @property
    def title(self):
        preferences = IApplicationPreferences(ISchoolToolApplication(None))
        return preferences.title

    def makeFileName(self, basename):
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        return '%s_%s.pdf' % (basename, timestamp)

    @property
    def filename(self):
        return self.makeFileName('resource_report')

    def ptos(self):
        collator = ICollator(self.request.locale)
        ptos_dict = {}
        for resource in sorted(self.context.values(),
                               key=lambda x:collator.key(x.title)):
            if ILocation(resource, None) is not None:
                resource_type = _('Location')
            elif IEquipment(resource, None) is not None:
                resource_type = _('Equipment')
            else:
                resource_type = _('Resource')
            pto = ptos_dict.setdefault(resource_type, {
                'type': resource_type,
                'rows': [],
                })
            pto['rows'].append({
                'title': resource.title,
                'description': resource.description,
                })
        return [ptos_dict[k] for k in sorted(ptos_dict.keys(),
                                             key=lambda x:collator.key(x))]

