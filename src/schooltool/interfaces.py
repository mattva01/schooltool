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

__metaclass__ = type

from zope.interface import Interface, Attribute
from schooltool.unchanged import Unchanged  # reexport from here


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
        conditions is not met, raises a TypeError.
        """

    def traverse(obj, path):
        """Return the object accessible as path from obj.

        Path is a list of names separated with forward slashes.  Multiple
        adjacent slashes are equivalent to a single slash.  Special names
        are '.' and '..'; they are treated as is customary in file systems.
        Traversing to .. at the root keeps you at the root.

        If path starts with a slash, then the traversal starts from
        getRoot(obj), otherwise the traversal starts from obj.
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
        """Return the path of child relative to self."""


#
# Services
#

class IServiceAPI(Interface):
    """Service API"""

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
        """Return all the links matching a specified role.

        Roles are matched by hierarchy (as interfaces).  The default
        argument of ISpecificURI therefore means 'all roles'.
        """


class IRelationshipValencies(Interface):
    """Gives information on what relationships are pertinent to this
    object.
    """

    valencies = Attribute("""A tuple of IValency objects""")

    def getValencies():
        """Return a mapping of valencies.

        The return value is a dictionary with tuples containing the
        relationship type (as an ISpecificURI) and the role of this
        object (also an ISpecificURI) as keys, and ISchemaInvocation
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

    type = Attribute("An ISpecificURI for the type of this relationship.")

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
        """Iterates over all dates in the range from the first to the last."""

    def __contains__(date):
        """Returns True if the date is within the range, otherwise False.

        Raises a TypeError if date is not a datetime.date.
        """

    def __len__():
        """Returns the number of dates covered by the range."""


class ISchooldayModel(IDateRange):
    """A calendar which can tell whether a day is a school day or not
    for a certain period of time.
    """

    def isSchoolday(date):
        """Returns whether the date is a schoolday.

        Raises a ValueError if the date is outside of the period covered.
        """


class ISchooldayModelWrite(Interface):

    def add(day):
        """Marks the day as a schoolday.

        Raises a ValueError if the date is outside of the period covered.
        """

    def remove(day):
        """Marks the day as a holiday.

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

    def reset(first, last):
        """Change the period and mark all days as holidays.

        If first is later than last, a ValueError is raised.
        """


class ICalendar(Interface):
    """A calendar, containing days which in turn contain events.
    """

    def __iter__():
        """Returns an iterator over the events in this calendar."""

    def byDate(date):
        """Returns an ICalendar for the given date.

        All events that overlap with the given day are included.  The timing of
        the events is not modified even if it falls outside the given date.
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


class ICalendarEvent(Interface):
    """A calendar event."""

    unique_id = Attribute("""A unique id for this calendar event.""")
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

    def __cmp__(other):
        """Compare calendar events in chronological order.

        Events that occur at the same time are compared by their titles.

        Events are considered equal only if all attributes are equal.
        """

    def __hash__():
        """Return the hash value of this event.

        It is guaranteed that if calendar events compare equal, hash will
        return the same value.
        """


class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Attribute("""The object's calendar.""")


#
# Timetabling
#

class ITimetable(Interface):
    """A timetable is a collection of timetable days that contain
    periods. Each period either contains a class, or is empty.

    A timetable represents the repeating lesson schedule for just one
    pupil, or one teacher, or one bookable resource.
    """

    model = Attribute(
        """A timetable model this timetable should be used with""")

    def keys():
        """Return a sequence of identifiers for days within the timetable"""

    def items():
        """Return a sequence of tuples of (day_id, ITimetableDay)."""

    def __getitem__(key):
        """Return a ITimetableDay for a given day id"""

    def cloneEmpty():
        """Return a new empty timetable with the same structure.

        The new timetable has the same set of day_ids, and the sets of
        period ids within each day.
        """

    def __eq__(other):
        """Return True iff other is a Timetable with the same set of
        day_ids and each day compares equal.
        """

    def __ne__(other):
        """Return True iff __eq__ returns False."""

    def itercontent():
        """Return an iterator for tuples (day_id, period_id, activity)
        for all activities in this timetable.
        """


class ITimetableWrite(Interface):

    def __setitem__(key, value):
        """Set an ITimetableDay for a given day id.

        Throws a TypeError if the value does not implement ITimetableDay.
        Throws a ValueError if the key is not a day id.
        """

    def clear():
        """Remove all activities for all periods."""

    def update(timetable):
        """Add all the events in the timetable passed to self, thus
        producing a combined template.
        """


class ITimetableDay(Interface):
    """A model of a day with a mapping of periods to ITimetableActivities"""

    periods = Attribute("""A list of periods which are meaningful within
                        this day.""")

    def keys():
        """Return a sequence of period_ids which have activities
        assigned to them within this day.
        """

    def items():
        """Return a sequence of tuples (period_id, iter(ITimetableActivities)).

        If there is no activity for a certain period, the timetable an
        empty set is given.
        """

    def __getitem__(key):
        """Get an iterator over ITimetableActivities for a given period
        identifier.

        If there is no activity for the period, an empty set is returned.
        """

    def __eq__(other):
        """Return True iff other is a TimetableDay with the same set of
        periods and with the same activities scheduled for those periods.
        """

    def __ne__(other):
        """Returns True iff __eq__ returns False."""


class ITimetableDayWrite(Interface):
    """Writable timetable day.

    Note that all clients which use ITimetableDayWrite or ITimetableWrite
    to modify timetables should maintain the following invariant:
     - every TimetableActivity is present in the timetable of its owner
       and all the timetables of its resources.
    """

    def clear(key):
        """Remove all the activities for a certain period id."""

    def add(key, value):
        """Adds a single activity to the set of activities planned for
        a given period.
        """

    def remove(key, value):
        """Remove a certain activity from a set of activities planned
        for a given period.
        """


class ITimetableActivity(Interface):
    """An event in a timetable.

    Something that happens on a certain period_id in a certain
    day_id.

    Timetable activities are immutable.
    """

    title = Attribute("""The title of the activity""")

    owner = Attribute(
        """The group or person or other object that owns the activity.

        The activity lives in the owner's timetable.
        """)

    resources = Attribute("""A set of resources assigned to this activity.

        The activity is also present in the timetables of all resources
        assigned to this activity.
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
        ('2003 autumn semester', 'Weekly')

        These timetables can be directly manipulated.  For a lot of
        objects this mapping will be empty.
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

    def makeCalendar():
        """Generate and return a calendar from all composite timetables."""


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
        """Returns an iterator over the ISchooldayPeriods of this
        template.
        """


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
        """Returns a sequence of day_ids which can be used in the timetable.
        """)

    dayTemplates = Attribute(
        """A mapping of weekdays (calendar.MONDAY,...) to ISchooldayTemplates.

        The template with the key of None is used if there is no
        template for a particular weekday.
        """)

    def createCalendar(schoolday_model, timetable):
        """Returns an ICalendar composed out of schoolday_model and timetable.

        This method has model-specific knowledge as to how schooldays,
        weekends and holidays map affect the mapping of the timetable
        onto the real-world calendar.
        """


class ITimetableModelRegistry(Interface):
    """A registry of timetable model classes present in the system.

    The timetable model classes are identified by the dotted class
    names.
    """

    def getTimetableModel(id):
        """Returns a timetable schema identified by a given id."""

    def registerTimetableModel(id, factory):
        """Registers a timetable schema identified by a given id."""

    def listTimetableModels():
        """Returns a sequence of keys of the timetable models in the
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

    def __setitem__(schema_id, schoolday_model):
        """Store a schoolday model for this time period."""

    def __delitem__(period_id):
        """Removes the specified time period."""


#
# Application objects
#

class IAvailabilitySearch(Interface):
    """An interface for querying the availability of resources."""

    def getFreeIntervals(first, last, time_periods, duration):
        """Returns all intervals of time not shorter than duration
        when the object is free within a range of dates [first, last]
        during the times of day specified by time_periods.

        fist, last     datetime.datetime objects specifying a range of
                       dates.

        time_periods   a sequence of tuples (start_time, duration)
                       specifying a the time of day.  These are
                       respectively datetime.time and
                       datetime.timedelta objects

        duration       datetime.timedelta object specifying a minimum
                       interval of time we're searching for.

        The returned value is a sequence of (start_datetime, duration).
        """


class IApplicationObject(ILocation, IRelatable, IEventTarget,
                         IEventConfigurable, IFaceted, ICalendarOwner,
                         ITimetabled, IAvailabilitySearch):
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
        """A set of unended absences this object has been notified
        of.""")


class IAbsenceTrackerUtility(IUtility, IAbsenceTracker):
    pass


class IAbsenceTrackerFacet(IFacet, IEventConfigurable, IAbsenceTracker):
    pass


class IApplication(IContainmentRoot, IServiceManager, ITraversable):
    """The application object.

    Services (as given by IServiceManager) are found by attribute.

    Root application objects are found by getRoots().

    Application object containers are found by __getitem__.
    """

    def getRoots():
        """Return a sequence of root application objects."""

    def __getitem__(name):
        """Get the named application object container."""

    def keys():
        """List the names of application object containers."""


class IApplicationObjectContainer(ILocation, ITraversable):
    """A collection of application objects."""

    # XXX split this into read and write interfaces.

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


#
# Modules
#

class IModuleSetup(Interface):
    """Module that needs initialization"""

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
