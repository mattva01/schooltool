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
Occupies relationship.

$Id$
"""
from zope.interface import implements, moduleProvides
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IOccupiesEvent
from schooltool.interfaces import IOccupiesAddedEvent
from schooltool.interfaces import IOccupiesRemovedEvent
from schooltool.relationship import RelationshipSchema, RelationshipEvent
from schooltool.relationship import RelationshipValenciesMixin
from schooltool.relationship import Valency
from schooltool import relationship
from schooltool.component import registerRelationship
from schooltool.uris import URIOccupies, URICurrentlyResides
from schooltool.uris import URICurrentResidence
from schooltool.facet import FacetMixin

moduleProvides(IModuleSetup)

__metaclass__ = type

Occupies = RelationshipSchema(URIOccupies,
                              resides=URICurrentlyResides,
                              residence=URICurrentResidence)


class ResidenceFacet(FacetMixin, RelationshipValenciesMixin):
    """Facet for an Address."""

    valencies = Valency(Occupies, 'residence')


class OccupiesEvent(RelationshipEvent):

    implements(IOccupiesEvent)

    def __init__(self, links):
        RelationshipEvent.__init__(self, links)
        self.resides = None
        self.residence = None
        for link in links:
            if link.role == URICurrentlyResides:
                if self.resides is not None:
                    raise TypeError("only one URICurrentlyResides must be"
                                    " present among links", links)
                self.resides = link.target
            if link.role == URICurrentResidence:
                if self.residence is not None:
                    raise TypeError("only one URICurrentResidence must be"
                                    " present among links", links)
                self.residence = link.target
        if self.residence is None or self.resides is None:
            raise TypeError("both URICurrentlyResides and URICurrentResidence"
                            "must be present among links", links)


class OccupiesAddedEvent(OccupiesEvent):
    implements(IOccupiesAddedEvent)


class OccupiesRemovedEvent(OccupiesEvent):
    implements(IOccupiesRemovedEvent)


def occupiesRelate(relationship_type, (a, role_a), (b, role_b)):
    """See IRelationshipFactory"""

    links = relationship.relate(relationship_type,
                                (a, role_a), (b, role_b))
    event = OccupiesAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def setUp():
    """Register the URIOccupies relationship handler."""
    registerRelationship(URIOccupies, occupiesRelate)
