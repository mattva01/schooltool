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

from zope.interface import moduleProvides, implements, providedBy, Interface
from zope.interface import directlyProvides
from zope.interface.adapter import AdapterRegistry
from zope.component import serviceManager, getService
from zope.component import getUtility, queryUtility, getUtilitiesFor
from zope.component.utility import IGlobalUtilityService
from zope.component.utility import GlobalUtilityService
from zope.component.exceptions import ComponentLookupError
from persistent import Persistent
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from schooltool.interfaces import IContainmentAPI, IFacetAPI
from schooltool.interfaces import ILocation, IContainmentRoot, ITraversable
from schooltool.interfaces import IMultiContainer
from schooltool.interfaces import IFacet, IFaceted, IFacetFactory
from schooltool.interfaces import IFacetManager
from schooltool.interfaces import IServiceAPI, IServiceManager
from schooltool.interfaces import IRelationshipAPI, IViewAPI
from schooltool.interfaces import IRelationshipFactory
from schooltool.interfaces import IUtilityService
from schooltool.interfaces import ITimetableModelRegistry
from schooltool.interfaces import ITimetableModelFactory
from schooltool.interfaces import IOptions
from schooltool.interfaces import IDynamicSchemaField, IDynamicSchema
from schooltool.interfaces import IDynamicSchemaService
from schooltool.interfaces import IModuleSetup

moduleProvides(IContainmentAPI, IFacetAPI, IServiceAPI,
               IRelationshipAPI, IViewAPI, ITimetableModelRegistry,
               IModuleSetup)

__metaclass__ = type


#
# IContainmentAPI
#

def getPath(obj):
    """See IContainmentAPI."""

    if IContainmentRoot.providedBy(obj):
        return '/'
    cur = obj
    segments = []
    while True:
        if IContainmentRoot.providedBy(cur):
            segments.append('')
            segments.reverse()
            return '/'.join(segments)
        elif ILocation.providedBy(cur):
            parent = cur.__parent__
            if IMultiContainer.providedBy(parent):
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
    while not IContainmentRoot.providedBy(cur):
        if ILocation.providedBy(cur):
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
            if IContainmentRoot.providedBy(cur):
                continue
            elif ILocation.providedBy(cur):
                cur = cur.__parent__
                continue
            else:
                raise TypeError('Could not traverse', cur, name)
        if ITraversable.providedBy(cur):
            cur = cur.traverse(name)
        else:
            raise TypeError('Could not traverse', cur, name)

    return cur


#
# IFacetAPI
#

class FacetManager:
    implements(IFacetManager, ILocation)

    def __init__(self, context):
        self.__name__ = 'facets'
        self.__parent__ = context
        if not IFaceted.providedBy(context):
            raise TypeError(
                "FacetManager's context must be IFaceted", context)

    def setFacet(self, facet, owner=None, name=None):
        """Set a facet on a faceted object."""
        ob = self.__parent__
        if not IFacet.providedBy(facet):
            raise TypeError("%r does not implement IFacet" % facet)
        assert (facet.__parent__ is None,
                "Trying to add a facet that already has a parent")
        ob.__facets__.add(facet, name=name)  # This sets facet.__name__
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



def registerFacetFactory(factory):
    """Register the given facet factory by the given name.

    factory must implement IFacetFactory
    """
    if not IFacetFactory.providedBy(factory):
        raise TypeError("factory must provide IFacetFactory", factory)
    utilities = getService('Utilities')
    utilities.provideUtility(IFacetFactory, factory, factory.name)


#
# Dynamic Schema Service
#

class DynamicSchemaField(Persistent):

    implements(IDynamicSchemaField)

    _keys = 'name', 'label', 'value', 'ftype', 'vocabulary'

    def __init__(self, name, label, ftype=None, value=None, vocabulary=[]):
        # XXX Mutable default argument!
        self.name = name
        self.label = label
        self.ftype = ftype
        self.value = value
        self.vocabulary = vocabulary

    def __getitem__(self, key):
        if key in self._keys:
            return getattr(self, key)
        else:
            raise ValueError("Invalid field value request.")

    def __setitem__(self, key, value):
        if key in self._keys:
            field = getattr(self, key)
        else:
            raise ValueError("Invalid field value")

        field = value

    def __eq__(self, other):
        return (self['name'] == other['name']
                and self['label'] == other['label'])


class DynamicSchema(Persistent):
    """Facet template for dynamic information storage."""

    implements(IDynamicSchema)

    __parent__ = None
    __name__ = None
    owner = None

    def __init__(self):
        self.fields = PersistentList()

    def hasField(self, name):
        for field in self.fields:
            if field.name == name:
                return True
        return False

    def getField(self, name):
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def setField(self, name, value):
        """Set a field value."""
        if not self.hasField(name):
            raise ValueError("Key %r not in fieldset")

        field = self.getField(name)
        field['value'] = value

    def delField(self, name):
        if self.hasField(name):
            # XXX This is completely bogus.
            field = self.getField(name)
            del field

    def addField(self, name, label, ftype, value=None, vocabulary=[]):
        """Add a new field"""
        # XXX Mutable default argument!
        field = DynamicSchemaField(name, label, ftype, value, vocabulary)
        self.fields.append(field)

    def cloneEmpty(self):
        pass

    # TODO Decide whether we want to use __getitem__ or getField.
    __getitem__ = getField


class DynamicSchemaService(Persistent):

    implements(IDynamicSchemaService)

    __parent__ = None
    __name__ = None

    _default_id = None

    def __init__(self):
        self.schemas = PersistentDict()

    def _set_default_id(self, new_id):
        if new_id is not None and new_id not in self.schemas:
            raise ValueError("Dynamic schema %r does not exist" % new_id)
        self._default_id = new_id

    default_id = property(lambda self: self._default_id, _set_default_id)

    def keys(self):
        return self.schemas.keys()

    def __getitem__(self, schema_id):
        schema = self.schemas[schema_id]
        schema.__parent__ = self
        schema.__name__ = schema_id
        return schema

    def __setitem__(self, schema_id, dfacet):
        prototype = dfacet
        self.schemas[schema_id] = prototype
        if self.default_id is None:
            self.default_id = schema_id

    def __delitem__(self, schema_id):
        del self.schemas[schema_id]
        if schema_id == self.default_id:
            self.default_id = None

    def getDefault(self):
        return self[self.default_id]



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
    while not IServiceManager.providedBy(place):
        if not ILocation.providedBy(place):
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


def getTimetableSchemaService(context):
    """See IServiceAPI"""
    return _getServiceManager(context).timetableSchemaService


def getTimePeriodService(context):
    """See IServiceAPI"""
    return _getServiceManager(context).timePeriodService


def getTicketService(context):
    """See IServiceAPI"""
    return _getServiceManager(context).ticketService


def getDynamicFacetSchemaService(context):
    """See IServiceAPI"""
    return _getServiceManager(context).dynamicFacetSchemaService


def getOptions(obj):
    """See IServiceAPI."""
    cur = obj
    while not IOptions.providedBy(cur):
        if ILocation.providedBy(cur):
            cur = cur.__parent__
        else:
            raise TypeError("Cannot find options from %s" % obj)
    return cur


#
# Relationships
#

def registerRelationship(rel_type, handler):
    """See IRelationshipAPI"""
    name = ''
    if rel_type is not None:
        name = rel_type.uri

    utilities = getService('Utilities')
    directlyProvides(handler, IRelationshipFactory)
    utilities.provideUtility(IRelationshipFactory, handler, name)


def getRelationshipHandlerFor(rel_type):
    """Returns the registered handler for relationship_type."""
    name = ''
    if rel_type is not None:
        name = rel_type.uri
    handler = queryUtility(IRelationshipFactory, name)
    if handler is not None:
        return handler
    return getUtility(IRelationshipFactory)


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

view_registry = AdapterRegistry()
class_view_registry = {}


def resetViewRegistry():
    """Replace the view registry with an empty one."""
    global view_registry
    global class_view_registry
    view_registry = AdapterRegistry()
    class_view_registry = {}


def getView(obj):
    """See IViewAPI"""
    if obj.__class__ in class_view_registry:
        factory = class_view_registry.get(obj.__class__)
    else:
        factory = view_registry.lookup([providedBy(obj)], Interface, '')
    if factory is None:
        raise ComponentLookupError("No view found for %r" % (obj,))
    return factory(obj)


def registerView(interface, factory):
    """See IViewAPI"""
    view_registry.register([interface], Interface, '', factory)


def registerViewForClass(cls, factory):
    """See IViewAPI"""
    class_view_registry[cls] = factory


#
#  Utilities
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


#
# ITimetableModelRegistry methods
#

def registerTimetableModel(id, factory):
    """Registers a timetable schema identified by a given id."""
    utilities = getService('Utilities')
    utilities.provideUtility(ITimetableModelFactory, factory, id)


def setUp():
    serviceManager.defineService('Utilities', IGlobalUtilityService)
    serviceManager.provideService('Utilities', GlobalUtilityService())
