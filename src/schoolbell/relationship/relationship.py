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
Implementation of relationships.

Relationships are represented as collections of links.  A link defines one
half of a relationship.  The storage of links on an object is determined by
an IRelationshipLinks adapter.  There is a default adapter registered for
all IAnnotatable objects that uses Zope 3 annotations.
"""

from persistent import Persistent
from persistent.list import PersistentList
from zope.interface import implements

from schoolbell.relationship.interfaces import IRelationshipLinks
from schoolbell.relationship.interfaces import IRelationshipLink


def relate(rel_type, (a, role_of_a), (b, role_of_b)):
    """Establish a relationship between objects `a` and `b`."""
    # TODO: BeforeRelationshipEvent
    IRelationshipLinks(a).add(Link(b, role_of_b, rel_type))
    IRelationshipLinks(b).add(Link(a, role_of_a, rel_type))
    # TODO: AfterRelationshipEvent


def getRelatedObjects(obj, role):
    """Return all objects related to `obj` with a given role."""
    return [link.target for link in IRelationshipLinks(obj)
            if link.role == role]


class Link(Persistent):
    """One half of a relationship.

    A link is a simple class that holds information about one side of the
    relationship:

        >>> target = object()
        >>> role = 'example:Member'
        >>> rel_type = 'example:Membership'
        >>> link = Link(target, role, rel_type)
        >>> link.target is target
        True
        >>> link.role
        'example:Member'
        >>> link.rel_type
        'example:Membership'

    The attributes are documented in IRelationshipLink

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IRelationshipLink, link)
        True

    """

    implements(IRelationshipLink)

    def __init__(self, target, role, rel_type):
        self.target = target
        self.role = role
        self.rel_type = rel_type


class LinkSet(Persistent):
    """Set of links.

    This class is used internally to represent relationships.  Initially it
    is empty

        >>> linkset = LinkSet()
        >>> list(linkset)
        []

    You can add new links to it

        >>> link1 = Link(object(), 'example:Member', 'example:Membership')
        >>> link2 = Link(object(), 'example:Friend', 'example:Friendship')
        >>> linkset.add(link1)
        >>> linkset.add(link2)
        >>> from sets import Set
        >>> Set(linkset) == Set([link1, link2]) # order is not preserved
        True

    It is documented in IRelationshipLinks

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IRelationshipLinks, linkset)
        True

    """

    implements(IRelationshipLinks)

    def __init__(self):
        self._links = PersistentList()

    def add(self, link):
        self._links.append(link)

    def __iter__(self):
        return iter(self._links)
