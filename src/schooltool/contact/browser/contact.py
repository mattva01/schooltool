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
Contact browser views.
"""
import urllib

import zope.schema
from zope.security.checker import canAccess
from zope.schema import getFieldsInOrder
from zope.interface import implements, Interface
from zope.catalog.interfaces import ICatalog
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
from zope.intid.interfaces import IIntIds
from zope.i18n import translate

from z3c.form import form, subform, field, button
from z3c.form.interfaces import DISPLAY_MODE

from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.catalog import buildQueryString
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.interfaces import IAddress, IPhoto
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.contact.interfaces import IContact
from schooltool.contact.contact import Contact
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonFactory
from schooltool.email.interfaces import IEmailUtility
from schooltool.email.mail import Email
from schooltool.skin import flourish
from schooltool.skin.containers import TableContainerView
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.contact.contact import getAppContactStates
from schooltool.contact.interfaces import IContactPerson
from schooltool.contact.interfaces import IEmails, IPhones, ILanguages
from schooltool import table

from schooltool.common import SchoolToolMessage as _


def get_relationship_title(person, contact):
    state = IContactable(person).contacts.state(contact)
    if state is None:
        return u''
    app_states = getAppContactStates()
    title = app_states.getTitle(state.today)
    return title or u''


class ContactContainerAbsoluteURLAdapter(BrowserView):

    adapts(IContactContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/contacts'

    __call__ = __str__


class FlourishContactContainerView(flourish.page.Page):
    """A flourish Contact Container view."""

    content_template = InlineViewPageTemplate('''
      <div tal:content="structure context/schooltool:content/ajax/table" />
    ''')

    @property
    def done_link(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/manage'


class ContactAddView(form.AddForm):
    """Contact add form for basic contact."""

    label = _("Add new contact")
    template = ViewPageTemplateFile('templates/contact_add.pt')
    fields = field.Fields(IContact)
    formErrorsMessage = _('Please correct the marked fields below.')

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


class FlourishContactAddView(flourish.page.Page, ContactAddView):
    label = None

    def update(self):
        self.buildFieldsetGroups()
        ContactAddView.update(self)

    def render(self):
        if self._finishedAdd:
            self.request.response.redirect(self.nextURL())
            return ""
        return super(FlourishContactAddView, self).render()

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
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result

    def buildFieldsetGroups(self):
        self.fieldset_groups = {
            'full_name': (
                _('Full Name'),
                ['prefix', 'first_name', 'middle_name', 'last_name',
                 'suffix']),
            'details': (
                _('Details'), ['photo']),
            'address': (
                _('Address'),
                ['address_line_1', 'address_line_2', 'city', 'state',
                 'country', 'postal_code']),
            'contact_information': (
                _('Contact Information'),
                ['home_phone', 'work_phone', 'mobile_phone', 'email',
                 'other_1', 'other_2',
                 'language']),
            }
        self.fieldset_order = (
            'full_name', 'details', 'address', 'contact_information')


SubmitLabel = button.StaticButtonActionAttribute(
    _('Submit'),
    button=FlourishContactAddView.buttons['add'])


class IContactPersonSubForm(Interface):
    """Information about a contact - person relationship."""

    relationship = zope.schema.Choice(
        title=_(u"Relationship"),
        description=_("Contact's relationship with the person"),
        vocabulary='schooltool.contact.contact.relationship_states',
        required=False)


class ContactPersonInfoSubForm(subform.EditSubForm):
    """Form for editing additional person's contact information."""

    template = ViewPageTemplateFile('templates/contactperson_subform.pt')
    fields = field.Fields(IContactPersonSubForm)
    prefix = 'person_contact'

    view = None

    changed = False
    data = None
    relationship = None

    def __init__(self, context, request, view, relationship_info):
        subform.EditSubForm.__init__(self, context, request, view)
        self.view = view
        self.relationship = relationship_info
        self.data = {}

    @property
    def person(self):
        if self.relationship is None:
            return self.context
        return self.relationship.target

    def getContent(self):
        return self.data

    def updateData(self):
        if self.relationship is not None:
            app_states = getAppContactStates()
            state_tuple = self.relationship.state.today
            self.data['relationship'] = app_states.getState(state_tuple)

    def update(self):
        self.updateData()
        return subform.EditSubForm.update(self)

    @button.handler(form.EditForm.buttons['apply'])
    def handleApply(self, action):
        data, errors = self.widgets.extract()
        if errors:
            # XXX: we don't handle errors for now
            return
        content = self.getContent()
        changed = form.applyChanges(self, content, data)
        self.changed = bool(changed)
        if self.changed and self.relationship is not None:
            self.relationship.state.set(
                self.request.util.today,
                meaning=self.data['relationship'].active,
                code=self.data['relationship'].code)

    @button.handler(ContactAddView.buttons['add'])
    def handleAdd(self, action):
        self.handleApply.func(self, action)
        if (self.view.added is None or
            self.data['relationship'] is None):
            # XXX: we don't handle errors for now
            return
        contacts = IContactable(removeSecurityProxy(self.context)).contacts
        contacts.on(self.request.util.today).relate(
            self.view.added,
            meaning=self.data['relationship'].active,
            code=self.data['relationship'].code,
            )


class PersonContactAddView(ContactAddView):
    """Contact add form that assigns the contact to a person."""

    form.extends(ContactAddView)

    added = None

    @property
    def label(self):
        return _("Add new contact for ${person}",
                 mapping={'person': self.context.title})

    def update(self):
        super(PersonContactAddView, self).update()
        self.subforms = [
            ContactPersonInfoSubForm(self.context, self.request, self, None),
            ]
        for subform in self.subforms:
            subform.update()

    def add(self, contact):
        """Add `contact` to the container and assign it to the person."""
        contact_container = IContactContainer(ISchoolToolApplication(None))
        name = INameChooser(contact_container).chooseName('', contact)
        contact_container[name] = contact
        self.added = contact
        return contact


class FlourishPersonContactAddView(FlourishContactAddView,
                                   PersonContactAddView):

    label = None

    add = PersonContactAddView.add

    def update(self):
        self.buildFieldsetGroups()
        PersonContactAddView.update(self)

    def nextURL(self):
        base_url = absoluteURL(self.context, self.request)
        return "%s/@@manage_contacts.html?%s" % (
            base_url,
            urllib.urlencode([('SEARCH_TITLE',
                               self.context.last_name.encode("utf-8"))]))


class ContactEditView(form.EditForm):
    """Edit form for basic contact."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/contact_add.pt')
    fields = field.Fields(IContact)

    formErrorsMessage = _('Please correct the marked fields below.')

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def update(self):
        super(ContactEditView, self).update()
        self.subforms = []
        for relationship_info in self.context.persons.all().relationships:
            subform = ContactPersonInfoSubForm(
                self.context, self.request, self, relationship_info)
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
        return _(u'Change contact information for ${person}',
                 mapping={'person': self.context.title})


class FlourishContactEditView(flourish.page.Page,
                              ContactEditView):

    form.extends(ContactEditView)

    label = None

    def update(self):
        self.buildFieldsetGroups()
        ContactEditView.update(self)

    @button.handler(ContactEditView.buttons['apply'])
    def handle_apply(self, action):
        # Pretty, isn't it?
        self.handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    def nextURL(self):
        if 'person_id' in self.request:
            person_id = self.request['person_id']
            app = ISchoolToolApplication(None)
            persons = app['persons']
            if person_id in persons:
                return absoluteURL(persons[person_id], self.request)
        return absoluteURL(self.context, self.request)

    @button.handler(ContactEditView.buttons['cancel'])
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

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
            'details': (
                _('Details'), ['photo']),
            'address': (
                _('Address'),
                ['address_line_1', 'address_line_2', 'city', 'state',
                 'country', 'postal_code']),
            'contact_information': (
                _('Contact Information'),
                ['home_phone', 'work_phone', 'mobile_phone', 'email',
                 'other_1', 'other_2',
                 'language']),
            }
        self.fieldset_order = (
            'full_name', 'details', 'address', 'contact_information')

    def fieldsets(self):
        result = []
        for fieldset_id in self.fieldset_order:
            legend, fields = self.fieldset_groups[fieldset_id]
            result.append(self.makeFieldSet(
                    fieldset_id, legend, list(fields)))
        return result


class ContactView(form.DisplayForm):
    """Display form for basic contact."""
    template = ViewPageTemplateFile('templates/contact_view.pt')
    fields = field.Fields(IContact)

    @property
    def app_states(self):
        return getAppContactStates()

    def relationships(self):
        app_states = self.app_states
        for info in self.context.persons.relationships:
            title = app_states.getTitle(info.state.today) or u''
            yield {
                'person': info.target,
                'title': title,
                }

    def __call__(self):
        self.update()
        return self.render()


class FlourishContactView(flourish.page.Page):

    pass


class FlourishBoundContactDetails(flourish.form.FormContent):

    fields = field.Fields(IContact).omit(*(
        list(IPhoto) +
        list(IContactPerson)
        ))
    mode = DISPLAY_MODE

    @property
    def has_data(self):
        return any([widget.value for widget in self.widgets.values()])

    @property
    def app_states(self):
        return getAppContactStates()

    def relationships(self):
        app_states = self.app_states
        for info in self.context.persons.any().relationships:
            title = app_states.getTitle(info.state.today) or u''
            yield {
                'person': info.target,
                'title': title,
                }

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishContactDetails(flourish.form.FormViewlet):

    template = ViewPageTemplateFile('templates/f_contact_view.pt')
    fields = field.Fields(IContact).omit('photo')
    mode = DISPLAY_MODE

    @property
    def app_states(self):
        return getAppContactStates()

    def relationships(self):
        app_states = self.app_states
        for info in self.context.persons.any().relationships:
            title = app_states.getTitle(info.state.today) or u''
            yield {
                'person': info.target,
                'title': title,
                }

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


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

    def columnsBefore(self):
        if self.canModify():
            return [
                table.column.DependableCheckboxColumn(
                    prefix="delete",
                    name='delete_checkbox',
                    title=u'',
                    id_getter=IUniqueFormKey,
                    show_disabled=False)]
        return []

    def setUpTableFormatter(self, formatter):
        columns_before = self.columnsBefore()
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


def contact_table_columns():
    return getUtility(IPersonFactory).columns()


class ContactTableFormatter(table.catalog.IndexedTableFormatter):

    columns = lambda self: contact_table_columns()

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()


class FlourishContactTableFormatter(ContactTableFormatter):

    def makeFormatter(self):
        formatter = ContactTableFormatter.makeFormatter(self)
        formatter.cssClasses['table'] = 'contacts-table relationships-table'
        return formatter

    def sortOn(self):
        return getUtility(IPersonFactory).sortOn()


class ContactTable(table.ajax.IndexedTable, FlourishContactTableFormatter):
    columns = FlourishContactTableFormatter.columns
    sortOn = FlourishContactTableFormatter.sortOn


class ContactFilterWidget(table.catalog.IndexedFilterWidget):

    template = ViewPageTemplateFile('templates/filter.pt')
    parameters = ['SEARCH_FIRST_NAME', 'SEARCH_LAST_NAME']

    def filter(self, items):
        if 'CLEAR_SEARCH' in self.request:
            for parameter in self.parameters:
                self.request.form[parameter] = ''
            return items

        catalog = self.catalog

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

    def quote(self, param):
        return urllib.quote(unicode(param).encode('UTF-8'))

    def extra_url(self):
        url = ""
        for parameter in self.parameters:
            if parameter in self.request:
                url += '&%s=%s' % (parameter, self.quote(self.request.get(parameter)))
        return url


class FlourishContactFilterWidget(ContactFilterWidget):

    template = ViewPageTemplateFile('templates/f_contact_filter.pt')

    parameters = ['SEARCH_TITLE']

    search_title_id = 'SEARCH_TITLE'

    def filter(self, items):
        if self.search_title_id in self.request:
            search_title = self.request[self.search_title_id]
            query = buildQueryString(search_title)
            if query:
                catalog = self.catalog
                result = catalog['text'].apply(query)
                items = [item for item in items
                         if item['id'] in result]
        return items


class ContactTableFilter(table.ajax.IndexedTableFilter,
                         FlourishContactFilterWidget):

    template = ViewPageTemplateFile('templates/f_contact_table_filter.pt')
    title = _('First name and/or last name')

    @property
    def search_title_id(self):
        return self.manager.html_id+"-title"

    @property
    def parameters(self):
        return (self.search_title_id, )

    active = FlourishContactFilterWidget.active
    extra_url = FlourishContactFilterWidget.extra_url

    def filter(self, results):
        if self.ignoreRequest:
            return results
        return FlourishContactFilterWidget.filter(self, results)

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
        return user.title

    @property
    def recipient(self):
        return self.context.title


class NoTeacherEmailView(BrowserView):

    __call__ = ViewPageTemplateFile('templates/noteacheremail.pt')


class BoundContactPersonActionViewlet(object):

    @property
    def person(self):
        return IPerson(self.context)


class FlourishContactsViewlet(flourish.viewlet.Viewlet):
    """A viewlet showing contacts of a person"""

    template = ViewPageTemplateFile('templates/f_contactsViewlet.pt')

    @property
    def bound_contact(self):
        return IContact(self.context)

    @property
    def contactable(self):
        return IContactable(removeSecurityProxy(self.context))

    @property
    def getContacts(self):
        contacts = self.contactable.contacts
        return [self.buildInfo(contact) for contact in contacts]

    @property
    def app_states(self):
        return getAppContactStates()

    def buildInfo(self, contact):
        return {
            'link': absoluteURL(contact, self.request),
            'relationship': get_relationship_title(self.contactable, contact),
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
            value = getattr(contact, attr)
            if value:
                label = fields[attr].field.title
                rows.append(self.makeRow(label, value))
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


class ContactsLinks(flourish.page.RefineLinksViewlet):
    """Links for manage contact page"""


class PersonAsContactLinkViewlet(flourish.page.LinkIdViewlet):

    @property
    def title(self):
        person = self.context
        return _('${person_full_name} as Contact',
                 mapping={'person_full_name': person.title})


class FlourishManageContactsOverview(flourish.page.Content,
                                     ActiveSchoolYearContentMixin):

    body_template = ViewPageTemplateFile(
        'templates/f_manage_contacts_overview.pt')

    @property
    def contacts(self):
        app = ISchoolToolApplication(None)
        contacts = IContactContainer(app)
        return contacts

    @property
    def total(self):
        catalog = ICatalog(self.contacts)
        return len(catalog.extent)

    def contacts_url(self):
        return self.url_with_schoolyear_id(self.context, view_name='contacts')


class ContactActionsLinks(flourish.page.RefineLinksViewlet):
    """Contact actions links viewlet."""


class FlourishContactDeleteView(flourish.form.DialogForm, form.EditForm):
    """View used for deleting a contact."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    def initDialog(self):
        super(FlourishContactDeleteView, self).initDialog()
        contact = self.context
        self.ajax_settings['dialog']['title'] = translate(
            _(u'Delete ${contact_full_name}',
              mapping={'contact_full_name': contact.title}),
              context=self.request)

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        url = '%s/delete.html?delete.%s&CONFIRM' % (
            absoluteURL(self.context.__parent__, self.request),
            self.context.__name__)
        self.request.response.redirect(url)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handleCancel(self, action):
        pass

    def updateActions(self):
        super(FlourishContactDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def app_states(self):
        return getAppContactStates()

    def relationships(self):
        app_states = self.app_states
        for info in self.context.persons.any().relationships:
            title = app_states.getTitle(info.state.today) or u''
            yield {
                'person': info.target,
                'title': title,
                }


class PhotoView(flourish.widgets.ImageView):
    attribute = "photo"
