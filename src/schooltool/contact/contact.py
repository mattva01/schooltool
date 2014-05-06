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
Contact objects
"""
from persistent import Persistent

from zope.catalog.text import TextIndex
from zope.component import adapter, adapts
from zope.index.text.interfaces import ISearchableText
from zope.interface import implementer
from zope.interface import implements
from zope.intid.interfaces import IIntIds
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer
from zope.component import getUtility

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IRelationshipStateContainer
from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.catalog import AttributeCatalog
from schooltool.app.states import StateStartUpBase
from schooltool.contact.interfaces import IContactPersonInfo
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContact, IContactContained
from schooltool.contact.interfaces import IContactContainer
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.relationship.uri import URIObject
from schooltool.relationship.temporal import ACTIVE, INACTIVE
from schooltool.relationship.temporal import TemporalURIObject
from schooltool.relationship.relationship import RelationshipProperty
from schooltool.relationship.relationship import RelationshipSchema
from schooltool.securitypolicy import crowds
from schooltool.table.catalog import ConvertingIndex
from schooltool.common import simple_form_key
from schooltool.person.interfaces import IPerson
from schooltool.course.section import PersonInstructorsCrowd
from schooltool.app.utils import vocabulary_titled

from schooltool.common import SchoolToolMessage as _


URIContactRelationship = TemporalURIObject('http://schooltool.org/ns/contact',
                                           'Contact relationship',
                                           'The contact relationship.')

URIContact = URIObject('http://schooltool.org/ns/contact/contact',
                       'Contact', 'A contact relationship contact record role.')

URIPerson = URIObject('http://schooltool.org/ns/contact/person',
                      'Person', 'A contact relationship person role.')

ContactRelationship = RelationshipSchema(URIContactRelationship,
                                         contact=URIContact, person=URIPerson)


PARENT = 'p'


class ContactGroup(crowds.DescriptionGroup):

    title = _(u"Contacts")

    description = _(u''
        'All SchoolTool users have contact information, that includes home '
        'address, phone number, email address, etc.'
        '\n'
        '"External contacts" can be created - people who are not SchoolTool '
        'users, but may need to recieve notifications and information about '
        'the student or the school as a whole.')


class ContactContainer(BTreeContainer):
    """Container of persons."""

    implements(IContactContainer)


class Contact(Persistent, Contained):
    """Contact."""

    implements(IContactContained)

    prefix = None
    first_name = None
    middle_name = None
    last_name = None
    suffix = None
    photo = None
    address_line_1 = None
    address_line_2 = None
    city = None
    state = None
    country = None
    postal_code = None
    email = None
    home_phone = None
    work_phone = None
    mobile_phone = None
    other_1 = None
    other_2 = None
    language = None

    persons = RelationshipProperty(URIContactRelationship,
                                   my_role=URIContact,
                                   other_role=URIPerson)

    @property
    def title(self):
        return "%s %s" % (self.first_name, self.last_name)


# BBB
class ContactPersonInfo(Persistent, Contained):
    implements(IContactPersonInfo)
    __parent__ = None
    relationship = None


class ContextRelationshipProperty(RelationshipProperty):
    """Context relationship property."""

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return RelationshipProperty.__get__(self, instance.context, owner)


class Contactable(object):
    implements(IContactable)

    contacts = ContextRelationshipProperty(URIContactRelationship,
                                           my_role=URIPerson,
                                           other_role=URIContact)

    def __init__(self, context):
        self.context = context

    def __conform__(self, iface):
        return iface(self.context)


class ContactAppStartup(StartUpBase):
    def __call__(self):
        if 'schooltool.contact' not in self.app:
            self.app['schooltool.contact'] = ContactContainer()


class ContactInit(InitBase):
    def __call__(self):
        self.app['schooltool.contact'] = ContactContainer()


@implementer(IContactContainer)
@adapter(ISchoolToolApplication)
def getContactContainer(app):
    return app['schooltool.contact']


@adapter(IContact)
@implementer(IUniqueFormKey)
def getContactFormKey(contact):
    doc_id = getUtility(IIntIds).getId(contact)
    return 'contacts.%s%x' % (simple_form_key(contact), doc_id)


class ContactCatalog(AttributeCatalog):
    version = '4 - added text index'
    interface = IContact
    attributes = ('first_name', 'last_name', 'title')

    def setIndexes(self, catalog):
        super(ContactCatalog, self).setIndexes(catalog)
        catalog['form_keys'] = ConvertingIndex(converter=IUniqueFormKey)
        catalog['text'] = TextIndex('getSearchableText', ISearchableText, True)


getContactCatalog = ContactCatalog.get


class SearchableTextContact(object):

    adapts(IContact)
    implements(ISearchableText)

    def __init__(self, context):
        self.context = context

    def getSearchableText(self):
        result = [self.context.first_name, self.context.last_name]
        return ' '.join(result)


class ContactPersonInstructorsCrowd(PersonInstructorsCrowd):
    """Crowd of instructors of any of related persons to this contact."""

    title = _(u'Instructors')
    description = _(u'Instructors of student(s) related to this contact.')

    def contains(self, principal):
        user = IPerson(principal, None)
        for person in self.context.persons:
            sections = self._getSections(person)
            for section in sections:
                if user in section.instructors:
                    return True
        return False


class ContactStatesStartup(StateStartUpBase):

    states_name = 'contact-relationship'
    states_title = _('Contact Relationships')

    def populate(self, states):
        states.add(_('Contact'), ACTIVE, 'a')
        states.add(_('Parent'), ACTIVE+PARENT, 'p')
        states.add(_('Step-parent'), ACTIVE+PARENT, 'sp')
        states.add(_('Foster parent'), ACTIVE+PARENT, 'fp')
        states.add(_('Guardian'), ACTIVE+PARENT, 'g')
        states.add(_('Sibling'), ACTIVE, 's')
        states.add(_('Inactive'), INACTIVE, 'i')
        states.add(_('Added in error'), INACTIVE, 'e')
        states.describe(ACTIVE, _('A contact'))
        states.describe(ACTIVE+PARENT, _('A parent'))
        states.describe(INACTIVE, _('Inactive'))
        states.describe(INACTIVE+PARENT, _('Inactive parent'))


class ParentCrowd(crowds.Crowd):

    def contains(self, principal):
        person = IPerson(principal, None)
        if person is None:
            return False
        relationships = ContactRelationship.bind(contact=IContact(person))
        is_parent = bool(relationships.any(ACTIVE+PARENT))
        return is_parent


class ParentOfCrowd(crowds.Crowd):

    @property
    def child(self):
        target = None
        obj = self.context
        while (target is None and obj is not None):
            target = IPerson(obj, None)
            if target is not None:
                return target
            obj = obj.__parent__
        return target

    def contains(self, principal):
        person = IPerson(principal, None)
        if person is None:
            return False
        target = self.child
        if target is None:
            return False
        relationships = ContactRelationship.bind(contact=IContact(person))
        is_parent = target in relationships.any(ACTIVE+PARENT)
        return is_parent


def getAppContactStates():
    app = ISchoolToolApplication(None)
    container = IRelationshipStateContainer(app)
    app_states = container['contact-relationship']
    return app_states


def contactStatesVocabulary(context):
    app_states = getAppContactStates()
    return vocabulary_titled(app_states.states.values())


def ContactStatesVocabularyFactory():
    return contactStatesVocabulary
