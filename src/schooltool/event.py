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
SchoolTool event model.

$Id$
"""

from sets import Set
from persistent import Persistent
from persistent.list import PersistentList
import zope.event
from zope.interface import implements
from schooltool.interfaces import IEvent, IEventTarget, IEventConfigurable
from schooltool.interfaces import IEventService, IEventAction, ILookupAction
from schooltool.interfaces import IRouteToMembersAction, IRouteToGroupsAction
from schooltool.interfaces import IRouteToRelationshipsAction, ICallAction
from schooltool.interfaces import IURIObject
from schooltool.uris import URIMember, URIGroup
from schooltool.component import getEventService
from schooltool.component import getRelatedObjects

__metaclass__ = type


class EventMixin:

    implements(IEvent)

    def __init__(self):
        self.__seen = Set()
        self.__sent_to_event_service = False

    def dispatch(self, target):
        if not self.__sent_to_event_service:
            self.__sent_to_event_service = True
            event_service = getEventService(target)
            self.dispatch(event_service)
        if target not in self.__seen:
            self.__seen.add(target)
            target.notify(self)


class EventTargetMixin:

    implements(IEventTarget, IEventConfigurable)

    def __init__(self):
        self.eventTable = PersistentList()

    def getEventTable(self):
        # this method can be overridden in subclasses
        return self.eventTable

    def notify(self, event):
        for action in self.getEventTable():
            if action.eventType.providedBy(event):
                action.handle(event, self)


class EventActionMixin:

    implements(IEventAction)

    def __init__(self, eventType):
        self.eventType = eventType

    def handle(self, event, target):
        raise NotImplementedError('Subclasses must override this method')


class CallAction(EventActionMixin):

    implements(ICallAction)

    def __init__(self, callback, eventType=IEvent):
        EventActionMixin.__init__(self, eventType)
        self.callback = callback

    def handle(self, event, target):
        self.callback(event)


class LookupAction(EventActionMixin):

    implements(ILookupAction)

    def __init__(self, eventTable=None, eventType=IEvent):
        EventActionMixin.__init__(self, eventType)
        if eventTable is None:
            eventTable = PersistentList()
        self.eventTable = eventTable

    def handle(self, event, target):
        for action in self.eventTable:
            if action.eventType.providedBy(event):
                action.handle(event, target)


class RouteToMembersAction(EventActionMixin):

    implements(IRouteToMembersAction)

    getRelatedObjects = staticmethod(getRelatedObjects)

    def handle(self, event, target):
        for member in self.getRelatedObjects(target, URIMember):
            event.dispatch(member)


class RouteToGroupsAction(EventActionMixin):

    implements(IRouteToGroupsAction)

    getRelatedObjects = staticmethod(getRelatedObjects)

    def handle(self, event, target):
        for group in self.getRelatedObjects(target, URIGroup):
            event.dispatch(group)


class RouteToRelationshipsAction(EventActionMixin):

    implements(IRouteToRelationshipsAction)

    def __init__(self, role=None, eventType=IEvent):
        EventActionMixin.__init__(self, eventType)
        if not IURIObject.providedBy(role):
            raise TypeError("Role must be a URIObject (got %r)" % (role,))
        self.role = role

    def handle(self, event, target):
        for obj in getRelatedObjects(target, self.role):
            event.dispatch(obj)


class EventService(Persistent):

    implements(IEventService)

    def __init__(self):
        self._subscriptions = PersistentList()

    def subscribe(self, target, event_type):
        '''See IEventService'''
        self._subscriptions.append((target, event_type))

    def unsubscribe(self, target, event_type):
        '''See IEventService'''
        self._subscriptions.remove((target, event_type))

    def unsubscribeAll(self, target):
        '''See IEventService'''
        new_subscriptions = PersistentList()
        for t, e in self._subscriptions:
            if t != target:
                new_subscriptions.append((t, e))
        self._subscriptions = new_subscriptions

    def listSubscriptions(self):
        '''See IEventService'''
        return tuple(self._subscriptions)

    def notify(self, event):
        """Send the event to all subscribers and forward it to Zope3.

        The event is sent out to the Zope3 event system after it has been
        processed by all interested subscribers.
        """
        for t, e in self._subscriptions:
            if e.providedBy(event):
                event.dispatch(t)
        zope.event.notify(event)
