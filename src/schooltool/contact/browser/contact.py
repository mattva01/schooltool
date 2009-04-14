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
from zope.security.proxy import removeSecurityProxy
from zope.interface import directlyProvides
from zope.interface import implements
from zope.component import getMultiAdapter
from zope.component import adapts
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser import absoluteURL
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.app.container.interfaces import INameChooser
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn
from z3c.form import form, field, button

from schooltool.table.table import SchoolToolTableFormatter
from schooltool.skin.containers import TableContainerView
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.contact import Contact
from schooltool.contact.interfaces import IContact

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


class PersonContactAddView(ContactAddView):
    """Contact add form that assigns the contact to a person."""

    form.extends(ContactAddView)

    @property
    def label(self):
        return _("Add new contact for ${person}",
                 mapping={'person': self.context.title})

    def add(self, contact):
        """Add `contact` to the container. And assign it to the person."""
        contact_container = IContactContainer(ISchoolToolApplication(None))
        name = INameChooser(contact_container).chooseName('', contact)
        contact_container[name] = contact
        IContactable(removeSecurityProxy(self.context)).contacts.add(contact)
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

    def updateActions(self):
        super(ContactEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def label(self):
        return _(u'Change information for ${first_name} ${last_name}',
                 mapping={'first_name': self.context.first_name,
                          'last_name': self.context.last_name})


class ContactView(form.DisplayForm):
    """Display form for basic contact."""
    template = ViewPageTemplateFile('templates/contact_view.pt')
    fields = field.Fields(IContact)

    def __call__(self):
        self.update()
        return self.render()


class ContactContainerView(TableContainerView):
    """A Contact Container view."""

    __used_for__ = IContactContainer

    index_title = _("Contact index")


class ContactTableFormatter(SchoolToolTableFormatter):

    def columns(self):
        first_name = GetterColumn(name='first_name',
                                  title=_(u"First Name"),
                                  getter=lambda i, f: i.first_name,
                                  subsort=True)
        directlyProvides(first_name, ISortableColumn)
        last_name = GetterColumn(name='last_name',
                                 title=_(u"Last Name"),
                                 getter=lambda i, f: i.last_name,
                                 subsort=True)
        directlyProvides(last_name, ISortableColumn)
        return [first_name, last_name]

    def sortOn(self):
        return (("first_name", False),)
