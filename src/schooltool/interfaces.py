#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
SchoolTool package interfaces.

An interface is a formal description of the public API of an object (usually a
class instance, but sometimes a Python module as well).  Interfaces are
introspectable, that is, we can ask whether an object provides a specific
interface, or simply ask for a list of all interfaces that are provided by an
object.  As you've already gathered, a single object may provide more than one
interface.  Conversely, any given interface may be provided by many objects
that may be instances of completely unrelated classes.

We say that a class implements an interface if instances of that class provide
the interface.

Interfaces in SchoolTool are mostly used for documentation purposes.  One of
the reasons why they are all declared in a single module is to keep the
internal API documentation in one place, and to provide a coherent picture of
interactions between different objects.

$Id$
"""

__metaclass__ = type

from zope.interface import Interface, Attribute
from schooltool.unchanged import Unchanged  # reexport from here


#
# Containment
#

class IContainmentAPI(Interface):
    """Containment API.

    Many of the objects in SchoolTool form a hierarchy with the main
    application object at the top.  The root object (the application)
    provides the IContainmentRoot interface, branches and leaves provide
    ILocation.

    Every object (except the root) has a reference to its parent (also known
    as its container), and a name.  Often you can traverse a container to get
    an object when you know its name (this is not always implemented, though):

       >>> container = obj.__parent__
       >>> name = obj.__name__
       >>> traverse(container, name) is obj
       True

    Every object has a unique path.  Given a path, you can get the object
    at that path by traversing the root object:

       >>> root = getRoot(obj)
       >>> path = getPath(obj)
       >>> obj is traverse(root, path)
       True

    """

    def getPath(obj):
        """Return the unique path of an object in the containment hierarchy.

        The object must implement ILocation or IContainmentRoot and must be
        attached to the hierarchy (i.e. following parent references should not
        reach None).  If either of those conditions is not met, raises a
        TypeError.

        The path of the root object is '/'.  The path of first-level objects
        (those that have the root object as their parent) is '/' + the name
        of the object.  The path of any other object is the path of the parent
        object + '/' + the name of the object, except when the parent
        implements IMultiContainer.  See also IMultiContainer.
        """

    def getRoot(obj):
        """Return the containment root for obj.

        The object must implement ILocation or IContainmentRoot and
        must be attached to the hierarchy (i.e. following parent
        references should not reach None).  If either of those
        conditions is not met, raises a TypeError.
        """

    def traverse(obj, path):
        """Return the object accessible as path from obj.

        Path is a list of names separated with forward slashes.  Multiple
        adjacent slashes are equivalent to a single slash.  Special names
        are '.' and '..'; they are treated as is customary in file systems.
        Traversing to '..' at the root keeps you at the root.

        If path starts with a slash, then the traversal starts from
        getRoot(obj), otherwise the traversal starts from obj.

        Traversing to '..' requires the object to provide either ILocation
        or IContainmentRoot.  Traversing to a non-empty name requires the
        object to provide ITraversable.
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

    Use this interface when the intermediate container is a dumb one (e.g. a
    Python dict) that does not provide ILocation/ITraversable.  For example,
    imagin ea hyphotetical LunchBox object located at /lunchbox that has
    two kinds of children:

      - food items (e.g. sandwitch), stored in an dict LunchBox.food
      - insects (e.g. ant), stored in a dict LunchBox.insects

    We want the foot items to have paths like /lunchbox/food/sandwitch, and
    insects to have paths like /lunchbox/insects/ant.  To achieve this we
    can set the __parent__ of both the sandwitch and the ant to refer directly
    to the lunchbox, and then make the LunchBox a multi-container:

        class LunchBox:
            implements(ILunchBox, IMultiContainer)

            def getRelativePath(self, obj):
                if obj in self.food.values():
                    return 'food/%s' % obj.__name__
                else:
                    return 'insects/%s' % obj.__name__

    Traversal of multi-containers is complicated and usually not implemented
    (i.e. the objects providing IMultiContainer usually do not provide
    ITraversal).

    We actually use this to make an object be able to tell the correct way to
    traverse to its relationships or facets.  Traversal in those cases is
    hardcoded in view classes, and not with ITraversal interfaces.
    """

    def getRelativePath(child):
        """Return the path of child relative to self.

        The relative path may contain several path segments separated by
        slashes, but it should not start nor end with a slash.
        """


#
# Services
#

class IServiceAPI(Interface):
    """Service API.

    There are a number of global services stored in the object database.  This
    API lets the code access those services.  The context argument passed to
    each of the functions in this API is an object connected to the containment
    hierarchy.  Looking up a service entails traversing up the chain of object
    parents until an object providing IServiceManager is found (usually this
    will be the root object).

    Every service has its own API defined in a separate interface.
    """

    def getEventService(context):
        """Return the global event service."""

    def getUtilityService(context):
        """Return the global utility service."""

    def getTimetableSchemaService(context):
        """Return the global timetable schema service."""

    def getTimePeriodService(context):
        """Return the global time period service."""

    def getTicketService(context):
        """Return the ticket service for authentication."""

    def getOptions(context):
        """Return an IOptions object found from the context."""


class IServiceManager(Interface):
    """Container of services"""

    eventService = Attribute("""Event service for this application""")

    utilityService = Attribute("""Utility service for this application""")

    timetableSchemaService = Attribute("""Timetable schema service""")

    timePeriodService = Attribute("""Time period service""")

    ticketService = Attribute("""Ticket service""")


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
        """Return a list of utilities."""


#
# URIs
#

class IURIObject(Interface):
    """An opaque identifier of a role or a relationship type.

    Roles and relationships are identified by URIs in XML representation.
    URI objects let the application assign human-readable names to roles
    and relationship types.

    URI objects are equal iff their uri attributes are equal.
    """

    uri = Attribute("""URI (as a string).""")

    name = Attribute("""Human-readable name.""")

    description = Attribute("""Human-readable description.""")


class IURIAPI(Interface):

    def registerURI(uri):
        """Add a URI to the registry so it can be queried by the URI string."""

    def getURI(str):
        """Return an URI object for a given URI string."""

    def verifyURI(uri):
        """Raise TypeError if the argument is not an IURIObject."""

    def listURIs():
        """Return a list of all registered URIObjects."""


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

        This attribute's value is an IURIObject.
        """)

    __parent__ = Attribute("""The object at this end of the relationship.""")

    __name__ = Attribute("""Unique name within the parent's links.""")

    def traverse():
        """Return the object at the other end of the relationship.

        The object returned by traversing a link is known as the link's target.
        """


class IRemovableLink(ILink):

    def unlink():
        """Remove a link.

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
        """Return an iterator over the placeholders in the set."""

    def remove(link_or_placeholder):
        """Remove a link or a placeholder from the set.

        If the given object is not in the set, raises a ValueError.
        The error is raised even if there is an equivalent link in the set.
        """

    def __iter__():
        """Return an iterator over the links in the set."""

    def getLink(name):
        """Returns a link by a name"""


class IRelatable(Interface):
    """An object which can take part in relationships."""

    __links__ = Attribute("""An object implementing ILinkSet.""")

    def getLink(name):
        """Returns a link by a name within this relatable"""


class IQueryLinks(Interface):
    """An interface for querying a collection of links for those that
    meet certain conditions.
    """

    def listLinks(role=None):
        """Return all the links (matching a specified role, if specified)."""


class IRelationshipValencies(Interface):
    """Gives information on what relationships are pertinent to this
    object.
    """

    valencies = Attribute("""A tuple of IValency objects""")

    def getValencies():
        """Return a mapping of valencies.

        The return value is a dictionary with tuples containing the
        relationship type (as an IURIObject) and the role of this
        object (also an IURIObject) as keys, and ISchemaInvocation
        objects as values.
        """


class ISchemaInvocation(Interface):
    """An object describing how to call a relationship schema for a valency"""

    schema = Attribute("""A relationship schema (IRelationshipSchema)""")

    this = Attribute(
        """A keyword argument the schema takes for this object""")

    other = Attribute(
        """A keyword argument the schema takes for the other object""")


class IValency(Interface):
    """An object signifying that the owner can participate in a
    certain relationship schema in a certain role.
    """

    schema = Attribute("""A relationship schema (IRelationshipSchema)""")

    keyword = Attribute(
        """A keyword argument the schema takes for this object""")


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

    type = Attribute("An IURIObject for the type of this relationship.")

    roles = Attribute(
        """A mapping of symbolic parameter names this schema expects
        to respective URIs""")

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

        relationship_type is an IURIObject (or None if you're registering the
        default handler).

        factory is an IRelationshipFactory.

        This function does nothing if the same registration is attempted the
        second time.

        When IRelationshipAPI.relate is called, it will find the handler for
        the relationship type (falling back to the default handler) and defer
        to that.
        """


#
# Events
#

class IEvent(Interface):
    """Base interface for events."""

    def dispatch(target):
        """Dispatch the event to target (which can propagate it further).

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
        """Handle the event.

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
        """Return a list of all subscribers as (target, event_type) tuples."""


class IEventConfigurable(Interface):
    """An object that has a configurable event table."""

    eventTable = Attribute(
        """Sequence of event table rows, each implementing IEventAction""")


class IEventAction(Interface):
    """Represents an action to be taken for certain types of events."""

    eventType = Attribute("""Interface of an event this action pertains to""")

    def handle(event, target):
        """Handle the event for a given target.

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

class IFacet(ILocation):
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
        """Return a faceted relationship schema."""


class IFacetedRelationshipSchema(IRelationshipSchema):
    """A relationship schema that sets facets on the parties after relating.
    """


class IFaceted(Interface):
    """Denotes that the object can have facets."""

    __facets__ = Attribute("""A set of facets that manages unique names.""")


class IFacetFactory(Interface):
    """An inspectable object that creates facets."""

    name = Attribute("The name of this factory")
    title = Attribute("Short description of this factory")
    facet_name = Attribute(
        """The __name__ the facet will get if it is a singleton facet.
        None if the facet is not a singleton facet.""")

    def __call__():
        """Return a facet."""


class IFacetManager(Interface):
    """A thing that manages the facets of some object."""

    def setFacet(facet, owner=None, name=None):
        """Set the facet on the object.

        Owner is the agent responsible for adding the facet.
        If owner is None, the ownership of the facet is not changed.

        facet.__name__ must be None before setting the facet.
        facet.__name__ will be set to a name unique within the set of facets,
        if the name argument is None.  Otherwise facet.__name__ will be
        set to the name provided in the argument, if it is possible (no other
        facet has the same name), or a ValueError will be raised if it is not.
        """

    def removeFacet(facet):
        """Remove the facet from the object."""

    def iterFacets():
        """Return an iterator over facets of an object."""

    def facetsByOwner(owner):
        """Return a sequence of all facets that are owned by owner."""

    def facetByName(name):
        """Return the facet with the given name.

        Raises KeyError if there is no facet with that name.
        """


class IFacetAPI(Interface):
    """Facet API"""

    def FacetManager(obj):
        """Return an IFacetManager for the given object.

        Raises TypeError if the object is not IFaceted.
        """

    def getFacetFactory(name):
        """Return the factory with the given name."""

    def registerFacetFactory(factory):
        """Register the facet factory.

        factory must implement IFacetFactory
        """

    def iterFacetFactories():
        """Iterate over all registered facet factories."""


#
# Access control
#

# Tell i18nextractor that permission names are translatable
_ = lambda s: s

ViewPermission = _('View')
AddPermission = _('Add')
ModifyPermission = _('Modify')

Everybody = _('Everybody')

del _


class IACL(Interface):
    """Access control list.

    Access control lists store and manage tuples of (principal, permission).
    Permission can be one of View, Add, and Modify.
    """

    def __iter__():
        """Iterate over tuples of (principal, permission)"""

    def __contains__((principal,  permission)):
        """Returns whether the principal, permission pair is in ACL."""

    def add((principal, permission)):
        """Grants the permission to a principal"""

    def remove((principal, permission)):
        """Revokes the permission from a principal.

        Raises KeyError if the principal does not have the permission.
        """

    def allows(principal, permission):
        """Return whether the principal has the permission.

        Contrary to __contains__, also returns True if the special
        principal Everybody has the permission.
        """

    def clear():
        """Remove all access from all principals"""


class IACLOwner(Interface):
    """An object that has an ACL"""

    acl = Attribute("""The ACL for this calendar.""")


#
# Calendaring
#

class IDateRange(Interface):
    """A range of dates (inclusive).

    If r is an IDateRange, then the following invariant holds:
    r.first <= r.last

    Note that empty date ranges cannot be represented.
    """

    first = Attribute("""The first day of the period of time covered.""")

    last = Attribute("""The last day of the period covered.""")

    def __iter__():
        """Iterate over all dates in the range from the first to the last."""

    def __contains__(date):
        """Return True if the date is within the range, otherwise False.

        Raises a TypeError if date is not a datetime.date.
        """

    def __len__():
        """Return the number of dates covered by the range."""


class ISchooldayModel(IDateRange):
    """A calendar which can tell whether a day is a school day or not
    for a certain period of time.
    """

    def isSchoolday(date):
        """Return whether the date is a schoolday.

        Raises a ValueError if the date is outside of the period covered.
        """


class ISchooldayModelWrite(Interface):

    def add(day):
        """Mark the day as a schoolday.

        Raises a ValueError if the date is outside of the period covered.
        """

    def remove(day):
        """Mark the day as a holiday.

        Raises a ValueError if the date is outside of the period covered.
        """

    def addWeekdays(*weekdays):
        """Mark that all days of week with a number in weekdays within the
        period will be schooldays.

        The numbering used is the same as one used by
        datetime.date.weekday() method, or the calendar module:
        0 is Monday, 1 is Tuesday, etc.
        """

    def removeWeekdays(*weekdays):
        """Mark that all days of week with a number in weekdays within the
        period will be holidays.

        The numbering used is the same as one used by
        datetime.date.weekday() method, or the calendar module.
        0 is Monday, 1 is Tuesday, etc.
        """

    def toggleWeekdays(*weekdays):
        """Toggle the state of all days of week with a number in weekdays.

        The numbering used is the same as one used by
        datetime.date.weekday() method, or the calendar module.
        0 is Monday, 1 is Tuesday, etc.
        """

    def reset(first, last):
        """Change the period and mark all days as holidays.

        If first is later than last, a ValueError is raised.
        """


class ICalendar(Interface):
    """A calendar, containing days which in turn contain events."""

    def __iter__():
        """Return an iterator over the events in this calendar."""

    def find(unique_id):
        """Return an event with the given unique id.

        Raises a KeyError if there is no event with this id.
        """

    def byDate(date):
        """Return an ICalendar for the given date.

        All events that overlap with the given day are included.  The timing of
        the events is not modified even if it falls outside the given date.
        """

    def expand(first, last):
        """Expand recurring events.

        Returns an ICalendar with all the IExpandedCalendarEvents in
        that occur in the given date range.  Recurrences of all events
        in the calendar happening during the specified period are
        included.
        """


class ICalendarWrite(Interface):
    """Writable calendar."""

    def clear():
        """Remove all events."""

    def addEvent(event):
        """Add an event to the calendar."""

    def removeEvent(event):
        """Remove event from the calendar."""

    def update(calendar):
        """Add all events from another calendar."""


class IACLCalendar(ICalendarWrite, IACLOwner):
    """A calendar that has an ACL."""


class IRecurrenceRule(Interface):
    """Base interface of the recurrence rules."""

    interval = Attribute(
        """Interval of recurrence (a positive integer).

        For example, for yearly recurrence the interval equal to 2
        will indicate that the event will recur once in two years.
        """)

    count = Attribute(
        """Number of times the event is repeated.

        Can be None or an integer value.  If count is not None then
        until must be None.  If both count and until are None the
        event repeats forever.
        """)

    until = Attribute(
        """The date of the last recurrence of the event.

        Can be None or a datetime.date instance.  If until is not None
        then count must be None.  If both count and until are None the
        event repeats forever.
        """)

    exceptions = Attribute(
        """A list of days when this event does not occur.

        Values in this list must be instances of datetime.date.
        """)

    def replace(interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged):
        """Return a copy of this recurrence rule with new specified fields."""

    def apply(event, enddate=None):
       """Apply this rule to an event.

       This is a generator function that returns the dates on which
       the event should recur.  Be careful when iterating over these
       dates -- rules that do not have either 'until' or 'count'
       attributes will go on forever.

       The optional enddate attribute can be used to set a range on
       the dates generated by this function (inclusive).
       """

    def __eq__(other):
        """See if self == other."""

    def __ne__(other):
        """See if self != other."""

    def __hash__():
        """Return the hash value of this recurrence rule.

        It is guaranteed that if recurrence rules compare equal, hash will
        return the same value.
        """

    def iCalRepresentation(dtstart):
        """Return the rule in iCalendar format.

        Returns a list of strings.

        dtstart is a datetime representing the date that the recurring
        event starts on.
        """


class IDailyRecurrenceRule(IRecurrenceRule):
    """Daily recurrence."""


class IYearlyRecurrenceRule(IRecurrenceRule):
    """Yearly recurrence."""


class IWeeklyRecurrenceRule(IRecurrenceRule):

    weekdays = Attribute(
        """A set of weekdays when this event occurs.

        Weekdays are represented as integers from 0 (Monday) to 6 (Sunday).

        The event repeats on the weekday of the first occurence even
        if that weekday is not in this set.
        """)

    def replace(interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, weekdays=Unchanged):
        """Return a copy of this recurrence rule with new specified fields."""


class IMonthlyRecurrenceRule(IRecurrenceRule):

    monthly = Attribute(
        """Specification of a monthly occurence.

        Can be one of three values: 'monthday', 'weekday', 'lastweekday',
        or None.

        'monthday'    specifies that the event recurs on the same
                      monthday.

        'weekday'     specifies that the event recurs on the same week
                      within a month on the same weekday, indexed from the
                      first (e.g. 3rd friday of a month).

        'lastweekday' specifies that the event recurs on the same week
                      within a month on the same weekday, indexed from the
                      end of month (e.g. 2nd last friday of a month).
        """)

    def replace(interval=Unchanged, count=Unchanged, until=Unchanged,
                exceptions=Unchanged, monthly=Unchanged):
        """Return a copy of this recurrence rule with new specified fields."""


class ICalendarEvent(Interface):
    """A calendar event.

    Calendar events are immutable, hashable and comparable.  Events are
    compared in chronological order (i.e., if e1 and e2 are events, then
    e1.dtstart < e2.dtstart implies e1 < e2.  If events start at the same
    time, their relative ordering is determined lexicographically comparing
    their titles.
    """

    unique_id = Attribute("""A globally unique id for this calendar event.""")
    dtstart = Attribute("""The datetime.datetime of the start of the event.""")
    duration = Attribute("""The duration of the event (datetime.timedelta).""")
    title = Attribute("""The title of the event.""")
    owner = Attribute("""The object that created this event.""")
    context = Attribute(
        """The object in whose calendar this event lives.

        For example, when booking resources, the person who's booking
        will be the owner of the booking event, and the resource will
        be the context.
        """)
    location = Attribute(
          """The title of the location where this event takes place.""")
    recurrence = Attribute(
        """The recurrence rule.

        A value providing IRecurrenceRule.  None if the event is not
        recurrent.
        """)
    privacy = Attribute(
        """One of "public", "private", or "hidden".

        Event that are "private" will be rendered as busy blocks to
        other users, and events that are "hidden" will not be shown to
        other users at all.

        "public" is the default.
        """)

    replace_kw = Attribute(
        """A sequence of keywords that can be passed to replace()""")

    def replace(**kw):
        """Return a calendar event with new specified fields."""

    def __eq__(other): """See if self == other."""
    def __ne__(other): """See if self != other."""
    def __lt__(other): """See if self < other."""
    def __gt__(other): """See if self > other."""
    def __le__(other): """See if self <= other."""
    def __ge__(other): """See if self >= other."""

    def __hash__():
        """Return the hash value of this event.

        It is guaranteed that if calendar events compare equal, hash will
        return the same value.
        """

    def hasOccurrences():
        """Does the event have any occurrences?

        Normally all events have at least one occurrence.  However if you have
        a repeating event that repeats a finite number of times, and all those
        repetitions are listed as exceptions, then hasOccurrences() will return
        False.
        """


class IExpandedCalendarEvent(ICalendarEvent):
    """A calendar event that may be a recurrence of a recurrent event."""


class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Attribute(
        """The object's calendar.""")

    composite_cal_groups = Attribute(
        """A list of groups whose calendars will be included in the composite
           calendar.
        """) # XXX Relationships should be used here.

    def makeCompositeCalendar():
        """Return the composite calendar for this person.

        Returns a calendar that contains all events from every group in
        composite_cal_groups. (XXX relationships)
        """


#
# Timetabling
#

class ITimetable(Interface):
    """A timetable.

    A timetable is an ordered collection of timetable days that contain
    periods. Each period either contains a class, or is empty.

    A timetable represents the repeating lesson schedule for just one
    pupil, or one teacher, or one bookable resource.
    """

    model = Attribute(
        """A timetable model this timetable should be used with.""")

    exceptions = Attribute(
        """A list of timetable exceptions (ITimetableExceptionList).""")

    def keys():
        """Return a sequence of identifiers for days within the timetable.

        The order of day IDs is fixed.
        """

    def items():
        """Return a sequence of tuples of (day_id, ITimetableDay).

        The order of day IDs is fixed and is the same as returned by keys().
        """

    def __getitem__(key):
        """Return a ITimetableDay for a given day id."""

    def itercontent():
        """Iterate over all activites in this timetable.

        Return an iterator for tuples (day_id, period_id, activity).
        """

    def cloneEmpty():
        """Return a new empty timetable with the same structure.

        The new timetable has the same set of day_ids, and the sets of
        period ids within each day.  It has no activities nor exceptions.
        """

    def __eq__(other):
        """Is this timetable equal to other?

        Timetables are equal iff they have the same model, set of exceptions,
        set of day IDs, and their corresponding days are equal.

        Returns False if other is not a timetable.
        """

    def __ne__(other):
        """Is this timetable different from other?

        The opposite of __eq__.
        """


class ITimetableWrite(Interface):

    def __setitem__(key, value):
        """Set an ITimetableDay for a given day id.

        Throws a TypeError if the value does not implement ITimetableDay.
        Throws a ValueError if the key is not a valid day id.
        """

    def clear():
        """Remove all activities for all periods."""

    def update(timetable):
        """Add all the events and exceptions from timetable to self.

        Useful for producing combined timetables.
        """


class ITimetableDay(Interface):
    """A day in a timetable.

    A timetable day is an ordered collection of periods that each have
    a set of activites that occur during that period.

    Different days within the same timetable may have different periods.
    """

    timetable = Attribute("""The timetable that contains this day.""")

    periods = Attribute("""A list of periods IDs for this day.""")

    def keys():
        """Return self.periods."""

    def items():
        """Return a sequence of tuples (period_id, set_of_ITimetableActivity).
        """

    def __getitem__(key):
        """Return the set of ITimetableActivities for a given period.

        If there is no activity for the period, an empty set is returned.
        """

    def __eq__(other):
        """Return True iff other is a TimetableDay with the same set of
        periods and with the same activities scheduled for those periods.
        """

    def __ne__(other):
        """Return True iff __eq__ returns False."""


class ITimetableDayWrite(Interface):
    """Writable timetable day.

    Note that all clients which use ITimetableDayWrite or ITimetableWrite
    to modify timetables should maintain the following invariant:
     - every TimetableActivity is present in the timetable of its owner
       and all the timetables of its resources.
    """

    def clear(period):
        """Remove all the activities for a certain period id."""

    def add(period, activity):
        """Adds a single activity to the set of activities planned for
        a given period.
        """

    def remove(period, value):
        """Remove a certain activity from a set of activities planned
        for a given period.
        """


class ITimetableActivity(Interface):
    """An event in a timetable.

    Something that happens on a certain period_id in a certain
    day_id.

    Timetable activities are immutable and can be hashed or compared for
    equality.
    """

    title = Attribute("""The title of the activity.""")

    owner = Attribute(
        """The group or person or other object that owns the activity.

        The activity lives in the owner's timetable.
        """)

    resources = Attribute("""A set of resources assigned to this activity.

        The activity is also present in the timetables of all resources
        assigned to this activity.
        """)

    timetable = Attribute("""The timetable that contains this activity.

        This attribute refers to the timetable of `owner`.  It never refers
        to a composite timetable or a timetable of a resource.
        """)

    def replace(title=Unchanged, owner=Unchanged, resources=Unchanged,
                timetable=Unchanged):
        """Return a copy of this activity with some fields changed."""

    def __eq__(other):
        """Is this timetable activity equal to `other`?

        Timetable activities are equal iff their title, owner and resources
        attributes are equal.

        Returns false if other is not a timetable activity.
        """

    def __ne__(other):
        """Is this timetable activity different from `other`?

        The opposite of __eq__.
        """

    def __hash__():
        """Calculate the hash value of a timetable activity."""


class ITimetableExceptionList(Interface):
    """A list of timetable exceptions.

    All items in this list are objects providing ITimetableException.
    """

    def __iter__():
        """Iterate over all timetable exceptions."""

    def __len__():
        """Return the number of exceptions in the list."""

    def __getitem__(index):
        """Return the n-th exception in the list."""

    def __eq__(other):
        """Is this list equal to other?"""

    def __ne__(other):
        """Is this list not equal to other?"""

    def append(exception):
        """Add a timetable exception.

        Sends an ITimetableExceptionAddedEvent to the __parent__ of the
        timetable, if the timetable provides ILocation, and its __parent__
        provides IEventTarget.
        """

    def remove(exception):
        """Remove a timetable exception.

        Sends an ITimetableExceptionAddedEvent to the __parent__ of the
        timetable, if the timetable provides ILocation, and its __parent__
        provides IEventTarget.
        """

    def extend(exceptions):
        """Extend the list with new exceptions.

        This method should only be used for constructing composite timetables.
        It does not send any events.
        """


class ITimetableException(Interface):
    """An exception in a timetable.

    An exception specifies that on a particular day a particular activity
    either does not occur, or occurs but at a different time, or is replaced
    by a different activity.
    """

    date = Attribute("""Date of the exception (a datetime.date instance).""")

    period_id = Attribute("""ID of the period that is exceptional.""")

    activity = Attribute(
        """The activity that does not occur (ITimetableActivity).""")

    replacement = Attribute(
        """Calendar event that should replace the exceptional activity.

        If None, then the activity is simply removed.

        If not None, then replacement is a IExceptionalTTCalendarEvent.
        """)

    def __eq__(other):
        """See if self == other."""

    def __ne__(other):
        """See if self != other."""


class ITimetableExceptionEvent(IEvent):
    """Base interface for timetable exception events."""

    timetable = Attribute("""The timetable.""")
    exception = Attribute("""The timetable exception.""")


class ITimetableExceptionAddedEvent(ITimetableExceptionEvent):
    """Event that gets sent when an exception is added to a timetable."""


class ITimetableExceptionRemovedEvent(ITimetableExceptionEvent):
    """Event that gets sent when an exception is removed from a timetable."""


class ITimetableCalendarEvent(ICalendarEvent):
    """A calendar event that has been created from a timetable."""

    period_id = Attribute(
        """The period id of the corresponding timetable event.""")

    activity = Attribute(
        """The activity from which this event was created.""")


class IExceptionalTTCalendarEvent(ICalendarEvent):
    """A calendar event that replaces a particular timetable event."""

    exception = Attribute(
        """The exception in which this event is stored.

        An ITimetableException.
        """)


class ICompositeTimetableProvider(Interface):
    """An object which knows how to get the timetables for composition
    """

    timetableSource = Attribute(
        """A specification of how the timetables of related object
        should be composed together to provide a composed timetable of
        this object.

        Actually it is a sequence of tuples with the following members:

               link_role    The role URI of a link to traverse
               composed     A boolean value specifying whether to use
                            the composed timetable, otherwise private.
        """)


class ITimetabled(Interface):
    """A facet or an object that has a timetable related to it --
    either its own, or composed of the timetables of related objects.
    """

    timetables = Attribute(
        """A mapping of private timetables of this object.

        The keys of this mapping are tuples of
        (time_period_id, timetable_schema_id), e.g.
        ('2004-autumn-semester', 'weekly')

        These timetables can be directly manipulated.  Adding, changing
        or removing a timetable will result in a ITimetableReplacedEvent
        being sent.

        For a lot of objects this mapping will be empty.  Instead, they
        will inherit timetable events through composition (see
        getCompositeTimetable).
        """)

    def getCompositeTimetable(time_period_id, tt_schema_id):
        """Return a composite timetable for a given object with a
        given timetable schema for a given time period id.

        The timetable returned includes the events from the timetables
        of parent groups, groups taught, etc.

        This function can return None if the object has no timetable.
        """

    def listCompositeTimetables():
        """Return a sequence of (time_period_id, tt_schema_id) for all
        available composite timetables.
        """

    def makeTimetableCalendar():
        """Generate and return a calendar from all composite timetables."""


class ITimetableReplacedEvent(IEvent):
    """Event that gets sent when a timetable is replaced."""

    object = Attribute("""ITimetabled.""")
    key = Attribute("""Tuple (time_period_id, schema_id).""")
    old_timetable = Attribute("""The old timetable (can be None).""")
    new_timetable = Attribute("""The new timetable (can be None).""")


class ISchooldayTemplate(Interface):
    """A school-day template represents the times that periods are
    scheduled during a prototypical school day.

    Some schools need only one school-day template. For example, they
    have seven periods in a day, and the periods are always in the
    sequence 1 to 7, and start and end at the same time on each school
    day.

    Other schools will need more than one school-day template. For
    example, a school that has shorter school days on Wednesdays will
    have one template for Wednesdays, and one other template for
    Monday, Tuesday, Thursday and Friday.

    Other schools will want to re-order the periods on different days,
    so they will have one template with periods ABCDEF in that order,
    and another template with periods DEFABC.
    """

    def __iter__():
        """Return an iterator over the ISchooldayPeriods of this template."""


class ISchooldayTemplateWrite(Interface):

    def add(obj):
        """Add an ISchooldayPeriod to the template.

        Raises a TypeError if obj is not an ISchooldayPeriod."""

    def remove(obj):
        """Remove an object from the template."""


class ISchooldayPeriod(Interface):
    """An object binding a timetable period to a concrete time
    interval within a schoolday template.
    """

    title = Attribute("Period id of this event")
    tstart = Attribute("datetime.time of the start of the event")
    duration = Attribute("datetime.timedelta of the duration of the event")

    def __eq__(other):
        """SchooldayPeriods are equal if all three of their
        attributes are equal.

        Raises TypeError if other does not implement ISchooldayPeriod.
        """

    def __ne__(other):
        """SchooldayPeriods are not equal if any of their three
        attributes are not equal.

        Raises TypeError if other does not implement ISchooldayPeriod.
        """

    def __hash__():
        """Hashes of ISchooldayPeriods are equal iff those
        ISchooldayPeriods are equal.
        """


class ITimetableModel(Interface):
    """A timetable model knows how to create an ICalendar object when
    it is given a School-day model and a Timetable.

    The implementation of the timetable model knows how to arrange
    timetable days within the available school days.

    For example, a school with four timetable days 1, 2, 3, 4 has its
    timetable days laid out in sequence across consecutive school
    days. A school with a timetable days for Monday through Friday has
    its timetable days laid out to match the day of the week that a
    school day occurs on.

    The ICalendar produced will use an appropriate school-day template
    for each day, depending on (for example) what day of the week that
    day occurs on, or whatever other rules the implementation of the
    timetable model is coded to use.
    """

    timetableDayIds = Attribute(
        """Return a sequence of day_ids which can be used in the timetable.""")

    dayTemplates = Attribute(
        """A mapping of weekdays (calendar.MONDAY,...) to ISchooldayTemplates.

        The template with the key of None is used if there is no template
        for a particular weekday.
        """)

    def createCalendar(schoolday_model, timetable):
        """Return an ICalendar composed out of schoolday_model and timetable.

        This method has model-specific knowledge as to how schooldays,
        weekends and holidays map affect the mapping of the timetable
        onto the real-world calendar.
        """


class ITimetableModelRegistry(Interface):
    """A registry of timetable model classes present in the system.

    The timetable model classes are identified by the dotted class names.
    """

    def getTimetableModel(id):
        """Return a timetable schema identified by a given id."""

    def registerTimetableModel(id, factory):
        """Register a timetable schema identified by a given id."""

    def listTimetableModels():
        """Return a sequence of keys of the timetable models in the
        registry."""


class ITimetableSchemaService(ILocation):
    """Service for creating timetables of a certain schema.

    This service stores timetable prototypes (empty timetables) and
    can return a new timetable of a certain schema on request.
    """

    def keys():
        """Return a sequence of all stored schema ids."""

    def __getitem__(schema_id):
        """Return a new empty timetable of a given schema."""

    def __setitem__(schema_id, timetable):
        """Store a given timetable as a schema with a given id."""

    def __delitem__(schema_id):
        """Remove a stored schema with a given id."""


class ITimePeriodService(ILocation):
    """Service for registering time periods.

    It stores schoolday models for registered time period IDs.
    """

    def keys():
        """Return a sequence of all time period ids."""

    def __contains__(period_id):
        """Return True iff period with this id is defined."""

    def __getitem__(period_id):
        """Return the schoolday model for this time period."""

    def __setitem__(period_id, schoolday_model):
        """Store a schoolday model for this time period."""

    def __delitem__(period_id):
        """Remove the specified time period."""


#
# Application objects
#

class IAvailabilitySearch(Interface):
    """An interface for querying the availability of resources."""

    def getFreeIntervals(first, last, time_periods, duration):
        """Return all intervals of time not shorter than duration
        when the object is free within a range of dates [first, last]
        during the times of day specified by time_periods.

        first, last    datetime.datetime objects specifying a range of
                       dates.

        time_periods   a sequence of tuples (start_time, duration)
                       specifying the time of day.  These are
                       respectively datetime.time and
                       datetime.timedelta objects

        duration       datetime.timedelta object specifying a minimum
                       interval of time we're searching for.

        The returned value is a sequence of tuples (start_datetime, duration).
        """


class IApplicationObject(ILocation, IRelatable, IEventTarget,
                         IEventConfigurable, IFaceted, ICalendarOwner,
                         ITimetabled, IAvailabilitySearch, IACLOwner):
    """A collection of interfaces common to all application objects."""

    title = Attribute("""Title of the application object""")


class IGroup(IApplicationObject):
    """A set of group members.

    Participates in URIMembership as URIGroup or URIMember.
    """


class IPerson(IApplicationObject):
    """A person.

    Participates in URIMembership as URIMember.
    """

    title = Attribute("""Person's full name""")

    username = Attribute("""The username of this person""")

    def iterAbsences():
        """Iterate over all absences."""

    def getAbsence(key):
        """Return the absence with a given key."""

    def getCurrentAbsence():
        """Return the current absence or None.

        At any given time a person can have at most one absence that is not
        ended.  It is called the current absence.
        """

    def reportAbsence(comment):
        """Report that this person is absent, still absent, or no
        longer absent.

        Returns the IAbsence which may be a new absence or this
        person's current absence extended by the comment.
        """

    def setPassword(password):
        """Set the password in a hashed form, so it can be verified later."""

    def checkPassword(password):
        """Check if the provided password is the same as the one set
        earlier using setPassword.

        Returns True if the passwords match.
        """

    def hasPassword():
        """Check if the user has a password.

        You can remove user's password (effectively disabling the account) by
        passing None to setPassword.  You can reenable the account by passing
        a new password to setPassword.
        """


class IResource(IApplicationObject):
    """A bookable resource used in."""


class IAbsence(ILocation):
    """Absence object.

    The __parent__ of an absence is its person.  The absence can be
    located in IPersons.absences by its __name__.

    All attributes are read-only.  They can be changed by adding new
    comments, therefore the list of comments also doubles as an audit log.
    """

    person = Attribute("""Person that was absent""")
    comments = Attribute("""Comments (a sequence of IAbsenceComment)""")
    ended = Attribute("""Has this absence been ended?""")
    resolved = Attribute("""Has this absence been resolved?""")
    expected_presence = Attribute(
        """Date and time after which the person is expected to be present""")

    def addComment(comment):
        """Add a comment.

        Sends out an IAbsenceEvent after the comment has been added.  The
        event is sent to the person and all application objects that the person
        was absent from.
        """


class IAbsenceComment(Interface):

    __parent__ = Attribute("""The absence this comment belongs to""")
    datetime = Attribute("""Date and time of the comment""")
    reporter = Attribute("""Person that made this comment""")
    text = Attribute("""Text of the comment""")
    absent_from = Attribute(
        """Application object (group or whatever) the person was absent
        from (can be None)""")
    ended = Attribute(
        """New value of ended (True, False or Unchanged)""")
    resolved = Attribute(
        """New value of resolved (True, False or Unchanged)""")
    expected_presence = Attribute(
        """New value of expected_presence (datetime, None, or Unchanged)""")


class IAttendanceEvent(IEvent):
    """Event that gets sent out when an absence is recorded or updated."""

    absence = Attribute("""IAbsence""")
    comment = Attribute("""IAbsenceComment that describes the change""")


class IAbsenceEvent(IAttendanceEvent):
    """An event that gets sent when a person is found absent."""


class IAbsenceEndedEvent(IAttendanceEvent):
    """An event that gets sent when an absence is ended."""


class IAbsenceTracker(IEventTarget):
    """An object which listens to the AttendanceEvents and keeps a set
    of unended absences."""

    absences = Attribute(
        """A set of unended absences this object has been notified of.""")


class IAbsenceTrackerUtility(IUtility, IAbsenceTracker):
    pass


class IAbsenceTrackerFacet(IFacet, IEventConfigurable, IAbsenceTracker):
    pass


class IOptions(Interface):
    """User-selectable options of the system."""

    new_event_privacy = Attribute(
        """The default value of the privacy attribute for the newly
        created events.
        """)

    timetable_privacy = Attribute(
        """The value of the privacy attribute for the timetable events.""")


class IApplication(IContainmentRoot, IServiceManager, ITraversable, IOptions):
    """The application object.

    Services (as given by IServiceManager) are found by attribute.

    Application objects (of which there currently are persons, groups and
    resources) form a second hierarchy in addition to the usual containment
    hierarchy that all objects form.  The second hierarchy is expressed
    by Membership relationships.  Roots of the membership hierarchy are found
    by getRoots().

    Application object containers are found by __getitem__.  They do not
    participate in the second (membership) hierarchy.  All application objects
    are children of application object containers if you look at the
    containment hierarchy.
    """

    def getRoots():
        """Return a sequence of root application objects."""

    def __getitem__(name):
        """Get the named application object container."""

    def keys():
        """List the names of application object containers."""


class IApplicationObjectContainer(ILocation, ITraversable):
    """A collection of application objects."""

    def __getitem__(name):
        """Return the contained object that has the given name."""

    def new(__name__=None, **kw):
        """Create and return a new contained object.

        If __name__ is None, a name is chosen for the object.
        Otherwise, __name__ is a unicode or seven bit safe string.
        The rest of the keyword arguments are passed to the object's
        constructor.

        If the given name is already taken, raises a KeyError.

        The contained object will be an ILocation, and will have this
        container as its __parent__, and the name as its __name__.
        """

    def __delitem__(name):
        """Remove the contained object that has the given name.

        Raises a KeyError if there is no such object.
        """

    def keys():
        """Return a list of the names of contained objects."""

    def itervalues():
        """Iterate over all contained objects."""


class IAuthenticator(Interface):

    def __call__(context, username, password):
        """Authenticate a user given a username and password.

        Returns an authentication token (IPerson object) if successful.
        Raises AuthenticationError if not.
        """


class IPersonInfoFacet(IFacet):
    """Some attributes for a person object"""

    first_name = Attribute("First name")
    last_name = Attribute("Last name")
    date_of_birth = Attribute("Date of birth")
    comment = Attribute("A free form text comment")

    photo = Attribute(
        """Photo.

        A byte string with a small JPEG image of a person.
        """
    )


class INote(ILocation):
    """An abitrary notation on an IApplication Object."""

    title = Attribute("""The title of the note.""")
    body = Attribute("""The body of the note.""")
    owner = Attribute("""The object that created this note.""")
    url = Attribute("""The path of the object this note refers to.""")


class IAddress(IRelatable, IFaceted):
    """The base of a physical address.

    Participates in URIOccupies as occupiedBy.
    """

    country = Attribute("""ISO Country code""")


class IAddressInfoFacet(IFacet):
    """Default address attributes

    The default info facet hopefully will cover most use cases.  It is based on
    a draft of the Address Data Interchange Specification (ADIS) version 04-1.
    See http://www.upu.int/document/2004/an/cep_gan-3/d010.pdf for more info.

    The examples show how the standard might map to a locale's terms.

    Note: this is not a comprehensive implementation of the standard, but
    enough to build relationships on.  The full standard should be implemented
    later.
    """
    postcode = Attribute("""Postal service sorting code
                         Ex. Zip in the US, DX in the UK""")
    district = Attribute("""District, Ex. US State""")
    town = Attribute("""Town, Ex. US City""")
    streetNr = Attribute("""Street number""")
    thoroughfareName = Attribute("""Street name""")


#
# Modules
#

class IModuleSetup(Interface):
    """Module that needs initialization."""

    def setUp():
        """Initialize the module."""


#
# Views
#

class IViewAPI(Interface):

    def getView(object):
        """Select a view for an object by its class or its interface.

        Views registered for a class take precedence.

        Returns a View object for obj.
        """

    def registerView(interface, factory):
        """Register a view for an interface."""

    def registerViewForClass(cls, factory):
        """Register a view for a content class."""


#
# Exceptions
#

class ComponentLookupError(Exception):
    """An exception for component architecture."""


class AuthenticationError(Exception):
    """Bad username or password."""
