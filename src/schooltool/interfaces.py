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
SchoolTool package interfaces

$Id$
"""

from zope.interface import Interface, Attribute, moduleProvides

#
# Containment
#

class IContainmentAPI(Interface):
    """Containment API"""

    def getPath(obj):
        """Return the unique path of an object in the containment hierarchy.

        The object must implement ILocation or IContainmentRoot and must be
        attached to the hierarchy (i.e. following parent references should not
        reach None).  If either of those conditions is not met, raises a
        TypeError.
        """

    def getRoot(obj):
        """Return the containment root for obj.

        The object must implement ILocation or IContainmentRoot and
        must be attached to the hierarchy (i.e. following parent
        references should not reach None).  If either of those
        conditions is not met, raises a TypeError.  """

    def traverse(obj, path):
        """Return the object accessible as path from obj.

        Path is a list of names separated with forward slashes.  Multiple
        adjacent slashes are equivalent to a single slash.  Special names
        are '.' and '..'; they are treated as is customary in file systems.
        Traversing to .. at the root keeps you at the root.

        If path starts with a slash, then the traversal starts from
        getRoot(obj), otherwise the travelsal starts from obj.
        """


class ILocation(Interface):
    """An object located in a containment hierarchy.

    From the location information, a unique path can be computed for
    an object. By definition, an object cannot be at two locations in
    a hierarchy.
    """

    __parent__ = Attribute(
        """The parent of an object.

        This value is None when the object is not attached to the hierarchy.
        Otherwise parent must implement either ILocation or IContainmentRoot.
        """)

    __name__ = Attribute(
        """The name of the object within the parent.

        This is a name that the parent can be traversed with to get
        the child.
        """)


class IContainmentRoot(Interface):
    """A marker interface for the top level application object."""


class ITraversable(Interface):
    """An object that can be traversed."""

    def traverse(name):
        """Return an object reachable as name.

        Raises a KeyError if the name cannot be traversed.

        Traversables do not have to handle special names '.' or '..'.
        """

class IMultiContainer(Interface):
    """A container that chooses names for its children.

    The use of this is to make an object be able to tell the correct
    way to traverse to its relationships or facets.
    """

    def getRelativePath(child):
        """Returns the path of child relative to self."""

#
# Services
#

class IServiceAPI(Interface):
    """Service API"""

    def getEventService(context):
        """Returns the global event service."""

    def getUtilityService(context):
        """Returns the global utility service."""


class IServiceManager(Interface):
    """Container of services"""

    eventService = Attribute("""Event service for this application""")

    utilityService = Attribute("""Utility service for this application""")


#
# URIs
#

class ISpecificURI(Interface):
    """All interfaces derived from this must have the URI they map on
    to as the first line of their docstring. Examples::

        class URITutor(ISpecificURI):
            '''http://schooltool.org/ns/tutor'''

        class URITutor(ISpecificURI):
            '''http://schooltool.org/ns/tutor

            A person who is responsible for a registration class.
            '''

    The suggested naming convention for URIs is to prefix the
    interface names with 'URI'.
    """


class IURIAPI(Interface):

    def inspectSpecificURI(uri):
        """Returns a tuple of a URI and the documentation of the ISpecificURI.

        Raises a TypeError if the argument is not ISpecificURI.
        Raises a ValueError if the URI's docstring does not conform.
        """

    def strURI(uri):
        """Returns the URI of ISpecificURI as a string"""

    def isURI(uri):
        """Checks if the argument looks like a URI.

        Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
        We're only approximating to the spec.
        """

    def registerURI(uri):
        """Adds a URI to the registry so it can be queried by the URI
        string."""

    def getURI(str):
        """Returns and ISpecificURI with a given URI string."""


class URIGroup(ISpecificURI):
    """http://schooltool.org/ns/membership/group

    A role of a containing group.
    """


class URIMember(ISpecificURI):
    """http://schooltool.org/ns/membership/member

    A group member role.
    """

class URIMembership(ISpecificURI):
    """http://schooltool.org/ns/membership

    The membership relationship.
    """

#
# Relationships
#

class ILink(ILocation):
    """A link is a 'view' of a relationship the relating objects have.

             A<--->Link<---->Relationship<---->Link<--->B

    """

    reltype = Attribute(
        """The SpecificURI of the relationship type.

        The value of reltype may be None.
        """)

    title = Attribute("""A title of the target of the link.""")

    role = Attribute(
        """The role implied by traversing this link.

        This is how the object got by traverse() relates to my __parent__.

        This attribute's value is an ISpecificURI.
        """)

    __parent__ = Attribute("The object at this end of the relationship")

    __name__ = Attribute("""Unique name within the parent's links""")

    def traverse():
        """Returns the object at the other end of the relationship.

        The object returned by traversing a link is known as the link's
        target.
        """


class IRemovableLink(ILink):

    def unlink():
        """Removes a link.

        Also removes the opposite direction of the relationship if the
        relationship is bidirectional.

        Sends a IRelationshipRemovedEvent to both previous participants
        of the relationship after the relationship has been broken.
        """

    def registerUnlinkCallback(callback):
        """Register an object that is notified after the link is unlinked.

        The callback must conform to IUnlinkHook and be pickleable.

        All callbacks will be unregistered when unlink is called.
        Callbacks are a set. If you register an identical callback more than
        once, it will still be called only once.
        """


class IUnlinkHook(Interface):

    def notifyUnlinked(link):
        """The given link was unlinked."""


class IPlaceholder(Interface):
    """A placeholder for a link."""

    def replacedBy(link):
        """The placeholder was replaced in the link set by the given link."""


class ILinkSet(Interface):
    """A set of links.

    Raises ValueError on an attempt to add duplicate members.

    Links with the same reltype, role and target are considered to be
    equal, for purposes of set membership.

    So, a link is a duplicate member if it has the same reltype, role and
    target as an existing member.
    """

    def add(link):
        """Add a link to the set.

        If an equivalent link (with the same reltype, role and target)
        already exists in the set, raises a ValueError.

        If an equivalent placeholder is in the set, replace the placeholder
        with the link, and call IPlaceholder.replacedBy(link).
        """

    def addPlaceholder(for_link, placeholder):
        """Add a placeholder to the set to fill the place of the given link.
        """

    def iterPlaceholders():
        """Returns an iterator over the placeholders in the set."""

    def remove(link_or_placeholder):
        """Remove a link or a placeholder from the set.

        If the given object is not in the set, raises a ValueError.
        The error is raised even if there is an equivalent link in the set.
        """

    def __iter__():
        """Return an iterator over the links in the set."""


class IRelatable(Interface):
    """An object which can take part in relationships."""

    __links__ = Attribute(
        """An object implementing ILinkSet.""")


class IQueryLinks(Interface):
    """An interface for querying a collection of links for those that
    meet certain conditions.
    """

    def listLinks(role=ISpecificURI):
        """Return all the links matching a specified role.

        Roles are matched by hierarchy (as interfaces).  The default
        argument of ISpecificURI therefore means 'all roles'.
        """


class IRelationshipValencies(Interface):
    """Gives information on what relationships are pertinent to this
    object.
    """

    def getValencies():
        """Returns a dictionary with tuples (relationship type URI,
        URI of a role of this object) as keys and IValency objects as
        values.
        """

class IValency(Interface):
    """An object describing a single valency"""

    schema = Attribute("""A relationship schema (IRelationshipSchema)""")

    this = Attribute(
        """A keyword argument the schema takes for this object""")

    other = Attribute(
        """A keyword argument the schema takes for the other object""")

class IRelationshipSchemaFactory(Interface):

    def __call__(relationship_type, optional_title, **roles):
        """Create an IRelationshipSchema of relationship_type.

        Use keyword arguments to say what roles are required when
        creating such a relationship.

        The relationship type must be given. However, the title is
        optional, and defaults to the URI of the relationship type.
        """


class IRelationshipSchema(Interface):
    """Object that represents a relationship."""

    type = Attribute("An ISpecificURI for the type of this relationship.")
    title = Attribute("The title of this relationship.")

    def __call__(**parties):
        """Relate the parties to the relationship.

        The objects are related according to the roles indicated
        by the keyword arguments.

        Returns a dict of {role_name: link}.
        """


class IRelationshipFactory:
    """Factory that establishes relationships of a certain type."""

    def __call__(relationship_type, (a, role_a), (b, role_b), title=None):
        """Relate a and b via the roles and the relationship type.

        Returns a tuple of links attached to a and b respectively.

        Sends a IRelationshipAddedEvent to both a and b after the
        relationship has been established.
        """


class IRelationshipAPI(Interface):

    def relate(relationship_type, (a, role_a), (b, role_b)):
        """Relate a and b via the roles and the relationship_type.

        Returns a tuple of links attached to a and b respectively.

        Sends a IRelationshipAddedEvent to both participants of the
        relationship after the relationship has been established.

        This function is implemented by looking up a relation factory
        by the relationship_type.

        Example::
                        my report
              /------------------------->
          officer  relationship_type  soldier
              <-------------------------/
                       my superior

        relate(URICommand,
               (officer, URIMySuperior),
               (soldier, URIMyReport))

        Returns a two-tuple of:
          * The link traversable from the officer, role is URIMyReport
          * The link traversable from the soldier, role is URIMySuperior

        If title is not given, the title links defaults to the
        relationship_type URI.
        """

    def getRelatedObjects(obj, role):
        """Return a sequence of object's relationships with a given role.

        Calling getRelatedObjects(obj, role) is equivalent to the following
        list comprehension::

            [link.traverse() for link in obj.listLinks(role)]
        """

    def registerRelationship(relationship_type, factory):
        """Register a relationship type.

        relationship_type is an ISpecificURI.
        factory is an IRelationshipFactory.

        This function does nothing if the same registration is
        attempted the second time.

        When IRelationshipAPI.relate is called, it will find the handler for
        the most specific relationship type and defer to that.
        """


#
# Events
#

class IEvent(Interface):
    """Base interface for events."""

    def dispatch(target):
        """Dispatches the event to target (which can propagate it further).

        Target must implement IEventTarget.

        On the first dispatch the event will also be sent to the global event
        service.

        It is guaranteed that no object will see the same event more than
        once, even if dispatch is called multiple times with the same target.
        """


class IRelationshipEvent(IEvent):
    """Base interface for relationship events"""

    links = Attribute("""Tuple containing the links of the relationship""")

class IRelationshipAddedEvent(IRelationshipEvent):
    """Event that gets sent out after a relationship has been established."""

class IRelationshipRemovedEvent(IRelationshipEvent):
    """Event that gets sent out after a relationship has been broken."""


class IMembershipEvent(IRelationshipEvent):
    """Base interface for membership events.

    This is a special case of IRelationshipEvent where one side has
    the role of URIGroup, and the other side has the role of URIMember.
    """

    group = Attribute("""The group""")
    member = Attribute("""The member""")

class IMemberAddedEvent(IRelationshipAddedEvent, IMembershipEvent):
    """Event that gets sent out after a member has been added to a group."""

class IMemberRemovedEvent(IRelationshipRemovedEvent, IMembershipEvent):
    """Event that gets sent out after a member has been removed from a group.
    """


class IEventTarget(Interface):
    """An object that can receive events."""

    def notify(event):
        """Handles the event.

        Event routing can be achieved by calling event.dispatch(other_target).
        """


class IEventService(IEventTarget):
    """Global event service.

    The global event service receives all events in the system and forwards
    them to the appropriate subscribers.
    """

    def subscribe(target, event_type):
        """Subscribe a target to receive events for a given event type.

        A target can be subscribed more than once for any given event_type, but
        in any case it will receive each event only once.
        """

    def unsubscribe(target, event_type):
        """Unsubscribe a target from receiving events for a given event
        type.

        event_type is treated as an exact type rather than the root of a
        hierarchy.  In other words, unsubscribing from IEvent will not remove
        any subscriptions for more specific event types.

        Raises ValueError if (target, event_type) is not subscribed.

        If target was subscribed multiple times for the same event type, it
        will need the same number of unsubscriptions in order to stop receiving
        that type of events.
        """

    def unsubscribeAll(target):
        """Unsubscribe all subscriptions for this target.

        Does nothing if target had no subscriptions.
        """

    def listSubscriptions():
        """Returns a list of all subscribers as (target, event_type) tuples."""


class IEventConfigurable(Interface):
    """An object that has a configurable event table."""

    eventTable = Attribute(
        """Sequence of event table rows, each implementing IEventAction""")


class IEventAction(Interface):
    """Represents an action to be taken for certain types of events."""

    eventType = Attribute("""Interface of an event this action pertains to""")

    def handle(event, target):
        """Handles the event for a given target.

        Should be called only if event is of an appropriate type.
        """


class ICallAction(IEventAction):
    """Event action that calls a callable."""

    callback = Attribute(
        """Callback that will be called with an event as its argument.""")


class ILookupAction(IEventAction):
    """Event action that looks up actions to be performed in another event
    table.
    """

    eventTable = Attribute(
        """Sequence of event table rows, each implementing IEventAction""")


class IRouteToRelationshipsAction(IEventAction):
    """Event action that routes this event to relationships of this object."""

    role = Attribute("""Role of the relationship""")


class IRouteToMembersAction(IEventAction):
    """Event action that routes this event to members of this object.

    This is equivalent to IRouteToRelationshipsAction with role URIMember.
    """


class IRouteToGroupsAction(IEventAction):
    """Event action that routes this event to groups of this object.

    This is equivalent to IRouteToRelationshipsAction with role URIGroup.
    """


#
# Facets
#

class IFacet(Interface):
    """A facet.

    A facet is a persistent adapter (a smart annotation) which
    implements some additional functionality and/or stores additional
    data.
    """

    active = Attribute("""The facet is active""")
    __parent__ = Attribute("""The object this facet is augmenting""")
    __name__ = Attribute("""Unique name within the parent's facets""")
    owner = Attribute(
        """The agent responsible for adding this facet to its __parent__""")


class IFacetedRelationshipSchemaFactory(Interface):

    def __call__(relationship_schema, **facet_factories):
        """Returns a faceted relationship schema."""


class IFacetedRelationshipSchema(IRelationshipSchema):
    """A relationship schema that sets facets on the parties after relating.
    """


class IFaceted(Interface):
    """Denotes that the object can have facets.
    """

    __facets__ = Attribute("""A set of facets that manages unique names.""")


class IFacetFactory(Interface):
    """An inspectible object that creates facets."""

    name = Attribute("The name of this factory")
    title = Attribute("Short description of this factory")

    def __call__():
        """Returns a facet."""


class IFacetManager(Interface):
    """A thing that manages the facets of some object."""

    def setFacet(facet, owner=None):
        """Set the facet on the object.

        Owner is the agent responsible for adding the facet.
        If owner is None, the ownership of the facet is not changed.

        facet.__name__ must be None before setting the facet.
        facet.__name__ will be set to a name unique within the set of facets.
        """

    def removeFacet(facet):
        """Remove the facet from the object."""

    def iterFacets():
        """Returns an iterator over facets of an object."""

    def facetsByOwner(owner):
        """Returns a sequence of all facets that are owned by owner."""

    def facetByName(name):
        """Returns the facet with the given name.

        Raises KeyError if there is no facet with that name.
        """


class IFacetAPI(Interface):
    """Facet API"""

    def FacetManager(obj):
        """Returns an IFacetManager for the given object.

        Raises TypeError if the object is not IFaceted.
        """

    def getFacetFactory(name):
        """Returns the factory with the given name."""

    def registerFacetFactory(factory):
        """Register the facet factory.

        factory must implement IFacetFactory
        """

    def iterFacetFactories():
        """Iterate over all registered facet factories."""

#
# Application objects
#

class IGroup(IFaceted, ILocation):
    """A set of group members.

    Participates in URIMembership as URIGroup or URIMember.
    """


class IPerson(IFaceted, ILocation):

    title = Attribute("Person's name")


class IApplication(IContainmentRoot, IServiceManager, ITraversable):
    """The application object.

    Services (as given by IServiceManager) are found by attribute.

    Root application objects are found by getRoots().

    Application object containers are found by __getitem__.
    """

    def getRoots():
        """Returns a sequence of root application objects."""

    def __getitem__(name):
        """Get the named application object container."""

    def keys():
        """List the names of application object containers."""


class IApplicationObjectContainer(ILocation, ITraversable):
    """A collection of application objects."""
    # XXX split this into read and write interfaces.

    def __getitem__(name):
        """Returns the contained object that has the given name."""

    def new(__name__=None, **kw):
        """Creates and returns a new contained object.

        If __name__ is None, a name is chosen for the object.
        Otherwise, __name__ is a unicode or seven bit safe string.
        The rest of the keyword arguments are passed to the object's
        constructor.

        If the given name is already taken, raises a KeyError.

        The contained object will be an ILocation, and will have this
        container as its __parent__, and the name as its __name__.
        """

    def __delitem__(name):
        """Removes the contained object that has the given name.

        Raises a KeyError if there is no such object.
        """

    def keys():
        """Returns a list of the names of contained objects."""


#
# Modules
#

class IModuleSetup(Interface):
    """Module that needs initialization"""

    def setUp():
        """Initializes the module."""


#
# Views
#

class IViewAPI(Interface):

    def getView(object):
        """Selects a view for an object by its interface.

        Returns a View object for obj.
        """

    def registerView(interface, factory):
        """Register a view for an interface."""

#
# Utilities
#

class IUtility(ILocation):
    """Utilities do stuff. They are managed by the utility service."""

    title = Attribute("Short descriptive text")


class IUtilityService(ILocation):
    """The utility service manages utilities."""

    def __getitem__(name):
        """Return the named utility."""

    def __setitem__(name, utility):
        """Add a new utility.

        The utility must provide IUtility, and will have the utility service
        set as its __parent__, and the name as its __name__.
        """

    def values():
        """Returns a list of utilities."""


#
# Exceptions
#

class ComponentLookupError(Exception):
    """An exception for component architecture."""

#
#  Configuration
#


def setUp():
    """See IModuleSetup"""
    from schooltool.component import registerURI
    registerURI(URIMembership)
    registerURI(URIMember)
    registerURI(URIGroup)

moduleProvides(IModuleSetup)
