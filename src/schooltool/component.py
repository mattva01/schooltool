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
from zope.interface import moduleProvides, InterfaceSpecification, implements
from zope.interface.interfaces import IInterface
from zope.interface.type import TypeRegistry
from persistence.dict import PersistentDict
from schooltool.interfaces import IContainmentAPI, IFacetAPI, IURIAPI
from schooltool.interfaces import ILocation, IContainmentRoot, ITraversable
from schooltool.interfaces import IMultiContainer
from schooltool.interfaces import IFacet, IFaceted, IFacetFactory
from schooltool.interfaces import IFacetManager
from schooltool.interfaces import IServiceAPI, IServiceManager
from schooltool.interfaces import IRelationshipAPI, IViewAPI
from schooltool.interfaces import ComponentLookupError, ISpecificURI
from schooltool.interfaces import IUtilityService

moduleProvides(IContainmentAPI, IFacetAPI, IServiceAPI, IURIAPI,
               IRelationshipAPI, IViewAPI)

__metaclass__ = type


#
# IContainmentAPI
#

def getPath(obj):
    """See IContainmentAPI."""

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
            parent = cur.__parent__
            if IMultiContainer.isImplementedBy(parent):
                segments.append(parent.getRelativePath(cur))
            else:
                segments.append(cur.__name__)
            cur = parent
        else:
            raise TypeError("Cannot determine path for %s, %s is neither "
                            "ILocation nor IContainmentRoot" % (obj, cur))


def getRoot(obj):
    """See IContainmentAPI."""
    cur = obj
    while not IContainmentRoot.isImplementedBy(cur):
        if ILocation.isImplementedBy(cur):
            cur = cur.__parent__
        else:
            raise TypeError("Cannot determine path for %s" % obj)
    return cur


def traverse(obj, path):
    """See IContainmentAPI."""
    if path.startswith('/'):
        cur = getRoot(obj)
    else:
        cur = obj
    for name in path.split('/'):
        if name in ('', '.'):
            continue
        if name == '..':
            if IContainmentRoot.isImplementedBy(cur):
                continue
            elif ILocation.isImplementedBy(cur):
                cur = cur.__parent__
                continue
            else:
                raise TypeError('Could not traverse', cur, name)
        if ITraversable.isImplementedBy(cur):
            cur = cur.traverse(name)
        else:
            raise TypeError('Could not traverse', cur, name)

    return cur


#
# IFacetAPI
#

class FacetManager:
    implements(IFacetManager)

    def __init__(self, context):
        if IFaceted.isImplementedBy(context):
            self.__parent__ = context
        else:
            raise TypeError(
                "FacetManager's context must be IFaceted", context)

    def setFacet(self, facet, owner=None):
        """Set a facet on a faceted object."""
        ob = self.__parent__
        if not IFacet.isImplementedBy(facet):
            raise TypeError("%r does not implement IFacet" % facet)
        ob.__facets__.add(facet)  # This sets facet.__name__
        # XXX Check that facet doesn't already have a parent.
        #     An assert will do for now.
        assert (facet.__parent__ is None,
                "Trying to add a facet that already has a parent")
        facet.__parent__ = ob
        if owner is not None:
            facet.owner = owner
        facet.active = True

    def removeFacet(self, facet):
        """Set a facet on a faceted object."""
        ob = self.__parent__
        ob.__facets__.remove(facet)  # This leaves facet.__name__ intact
        facet.active = False
        facet.__parent__ = None

    def iterFacets(self):
        """Returns an iterator all facets of an object."""
        ob = self.__parent__
        return iter(ob.__facets__)

    def facetsByOwner(self, owner):
        """Returns a sequence of all facets of ob that are owned by owner."""
        return [facet for facet in self.iterFacets() if facet.owner is owner]

    def facetByName(self, name):
        """Returns the facet with the given name."""
        ob = self.__parent__
        return ob.__facets__.valueForName(name)


facet_factory_registry = {}


def resetFacetFactoryRegistry():
    """Replace the facet factory registry with an empty one."""
    global facet_factory_registry
    facet_factory_registry = {}


def registerFacetFactory(factory):
    """Register the given facet factory by the given name.

    factory must implement IFacetFactory
    """
    if not IFacetFactory.isImplementedBy(factory):
        raise TypeError("factory must provide IFacetFactory", factory)

    if factory.name in facet_factory_registry:
        if facet_factory_registry[factory.name] is factory:
            # Registering the same factory more than once. Ignore this.
            return
        else:
            raise ValueError(
                'Another factory with that name is registered already.',
                factory.name, factory)
    facet_factory_registry[factory.name] = factory


def iterFacetFactories():
    """Iterates over all registered facet factories."""
    return facet_factory_registry.itervalues()


def getFacetFactory(name):
    """Returns the named facet factory."""
    return facet_factory_registry[name]


#
# IServiceAPI
#

def _getServiceManager(context):
    """Internal method used by IServiceAPI functions."""
    # The following options for finding the service manager are available:
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
    return place


def getEventService(context):
    """See IServiceAPI"""
    return _getServiceManager(context).eventService


def getUtilityService(context):
    """See IServiceAPI"""
    return _getServiceManager(context).utilityService


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


def strURI(uri):
    """Returns the URI of ISpecificURI as a string"""
    return inspectSpecificURI(uri)[0]


_uri_registry = {}


def resetURIRegistry():
    """Replace the URI registry with an empty one."""
    global _uri_registry
    _uri_registry = {}


def registerURI(uri):
    """Adds an ISpecificURI to the registry so it can be queried by
    the URI string."""
    str_uri = strURI(uri)
    if str_uri in _uri_registry:
        if _uri_registry[str_uri] is not uri:
            raise ValueError("Two interfaces with one URI:  "
                             "%r, %r" % (_uri_registry[str_uri], uri))
        else:
            return
    else:
        _uri_registry[str_uri] = uri


def getURI(str):
    """Returns and ISpecificURI with a given URI string."""
    try:
        return _uri_registry[str]
    except KeyError:
        raise ComponentLookupError(str)


#
# Relationships
#

relationship_registry = TypeRegistry()


def resetRelationshipRegistry():
    """Replace the relationship registry with an empty one."""
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


def relate(relationship_type, (a, role_a), (b, role_b)):
    """See IRelationshipAPI"""
    handler = getRelationshipHandlerFor(relationship_type)
    return handler(relationship_type, (a, role_a), (b, role_b))


def getRelatedObjects(obj, role):
    """See IRelationshipAPI"""
    return [link.traverse() for link in obj.listLinks(role)]


#
#  Views
#

view_registry = TypeRegistry()
class_view_registry = {}


def resetViewRegistry():
    """Replace the view registry with an empty one."""
    global view_registry
    global class_view_registry
    view_registry = TypeRegistry()
    class_view_registry = {}


def getView(obj):
    """See IViewAPI"""
    try:
        if obj.__class__ in class_view_registry:
            return class_view_registry[obj.__class__](obj)
        else:
            return view_registry.getAllForObject(obj)[0](obj)
    except IndexError:
        raise ComponentLookupError("No view found for %r" % (obj,))


def registerView(interface, factory):
    """See IViewAPI"""
    view_registry.register(interface, factory)


def registerViewForClass(cls, factory):
    """See IViewAPI"""
    class_view_registry[cls] = factory


#
#  Utillities
#

class UtilityService:
    implements(IUtilityService)

    __parent__ = None
    __name__ = None

    def __init__(self):
        self._utils = PersistentDict()

    def __getitem__(self, name):
        return self._utils[name]

    def __setitem__(self, name, utility):
        if utility.__parent__ is None:
            self._utils[name] = utility
            utility.__parent__ = self
            utility.__name__ = name
        else:
            raise ValueError('Utility already has a parent',
                             utility, utility.__parent__)

    def values(self):
        return self._utils.values()
