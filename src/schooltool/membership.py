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
from schooltool.interfaces import IBeforeMembershipEvent
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IEventTarget
from schooltool.interfaces import IPerson
from schooltool.uris import URIMembership, URIGroup, URIMember
from schooltool.relationship import RelationshipSchema, RelationshipEvent
from schooltool import relationship
from schooltool.component import registerRelationship
from schooltool.component import getRelatedObjects, getOptions, getPath
from schooltool.event import EventMixin
from schooltool.translation import ugettext as _

moduleProvides(IModuleSetup)

__metaclass__ = type

Membership = RelationshipSchema(URIMembership,
                                group=URIGroup, member=URIMember)


def checkForPotentialCycles(group, potential_member):
    """Check if adding potential_member to group would create a cycle.

    Raises ValueError if that is the case.
    """
    seen = Set()
    last = Set()
    last.add(group)
    while last:
        if potential_member in last:
            raise ValueError(_('Circular membership is not allowed.'))
        seen |= last
        new_last = Set()
        for obj in last:
            if IQueryLinks.providedBy(obj):
                links = obj.listLinks(URIGroup)
                new_last |= Set([link.traverse() for link in links])
        new_last.difference_update(seen)
        last = new_last


def belongsToParentGroup(member, group):
    """Check if member belongs to a parent of group.

    Returns False if member does not belong to a parent of the group,
    (which means that member may not be added to the given group),
    True otherwise.
    """
    parents = getRelatedObjects(group, URIGroup)
    if parents:
        possible_members = Set()
        for parent in parents:
            members = getRelatedObjects(parent, URIMember)
            possible_members.update(members)
        return member in possible_members
    return True


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


class BeforeMembershipEvent(EventMixin):

    implements(IBeforeMembershipEvent)

    def __init__(self, group, member):
        EventMixin.__init__(self)
        self.group = group
        self.member = member
        self.links = ()

    def __unicode__(self):
        event = self.__class__.__name__
        s = [u"%s" % event]
        s.append("group='%s'" % getPath(self.group))
        s.append("member='%s'" % getPath(self.member))
        return u"\n    ".join(s) + u'\n'


def membershipRelate(relationship_type, (a, role_a), (b, role_b)):
    """See IRelationshipFactory"""

    if role_a == URIGroup:
        group, potential_member = a, b
    else:
        group, potential_member = b, a
    checkForPotentialCycles(group, potential_member)
    before_event = BeforeMembershipEvent(group, potential_member)
    before_event.dispatch(group)
    before_event.dispatch(potential_member)
    if memberOf(potential_member, group):
        raise ValueError(_('Already a member'))
    links = relationship.relate(relationship_type,
                                (a, role_a), (b, role_b))
    event = MemberAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def memberOf(member, group):
    """Is `member` a member of `group`?"""
    return group in getRelatedObjects(member, URIGroup)


class RestrictedMembershipPolicy:
    """Restricted membership policy"""

    implements(IEventTarget)

    def notify(self, event):
        if (IBeforeMembershipEvent.providedBy(event) and
            IPerson.providedBy(event.member) and
            getOptions(event.group).restrict_membership):
            if not belongsToParentGroup(event.member, event.group):
                raise ValueError(_('Only immediate members of parent'
                                   ' groups can be members'))


def setUp():
    """Register the URIMembership relationship handler."""
    registerRelationship(URIMembership, membershipRelate)
