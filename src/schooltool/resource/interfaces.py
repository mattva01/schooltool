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
Resource-related interfaces

$Id$
"""

import zope.interface
import zope.schema

import zope.app.container.constraints
from zope.app import container

from schooltool import SchoolToolMessage as _


class IResource(zope.interface.Interface):
    """Resource."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the resource."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the resource."))

    notes = zope.schema.Text(
        title=_("Notes"),
        required=False,
        description=_("Notes for the resource."))


class IResourceContainer(container.interfaces.IContainer):
    """Container of resources."""

    container.constraints.contains(IResource)


class IResourceContained(IResource, container.interfaces.IContained):
    """Resource contained in an IResourceContainer."""

    container.constraints.containers(IResourceContainer)


class ILocation(IResourceContained):
    """Location."""

    capacity = zope.schema.Int(
        title=_("Capacity"),
        description=_("Capacity of the room"),
        required=False)

class IEquipment(IResourceContained):
    """Equipment."""

    manufacturer = zope.schema.TextLine(
        title=_("Manufacturer"),
        description=_("Manufacturer of Equipment"),
        required=False)

    model = zope.schema.TextLine(
        title=_("Model"),
        description=_("Model of Equipment"),
        required=False)

    serialNumber = zope.schema.TextLine(
        title=_("SerialNumber"),
        description=_("SerialNumber of Equipment"),
        required=False)

    serialNumber = zope.schema.TextLine(
        title=_("Serial Number"),
        description=_("Serial Number of Equipment"),
        required=False)

    purchaseDate = zope.schema.Date(
        title=_("Purchase Date"),
        description=_("Purchase Date of Equipment"),
        required=False)
