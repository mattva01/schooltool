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
Contact information of a Person.

Glue between schooltool.basicperson and schooltool.contact.
"""

from zope.component import getUtility
from zope.component import adapter, adapts
from zope.interface import implements, implementer
from zope.annotation.interfaces import IAnnotations
from zope.security.proxy import removeSecurityProxy
from zope.intid.interfaces import IIntIds
from zope.app.dependable.interfaces import IDependable
from zope.container.interfaces import IContained
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent import ObjectAddedEvent, ObjectRemovedEvent
from zope.lifecycleevent import ObjectModifiedEvent
from zope.event import notify

from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.contact.interfaces import IContact
from schooltool.contact.contact import Contact
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.person.interfaces import IPerson
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.table.table import simple_form_key


PERSON_CONTACT_KEY = 'schooltool.contact.basicperson'


class IBoundContact(IContact):
    pass


class IBoundContactContained(IBoundContact, IContained):
    pass


class BoundContact(Contact):
    implements(IBoundContactContained)

    @property
    def _person(self):
        person = IBasicPerson(self.__parent__)
        return person

    @property
    def prefix(self):
        return self._person.prefix

    @property
    def first_name(self):
        return self._person.first_name

    @property
    def middle_name(self):
        return self._person.middle_name

    @property
    def last_name(self):
        return self._person.last_name

    @property
    def suffix(self):
        return self._person.suffix

    @property
    def photo(self):
        return self._person.photo

    # XXX: person's language is stored both in a default demographics field
    #      and self contact information now.


@implementer(IPerson)
@adapter(IBoundContact)
def getPersonOfBoundContact(contact):
    return contact.__parent__


@implementer(IContact)
def getBoundContact(context):
    person = IBasicPerson(removeSecurityProxy(context))
    annotations = IAnnotations(person)
    contact = annotations.get(PERSON_CONTACT_KEY, None)
    if contact is None:
        contact = BoundContact()
        annotations[PERSON_CONTACT_KEY] = contact
        contact.__name__ = 'contact'
        contact.__parent__ = person
        dependable = IDependable(contact)
        dependable.addDependent("")
        notify(ObjectAddedEvent(contact, contact.__parent__, contact.__name__))
    return contact


class PersonAddedSubsciber(ObjectEventAdapterSubscriber):
    adapts(IObjectAddedEvent, IBasicPerson)

    def __call__(self):
        # auto-vivification of bound contact
        contact = IContact(self.object)


class PersonModifiedSubsciber(ObjectEventAdapterSubscriber):
    adapts(IObjectModifiedEvent, IBasicPerson)

    def __call__(self):
        contact = IContact(self.object)
        # notify about possible changes in contact information
        # note: we do not provide descriptions of changes
        notify(ObjectModifiedEvent(contact))


class PersonRemovedSubsciber(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, IBasicPerson)

    def __call__(self):
        contact = IContact(self.object)
        dependable = IDependable(contact)
        dependable.removeDependent("")
        notify(ObjectRemovedEvent(contact, contact.__parent__, contact.__name__))


@adapter(IBoundContact)
@implementer(IUniqueFormKey)
def getBoundContactFormKey(contact):
    doc_id = getUtility(IIntIds).getId(contact)
    return 'persons.%s%x' % (simple_form_key(contact.__parent__), doc_id)
