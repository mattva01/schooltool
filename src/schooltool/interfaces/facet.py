#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
SchoolTool interfaces for the facet system.

$Id$
"""

from zope.app.location.interfaces import ILocation
from zope.interface import Interface
from zope.schema import Field, Object, TextLine, Set, Bool
from schooltool.interfaces.relationship import IRelationshipSchema


#
# Facets
#

class IFacet(ILocation):
    """A facet.

    A facet is a persistent adapter (a smart annotation) which implements
    some additional functionality / stores additional data.
    """

    __name__ = TextLine(
        title=u"Unique name within the parent's facets")

    __parent__ = Field(
        title=u"The object this facet is augmenting",
        description=u"""
        The object will provide IFaceted, but we cannot declare that without
        creating a dependency cycle.
        """)

    active = Bool(
        title=u"The facet is active")

    owner = Field(
        title=u"The agent responsible for adding this facet to its __parent__",
        description=u"""
        Some facets are attached to an object because the user requested them
        to be added.  Other facets appear on object automatically as a side
        effect of, for example, group membership.  The second sort of facets
        (called "owned facets") will have the `owner` attribute set and will
        not be removable by the user.
        """)


class IFacetedRelationshipSchemaFactory(Interface):

    def __call__(relationship_schema, **facet_factories):
        """Return a faceted relationship schema."""


class IFacetedRelationshipSchema(IRelationshipSchema):
    """A relationship schema that sets facets on the parties after relating."""


class IFaceted(Interface):
    """Denotes that the object can have facets."""

    __facets__ = Set(
        title=u"A set of facets that manages unique names.",
        value_type=Object(title=u"Facet", schema=IFacet))


class IFacetFactory(Interface):
    """An inspectable object that creates facets."""

    name = TextLine(
        title=u"The name of this factory")

    title = TextLine(
        title=u"Short description of this factory")

    facet_name = TextLine(
        title=u"The __name__ the facet will get if it is a singleton facet.",
        required=False,
        description=u"""
        The singleton facet name.  None if the facet is not a singleton facet.
        """)

    def __call__():
        """Return a facet."""


class IFacetManager(Interface):
    """A thing that manages the facets of some object."""

    def setFacet(facet, owner=None, name=None):
        """Set the facet on the object.

        Owner is the agent responsible for adding the facet.
        If owner is None, the ownership of the facet is not changed.

        facet.__name__ must be None before setting the facet.
        facet.__name__ will be set to a name unique within the set of facets,
        if the name argument is None.  Otherwise facet.__name__ will be
        set to the name provided in the argument, if it is possible (no other
        facet has the same name), or a ValueError will be raised if it is not.
        """

    def removeFacet(facet):
        """Remove the facet from the object."""

    def iterFacets():
        """Return an iterator over facets of an object."""

    def facetsByOwner(owner):
        """Return a sequence of all facets that are owned by owner."""

    def facetByName(name):
        """Return the facet with the given name.

        Raises KeyError if there is no facet with that name.
        """


class IFacetAPI(Interface):
    """Facet API

    Facet factories are named utilities implementing IFacetFactory.
    """

    def FacetManager(obj):
        """Return an IFacetManager for the given object.

        Raises TypeError if the object is not IFaceted.
        """

    def registerFacetFactory(factory):
        """Register the facet factory.

        factory must implement IFacetFactory
        """
