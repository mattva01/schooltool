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
Relationship interfaces

$Id$
"""

from zope.interface import Interface, Attribute


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


class IRelationshipLink(Interface):
    """One half of a relationship.

    When a relationship between `a` and `b` is established, two links are
    created and placed into link sets of `a` and `b` respectively.
    """

    rel_type = Attribute("""Relationship type.""")
    target = Attribute("""The other member of the relationship.""")
    role = Attribute("""Role of `target`.""")


class IRelationshipEvent(Interface):
    """Common attributes for relationship events."""

    rel_type = Attribute("""Relationship type.""")
    participant1 = Attribute("""One of the participants.""")
    role1 = Attribute("""Role of `participant1`.""")
    participant2 = Attribute("""One of the participants.""")
    role2 = Attribute("""Role of `participant2`.""")

    def __getitem__(role):
        """Return the participant with a given role.

        This does not work well with "peer-to-peer" relationships, that is,
        when role1 == role2.
        """


class IBeforeRelationshipEvent(IRelationshipEvent):
    """A relationship is about to be established.

    You can register subscribers for this event to implement constraints.
    By convention, subscribers raise InvalidRelationship or a subclass
    when a relationship does not meet all the constraints.
    """


class IRelationshipAddedEvent(IRelationshipEvent):
    """A relationship has been established."""


class InvalidRelationship(Exception):
    """Invalid relationship."""


class DuplicateRelationship(InvalidRelationship):
    """Relationship already exists"""

