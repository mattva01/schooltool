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
Membership relationship.

This module defines group membership as a relationship.

We can reuse most of the test fixture from schoolbell.relationship.tests.

    >>> from schoolbell.relationship.tests import setUp, tearDown
    >>> setUp()

We also need to register an event subscriber for IBeforeRelationshipEvent,
to enforce relationship constraints.

    >>> import zope.event
    >>> old_subscribers = zope.event.subscribers[:]
    >>> zope.event.subscribers.append(enforceMembershipConstraints)

We will need some sample persons and groups for the demonstration

    >>> from schoolbell.app.group.group import Group
    >>> from schoolbell.app.person.person import Person
    >>> jonas = Person()
    >>> petras = Person()
    >>> developers = Group()
    >>> admins = Group()

You can create memberships this way:

    >>> from schoolbell.app.membership import Membership
    >>> Membership(member=jonas, group=developers)
    >>> Membership(member=petras, group=developers)
    >>> Membership(member=petras, group=admins)

You can find all members of a group, or groups of a persons this way:

    >>> from sets import Set
    >>> from schoolbell.relationship import getRelatedObjects
    >>> from schoolbell.app.membership import URIMember, URIGroup
    >>> Set(getRelatedObjects(developers, URIMember)) == Set([jonas, petras])
    True
    >>> Set(getRelatedObjects(petras, URIGroup)) == Set([admins, developers])
    True

There are some constraints: Only objects providing IGroup can be groups.

    >>> Membership(member=jonas, group=petras)
    Traceback (most recent call last):
      ...
    InvalidRelationship: Groups must provide IGroup.

You may not create cyclic memberships.

    >>> Membership(member=admins, group=developers)
    >>> Membership(member=developers, group=admins)
    Traceback (most recent call last):
      ...
    InvalidRelationship: No cycles are allowed.

You may not create ill-formed relationships

    >>> from schoolbell.relationship import relate
    >>> from schoolbell.app.membership import URIMembership
    >>> relate(URIMembership, (jonas, URIMember), (petras, URIMember))
    Traceback (most recent call last):
      ...
    InvalidRelationship: Membership must have one member and one group.

    >>> relate(URIMembership, (jonas, URIGroup), (petras, URIGroup))
    Traceback (most recent call last):
      ...
    InvalidRelationship: Membership must have one member and one group.

Resources can't be part of a group:

    >>> from schoolbell.app.app import Resource
    >>> printer = Resource()
    >>> relate(URIMembership, (admins, URIGroup), (printer, URIMember))
    Traceback (most recent call last):
      ...
    InvalidRelationship: Resources cannot be members of a group.

Of course, these constraints do not apply to other kinds of relationships.

    >>> relate('example:Frogship', (jonas, 'example:Frog'),
    ...                            (petras, 'example:Frog'))

That's all.

    >>> zope.event.subscribers[:] = old_subscribers
    >>> tearDown()

"""

import sets

from schoolbell.relationship import URIObject, RelationshipSchema
from schoolbell.relationship import getRelatedObjects
from schoolbell.relationship.interfaces import IBeforeRelationshipEvent
from schoolbell.relationship.interfaces import InvalidRelationship
from schoolbell.app.interfaces import IResource
from schoolbell.app.group.interfaces import IGroup


URIMembership = URIObject('http://schooltool.org/ns/membership',
                          'Membership', 'The membership relationship.')
URIGroup = URIObject('http://schooltool.org/ns/membership/group',
                     'Group', 'A role of a containing group.')
URIMember = URIObject('http://schooltool.org/ns/membership/member',
                      'Member', 'A group member role.')

Membership = RelationshipSchema(URIMembership,
                                member=URIMember,
                                group=URIGroup)


def enforceMembershipConstraints(event):
    """Enforce membership constraints (IBeforeRelationshipEvent subscriber)."""
    if not IBeforeRelationshipEvent.providedBy(event):
        return
    if event.rel_type != URIMembership:
        return
    if ((event.role1, event.role2) != (URIMember, URIGroup) and
        (event.role1, event.role2) != (URIGroup, URIMember)):
        raise InvalidRelationship('Membership must have one member'
                                  ' and one group.')
    if IResource.providedBy(event[URIMember]):
        raise InvalidRelationship("Resources cannot be members of a group.")
    if not IGroup.providedBy(event[URIGroup]):
        raise InvalidRelationship('Groups must provide IGroup.')
    if isTransitiveMember(event[URIGroup], event[URIMember]):
        raise InvalidRelationship('No cycles are allowed.')


def isTransitiveMember(obj, group):
    """Is `obj` a member of `group` (either directly or indirectly)?

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

    Suppose we have four groups, named a, b, c and d.

        >>> from schoolbell.app.group.group import Group
        >>> a, b, c, d = [Group() for n in range(4)]

    A is a member of b, which is a member of c.

        >>> Membership(member=a, group=b)
        >>> Membership(member=b, group=c)

    If a is a member of b, it is, obviously, a transitive member

        >>> isTransitiveMember(a, b)
        True

    If a is a member of b, which is a member of c, then a is a transitive
    member of c.

        >>> isTransitiveMember(a, c)
        True

    We say that a is a transitive member of a, for convenience.

        >>> isTransitiveMember(a, a)
        True

    In all other cases, we return False.

        >>> isTransitiveMember(b, a)
        False
        >>> isTransitiveMember(c, a)
        False
        >>> isTransitiveMember(a, d)
        False

    That's it.

        >>> tearDown()

    """
    if obj is group:
        return True
    # A group usually has more members than a member has groups, so we will
    # find all transitive groups of `obj` and see whether `group` is one of
    # them.  It does not matter if we use breadth-first or depth-first search.
    queue = [obj]
    seen = sets.Set([id(obj)])
    while queue:
        cur_obj = queue.pop() # therefore DFS; change to pop(0) to get BFS
        for new_group in getRelatedObjects(cur_obj, URIGroup):
            if new_group is group:
                return True
            if id(new_group) not in seen:
                seen.add(id(new_group))
                queue.append(new_group)
    return False
