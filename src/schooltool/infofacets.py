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
from schooltool.interfaces import IAddressInfoFacet
from schooltool.interfaces import IPersonInfoFacet, IDynamicFacetSchemaService


__metaclass__ = type


class DynamicFacetField(Persistent):
    """A display-agnostic field definition"""

    def __init__(self, name, label, ftype=None, value=None, vocabulary=[]):
        self.name = name
        self.label = label
        self.ftype = ftype
        self.value = value
        self.vocabulary = vocabulary

    def __getitem__(self, key):
        if key in ('name', 'label', 'value', 'ftype', 'vocabulary'):
            return getattr(self, key)
        else:
            raise ValueError("Invalid field value request.")

    def __setitem__(self, key, value):
        if key in ('name', 'label', 'value', 'ftype', 'vocabulary'):
            field = getattr(self, key)
        else:
            raise ValueError("Invalid field value")

        field = value

    def __eq__(self, other):
        """Equality test for Field.

        Only compares name and label.
        """
        if self['name'] != other['name']:
            return False
        if self['label'] != other['label']:
            return False

        return True


class DynamicFacet(Persistent):
    """Facet template for dynamic information storage"""

    implements(IDynamicFacet)

    __parent__ = None
    __name__ = None
    owner = None
    active = True

    def __init__(self):
        self.fields = PersistentList()

    def hasField(self, field):
        for f in self.fields:
            if field == f:
                return True
        return False

    def getField(self, name):
        for f in self.fields:
            if f['name'] == name:
                return f
        return None

    def setField(self, name, value):
        """Set a field value."""
        if name not in self.data.keys():
            raise ValueError("Key %r not in fieldset")
        self.data[name]['value'] = value

    def delField(self, name):
        if self.data.has_key(name):
            del self.data[name]
        
    def addField(self, name, label, ftype, value=None, vocabulary=[]):
        """Add a new field"""
        field = DynamicFacetField(name, label, ftype, value, vocabulary)
        self.fields.append(field)

    def cloneEmpty(self):
        empty = DynamicFacet()
        for field in self.fields:
            empty.addField(field.name, field.label, field.ftype,
                    field.value, field.vocabulary)
        return empty

    def __getitem__(self, key):
        return self.getField(key)

class DynamicFacetSchemaService(Persistent):

    implements(IDynamicFacetSchemaService)

    __parent__ = None
    __name__ = None

    _default_id = None

    def __init__(self):
        self.schemas = PersistentDict()

    def _set_default_id(self, new_id):
        if new_id is not None and new_id not in self.schemas:
            raise ValueError("DynamicFacet schema %r does not exist" % new_id)
        self._default_id = new_id

    default_id = property(lambda self: self._default_id, _set_default_id)

    def keys(self):
        return self.schemas.keys()

    def __getitem__(self, schema_id):
        schema = self.schemas[schema_id]
        schema.__parent__ = self
        schema.__name__ = schema_id
        return schema

    def __setitem__(self, schema_id, dfacet):
        prototype = dfacet
        self.schemas[schema_id] = prototype
        if self.default_id is None:
            self.default_id = schema_id

    def __delitem__(self, schema_id):
        del self.schemas[schema_id]
        if schema_id == self.default_id:
            self.default_id = None

    def getDefault(self):
        return self[self.default_id]


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


class AddressInfoFacet(Persistent):
    implements(IAddressInfoFacet)

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

