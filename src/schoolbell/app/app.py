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
"""
SchoolBell application object

$Id$
"""

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app.container.btree import BTreeContainer
from zope.app.container.sample import SampleContainer

from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.interfaces import IPersonContainer
from schoolbell.app.interfaces import IGroupContainer
from schoolbell.app.interfaces import IResourceContainer


class SchoolBellApplication(Persistent, SampleContainer):
    """The main application object.

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """

    implements(ISchoolBellApplication)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = PersonContainer()
        self['groups'] = GroupContainer()
        self['resources'] = ResourceContainer()

    def _newContainerData(self):
        return PersistentDict()


class PersonContainer(BTreeContainer):
    """Container of persons."""

    implements(IPersonContainer)


class GroupContainer(BTreeContainer):
    """Container of groups."""

    implements(IGroupContainer)


class ResourceContainer(BTreeContainer):
    """Container of resources."""

    implements(IResourceContainer)
