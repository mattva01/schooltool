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
Contact browser views.
"""
from zope.interface import directlyProvides
from zope.interface import implements
from zope.component import getMultiAdapter
from zope.component import adapts
from zope.component import getUtility
from zope.schema import getFieldNamesInOrder
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.app.container.interfaces import INameChooser
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.catalog.interfaces import ICatalog
from zope.app.intid.interfaces import IIntIds
from zope.app.catalog.interfaces import ICatalog

from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn
from z3c.form import form, subform, field, button

from schooltool.table.interfaces import ITableFormatter
from schooltool.table.table import url_cell_formatter
from schooltool.table.table import DependableCheckboxColumn
from schooltool.table.catalog import FilterWidget
from schooltool.table.catalog import IndexedTableFormatter
from schooltool.table.catalog import IndexedLocaleAwareGetterColumn
from schooltool.skin.containers import TableContainerView
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.interfaces import IContactPersonInfo
from schooltool.contact.interfaces import IAddress
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.contact.contact import ContactPersonInfo
from schooltool.contact.interfaces import IContact
from schooltool.contact.contact import Contact

from schooltool.common import SchoolToolMessage as _


class ContactContainerAbsoluteURLAdapter(BrowserView):

    adapts(IContactContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/contacts'

    __call__ = __str__


class ContactAddView(form.AddForm):
    """Contact add form for basic contact."""

    label = _("Add new contact")
    template = ViewPageTemplateFile('templates/contact_add.pt')
    fields = field.Fields(IContact)

    def __init__(self, *args, **kw):
        super(ContactAddView, self).__init__(*args, **kw)
        self.subforms = []

    def updateActions(self):
        super(ContactAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        obj = self.createAndAdd(data)
        if obj is not None:
            # mark only as finished if we get the new object
            self._finishedAdd = True

    def create(self, data):
        contact = Contact()
        form.applyChanges(self, contact, data)
        return contact

    def nextURL(self):
        return absoluteURL(self.context, self.request)

    def add(self, contact):
        """Add `contact` to the container.

        Uses the username of `contact` as the object ID (__name__).
        """
        name = INameChooser(self.context).chooseName('', contact)
        self.context[name] = contact
        return contact

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class ContactPersonInfoSubForm(subform.EditSubForm):
    """Form for editing additional person's contact information."""

    template = ViewPageTemplateFile('templates/contactperson_subform.pt')
    fields = field.Fields(IContactPersonInfo)
    prefix = 'person_contact'

    changed = False

    @property
    def person(self):
        return self.context.__parent__

    @button.handler(form.EditForm.buttons['apply'])
    def handleApply(self, action):
        data, errors = self.widgets.extract()
        if errors:
            # XXX: we don't handle errors for now
            pass
        content = self.getContent()
        changed = form.applyChanges(self, content, data)
        self.changed = bool(changed)

    @button.handler(ContactAddView.buttons['add'])
    def handleAdd(self, action):
        # Pretty, isn't it?
        self.handleApply.func(self, action)


class PersonContactAddView(ContactAddView):
    """Contact add form that assigns the contact to a person."""

    form.extends(ContactAddView)

    @property
    def label(self):
        return _("Add new contact for ${person}",
                 mapping={'person': self.context.title})

    def update(self):
        # Create contact_info object for adding
        self.contact_info = ContactPersonInfo()
        # Add person contact.
        super(PersonContactAddView, self).update()
        # Update contact info.
        self.subforms = [
            ContactPersonInfoSubForm(self.contact_info, self.request, self),
            ]
        for subform in self.subforms:
            subform.update()

    def add(self, contact):
        """Add `contact` to the container and assign it to the person."""
        contact_container = IContactContainer(ISchoolToolApplication(None))
        name = INameChooser(contact_container).chooseName('', contact)
        contact_container[name] = contact

        context = removeSecurityProxy(self.context)
        self.contact_info.__parent__ = context
        IContactable(context).contacts.add(contact, self.contact_info)
        return contact


class ContactEditView(form.EditForm):
    """Edit form for basic contact."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/contact_add.pt')
    fields = field.Fields(IContact)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def update(self):
        super(ContactEditView, self).update()
        self.subforms = []
        for relationship_info in self.context.persons.relationships:
            subform = ContactPersonInfoSubForm(
                relationship_info.extra_info, self.request, self)
            # XXX: should also apply at least urllib.quote here:
            prefix = unicode(relationship_info.target.__name__).encode('punycode')
            subform.prefix += '.%s' % prefix
            subform.update()
            # One more hack.
            if subform.changed and self.status == self.noChangesMessage:
                self.status = self.successMessage
            self.subforms.append(subform)

    def updateActions(self):
        super(ContactEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def label(self):
        return _(u'Change contact information for ${first_name} ${last_name}',
                 mapping={'first_name': self.context.first_name,
                          'last_name': self.context.last_name})


class ContactView(form.DisplayForm):
    """Display form for basic contact."""
    template = ViewPageTemplateFile('templates/contact_view.pt')
    fields = field.Fields(IContact)

    def relationships(self):
        return [relationship_info.extra_info
                for relationship_info in self.context.persons.relationships]

    def __call__(self):
        self.update()
        return self.render()


class ContactContainerView(TableContainerView):
    """A Contact Container view."""

    __used_for__ = IContactContainer

    delete_template = ViewPageTemplateFile('templates/contacts_delete.pt')
    index_title = _("Contact index")

    @property
    def itemsToDelete(self):
        return sorted(
            TableContainerView._listItemsForDeletion(self),
            key=lambda obj: '%s %s' % (obj.last_name, obj.first_name))

    def setUpTableFormatter(self, formatter):
        columns_before = []
        if self.canModify():
            columns_before = [
                DependableCheckboxColumn(
                    prefix="delete",
                    name='delete_checkbox',
                    title=u'',
                    id_getter=IUniqueFormKey,
                    show_disabled=False)]
        formatter.setUp(columns_before=columns_before)

    def listIdsForDeletion(self):
        int_ids = getUtility(IIntIds)
        return [int_ids.getObject(intid).__name__
                for intid in self.listIntIdsForDeletion()]

    def listFormKeysForDeletion(self):
        catalog = ICatalog(self.context)
        index = catalog['form_keys']
        return ['delete.%s' % index.documents_to_values[intid]
                for intid in self.listIntIdsForDeletion()]

    def listIntIdsForDeletion(self):
        catalog = ICatalog(self.context)
        index = catalog['form_keys']
        return [intid for intid in catalog.extent
                if 'delete.%s' % index.documents_to_values[intid] in self.request]


def format_street_address(item, formatter):
    address_parts = []
    for attribute in getFieldNamesInOrder(IAddress):
        address_part = getattr(item, attribute, None)
        if address_part is not None:
            address_parts.append(address_part)
    return ", ".join(address_parts)


def contact_table_collumns():
        first_name = IndexedLocaleAwareGetterColumn(
            index='first_name',
            name='first_name',
            cell_formatter=url_cell_formatter,
            title=_(u'First Name'),
            getter=lambda i, f: i.first_name,
            subsort=True)
        last_name = IndexedLocaleAwareGetterColumn(
            index='last_name',
            name='last_name',
            cell_formatter=url_cell_formatter,
            title=_(u'Last Name'),
            getter=lambda i, f: i.last_name,
            subsort=True)
        address = GetterColumn(name='address',
                               title=_(u"Address"),
                               getter=format_street_address)
        return [first_name, last_name, address]


class ContactTableFormatter(IndexedTableFormatter):

    columns = lambda self: contact_table_collumns()

    def sortOn(self):
        return (("first_name", False),)


class ContactFilterWidget(FilterWidget):

    template = ViewPageTemplateFile('templates/filter.pt')
    parameters = ['SEARCH_FIRST_NAME', 'SEARCH_LAST_NAME']

    def filter(self, items):
        if 'CLEAR_SEARCH' in self.request:
            for parameter in self.parameters:
                self.request.form[parameter] = ''
            return items

        catalog = ICatalog(self.context)

        if 'SEARCH_FIRST_NAME' in self.request:
            # XXX: applying normalized catalog queries would be nicer
            fn_idx = catalog['first_name']
            searchstr = self.request['SEARCH_FIRST_NAME'].lower()
            items = [item for item in items
                     if searchstr in fn_idx.documents_to_values[item['id']].lower()]

        if 'SEARCH_LAST_NAME' in self.request:
            # XXX: applying normalized catalog queries would be nicer
            ln_idx = catalog['last_name']
            searchstr = self.request['SEARCH_LAST_NAME'].lower()
            items = [item for item in items
                     if searchstr in ln_idx.documents_to_values[item['id']].lower()]

        return items

    def active(self):
        for parameter in self.parameters:
            if parameter in self.request:
                return True
        return False

    def extra_url(self):
        url = ""
        for parameter in self.parameters:
            if parameter in self.request:
                url += '&%s=%s' % (parameter, self.request.get(parameter))
        return url


class ContactBackToContainerViewlet(object):
    @property
    def link(self):
        container = IContactContainer(ISchoolToolApplication(None))
        return absoluteURL(container, self.request)

