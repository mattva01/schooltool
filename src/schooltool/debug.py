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
Utilities for debugging SchoolTool
"""

import logging
import datetime
from persistence import Persistent
from persistence.list import PersistentList
from zope.interface import implements, moduleProvides, Attribute
from schooltool.interfaces import IEventTarget, ILocation, IUtility
from schooltool.interfaces import IEventConfigurable, IFacet
from schooltool.interfaces import IModuleSetup, IFacetFactory
from schooltool.event import CallAction
from schooltool.component import registerFacetFactory

moduleProvides(IModuleSetup)

__metaclass__ = type


class IEventLog(IEventTarget):
    """Event log that stores all received events persistently."""

    received = Attribute(
        """List of received events and their timestamps.

        Every item in the list is a tuple (timestamp, event), where timestamp
        is a datetime.datetime instance (in UTC).
        """)

    def clear():
        """Clear the list of received events."""

class IEventLogUtility(IEventLog, IUtility):
    """Event log that is a utility."""

class IEventLogFacet(IEventLog, IEventConfigurable, IFacet):
    """Event log that is a facet."""


class EventLog(Persistent):
    """Base class for event logs.  See IEventLog."""

    implements(IEventLog)

    datetime_hook = datetime.datetime

    def __init__(self):
        self.received = PersistentList()

    def notify(self, event):
        self.received.append((self.datetime_hook.utcnow(), event))

    def clear(self):
        del self.received[:]


class EventLogUtility(EventLog):
    """Event log as a utility.  See IEventLogUtility."""

    implements(IEventLogUtility)

    def __init__(self):
        EventLog.__init__(self)
        self.__parent__ = None
        self.__name__ = None
        self.title = "Event Log"


class EventLogFacet(EventLog):
    """Event log that can be attached to an object as a facet."""

    implements(IEventLogFacet)

    def __init__(self):
        EventLog.__init__(self)
        self.__parent__ = None
        self.__name__ = None
        self.active = False
        self.owner = None
        self.eventTable = (CallAction(self.notify), )


class EventLogFacetFactory:
    """Free-floating facet factory for event log facets."""

    implements(IFacetFactory)

    name = "eventlog"
    title = "Event Log Factory"
    __call__ = EventLogFacet


class EventLogger(Persistent):
    """Locatable event logger."""

    implements(IEventTarget, ILocation)

    def __init__(self):
        self.__parent__ = None
        self.__name__ = None

    def notify(self, event):
        logging.debug('Event: %r' % event)


def setUp():
    """Register the EventLogFacetFactory."""
    registerFacetFactory(EventLogFacetFactory())

