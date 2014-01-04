#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
Parent access.
"""
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from zope.interface import invariant, Invalid, Interface
from zope.schema import Password, TextLine
from zope.traversing.browser.absoluteurl import absoluteURL

import z3c.form.validator
import z3c.form.form
import z3c.form.button
import z3c.form.field

from schooltool.skin import flourish
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.browser.person import UsernameValidator
from schooltool.basicperson.browser.person import PasswordValidator
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IContactInformation
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonFactory
from schooltool.securitypolicy.crowds import inCrowd
from schooltool.relationship.relationship import IRelationshipLinks
from schooltool.relationship.relationship import duplicate
from schooltool.contact.contact import ACTIVE, PARENT
from schooltool.contact.contact import ContactRelationship

from schooltool.common import SchoolToolMessage as _


class ParentNavViewlet(flourish.page.LinkViewlet):

    @property
    def target(self):
        return IPerson(self.request.principal, None)

    @property
    def enabled(self):
        target = self.target
        if target is None:
            return False
        enabled = inCrowd(
            self.request.principal, 'parent', self.target)
        return enabled


class ParentHome(flourish.page.Page):
    pass


class ChildrenOverview(flourish.viewlet.Viewlet):

    @property
    def person(self):
        return IPerson(self.context, None)

    def children(self):
        contact = IContact(self.person)
        relationships = ContactRelationship.bind(contact=contact)
        return list(relationships.any(ACTIVE+PARENT))


class IParentAccessForm(Interface):

    username = TextLine(
        title=_("Username"),
        description=_(u"Cannot begin with '+' or '@,' contain non-ascii characters or '/.'"),
        required=True)

    password = Password(
        title=_("Password"),
        description=_(u"Users cannot log in until a password is assigned."),
        required=False)

    confirm = Password(
        title=_("Confirm password"),
        required=False)

    @invariant
    def isPasswordConfirmed(person):
        if person.password != person.confirm:
            raise Invalid(_(u"Passwords do not match"))


class ContactUsernameValidator(UsernameValidator):

    @property
    def container(self):
        return ISchoolToolApplication(None)['persons']


z3c.form.validator.WidgetValidatorDiscriminators(
    ContactUsernameValidator,
    field=IParentAccessForm['username'])


class ContactPasswordValidator(PasswordValidator):
    pass


z3c.form.validator.WidgetValidatorDiscriminators(
    ContactPasswordValidator,
    field=IParentAccessForm['password'])


class EnableParentAccess(z3c.form.form.AddForm, flourish.page.Page):
    fields = z3c.form.field.Fields(IParentAccessForm)
    template = flourish.templates.Inherit(flourish.page.Page.template)
    page_template = flourish.templates.Inherit(flourish.page.Page.page_template)

    label = None
    legend = _('Create SchoolTool user')

    content = None
    added = None

    @z3c.form.button.buttonAndHandler(_('Enable'), name='add')
    def handleAdd(self, action):
        super(EnableParentAccess, self).handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_("Cancel"))
    def handleCancel(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(EnableParentAccess, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def update(self):
        self.content = {}
        super(EnableParentAccess, self).update()

    def getContent(self):
        return self.content

    @property
    def _factory(self):
        return getUtility(IPersonFactory)

    @property
    def contact(self):
        return self.context

    def create(self, data):
        contact = removeSecurityProxy(self.contact)
        person = self._factory(data['username'],
                               contact.first_name,
                               contact.last_name)
        if data['password']:
            person.setPassword(data['password'])
        return person


    def copyContactInfo(self, contact, target):
        for name in IContactInformation:
            if name=='photo':
                continue
            value = getattr(contact, name, None)
            if value is not None:
                setattr(target, name, value)
        source_links = removeSecurityProxy(IRelationshipLinks(contact))
        for link in source_links:
            duplicate(link, target)

    def add(self, person):
        name = person.username

        persons = ISchoolToolApplication(None)['persons']
        persons[name] = person

        contact = removeSecurityProxy(self.contact)

        person.prefix = contact.prefix
        person.middle_name = contact.middle_name
        person.suffix = contact.suffix

        person.photo = contact.photo
        if person.photo is not None:
            person.photo.__parent__ = person

        self.copyContactInfo(contact, IContact(person))

        del contact.__parent__[contact.__name__]

        self.added = person
        return person

    def nextURL(self):
        if self.added is None:
            url = absoluteURL(self.context, self.request)
            return url
        url = "%s/contact" % absoluteURL(self.added, self.request)
        return url
