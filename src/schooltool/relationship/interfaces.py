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
Relationship interfaces
"""

from zope.interface import Interface, Attribute


class IRelationshipProperty(Interface):
    """A property tied to a relationship."""

    rel_type = Attribute("""Relationship type""")
    my_role = Attribute("""Role of the object with this property""")
    other_role = Attribute("""Role of other objects in this relationship""")
    this = Attribute("""The object that this property is bound to.""")
    relationships = Attribute(
        """A list of RelationshipInfo helpers for all related objects.""")

    def __nonzero__():
        """Are there any related objects?

        Equivalent to bool(list(self)), but can be implemented more
        efficiently.
        """

    def __len__():
        """Return the number of related objects."""

    def __iter__():
        """Iterate over all related objects."""

    def iter_refs():
        """Iterate over all related objects."""

    def add(other, extra_info=None):
        """Establish a relationship with `other`."""

    def remove(other):
        """Unlink a relationship with `other`."""


class IRelationshipInfo(Interface):
    """Non-persistent helper to access relationship extra information."""

    source = Attribute("""Source object of the relationship.""")
    target = Attribute("""Target object of the relationship.""")
    state = Attribute("""State of the relationship.""")
    extra_info = Attribute("""Extra information that was passed to `relate`.""")


class IRelationshipLink(Interface):
    """One half of a relationship.

    When a relationship between `a` and `b` is established, two links are
    created and placed into link sets of `a` and `b` respectively.
    """

    rel_type = Attribute("""Relationship type.""")
    rel_type_hash = Attribute("""Hash of relationship type URI.""")
    target = Attribute("""The other member of the relationship.""")
    role = Attribute("""Role of `target`.""")
    role_hash = Attribute("""hash of `target` role URI.""")
    my_role = Attribute("""Role of the object that has this link.""")
    my_role_hash = Attribute("""Hash of role URI of this object.""")
    extra_info = Attribute("""Extra information that was passed to `relate`.

        Be careful to keep extra info in sync on both links of the
        relationship.
        """)
    state = Attribute("""State of a relationship.""")


class IRelationshipLinks(Interface):
    """A set of relationship links.

    Objects that can be used in relationships are those that have an adapter to
    IRelationshipLinks.

    See also `IRelationshipLink`.
    """

    def __iter__():
        """Iterate over all links."""

    def add(link):
        """Add a new link."""

    def remove(link):
        """Remove a link.

        Raises ValueError if link is not in the set.
        """

    def clear():
        """Remove all links."""

    def find(my_role, target, role, rel_type):
        """Find a link with matching attributes.

        Raises ValueError if a matching link is not found.
        """

    def __getitem__(id):
        """Return the link with a given id."""

    def get(key, default=None):
        """Get a link for a key

        The default is returned if there is no value for the key.
        """

    def iterLinksByRole(role, rel_type=None, catalog=None):
        """Iterate over all links from this object with a given role."""

    def getTargetsByRole(role, rel_type=None, catalog=None):
        """Return all objects related to this object with a given role."""

    def iterTargetsByRole(role, rel_type=None, catalog=None):
        """Return all objects related to this object with a given role."""

    def getCachedLinksByRole(role, catalog=None):
        """Get a set of links by role."""

    def getCachedLinksByTarget(target, catalog=None):
        """Get a set of links by target."""


class IRelationshipEvent(Interface):
    """Common attributes for relationship events."""

    rel_type = Attribute("""Relationship type.""")
    participant1 = Attribute("""One of the participants.""")
    role1 = Attribute("""Role of `participant1`.""")
    participant2 = Attribute("""One of the participants.""")
    role2 = Attribute("""Role of `participant2`.""")
    extra_info = Attribute("""Extra info, as passed to relate().""")

    def __getitem__(role):
        """Return the participant with a given role.

        This does not work well with "peer-to-peer" relationships, that is,
        when role1 == role2.
        """

    def match(schema):
        """Return an accessor object if this event matches the schema."""

    def getLinks():
        """Return links of participants."""


class IBeforeRelationshipEvent(IRelationshipEvent):
    """A relationship is about to be established.

    You can register subscribers for this event to implement constraints.
    By convention, subscribers raise InvalidRelationship or a subclass
    when a relationship does not meet all the constraints.
    """


class IRelationshipAddedEvent(IRelationshipEvent):
    """A relationship has been established."""


class IBeforeRemovingRelationshipEvent(IRelationshipEvent):
    """A relationship is about to be broken.

    You can register subscribers for this event to implement constraints
    (by raising exceptions).
    """


class IRelationshipRemovedEvent(IRelationshipEvent):
    """A relationship has been broken."""


class InvalidRelationship(Exception):
    """Invalid relationship."""


class DuplicateRelationship(InvalidRelationship):
    """Relationship already exists"""


class NoSuchRelationship(Exception):
    """Relationship does not exist"""


class IRelationshipSchema(Interface):
    """Relationship schema."""

    roles = Attribute("""Roles of members of the relationship.""")
    rel_type = Attribute("""Type of the relationship.""")

    def __call__(**parties):
        """Establish a relationship."""

    def unlink(**parties):
        """Break a relationship."""

    def query(**party):
        """Retrieve relationship targets."""
