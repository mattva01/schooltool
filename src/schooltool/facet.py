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
SchoolTool facets.

A facet is a persistent adapter (a smart annotation) which implements
some additional functionality and/or stores additional data.

Facets depend on events.

$Id$
"""

from zope.interface import implements, classProvides
from persistence import Persistent
from schooltool.interfaces import IFaceted, IEventConfigurable
from schooltool.interfaces import IFacetedRelationshipSchemaFactory
from schooltool.interfaces import IFacetedRelationshipSchema, IUnlinkHook
from schooltool.interfaces import IPlaceholder
from schooltool.event import EventTargetMixin
from schooltool.component import setFacet, iterFacets
from schooltool.db import PersistentKeysSet

__metaclass__ = type


class FacetedMixin:

    implements(IFaceted)

    def __init__(self):
        self.__facets__ = PersistentKeysSet()


class FacetedEventTargetMixin(FacetedMixin, EventTargetMixin):

    def __init__(self):
        FacetedMixin.__init__(self)
        EventTargetMixin.__init__(self)

    def getEventTable(self):
        tables = [self.eventTable]
        for facet in iterFacets(self):
            if facet.active and IEventConfigurable.isImplementedBy(facet):
                tables.append(facet.eventTable)
        return sum(tables, [])


class FacetedRelationshipSchema:

    classProvides(IFacetedRelationshipSchemaFactory)
    implements(IFacetedRelationshipSchema)

    def __init__(self, relationship_schema, **facet_factories):
        """Returns a faceted relationship schema."""
        self._schema = relationship_schema
        self._factories = facet_factories
        self.type = relationship_schema.type
        self.title = relationship_schema.title

    def __call__(self, **parties):
        """See IRelationshipSchema"""
        links = self._schema(**parties)

        # No need to check that all facet factories are accounted for.
        # It it is ok with the schema to make such a relationship, it is ok
        # to only apply some of the facets.
        for role_name, factory in self._factories.iteritems():
            if role_name in links:
                link = links[role_name]
                target = link.traverse()
                if IFaceted.isImplementedBy(target):
                    setFacet(target, factory(), owner=link)
                    link.registerUnlinkCallback(facetDeactivator)
                else:
                    raise TypeError('Target of link "%s" must be IFaceted: %r'
                                    % (role_name, target))
        return links


class FacetReactivator(Persistent):
    """Linkset Placeholder that knows what facets are associated with links
    like this. When replaced by a link, reactivates the facets."""

    implements(IPlaceholder)

    facets = ()

    def replacedBy(self, link):
        for facet in self.facets:
            facet.owner = link
            facet.active = True


def facetDeactivator(link):
    """Deactivate any facets registered in the link target that are owned by
    the link. Add a placeholder for the link that reactivates and reowns the
    facets to a new equivalent link. Set the ownership of such facets to the
    placeholder.
    """
    placeholder = FacetReactivator()
    facets = []
    target = link.traverse()
    for facet in iterFacets(target):
        if facet.owner is link:
            facets.append(facet)
            facet.active = False
            facet.owner = placeholder
    if facets:
        placeholder.facets = facets
        target.__links__.addPlaceholder(link, placeholder)
