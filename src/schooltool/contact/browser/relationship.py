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
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.component import getMultiAdapter
from zc.table.column import GetterColumn

from schooltool.common import SchoolToolMessage as _
from schooltool.relationship.relationship import IRelationshipLinks
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.app.interfaces import ISchoolToolApplication

from schooltool.contact.interfaces import IContactPersonInfo
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.contact import URIPerson, URIContact
from schooltool.contact.contact import URIContactRelationship
from schooltool.contact.contact import ContactPersonInfo
from schooltool.contact.browser.contact import contact_table_collumns
from schooltool.app.browser.app import RelationshipViewBase


def make_relationship_collumn_getter(person=None):
    def format_item(item, formatter):
        if person is None:
            return u''
        item = removeSecurityProxy(item)
        try:
            links = IRelationshipLinks(person)
            link = links.find(
                URIPerson, item, URIContact, URIContactRelationship)
        except ValueError:
            return u''
        return link.extra_info.getRelationshipTitle()
    return format_item


def assigned_contacts_columns(person=None):
    first_name, last_name, address = contact_table_collumns()
    relationship = GetterColumn(
        name='relationship',
        title=_(u"Relationship"),
        getter=make_relationship_collumn_getter(person))
    return [first_name, last_name, relationship, address]


class ContactManagementView(RelationshipViewBase):
    """View class for adding/removing contacts to/from a person."""

    __used_for__ = IBasicPerson

    __call__ = ViewPageTemplateFile('templates/manage_contacts.pt')
    current_title = _("Assigned Contacts")
    available_title = _("Assign existing contact")

    @property
    def title(self):
        return _("Manage contacts of ${person}",
            mapping={'person': self.context.title})

    def getSelectedItems(self):
        return IContactable(self.context).contacts

    def getAvailableItemsContainer(self):
        return IContactContainer(ISchoolToolApplication(None))

    def getCollection(self):
        return IContactable(removeSecurityProxy(self.context)).contacts

    def add(self, item):
        """Add an item to the list of selected items."""
        collection = removeSecurityProxy(self.getCollection())
        info = ContactPersonInfo()
        info.__parent__ = removeSecurityProxy(self.context)
        collection.add(item, info)

    def setUpTables(self):
        self.available_table = self.createTableFormatter(
            ommit=self.getOmmitedItems(),
            prefix="add_item")

        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=self.getSelectedItems(),
            columns=assigned_contacts_columns(self.context),
            prefix="remove_item",
            batch_size=0)

