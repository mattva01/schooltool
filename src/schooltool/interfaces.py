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

from zope.interface import Interface, Attribute

#
# Containment
#

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


class IContainmentAPI(Interface):
    """Containment API"""

    def getPath(obj):
        """Returns the unique path of an object in the containment hierarchy.

        The object must implement ILocation or IContainmentRoot and must be
        attached to the hierarchy (i.e. following parent references should not
        reach None).
        """


#
# Services
#

class IServiceAPI(Interface):
    """Service API"""

    def getEventService():
        """Returns the global event service."""


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


class IFaceted(Interface):
    """Denotes that the object can have facets.
    """

    __facets__ = Attribute("""A dictionary of facets.""")


class IFacetAPI(Interface):
    """Facet API"""

    def setFacet(ob, key, facet):
        """Set the facet identified by the key on the object."""

    def getFacet(ob, key):
        """Get a facet of an object.

        Raises KeyError if no facet with a given key exists.
        """

    def queryFacet(ob, key, default=None):
        """Get a facet of an object.

        Returns default if no facet with a given key exists.
        """

    def getFacetItems(ob):
        """Returns a sequence of (key, facet) for all facets of an object."""

#
# URIs
#

class ISpecificURI(Interface):
    """All interfaces derived from this must have the URI they map on
    to as the first line of their docstring. Examples::

        class ITutor(ISpecificURI):
            '''http://schooltool.org/ns/tutor'''

        class ITutor(ISpecificURI):
            '''http://schooltool.org/ns/tutor

            A person who is responsible for a registration class.
            '''
    """

class IURIAPI(Interface):

    def inspectSpecificURI(uri):
        """Returns a tuple of a URI and the documentation of the ISpecificURI.

        Raises a TypeError if the argument is not ISpecificURI.
        Raises a ValueError if the URI's docstring does not conform.
        """

    def isURI(uri):
        """Checks if the argument looks like a URI.

        Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
        We're only approximating to the spec.
        """

#
# Relationships
#

class ILink(Interface):
    """A link is a 'view' of a relationship the relating objects have.

             A<--->Link<---->Relationship<---->Link<--->B

    """

    title = Attribute(
        """A title of the whole relationship.

        The title should be the same on both links of a relationship.
        """)

    role = Attribute(
        """The role implied by traversing this link.

        This is how the object got by traverse() relates to my __parent__.

        This attribute's value is an ISpecificURI.
        """)

    __parent__ = Attribute("The object at this end of the relationship")

    def traverse():
        """Returns the object at the other end of the relationship."""


class IRelatable(Interface):
    """An object which can take part in relationships."""

    __links__ = Attribute(
        """A dictionary of links of relationships indexed by serial numbers."""
        )

class IQueryLinks(Interface):
    """An interface for querying a collection of links for those that
    meet certain conditions.
    """
    def listLinks(role=ISpecificURI):
        """Return all the links matching a specified role.

        Roles are matched by hierarchy (as interfaces).  The default
        argument of ISpecificURI therefore means 'all roles'.
        """


#
# Groups and membership
#

class IGroupRead(Interface):
    """A set of group members.

    All group members must implement IGroupMember.  If facetFactory is not
    None, they also must implement IFaceted.
    """

    facetFactory = Attribute(
        """Factory for facets set on new members.

        Can be None.  Factory gets called with a single argument that is
        the member the facet will be set on.

        Note that if you change facetFactory once some members have
        been added (and possibly removed), those members will keep their
        old facets.
        """)

    def __getitem__(key):
        """Returns a member with the given key.

        Raises a KeyError if there is no such member.
        """

    def keys():
        """Returns a sequence of member keys."""

    def values():
        """Returns a sequence of members."""

    def items():
        """Returns a sequence of (key, member) pairs."""


class IGroupWrite(Interface):
    """Modification access to a group."""

    def add(memeber):
        """Adds a new member to this group.

        Returns the key assigned to this member.

        If facetFactory is not None, creates a facet for this member
        if it does not already have one, and marks it as active.
        Member facets are keyed by the group.
        """

    def __delitem__(key):
        """Removes a member from the group.

        Raises a KeyError if there is no such member.

        If facetFactory is not None, marks the facet keyed by this
        group as inactive.
        """


class IGroup(IGroupWrite, IGroupRead, IFaceted):
    __doc__ = IGroupRead.__doc__


class IGroupMember(ILocation):

    name = Attribute("A human readable name of this member.")

    def groups():
        """Returns a set for all groups this object is a member of."""

    def notifyAdd(group, name):
        """Notifies the member that it's added to a group."""

    def notifyRemove(group):
        """Notifies the member that it's removed from a group."""


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


class ILookupAction(IEventAction):
    """Event action that looks up actions to be performed in another event
    table.
    """

    eventTable = Attribute(
        """Sequence of event table rows, each implementing IEventAction""")


class IRouteToMembersAction(IEventAction):
    """Event action that routes this event to members of this object."""


class IRouteToGroupsAction(IEventAction):
    """Event action that routes this event to groups of this object."""


#
# Application objects
#

class IPerson(IGroupMember, IFaceted):

    name = Attribute("Person's name")


class IRootGroup(IGroup, IContainmentRoot):
    """An interface for the application root group."""


#
# Exceptions
#

class ComponentLookupError(Exception):
    """An exception for component architecture."""
