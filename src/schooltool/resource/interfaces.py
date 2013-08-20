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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Resource-related interfaces
"""

import zope.schema
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains, containers
from zope.interface import Interface, Attribute

from schooltool.basicperson.interfaces import IDemographics, IDemographicsFields
from schooltool.calendar.interfaces import ICalendarEvent
from schooltool.calendar.interfaces import ICalendar
from schooltool.common import SchoolToolMessage as _


class ResourceSubType(zope.schema.TextLine):
    """Sub-type of the resource is a free-form text line."""


class IBaseResource(Interface):
    """Resource."""

    title = zope.schema.TextLine(
        title=_("Title"))

    type = ResourceSubType(
        title=_("Resource Type"),
        description=_("Type of resource"),
        required=True)


    description = zope.schema.Text(
        title=_("Description"),
        required=False)

    notes = zope.schema.Text(
        title=_("Notes"),
        required=False,
        description=_("Notes for the resource."))


class IResourceContainer(IContainer):
    """Container of resources."""

    contains(IBaseResource)


class IBaseResourceContained(IBaseResource, IContained):
    """Resource contained in an IResourceContainer."""

    containers(IResourceContainer)


class IResource(IBaseResource):
    """Marker for a regular old resource"""


class ILocation(IBaseResource):
    """Location."""

    type = ResourceSubType(
        title=_("Location Type"),
        description=_("Type of location (i.e. computer lab, class room, etc.)"),
        required=True)


    capacity = zope.schema.Int(
        title=_("Capacity"),
        description=_("Capacity of the room"),
        required=False)


class IEquipment(IBaseResource):
    """Equipment."""

    type = ResourceSubType(
        title=_("Equipment Type"),
        description=_("Type of equipment (i.e. camcorder, computer, etc.)"),
        required=True)

    manufacturer = zope.schema.TextLine(
        title=_("Manufacturer"),
        description=_("Manufacturer of Equipment"),
        required=False)

    model = zope.schema.TextLine(
        title=_("Model"),
        description=_("Model of Equipment"),
        required=False)

    serialNumber = zope.schema.TextLine(
        title=_("Serial Number"),
        description=_("Serial Number of Equipment"),
        required=False)

    purchaseDate = zope.schema.Date(
        title=_("Purchase Date"),
        description=_("Purchase Date of Equipment"),
        required=False)


class IResourceTypeInformation(Interface):

    id = zope.schema.TextLine(
        title=_("Id of the resource type."),
        description=_(
            "Used for lookup of named utilities that have resource "
            "type specific information."))

    title = zope.schema.TextLine(
        title=_("The title of a resource type."),
        description=_(
            "A string that will be displayed to users in tables or "
            "resource type selection widgets."))


class IResourceFactoryUtility(Interface):

    title = zope.schema.TextLine(
        title=_("The title of a resource type."),
        description=_(
            "A string that will be displayed to users in tables or "
            "resource type selection widgets."))

    def columns():
        """Default columns for display of this resource in a table."""


class IResourceTypeSource(zope.schema.interfaces.IIterableSource):
    """Marker interface for a source of resource types."""


class IResourceSubTypes(Interface):
    """Contains a list of sub types for a given type."""

    def types():
        """returns Types among a type (subtypes)"""


class IBookResources(Interface):
    """An object that can have booked resources."""

    resources = zope.schema.Iterable(
        title=u"Booked Resources")


class IBookingCalendar(ICalendar):

    title = Attribute("")


class IBookingCalendarEvent(ICalendarEvent):
    """Event that represents a possible booking on an existing event."""


class IBookingTimetableEvent(ICalendarEvent):
    """Event that represents a possible booking in a timetable slot."""


class IResourceDemographics(IDemographics):
    """Demographics data storage for a resource

    Stores any kind of data defined by field descriptions that are set
    up for the resource container.
    """


class IResourceDemographicsFields(IDemographicsFields):
    """Demographics field storage for resource demos."""

