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
SchoolTool organisational model.

$Id$
"""

from zope.interface import implements
from schooltool.interfaces import IPerson, IGroup
from schooltool.interfaces import URIMembership, URIMember, URIGroup
from schooltool.relationship import RelationshipValenciesMixin
from schooltool.facet import FacetedEventTargetMixin

__metaclass__ = type


class Person(FacetedEventTargetMixin, RelationshipValenciesMixin):

    implements(IPerson)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None
        self._valencies.append((URIMembership, URIMember))


class Group(FacetedEventTargetMixin, RelationshipValenciesMixin):

    implements(IGroup)

    def __init__(self, title=None):
        FacetedEventTargetMixin.__init__(self)
        RelationshipValenciesMixin.__init__(self)
        self.title = title
        self.__name__ = None
        self.__parent__ = None
        self._valencies.append((URIMembership, URIGroup))
