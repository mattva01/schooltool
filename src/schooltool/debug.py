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
from persistence import Persistent
from persistence.list import PersistentList
from zope.interface import implements, Attribute
from schooltool.interfaces import IEventTarget, ILocation
from schooltool.interfaces import IEventConfigurable, IFacet
from schooltool.event import CallAction

__metaclass__ = type


class IEventLog(IEventTarget):
    """Event log that stores all received events persistently"""

    received = Attribute("""List of received events""")

    def clear():
        """Clear the list of received events."""


class EventLog(Persistent):
    """Locatable event log.  See IEventLog."""

    implements(IEventLog, ILocation)

    def __init__(self):
        self.received = PersistentList()
        self.__parent__ = None
        self.__name__ = None

    def notify(self, event):
        self.received.append(event)

    def clear(self):
        del self.received[:]


class EventLogFacet(Persistent):
    """Event log that can be attached to an object as a facet."""

    implements(IEventLog, IEventConfigurable, IFacet)

    def __init__(self):
        self.received = PersistentList()
        self.__parent__ = None
        self.active = False
        self.owner = None
        self.eventTable = (CallAction(self.notify), )

    def notify(self, event):
        self.received.append(event)

    def clear(self):
        del self.received[:]


class EventLogger(Persistent):
    """Locatable event logger."""

    implements(IEventTarget, ILocation)

    def __init__(self):
        self.__parent__ = None
        self.__name__ = None

    def notify(self, event):
        logging.debug('Event: %r' % event)

