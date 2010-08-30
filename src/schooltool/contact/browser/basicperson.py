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
Contact information of a Person.

Glue between schooltool.basicperson and schooltool.contact.
"""
import urllib

from zope.schema import getFieldsInOrder
from zope.security.proxy import removeSecurityProxy
from zope.publisher.browser import BrowserView
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form import field

from schooltool.contact.basicperson import IBoundContact
from schooltool.contact.interfaces import IContactInformation
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactPerson
from schooltool.contact.interfaces import IAddress, IEmails, IPhones, ILanguages
from schooltool.contact.browser.contact import ContactEditView
from schooltool.contact.browser.relationship import get_relationship_title


class ContactOverviewView(BrowserView):
    """View class for listing all relevant contact information of a person."""

    __used_for__ = IBoundContact

    __call__ = ViewPageTemplateFile('templates/view_contacts.pt')

    @property
    def person(self):
        return self.context.__parent__

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

    def buildInfo(self, contact):
        return {
            'link': absoluteURL(contact, self.request),
            'relationship': get_relationship_title(self.person, contact),
            'name': " ".join(self._extract_attrs(
                contact, IContactPerson)),
            'address': ", ".join(self._extract_attrs(contact, IAddress)),
            'emails': ", ".join(self._extract_attrs(contact, IEmails)),
            'phones': list(self._extract_attrs(contact, IPhones, add_title=True)),
            'languages': ", ".join(self._extract_attrs(contact, ILanguages)),
            }

    def getContacts(self):
        contacts = IContactable(removeSecurityProxy(self.person)).contacts
        return [self.buildInfo(contact) for contact in contacts]

    def getRelationships(self):
        bound = IContact(self.person)
        return [relationship_info.extra_info
                for relationship_info in bound.persons.relationships]

    def getPerson(self):
        bound = IContact(self.person)
        return self.buildInfo(bound)


class BoundContactEditView(ContactEditView):
    """Edit form for a bound contact."""
    fields = field.Fields(IContactInformation)


class ManageContactsActionViewlet(object):
    @property
    def link(self):
        base_url = absoluteURL(self.context.__parent__, self.request)
        return "%s/@@manage_contacts.html?%s" % (
            base_url,
            urllib.urlencode([('SEARCH_LAST_NAME',
                               self.context.last_name.encode("utf-8"))]))

