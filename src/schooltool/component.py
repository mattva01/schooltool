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
The schooltool component.

$Id$
"""

import re
from zope.interface import moduleProvides, InterfaceSpecification
from zope.interface.interfaces import IInterface
from zope.interface.type import TypeRegistry
from schooltool.interfaces import IContainmentAPI, IFacetAPI, IURIAPI
from schooltool.interfaces import ILocation, IContainmentRoot
from schooltool.interfaces import IFacet, IFaceted
from schooltool.interfaces import IServiceAPI, IServiceManager
from schooltool.interfaces import IRelationshipAPI
from schooltool.interfaces import ComponentLookupError, ISpecificURI

moduleProvides(IContainmentAPI, IFacetAPI, IServiceAPI, IURIAPI,
               IRelationshipAPI)

__metaclass__ = type


#
# Adapters
#

adapterRegistry = {}

provideAdapter = adapterRegistry.__setitem__

def getAdapter(object, interface):
    """Stub adapter lookup.

    Only matches exact resulting interfaces and does not look at the
    context's interfaces at all.  Will be replaced with PyProtocols
    when we need more features.
    """

    if interface.isImplementedBy(object):
        return object
    try:
        factory = adapterRegistry[interface]
    except KeyError:
        raise ComponentLookupError("adapter from %s to %s"
                                   % (object, interface))
    return factory(object)


#
# IContainmentAPI
#

def getPath(obj):
    """Returns the path of an object implementing ILocation"""

    if IContainmentRoot.isImplementedBy(obj):
        return '/'
    cur = obj
    segments = []
    while True:
        if IContainmentRoot.isImplementedBy(cur):
            segments.append('')
            segments.reverse()
            return '/'.join(segments)
        elif ILocation.isImplementedBy(cur):
            segments.append(cur.__name__)
            cur = cur.__parent__
        else:
            raise TypeError("Cannot determine path for %s" % obj)


#
# IFacetAPI
#

def setFacet(ob, facet, owner=None):
    """Set a facet on a faceted object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    if not IFacet.isImplementedBy(facet):
        raise TypeError("%r does not implement IFacet" % facet)
    ob.__facets__.add(facet)
    facet.__parent__ = ob
    if owner is not None:
        facet.owner = owner
    facet.active = True

def removeFacet(ob, facet):
    """Set a facet on a faceted object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    ob.__facets__.remove(facet)

def iterFacets(ob):
    """Returns an iterator all facets of an object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    return iter(ob.__facets__)

def facetsByOwner(ob, owner):
    """Returns a sequence of all facets of ob that are owned by owner."""
    return [facet for facet in iterFacets(ob) if facet.owner is owner]

#
# IServiceAPI
#

def getEventService(context):
    """See IServiceAPI"""

    # The following options for finding the event service are available:
    #   1. Use a thread-global variable
    #      - downside: only one event service per process
    #   2. Use context._p_jar.root()[some_hardcoded_name]
    #      - downside: only one event service per database
    #      - downside: context might not be in the database yet
    #   3. Traverse context until you get at the root and look for services
    #      there
    #      - downside: context might not be attached to the hierarchy yet
    # I dislike globals immensely, so I won't use option 1 without a good
    # reason.  Option 2 smells of too much magic.  I will consider it if
    # option 3 proves to be non-viable.

    place = context
    while not IServiceManager.isImplementedBy(place):
        if not ILocation.isImplementedBy(place):
            raise ComponentLookupError(
                    "Could not find the service manager for ", context)
        place = place.__parent__
    return place.eventService


#
# URI API
#

def inspectSpecificURI(uri):
    """Returns a tuple of a URI and the documentation of the ISpecificURI.

    Raises a TypeError if the argument is not ISpecificURI.
    Raises a ValueError if the URI's docstring does not conform.
    """
    if not IInterface.isImplementedBy(uri):
        raise TypeError("URI must be an interface (got %r)" % (uri,))

    if not uri.extends(ISpecificURI, True):
        raise TypeError("URI must strictly extend ISpecificURI (got %r)" %
                        (uri,))

    segments = uri.__doc__.split("\n", 1)
    uri = segments[0].strip()
    if not isURI(uri):
        raise ValueError("This does not look like a URI: %r" % uri)

    if len(segments) > 1:
        doc = segments[1].lstrip()
    else:
        doc = ""

    return uri, doc


def isURI(uri):
    """Checks if the argument looks like a URI.

    Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
    We're only approximating to the spec.
    """
    uri_re = re.compile(r"^[A-Za-z][A-Za-z0-9+-.]*:\S\S*$")
    return uri_re.search(uri)


#
# Relationships
#

relationship_registry = TypeRegistry()

def resetRelationshipRegistry():
    """Clears the relationship registry"""
    global relationship_registry
    relationship_registry = TypeRegistry()


def registerRelationship(rel_type, handler):
    """See IRelationshipAPI"""
    reghandler = relationship_registry.get(rel_type)
    if reghandler is handler:
        return
    elif reghandler is not None:
        raise ValueError("Handler for %s already registered" % rel_type)
    else:
        relationship_registry.register(rel_type, handler)


def getRelationshipHandlerFor(rel_type):
    """Returns the registered handler for relationship_type."""
    handlers = relationship_registry.getAll(InterfaceSpecification(rel_type))
    if not handlers:
        raise ComponentLookupError("No handler registered for %s" % rel_type)
    return handlers[0]


def relate(relationship_type, (a, role_a), (b, role_b), title=None):
    """See IRelationshipAPI"""
    handler = getRelationshipHandlerFor(relationship_type)
    return handler(relationship_type, (a, role_a), (b, role_b), title=title)


def getRelatedObjects(obj, role):
    """See IRelationshipAPI"""
    return [link.traverse() for link in obj.listLinks(role)]

