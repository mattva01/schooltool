#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
The infofacets for addres and person Schooltool objects.

$Id$
"""

from persistent import Persistent
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from zope.interface import implements
from schooltool.interfaces import IDynamicFacet, IPersonInfoFacet
from schooltool.interfaces import IAddressFacet
from schooltool.interfaces import IPersonInfoFacet, IDynamicFacetSchemaService
from schooltool.component import DynamicSchemaField, DynamicSchema
from schooltool.component import DynamicSchemaService


__metaclass__ = type


class DynamicFacet(DynamicSchema):
    """Facet template for dynamic information storage"""

    implements(IDynamicFacet)

    active = True

    def cloneEmpty(self):
        empty = DynamicFacet()
        for field in self.fields:
            empty.addField(field.name, field.label, field.ftype,
                    field.value, field.vocabulary)
        return empty


class DynamicFacetSchemaService(DynamicSchemaService):

    implements(IDynamicFacetSchemaService)
    pass


class PersonInfoFacet(Persistent):

    implements(IPersonInfoFacet)

    __parent__ = None
    __name__ = None
    owner = None
    active = True

    def __init__(self):
        self._first_name = None
        self._last_name = None
        self.date_of_birth = None
        self.photo = None
        self.comment = None

    def _getFirstName(self):
        return self._first_name

    def _setFirstName(self, name):
        self._first_name = name
        self._updateTitle()

    first_name = property(_getFirstName, _setFirstName)

    def _getLastName(self):
        return self._last_name

    def _setLastName(self, name):
        self._last_name = name
        self._updateTitle()

    last_name = property(_getLastName, _setLastName)

    def _updateTitle(self):
        if self._first_name or self._last_name:
            title = "%s %s" % (self._first_name or '', self._last_name or '')
            self.__parent__.title = title.strip()

    def addField(self, name, value = None):
        pass

    def delField(self, name):
        pass

    def getField(self, name):
        pass

    def listFields(self):
        pass


class AddressFacet(Persistent):

    implements(IAddressFacet)

    __parent__ = None
    __name__ = None
    owner = None
    active = True

    postcode = None
    district = None
    town = None
    streetNr = None
    thoroughfareName = None
    #country = property(lambda self: self._country)
    #postcode = property(lambda self: self._postcode)
    #district = property(lambda self: self._district)
    #town = property(lambda self: self._town)
    #streetNr = property(lambda self: self._streetNr)
    #town = property(lambda self: self._town)
    #thoroughfareName = property(lambda self: self._thoroughfareName)

    def __init__(self):
        #self._country = None
        self.postcode = None
        self.district = None
        self.town = None
        self.streetNr = None
        self.thoroughfareName = None

    def __eq__(self, other):
        try:
            if self.postcode == other.postcode and \
                    self.district == other.district and \
                    self.town == other.town and \
                    self.streetNr == other.streetNr and \
                    self.thoroughfareName == other.thoroughfareName:
                        return True
        except:
            pass

        return False

    def contains(self, s):
        if str(self.postcode).find(s) >= 0:
            return True
        if str(self.district).find(s) >= 0:
            return True
        if str(self.town).find(s) >= 0:
            return True
        if str(self.streetNr).find(s) >= 0:
            return True
        if str(self.thoroughfareName).find(s) >= 0:
            return True
        return False

