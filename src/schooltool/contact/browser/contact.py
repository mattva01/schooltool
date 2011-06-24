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
import urllib
from zope.security.checker import canAccess
from zope.schema import getFieldsInOrder
from zope.interface import implements, Interface
from zope.component import getMultiAdapter
from zope.component import adapts
from zope.component import getUtility
from zope.schema import getFieldNamesInOrder, TextLine, Text
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.container.interfaces import INameChooser
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.catalog.interfaces import ICatalog
from zope.intid.interfaces import IIntIds

from zc.table.column import GetterColumn
from z3c.form import form, subform, field, button

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
from schooltool.person.interfaces import IPerson
from schooltool.email.interfaces import IEmailUtility
from schooltool.email.mail import Email
from schooltool.skin.flourish.viewlet import Viewlet
from schooltool.skin.flourish.page import RefineLinksViewlet, ExpandedPage
from schooltool.relationship.relationship import IRelationshipLinks
from schooltool.contact.contact import URIPerson, URIContact
from schooltool.contact.contact import URIContactRelationship
from schooltool.contact.interfaces import IContactPerson
from schooltool.contact.interfaces import IEmails, IPhones, ILanguages

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
        self.request.response.redirect(self.nextURL())


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


class FlourishPersonContactAddView(ExpandedPage, PersonContactAddView):

    def update(self):
        self.buildFieldsetGroups()
        PersonContactAddView.update(self)

    def render(self):
        if self._finishedAdd:
            self.request.response.redirect(self.nextURL())
            return ""
        return super(FlourishPersonContactAddView, self).render()

    def nextURL(self):
        base_url = absoluteURL(self.context, self.request)
        return "%s/@@manage_contacts.html?%s" % (
            base_url,
            urllib.urlencode([('SEARCH_TITLE',
                               self.context.last_name.encode("utf-8"))]))

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

    def buildFieldsetGroups(self):
        self.fieldset_groups = {
            'full_name': (
                _('Full Name'),
                ['prefix', 'first_name', 'middle_name', 'last_name',
                 'suffix']),
            'address': (
                _('Address'),
                ['address_line_1', 'address_line_2', 'city', 'state',
                 'country', 'postal_code']),
            'contact_information': (
                _('Contact Information'),
                ['home_phone', 'work_phone', 'mobile_phone', 'email',
                 'language']),
            }
        self.fieldset_order = (
            'full_name', 'address', 'contact_information')

    def fieldsets(self):
        result = []
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result


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


class FlourishContactFilterWidget(ContactFilterWidget):

    template = ViewPageTemplateFile('templates/f_contact_filter.pt')

    parameters = ['SEARCH_TITLE']

    def match(self, item, idx, search_terms):
        matches = []
        for term in search_terms:
            if term in idx.documents_to_values[item['id']].lower():
               matches.append(term)
        return len(matches) == len(search_terms)

    def filter(self, items):
        if 'SEARCH_TITLE' in self.request:
            catalog = ICatalog(self.context)
            title_idx = catalog['title']
            # XXX: applying normalized catalog queries would be nicer
            search_terms = self.request['SEARCH_TITLE'].lower().split(' ')
            items = [item for item in items if self.match(item,
                                                          title_idx,
                                                          search_terms)]
        return items


class ContactBackToContainerViewlet(object):
    @property
    def link(self):
        container = IContactContainer(ISchoolToolApplication(None))
        return absoluteURL(container, self.request)


class SendEmailActionViewlet(object):
    @property
    def link(self):
        utility = getUtility(IEmailUtility)
        if utility.enabled() and self.context.email:
            return absoluteURL(self.context, self.request) + '/sendEmail.html'
        return ''


class ISendEmailForm(Interface):

    from_address = TextLine(title=_(u'From'), required=False)
    to_addresses = TextLine(title=_(u'To'), required=False)
    subject = TextLine(title=_(u'Subject'))
    body = Text(title=_(u'Body'))


class SendEmailFormAdapter(object):

    implements(ISendEmailForm)
    adapts(IContact)

    def __init__(self, context):
        self.context = context


class SendEmailView(form.Form):

    template = ViewPageTemplateFile('templates/email_form.pt')
    label = _('Send Email')
    fields = field.Fields(ISendEmailForm)

    @button.buttonAndHandler(_('Send'))
    def handle_send_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = _('There were some errors.')
            return
        body = data['body']
        subject = data['subject']
        email = Email(self.from_address, self.to_addresses, body, subject)
        utility = getUtility(IEmailUtility)
        success = utility.send(email)
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SendEmailView, self).updateActions()
        self.actions['cancel'].addClass('button-cancel')
        utility = getUtility(IEmailUtility)
        if utility.enabled() and self.context.email:
            self.actions['send'].addClass('button-ok')
        else:
            self.actions['send'].mode = 'display'

    def update(self):
        user = IPerson(self.request.principal)
        super(SendEmailView, self).update()
        if not IContact(user).email:
            url = absoluteURL(self.context, self.request) + \
                  '/noTeacherEmail.html'
            self.request.response.redirect(url)
            return
        self.updateDisplayWidgets()

    def updateDisplayWidgets(self):
        self.widgets['from_address'].mode = 'display'
        self.widgets['to_addresses'].mode = 'display'
        self.widgets['from_address'].value = "%s <%s>" % (self.sender,
                                                          self.from_address)
        self.widgets['to_addresses'].value = "%s <%s>" % (self.recipient,
                                                          ''.join(self.to_addresses))

    @property
    def from_address(self):
        user = IPerson(self.request.principal, None)
        if user is None:
            return u''
        return IContact(user).email

    @property
    def to_addresses(self):
        return [self.context.email]

    @property
    def sender(self):
        user = IPerson(self.request.principal, None)
        if user is None:
            return u''
        return "%s %s" % (user.first_name, user.last_name)

    @property
    def recipient(self):
        first_name = self.context.first_name or ''
        last_name = self.context.last_name or ''
        return "%s %s" % (first_name, last_name)


class NoTeacherEmailView(BrowserView):

    __call__ = ViewPageTemplateFile('templates/noteacheremail.pt')


class BoundContactPersonActionViewlet(object):

    @property
    def person(self):
        return IPerson(self.context)


class FlourishContactsViewlet(Viewlet):
    """A viewlet showing contacts of a person"""

    template = ViewPageTemplateFile('templates/f_contactsViewlet.pt')
    body_template = None

    @property
    def getContacts(self):
        contacts = IContactable(removeSecurityProxy(self.context)).contacts
        return [self.buildInfo(contact) for contact in contacts]

    # XXX: copied from relationship.py to avoid circular dependency
    def get_relationship_title(self, contact):
        try:
            links = IRelationshipLinks(self.context)
            link = links.find(
                URIPerson, contact, URIContact, URIContactRelationship)
        except ValueError:
            return u''
        return link.extra_info.getRelationshipTitle()

    def buildInfo(self, contact):
        return {
            'link': absoluteURL(contact, self.request),
            'relationship': self.get_relationship_title(contact),
            'name': " ".join(self._extract_attrs(
                contact, IContactPerson)),
            'address': ", ".join(self._extract_attrs(contact, IAddress)),
            'emails': ", ".join(self._extract_attrs(contact, IEmails)),
            'phones': list(self._extract_attrs(contact, IPhones, add_title=True)),
            'languages': ", ".join(self._extract_attrs(contact, ILanguages)),
            'obj': contact,
            }

    def _extract_attrs(self, contact, interface,
                       conjunctive=", ", add_title=False):
        parts = []
        for name, field in getFieldsInOrder(interface):
            part = getattr(contact, name, None)
            part = part and part.strip() or part
            if not part:
                continue
            if add_title:
                parts.append("%s (%s)" % (part, field.title))
            else:
                parts.append(part)
        return parts

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')

    def makeRows(self, contact):
        rows = []
        fields = field.Fields(IAddress, IEmails, IPhones, ILanguages)
        for attr in fields:
            label = fields[attr].field.title
            rows.append(self.makeRow(label, getattr(contact, attr)))
        return rows

    def makeRow(self, attr, value):
        if value is None:
            value = u''
        return {
            'label': attr,
            'value': unicode(value),
            }

    @property
    def manage_link(self):
        base_url = absoluteURL(self.context, self.request)
        return "%s/@@manage_contacts.html?%s" % (
            base_url,
            urllib.urlencode([('SEARCH_TITLE',
                               self.context.last_name.encode("utf-8"))]))


class PersonManageContactsLinks(RefineLinksViewlet):
    """Links for manage contact page"""
