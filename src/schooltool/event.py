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
from persistence.list import PersistentList
from zope.interface import implements
from schooltool.interfaces import IEvent, IEventTarget, IEventConfigurable
from schooltool.interfaces import IEventAction, ILookupAction
from schooltool.interfaces import IRouteToMembersAction, IRouteToGroupsAction

__metaclass__ = type


class EventMixin:

    implements(IEvent)

    def __init__(self, context=None):
        self.context = context
        self.__seen = Set()

    def dispatch(self, target=None):
        if target is None:
            target = self.context
        if target not in self.__seen:
            self.__seen.add(target)
            target.handle(self)


class EventTargetMixin:

    implements(IEventTarget, IEventConfigurable)

    def __init__(self):
        self.eventTable = PersistentList()

    def getEventTable(self):
        # this method can be overriden in subclasses
        return self.eventTable

    def handle(self, event):
        for action in self.getEventTable():
            if action.eventType.isImplementedBy(event):
                action.handle(event, self)


class EventActionMixin:

    implements(IEventAction)

    def __init__(self, eventType):
        self.eventType = eventType

    def handle(self, event, target):
        raise NotImplementedError('Subclasses must override this method')


class LookupAction(EventActionMixin):

    implements(ILookupAction)

    def __init__(self, eventTable=None, eventType=IEvent):
        EventActionMixin.__init__(self, eventType)
        if eventTable is None:
            eventTable = PersistentList()
        self.eventTable = eventTable

    def handle(self, event, target):
        for action in self.eventTable:
            if action.eventType.isImplementedBy(event):
                action.handle(event, target)


class RouteToMembersAction(EventActionMixin):

    implements(IRouteToMembersAction)

    def handle(self, event, target):
        for member in target.values():
            event.dispatch(member)


class RouteToGroupsAction(EventActionMixin):

    implements(IRouteToGroupsAction)

    def handle(self, event, target):
        for group in target.groups():
            event.dispatch(group)

