#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Contact relationship views.
"""
from zope.security.proxy import removeSecurityProxy
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.publisher.browser import BrowserView
from zope.catalog.interfaces import ICatalog
from zope.intid.interfaces import IIntIds
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.traversing.browser.absoluteurl import absoluteURL

from zc.table.column import GetterColumn

from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.app.browser.states import TemporalRelationshipAddTableMixin
from schooltool.app.browser.states import TemporalRelationshipRemoveTableMixin
from schooltool.app.browser.states import TemporalAddAllResultsButton
from schooltool.app.browser.states import TemporalRemoveAllResultsButton
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common.inlinept import InheritTemplate
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.contact.browser.contact import ContactTable
from schooltool.contact.browser.contact import contact_table_columns
from schooltool.contact.browser.contact import get_relationship_title
from schooltool.table.table import CheckboxColumn
from schooltool.table.table import label_cell_formatter_factory
from schooltool.table.interfaces import ITableFormatter
from schooltool.app.browser.states import EditTemporalRelationships
from schooltool.skin.flourish.page import Page

from schooltool.common import SchoolToolMessage as _


def make_relationship_column_getter(person=None):
    def format_item(item, formatter):
        if person is None:
            return u''
        item = removeSecurityProxy(item)
        return get_relationship_title(person, item)
    return format_item


def assigned_contacts_columns(person=None):
    default_columns = contact_table_columns()
    relationship = GetterColumn(
        name='relationship',
        title=_(u"Relationship"),
        getter=make_relationship_column_getter(person))
    return default_columns + [relationship]


class ContactManagementView(BrowserView):
    """View class for adding/removing contacts to/from a person."""

    __used_for__ = IBasicPerson

    __call__ = ViewPageTemplateFile('templates/manage_contacts.pt')
    current_title = _("Assigned Contacts")
    available_title = _("Assign existing contact")

    @property
    def title(self):
        return _("Manage contacts of ${person}",
            mapping={'person': self.context.title})

    def add(self, item):
        """Add an item to the list of selected items."""
        collection = removeSecurityProxy(self.getCollection())
        collection.add(item)

    def remove(self, item):
        """Remove an item from selected items."""
        collection = removeSecurityProxy(self.getCollection())
        collection.remove(item)

    def getCollection(self):
        return IContactable(removeSecurityProxy(self.context)).contacts

    def getSelectedItemIds(self):
        int_ids = getUtility(IIntIds)
        return [int_ids.getId(item) for item in self.getCollection()]

    def getItemContainer(self):
        return IContactContainer(ISchoolToolApplication(None))

    def getCatalog(self):
        return ICatalog(self.getItemContainer())

    def getAvailableItemIds(self):
        selected = self.getSelectedItemIds()
        catalog = self.getCatalog()
        return [intid for intid in catalog.extent
                if intid not in selected]

    def getOmmitedItemIds(self):
        int_ids = getUtility(IIntIds)
        self_contact = IContact(self.context)
        return self.getSelectedItemIds() + [int_ids.getId(self_contact)]

    def createTableFormatter(self, **kwargs):
        prefix = kwargs['prefix']
        container = self.getItemContainer()
        formatter = getMultiAdapter((container, self.request),
                                    ITableFormatter)
        columns_before = [CheckboxColumn(
            prefix=prefix, title="", id_getter=IUniqueFormKey)]
        formatters = [label_cell_formatter_factory(prefix, IUniqueFormKey)]
        formatter.setUp(formatters=formatters,
                        columns_before=columns_before,
                        **kwargs)
        return formatter

    def setUpTables(self):
        int_ids = getUtility(IIntIds)
        self.available_table = self.createTableFormatter(
            ommit=[int_ids.getObject(intid)
                   for intid in self.getOmmitedItemIds()],
            prefix="add_item")

        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=[int_ids.getObject(intid)
                   for intid in self.getSelectedItemIds()],
            columns=assigned_contacts_columns(self.context),
            prefix="remove_item",
            batch_size=0)

    def update(self):
        context_url = absoluteURL(self.context, self.request)
        catalog = self.getCatalog()
        int_ids = getUtility(IIntIds)
        index = catalog['form_keys']
        if 'ADD_ITEMS' in self.request:
            for intid in self.getAvailableItemIds():
                key = 'add_item.%s' % index.documents_to_values[intid]
                if key in self.request:
                    self.add(IContact(int_ids.getObject(intid)))
        elif 'REMOVE_ITEMS' in self.request:
            for intid in self.getSelectedItemIds():
                key = 'remove_item.%s' % index.documents_to_values[intid]
                if key in self.request:
                    self.remove(int_ids.getObject(intid))
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)

        self.setUpTables()


class EditContactRelationships(EditTemporalRelationships):

    app_states_name = 'contact-relationship'

    def getOmmitedItems(self):
        for item in EditTemporalRelationships.getOmmitedItems(self):
            yield item
        self_contact = IContact(self.context)
        yield self_contact

    def getTargets(self, keys):
        if not keys:
            return None
        catalog = self.getCatalog()
        ids = []
        for key in keys:
            for iid in catalog['form_keys'].values_to_documents.get(key, ()):
                if iid not in ids:
                    ids.append(iid)
        int_ids = getUtility(IIntIds)
        targets = [
            int_ids.getObject(iid)
            for iid in ids
            ]
        return targets


class ContactAddRelationshipTable(TemporalRelationshipAddTableMixin, ContactTable):

    def submitItems(self):
        int_ids = getUtility(IIntIds)
        catalog = self.view.getCatalog()
        index = catalog['form_keys']
        for intid in self.view.getAvailableItemIds():
            key = '%s.%s' % (self.button_prefix, index.documents_to_values[intid])
            if key in self.request:
                self.view.add(IContact(int_ids.getObject(intid)))


class ContactRemoveRelationshipTable(TemporalRelationshipRemoveTableMixin, ContactTable):

    def submitItems(self):
        int_ids = getUtility(IIntIds)
        catalog = self.view.getCatalog()
        index = catalog['form_keys']
        for intid in self.view.getSelectedItemIds():
            key = '%s.%s' % (self.button_prefix, index.documents_to_values[intid])
            if key in self.request:
                self.view.remove(IContact(int_ids.getObject(intid)))


class AddAllContactResultsButton(TemporalAddAllResultsButton):

    def processSearchResults(self):
        if (self.button_name not in self.request or
            self.token_key not in self.request):
            return False
        add_ids = self.request[self.token_key]
        if not isinstance(add_ids, list):
            add_ids = [add_ids]
        changed = False
        relationship_view = self.manager.view
        int_ids = getUtility(IIntIds)
        for item_id in relationship_view.getAvailableItemIds():
            item = int_ids.getObject(item_id)
            if relationship_view.getKey(item) in add_ids:
                self.process_item(relationship_view, item)
                changed = True
        return changed


class RemoveAllContactResultsButton(TemporalRemoveAllResultsButton):

    def processSearchResults(self):
        if (self.button_name not in self.request or
            self.token_key not in self.request):
            return False
        add_ids = self.request[self.token_key]
        if not isinstance(add_ids, list):
            add_ids = [add_ids]
        changed = False
        relationship_view = self.manager.view
        int_ids = getUtility(IIntIds)
        for item_id in relationship_view.getSelectedItemIds():
            item = int_ids.getObject(item_id)
            if relationship_view.getKey(item) in add_ids:
                self.process_item(relationship_view, item)
                changed = True
        return changed


class FlourishContactManagementView(EditContactRelationships):

    page_template = InheritTemplate(Page.page_template)

    current_title = _('Current contacts')
    available_title = _('Available contacts')

    def getCollection(self):
        return IContactable(removeSecurityProxy(self.context)).contacts

    def getSelectedItemIds(self):
        collection = self.getCollection()
        return list(collection.all().int_ids)

    def getAvailableItemsContainer(self):
        return IContactContainer(ISchoolToolApplication(None))

    def getCatalog(self):
        return ICatalog(self.getAvailableItemsContainer())

    def getAvailableItemIds(self):
        selected = self.getSelectedItemIds()
        catalog = self.getCatalog()
        return [intid for intid in catalog.extent
                if intid not in selected]

    def getOmmitedItemIds(self):
        int_ids = getUtility(IIntIds)
        self_contact = IContact(self.context)
        return self.getSelectedItemIds() + [int_ids.getId(self_contact)]

    def getKey(self, item):
        return IUniqueFormKey(item)
