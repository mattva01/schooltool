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
Gaurdian relationship.

$Id$
"""
from zope.interface import implements, moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IGuardianEvent
from schooltool.interfaces import IGuardianAddedEvent
from schooltool.interfaces import IGuardianRemovedEvent
from schooltool.relationship import RelationshipSchema, RelationshipEvent
from schooltool.component import registerRelationship
from schooltool.uris import URIGuardian
from schooltool.uris import URICustodian
from schooltool.uris import URIWard

moduleProvides(IModuleSetup)

__metaclass__ = type

Guardian = RelationshipSchema(URIGuardian,
                              custodian=URICustodian,
                              ward=URIWard)


class GuardianEvent(RelationshipEvent):

    implements(IGuardianEvent)

    def __init__(self, links):
        RelationshipEvent.__init__(self, links)
        self.custodian = None
        self.ward = None
        for link in links:
            if link.role == URICustodian:
                if self.custodian is not None:
                    raise TypeError("only one URICustodian must be"
                                    " present among links", links)
                self.custodian = link.target
            if link.role == URIWard:
                if self.ward is not None:
                    raise TypeError("only one URIWard must be"
                                    " present among links", links)
                self.ward = link.target
        if self.ward is None or self.resides is None:
            raise TypeError("both URICustodian and URIWard"
                            "must be present among links", links)


class GuardianAddedEvent(GuardianEvent):
    implements(IGuardianAddedEvent)


class GuardianRemovedEvent(GuardianEvent):
    implements(IGuardianRemovedEvent)


def guardianRelate(relationship_type, (a, role_a), (b, role_b)):
    """See IRelationshipFactory"""

    links = relationship.relate(relationship_type, (a, role_a), (b, role_b))
    event = GuardianAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def setUp():
    """Register the URIGuardian relationship handler."""
    registerRelationship(URIGuardian, guardianRelate)

