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
The information facets for the Schooltool objects.

$Id$
"""

from persistent import Persistent
from zope.interface import implements
from schooltool.interfaces import IPersonInfoFacet, IAddressInfoFacet 


__metaclass__ = type


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


class AddressInfoFacet(Persistent):

    implements(IAddressInfoFacet)

    __parent__ = None
    __name__ = None
    owner = None
    active = True

    def __init__(self):
        self.country = None
        self.postcode = None
        self.district = None
        self.town = None
        self.streetNr = None
        self.thoroughfareName = None
