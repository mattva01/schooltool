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
Membership relationship.

This module defines group membership as a relationship.

We can reuse most of the test fixture from schooltool.relationship.tests.

    >>> from schooltool.relationship.tests import setUp, tearDown
    >>> setUp()

We also need to register an event subscriber for IBeforeRelationshipEvent,
to enforce relationship constraints.

    >>> import zope.event
    >>> old_subscribers = zope.event.subscribers[:]
    >>> zope.event.subscribers.append(enforceMembershipConstraints)

We will need some sample persons and groups for the demonstration

    >>> from schooltool.group.group import Group
    >>> from schooltool.person.person import Person
    >>> jonas = Person()
    >>> petras = Person()
    >>> developers = Group()
    >>> admins = Group()

You can create memberships this way:

    >>> from schooltool.app.membership import Membership
    >>> Membership(member=jonas, group=developers)
    >>> Membership(member=petras, group=developers)
    >>> Membership(member=petras, group=admins)

You can find all members of a group, or groups of a persons this way:

    >>> from schooltool.relationship import getRelatedObjects
    >>> from schooltool.app.membership import URIMember, URIGroup
    >>> set(getRelatedObjects(developers, URIMember)) == set([jonas, petras])
    True
    >>> set(getRelatedObjects(petras, URIGroup)) == set([admins, developers])
    True

There are some constraints: Only objects providing IGroup can be groups.

    >>> Membership(member=jonas, group=petras)
    Traceback (most recent call last):
      ...
    InvalidRelationship: Groups must provide IGroup.

You may not create cyclic memberships as support is dropped now for
group-to-group Membership relationships.

    >>> Membership(member=admins, group=developers)
    Traceback (most recent call last):
      ...
    InvalidRelationship: Groups cannot be members of a group anymore.

You may not create ill-formed relationships

    >>> from schooltool.relationship import relate
    >>> from schooltool.app.membership import URIMembership
    >>> relate(URIMembership, (jonas, URIMember), (petras, URIMember))
    Traceback (most recent call last):
      ...
    InvalidRelationship: Membership must have one member and one group.

    >>> relate(URIMembership, (jonas, URIGroup), (petras, URIGroup))
    Traceback (most recent call last):
      ...
    InvalidRelationship: Membership must have one member and one group.

Resources can't be part of a group:

    >>> from schooltool.resource.resource import Resource
    >>> printer = Resource()
    >>> relate(URIMembership, (admins, URIGroup), (printer, URIMember))
    Traceback (most recent call last):
      ...
    InvalidRelationship: Resources cannot be members of a group.

Of course, these constraints do not apply to other kinds of relationships.

    >>> from schooltool.relationship.tests import URIStub
    >>> relate('example:Frogship', (jonas, URIStub('example:Frog')),
    ...                            (petras, URIStub('example:Frog')))

That's all.

    >>> zope.event.subscribers[:] = old_subscribers
    >>> tearDown()

"""

from zope.component import adapts

from schooltool.relationship import URIObject, RelationshipSchema
from schooltool.relationship import getRelatedObjects
from schooltool.relationship.interfaces import IBeforeRelationshipEvent
from schooltool.relationship.interfaces import InvalidRelationship
from schooltool.resource.interfaces import IBaseResource
from schooltool.group.interfaces import IBaseGroup as IGroup
from schooltool.person.interfaces import IPerson
from schooltool.securitypolicy.crowds import Crowd

from schooltool.common import SchoolToolMessage as _


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
    # XXX look through all the IBeforeRelationshipEvent subscribers,
    # if there are any, and convert them to something different.
    if not IBeforeRelationshipEvent.providedBy(event):
        return
    if event.rel_type != URIMembership:
        return
    if ((event.role1, event.role2) != (URIMember, URIGroup) and
        (event.role1, event.role2) != (URIGroup, URIMember)):
        raise InvalidRelationship('Membership must have one member'
                                  ' and one group.')
    if IBaseResource.providedBy(event[URIMember]):
        raise InvalidRelationship("Resources cannot be members of a group.")
    if not IGroup.providedBy(event[URIGroup]):
        raise InvalidRelationship('Groups must provide IGroup.')
    if IGroup.providedBy(event[URIMember]):
        raise InvalidRelationship("Groups cannot be members of a group anymore.")
    if isTransitiveMember(event[URIGroup], event[URIMember]):
        raise InvalidRelationship('No cycles are allowed.')


def isTransitiveMember(obj, group):
    """Is `obj` a member of `group` (either directly or indirectly)?

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> setUp()

    Suppose we have four groups, named a, b, c and d.

        >>> from schooltool.group.group import Group
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
    seen = set([id(obj)])
    while queue:
        cur_obj = queue.pop() # therefore DFS; change to pop(0) to get BFS
        for new_group in getRelatedObjects(cur_obj, URIGroup):
            if new_group is group:
                return True
            if id(new_group) not in seen:
                seen.add(id(new_group))
                queue.append(new_group)
    return False


class GroupMemberCrowd(Crowd):
    """Crowd that contains all the members of the group.

        >>> from schooltool.app.membership import GroupMemberCrowd
        >>> class GroupStub(object):
        ...     def __init__(self, members):
        ...         self.members = members
        >>> class PrincipalStub(object):
        ...     def __init__(self, name):
        ...         self.name = name
        ...     def __conform__(self, iface):
        ...         if iface == IPerson:
        ...             return self.name
        >>> group = GroupStub(["Petras"])
        >>> crowd = GroupMemberCrowd(group)

    If person is not a member of the group return False:

        >>> crowd.contains(PrincipalStub("Jonas"))
        False

    If the person is in the member list of the context group return
    True:

        >>> crowd.contains(PrincipalStub("Petras"))
        True

    Some principals might not adapt to IPerson, they should be
    rejected:

        >>> crowd.contains("Foo")
        False

    """

    adapts(IGroup)

    title = _(u'Members')
    description = _(u'Members of the group.')

    def contains(self, principal):
        return IPerson(principal, None) in self.context.members
