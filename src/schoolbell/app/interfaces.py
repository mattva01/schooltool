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
SchoolBell application interfaces

$Id$
"""

from zope.interface import Interface
from zope.schema import Object
from zope.app.container.interfaces import IReadContainer, IContainer
from zope.app.container.constraints import contains


class IPerson(Interface):
    """Person."""


class IPersonContainer(IContainer):
    """Container of persons."""

    contains(IPerson)


class IGroup(Interface):
    """Group."""


class IGroupContainer(IContainer):
    """Container of groups."""

    contains(IGroup)


class IResource(Interface):
    """Resource."""


class IResourceContainer(IContainer):
    """Container of resources."""

    contains(IResource)


class ISchoolBellApplication(IReadContainer):
    """The main SchoolBell application object.

    The application is a read-only container with the following items:

        'persons' - IPersonContainer
        'groups' - IGroupContainer
        'resources' - IResourceContainer

    TODO: this object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """
