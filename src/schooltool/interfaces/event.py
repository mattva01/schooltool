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
SchoolTool interfaces for the event system.

$Id$
"""

from zope.interface import Interface
from zope.interface.interfaces import IInterface
from zope.schema import Object, List, Tuple
from schooltool.interfaces.relationship import ILink, IRelatable
from schooltool.interfaces.uris import IURIObject


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

    links = Tuple(
        title=u"The links of the relationship",
        value_type=Object(title=u"A link", schema=ILink))


class IRelationshipAddedEvent(IRelationshipEvent):
    """Event that gets sent out after a relationship has been established."""


class IRelationshipRemovedEvent(IRelationshipEvent):
    """Event that gets sent out after a relationship has been broken."""


class IMembershipEvent(IRelationshipEvent):
    """Base interface for membership events.

    This is a special case of IRelationshipEvent where one side has
    the role of URIGroup, and the other side has the role of URIMember.
    """

    group = Object(
        title=u"The membership group",
        schema=IRelatable)

    member = Object(
        title=u"The membership member",
        schema=IRelatable)


class IBeforeMembershipEvent(IMembershipEvent):
    """Event that gets sent out before the member is added to the group.

    This event allows listeners to veto this relationship by raising
    ValueError with an error message.
    """


class IMemberAddedEvent(IRelationshipAddedEvent, IMembershipEvent):
    """Event that is sent after a member has been added to a group."""


class IMemberRemovedEvent(IRelationshipRemovedEvent, IMembershipEvent):
    """Event that is sent after a member has been removed from a group."""


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
        """Unsubscribe a target from receiving events for a given event type.

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


class IEventAction(Interface):
    """Represents an action to be taken for certain types of events."""

    eventType = Object(
        title=u"Interface of an event this action pertains to",
        schema=IInterface)

    def handle(event, target):
        """Handle the event for a given target.

        Should be called only if event is of an appropriate type.
        """


class IEventConfigurable(Interface):
    """An object that has a configurable event table."""

    eventTable = List(
        title=u"Sequence of event table rows",
        value_type=Object(title=u"Event table row", schema=IEventAction))


class IEventCallback(Interface):

    def __call__(self, event):
        """Invoke the callback."""


class ICallAction(IEventAction):
    """Event action that calls a callable."""

    callback = Object(
        title=u"Callback that will be called with an event as its argument.",
        schema=IEventCallback)


class ILookupAction(IEventAction):
    """Event action that looks up actions to be performed in another event
    table.
    """

    eventTable = List(
        title=u"Sequence of event table rows",
        value_type=Object(title=u"Event table row", schema=IEventAction))


class IRouteToRelationshipsAction(IEventAction):
    """Event action that routes this event to relationships of this object."""

    role = Object(
        title=u"Role of the relationship",
        schema=IURIObject)


class IRouteToMembersAction(IEventAction):
    """Event action that routes this event to members of this object.

    This is equivalent to IRouteToRelationshipsAction with role URIMember.
    """


class IRouteToGroupsAction(IEventAction):
    """Event action that routes this event to groups of this object.

    This is equivalent to IRouteToRelationshipsAction with role URIGroup.
    """


class IOccupiesEvent(IRelationshipEvent):
    """Base interface for residence events.

    This is a special case of IRelationshipEvent where one side has
    the role of URICurrentlyResides, and the other side has the role of
    URICurrentResidence.
    """

    resides = Object(
        title=u"The person",
        schema=IRelatable)

    residence = Object(
        title=u"The address",
        schema=IRelatable)


class IOccupiesAddedEvent(IRelationshipAddedEvent, IOccupiesEvent):
    """Event that is sent after a person is associated with an address."""


class IOccupiesRemovedEvent(IRelationshipRemovedEvent, IOccupiesEvent):
    """Event that is sent after a person has been removed from an address."""


class INotedEvent(IRelationshipEvent):
    """Base interface for noted events."""

    notandum = Object(
        title=u"The noted object",
        schema=IRelatable)

    notation = Object(
        title=u"The note",
        schema=IRelatable)


class INotedAddedEvent(IRelationshipAddedEvent, INotedEvent):
    """Event that is sent after a note is associated with an object."""


class INotedRemovedEvent(IRelationshipRemovedEvent, INotedEvent):
    """Event that is sent after a note has been removed from an object."""


class IGuardianEvent(IRelationshipEvent):
    """Base interface for guardian events."""

    custodian = Object(
        title=u"Custodian",
        schema=IRelatable)

    ward = Object(
        title=u"Ward",
        schema=IRelatable)


class IGuardianAddedEvent(IRelationshipAddedEvent, IGuardianEvent):
    """Event that is sent after a guardian is associated with an object."""


class IGuardianRemovedEvent(IRelationshipRemovedEvent, IGuardianEvent):
    """Event that is sent after a guardian has been removed from an object."""
