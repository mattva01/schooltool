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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
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

from schooltool.relationship.relationship import IRelationshipLinks
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common.inlinept import InheritTemplate
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.contact.contact import URIPerson, URIContact
from schooltool.contact.contact import URIContactRelationship
from schooltool.contact.contact import ContactPersonInfo
from schooltool.contact.browser.contact import contact_table_columns
from schooltool.table.table import CheckboxColumn
from schooltool.table.table import label_cell_formatter_factory
from schooltool.table.interfaces import ITableFormatter
from schooltool.app.browser.app import FlourishRelationshipViewBase
from schooltool.skin.flourish.page import Page

from schooltool.common import SchoolToolMessage as _


def get_relationship_title(person, contact):
    try:
        links = IRelationshipLinks(person)
        link = links.find(
            URIPerson, contact, URIContact, URIContactRelationship)
    except ValueError:
        return u''
    return link.extra_info.getRelationshipTitle()


def make_relationship_column_getter(person=None):
    def format_item(item, formatter):
        if person is None:
            return u''
        item = removeSecurityProxy(item)
        return get_relationship_title(person, item)
    return format_item


def assigned_contacts_columns(person=None):
    first_name, last_name = contact_table_columns()
    relationship = GetterColumn(
        name='relationship',
        title=_(u"Relationship"),
        getter=make_relationship_column_getter(person))
    return [first_name, last_name, relationship]


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
        info = ContactPersonInfo()
        info.__parent__ = removeSecurityProxy(self.context)
        collection.add(item, info)

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


class FlourishContactManagementView(FlourishRelationshipViewBase):

    page_template = InheritTemplate(Page.page_template)

    current_title = _('Current contacts')
    available_title = _('Available contacts')

    def add(self, item):
        """Add an item to the list of selected items."""
        collection = removeSecurityProxy(self.getCollection())
        info = ContactPersonInfo()
        info.__parent__ = removeSecurityProxy(self.context)
        collection.add(item, info)

    def remove(self, item):
        """Remove an item from selected items."""
        collection = removeSecurityProxy(self.getCollection())
        collection.remove(item)

    def getCollection(self):
        return IContactable(removeSecurityProxy(self.context)).contacts

    def getSelectedItemIds(self):
        int_ids = getUtility(IIntIds)
        return [int_ids.getId(item) for item in self.getCollection()]

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

    def getKey(self, item):
        return IUniqueFormKey(item)

    def applyFormChanges(self):
        changed = False
        add_item_prefix = 'add_item.'
        remove_item_prefix = 'remove_item.'
        add_item_submitted = False
        remove_item_submitted = False
        catalog = self.getCatalog()
        int_ids = getUtility(IIntIds)
        index = catalog['form_keys']
        for param in self.request.form:
            if param.startswith(add_item_prefix):
                add_item_submitted = True
            elif param.startswith(remove_item_prefix):
                remove_item_submitted = True
        if add_item_submitted:
            for intid in self.getAvailableItemIds():
                key = add_item_prefix + index.documents_to_values[intid]
                if key in self.request:
                    self.add(IContact(int_ids.getObject(intid)))
                    changed = True
        if remove_item_submitted:
            for intid in self.getSelectedItemIds():
                key = remove_item_prefix + index.documents_to_values[intid]
                if key in self.request:
                    self.remove(int_ids.getObject(intid))
                    changed = True
        return changed
