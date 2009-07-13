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
Contact objects
"""
from persistent import Persistent

from zope.component import adapter
from zope.component import adapts
from zope.interface import implementer
from zope.interface import implements
from zope.app.container.contained import Contained
from zope.app.container.btree import BTreeContainer

from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationStartUpEvent
from schooltool.app.app import InitBase, StartUpBase
from schooltool.contact.interfaces import IContactPersonInfo
from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactContained
from schooltool.contact.interfaces import IContactContainer
from schooltool.relationship.uri import URIObject
from schooltool.relationship.relationship import BoundRelationshipProperty
from schooltool.relationship.relationship import RelationshipProperty
from schooltool.relationship.relationship import RelationshipSchema


URIContactRelationship = URIObject('http://schooltool.org/ns/contact',
                                   'Contact relationship',
                                   'The contact relationship.')

URIContact = URIObject('http://schooltool.org/ns/contact/contact',
                       'Contact', 'A contact relationship contact record role.')

URIPerson = URIObject('http://schooltool.org/ns/contact/person',
                      'Person', 'A contact relationship person role.')

Contact = RelationshipSchema(URIContactRelationship,
                             contact=URIContact, person=URIPerson)


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
    language = None

    persons = RelationshipProperty(URIContactRelationship,
                                   my_role=URIContact,
                                   other_role=URIPerson)


class ContactPersonInfo(Persistent, Contained):
    """Additional information about contact of a specific person."""

    implements(IContactPersonInfo)

    __parent__ = None
    relationship = None

    def getRelationshipTitle(self):
        vocabulary = IContactPersonInfo['relationship'].vocabulary
        try:
            term = vocabulary.getTerm(self.relationship)
        except LookupError:
            return u''
        return term.title


class ContextRelationshipProperty(RelationshipProperty):
    """Context relationship property."""

    def __get__(self, instance, owner):
        """Bind the property to the context of an instance."""
        if instance is None:
            return self
        else:
            return BoundRelationshipProperty(instance.context,
                                             self.rel_type,
                                             self.my_role,
                                             self.other_role)


class Contactable(object):
    implements(IContactable)

    contacts = ContextRelationshipProperty(URIContactRelationship,
                                           my_role=URIPerson,
                                           other_role=URIContact)

    def __init__(self, context):
        self.context = context


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
