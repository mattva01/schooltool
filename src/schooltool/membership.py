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
SchoolTool groups and members

$Id: model.py 153 2003-10-16 12:33:50Z mg $
"""

from sets import Set
from zope.interface import implements, moduleProvides
from schooltool.interfaces import IQueryLinks
from schooltool.interfaces import IMembershipEvent
from schooltool.interfaces import IMemberAddedEvent
from schooltool.interfaces import IMemberRemovedEvent
from schooltool.interfaces import IModuleSetup
from schooltool.uris import URIMembership, URIGroup, URIMember
from schooltool.relationship import RelationshipSchema, RelationshipEvent
from schooltool import relationship
from schooltool.component import registerRelationship

moduleProvides(IModuleSetup)

__metaclass__ = type

Membership = RelationshipSchema(URIMembership,
                                group=URIGroup, member=URIMember)


def checkForPotentialCycles(group, potential_member):
    """Raises ValueError if adding potential_member would create a
    cycle in membership relationships.
    """
    for a, b in (group, potential_member), (potential_member, group):
        seen = Set()
        last = Set()
        last.add(a)
        while last:
            if b in last:
                raise ValueError('Group %r is a transitive member of %r' %
                                 (a, b))
            seen |= last
            new_last = Set()
            for obj in last:
                if IQueryLinks.providedBy(obj):
                    links = obj.listLinks(URIGroup)
                    new_last |= Set([link.traverse() for link in links])
            new_last.difference_update(seen)
            last = new_last


class MembershipEvent(RelationshipEvent):

    implements(IMembershipEvent)

    def __init__(self, links):
        RelationshipEvent.__init__(self, links)
        self.member = None
        self.group = None
        for link in links:
            if link.role == URIMember:
                if self.member is not None:
                    raise TypeError("only one URIMember must be present"
                                    " among links", links)
                self.member = link.traverse()
            if link.role == URIGroup:
                if self.group is not None:
                    raise TypeError("only one URIGroup must be present"
                                    " among links", links)
                self.group = link.traverse()
        if self.member is None or self.group is None:
            raise TypeError("both URIGroup and URIMember must be present"
                            " among links", links)


class MemberAddedEvent(MembershipEvent):
    implements(IMemberAddedEvent)


class MemberRemovedEvent(MembershipEvent):
    implements(IMemberRemovedEvent)


def membershipRelate(relationship_type, (a, role_a), (b, role_b)):
    """See IRelationshipFactory"""

    checkForPotentialCycles(a, b)
    links = relationship.relate(relationship_type,
                                (a, role_a), (b, role_b))
    event = MemberAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def setUp():
    """Register the URIMembership relationship handler."""
    registerRelationship(URIMembership, membershipRelate)
