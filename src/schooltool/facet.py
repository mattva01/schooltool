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

from persistent import Persistent
from zope.interface import implements, classProvides
from zope.interface.advice import addClassAdvisor
from schooltool.interfaces import IFacet, IFaceted, IEventConfigurable
from schooltool.interfaces import IFacetedRelationshipSchemaFactory
from schooltool.interfaces import IFacetedRelationshipSchema, IFacetFactory
from schooltool.interfaces import IPlaceholder
from schooltool.interfaces import IRelationshipValencies
from schooltool.event import EventTargetMixin
from schooltool.component import FacetManager
from schooltool.db import PersistentKeysSetContainer
from schooltool.relationship import Valency
from schooltool.membership import Membership

__metaclass__ = type


class FacetMixin:
    """Mixin for writing facets."""

    implements(IFacet)

    __parent__ = None
    __name__ = None
    active = False
    owner = None


class FacetFactory:
    """Class that provides metadata for a callable that produced facets."""

    implements(IFacetFactory)

    def __init__(self, factory, name, title=None, facet_name=None):
        self.factory = factory
        self.name = name
        if title is None:
            self.title = name
        else:
            self.title = title
        self.facet_name = facet_name

    def __call__(self):
        return self.factory()


class FacetedMixin:

    implements(IFaceted)

    def __init__(self):
        self.__facets__ = PersistentKeysSetContainer('facets', self, IFacet)


class FacetedEventTargetMixin(FacetedMixin, EventTargetMixin):

    def __init__(self):
        FacetedMixin.__init__(self)
        EventTargetMixin.__init__(self)

    def getEventTable(self):
        tables = [self.eventTable]
        for facet in FacetManager(self).iterFacets():
            if facet.active and IEventConfigurable.providedBy(facet):
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
        self.roles = relationship_schema.roles
        for factory in self._factories.itervalues():
            if not IFacetFactory.providedBy(factory):
                raise TypeError("Facet factory %r does not"
                                " implement IFacetFactory" % (factory, ))

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
                if IFaceted.providedBy(target):
                    fm = FacetManager(target)
                    my_facets = fm.facetsByOwner(link)
                    if my_facets:
                        # Check my facets are active.
                        # These facets would have come from a previous
                        # equivalent relationship.
                        # Reactivating existing facets is a policy decision
                        # by this class. This is the point at which the
                        # decision is made.
                        for facet in my_facets:
                            if not facet.active:
                                facet.active = True
                    else:
                        fm.setFacet(factory(), owner=link,
                                    name=factory.facet_name)
                    link.registerUnlinkCallback(facetDeactivator)
                else:
                    raise TypeError('Target of link "%s" must be IFaceted: %r'
                                    % (role_name, target))
        return links


class FacetOwnershipSetter(Persistent):
    """Linkset Placeholder that knows what facets are associated with links
    like this. When replaced by a link, makes the facets owned by the new
    link."""

    implements(IPlaceholder)

    facets = ()

    __name__ = None

    def replacedBy(self, link):
        for facet in self.facets:
            facet.owner = link


def facetDeactivator(link):
    """Deactivate any facets registered in the link target that are owned by
    the link. Add a placeholder for the link that reactivates and reowns the
    facets to a new equivalent link. Set the ownership of such facets to the
    placeholder.
    """
    placeholder = FacetOwnershipSetter()
    facets = []
    target = link.traverse()
    for facet in FacetManager(target).facetsByOwner(link):
        facets.append(facet)
        facet.active = False
        facet.owner = placeholder
    if facets:
        placeholder.facets = facets
        target.__links__.addPlaceholder(link, placeholder)


def membersGetFacet(facet_class, facet_name=None, factory_name=None):
    """Provide a Membership valency that sets facets on members.

    This function is called in a class definition.

    facet_class is the class of the facets that will be placed on members.

    facet_name is the name those facets will get (see IFacetFactory attribute
    facet_name).

    factory_name is the name of the internally generated facet factory.  If
    None, facet_class.__name__ will be used.

    Sample usage:

        class FooGroupFacet(FacetMixin, RelationshipValenciesMixin):
            membersGetFacet(FooFacet)

    """
    if factory_name is None:
        factory_name = facet_class.__name__

    def setValencies(cls):
        if not IFacet.implementedBy(cls):
            raise TypeError("membersGetFacet should only be used for facets")
        if not IRelationshipValencies.implementedBy(cls):
            raise TypeError("membersGetFacet should only be used for facets"
                            " that implement IRelationshipValencies")
        factory = FacetFactory(facet_class, factory_name,
                               facet_name=facet_name)
        schema = FacetedRelationshipSchema(Membership, member=factory)
        cls.valencies = Valency(schema, 'group')
        return cls

    addClassAdvisor(setValencies)
