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
SchoolTool package interfaces

$Id$
"""

from zope.interface import Interface, Attribute

#
# Containment
#

class ILocation(Interface):
    """An object located in a containment hierarchy.

    From the location information, a unique path can be computed for
    an object. By definition, an object cannot be at two locations in
    a hierarchy.
    """

    __parent__ = Attribute(
        """The parent of an object.

        This value is None when the object is not attached to the hierarchy.
        Otherwise parent must implement either ILocation or IContainmentRoot.
        """)

    __name__ = Attribute(
        """The name of the object within the parent.

        This is a name that the parent can be traversed with to get
        the child.
        """)


class IContainmentRoot(Interface):
    """A marker interface for the top level application object."""


class IContainmentAPI(Interface):
    """Containment API"""

    def getPath(obj):
        """Returns the unique path of an object in the containment hierarchy.

        The object must implement ILocation or IContainmentRoot and must be
        attached to the hierarchy (i.e. following parent references should not
        reach None).
        """

#
# Facets
#

class IFacet(Interface):
    """A facet.

    A facet is a persistent adapter (a smart annotation) which
    implements some additional functionality and/or stores additional
    data.
    """

    active = Attribute("""The facet is active""")


class IFaceted(Interface):
    """Denotes that the object can have facets.
    """

    __facets__ = Attribute("""A dictionary of facets.""")


class IFacetAPI(Interface):
    """Facet API"""

    def setFacet(ob, key, facet):
        """Set the facet identified by the key on the object."""

    def getFacet(ob, key):
        """Get a facet of an object.

        Raises KeyError if no facet with a given key exists.
        """

    def queryFacet(ob, key, default=None):
        """Get a facet of an object.

        Returns default if no facet with a given key exists.
        """

    def getFacetItems(ob):
        """Returns a sequence of (key, facet) for all facets of an object."""


#
# Groups and membership
#

class IGroupRead(Interface):
    """A set of group members.

    All group members must implement IGroupMember.  If facetFactory is not
    None, they also must implement IFaceted.
    """

    facetFactory = Attribute(
        """Factory for facets set on new members.

        Can be None.  Factory gets called with a single argument that is
        the member the facet will be set on.

        Note that if you change facetFactory once some members have
        been added (and possibly removed), those members will keep their
        old facets.
        """)

    def __getitem__(key):
        """Returns a member with the given key.

        Raises a KeyError if there is no such member.
        """

    def keys():
        """Returns a sequence of member keys."""

    def values():
        """Returns a sequence of members."""

    def items():
        """Returns a sequence of (key, member) pairs."""


class IGroupWrite(Interface):
    """Modification access to a group."""

    def add(memeber):
        """Adds a new member to this group.

        Returns the key assigned to this member.

        If facetFactory is not None, creates a facet for this member
        if it does not already have one, and marks it as active.
        Member facets are keyed by the group.
        """

    def __delitem__(key):
        """Removes a member from the group.

        Raises a KeyError if there is no such member.

        If facetFactory is not None, marks the facet keyed by this
        group as inactive.
        """


class IGroup(IGroupWrite, IGroupRead, IFaceted):
    __doc__ = IGroupRead.__doc__


class IGroupMember(ILocation):

    name = Attribute("A human readable name of this member.")

    def groups():
        """Returns a set for all groups this object is a member of."""

    def notifyAdd(group, name):
        """Notifies the member that it's added to a group."""

    def notifyRemove(group):
        """Notifies the member that it's removed from a group."""


#
# Application objects
#

class IPerson(IGroupMember, IFaceted):

    name = Attribute("Person's name")


class IRootGroup(IGroup, IContainmentRoot):
    """An interface for the application root group."""


#
# Exceptions
#

class ComponentLookupError(Exception):
    """An exception for component architecture."""
