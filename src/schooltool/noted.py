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
Noted relationship.

$Id$
"""
from zope.interface import implements, moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import INotedEvent
from schooltool.interfaces import INotedAddedEvent
from schooltool.interfaces import INotedRemovedEvent
from schooltool.relationship import RelationshipSchema, RelationshipEvent
from schooltool.uris import URINoted
from schooltool.uris import URINotation
from schooltool.uris import URINotandum

moduleProvides(IModuleSetup)

__metaclass__ = type

Noted = RelationshipSchema(URINoted,
                              notation=URINotation,
                              notandum=URINotandum)


class NotedEvent(RelationshipEvent):

    implements(INotedEvent)

    def __init__(self, links):
        RelationshipEvent.__init__(self, links)
        self.notation = None
        self.notandum = None
        for link in links:
            if link.role == URINotation:
                if self.notation is not None:
                    raise TypeError("only one URINotation must be"
                                    " present among links", links)
                self.notation = link.traverse()
            if link.role == URINotandum:
                if self.notandum is not None:
                    raise TypeError("only one URINotandum must be"
                                    " present among links", links)
                self.notandum = link.traverse()
        if self.notandum is None or self.resides is None:
            raise TypeError("both URINotation and URINotandum"
                            "must be present among links", links)


class NotedAddedEvent(NotedEvent):
    implements(INotedAddedEvent)


class NotedRemovedEvent(NotedEvent):
    implements(INotedRemovedEvent)


def notedRelate(relationship_type, (a, role_a), (b, role_b)):
    """See IRelationshipFactory"""

    links = relationship.relate(relationship_type, (a, role_a), (b, role_b))
    event = NotedAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def setUp():
    """Register the URINoted relationship handler."""
    registerRelationship(URINoted, notedRelate)

