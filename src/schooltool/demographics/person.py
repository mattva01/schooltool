#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
from pytz import utc
from datetime import datetime
from persistent import Persistent

from zope.interface import implements
from zope import schema
from zope.location import locate, ILocation

import interfaces
from schooltool.person.person import Person as PersonBase


class Person(PersonBase):
    """Special person that adds demographics information.
    """
    implements(interfaces.IDemographicsPerson)

    def __init__(self, username=None, title=None):
        super(Person, self).__init__(username, title)
        self.modified = now()
        self.nameinfo = NameInfo()
        locate(self.nameinfo, self, 'nameinfo')
        self.demographics = Demographics()
        locate(self.demographics, self, 'demographics')
        self.schooldata = SchoolData()
        locate(self.schooldata, self, 'schooldata')
        self.parent1 = ContactInfo()
        locate(self.parent1, self, 'parent1')
        self.parent2 = ContactInfo()
        locate(self.parent2, self, 'parent2')
        self.emergency1 = ContactInfo()
        locate(self.emergency1, self, 'emergency1')
        self.emergency2 = ContactInfo()
        locate(self.emergency2, self, 'emergency2')
        self.emergency3 = ContactInfo()
        locate(self.emergency3, self, 'emergency3')


class NameInfo(Persistent):
    implements(interfaces.INameInfo, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.INameInfo, self,
                                   ['full_name', 'photo'])

    def _get_full_name(self):
        return self.__parent__.title

    def _set_full_name(self, s):
        self.__parent__.title = s

    full_name = property(_get_full_name, _set_full_name)

    def _get_photo(self):
        return self.__parent__.photo

    def _set_photo(self, d):
        self.__parent__.photo = d

    photo = property(_get_photo, _set_photo)


class Demographics(Persistent):
    implements(interfaces.IDemographics, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.IDemographics, self)


class SchoolData(Persistent):
    implements(interfaces.ISchoolData, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.ISchoolData, self)


class ContactInfo(Persistent):
    implements(interfaces.IContactInfo, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.IContactInfo, self)


def initializeSchemaAttributes(iface, obj, suppress=None):
    """Initialize an object given the schema attributes in an interface.

    The names of the attributes given in suppress are not initialized.
    This can be useful in case that attribute is managed by a property.
    """
    suppress = suppress or []
    for field in schema.getFields(iface).values():
        if field.__name__ in suppress:
            continue
        field.set(obj, field.default)


def personModifiedSubscriber(person, event):
    person.modified = now()


def now():
    return utc.localize(datetime.utcnow())
