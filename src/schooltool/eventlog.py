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
import time
from persistent import Persistent
from BTrees.OOBTree import OOBTree
from zope.interface import implements, moduleProvides
from schooltool.interfaces import IEventTarget, ILocation, IUtility
from schooltool.interfaces import IEventConfigurable, IFacet
from schooltool.interfaces import IModuleSetup
from schooltool.event import CallAction
from schooltool.facet import FacetMixin, FacetFactory
from schooltool.component import registerFacetFactory
from schooltool.translation import ugettext as _

moduleProvides(IModuleSetup)

__metaclass__ = type


class IEventLog(IEventTarget):
    """Event log that stores all received events persistently."""

    def getReceived():
        """Returns events received as a sequence of (timestamp, received event)

        Timestamps are datetime.datetime instances in UTC.
        """

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

    def __init__(self, enabled=True):
        self._received = OOBTree()
        self.enabled = enabled

    def notify(self, event):
        if not self.enabled:
            return
        rest = 0.001
        while not self._received.insert(self.datetime_hook.utcnow(), event):
            time.sleep(rest)
            rest *= 2
            if rest > 1:
                raise RuntimeError("Cannot insert event. Time has stopped.")

    def clear(self):
        self._received.clear()

    def getReceived(self):
        return self._received.items()


class EventLogUtility(EventLog):
    """Event log as a utility.  See IEventLogUtility."""

    implements(IEventLogUtility)

    def __init__(self):
        EventLog.__init__(self)
        self.__parent__ = None
        self.__name__ = None
        self.title = _("Event Log")


class EventLogFacet(EventLog, FacetMixin):
    """Event log that can be attached to an object as a facet."""

    implements(IEventLogFacet)

    def __init__(self):
        EventLog.__init__(self)
        self.eventTable = (CallAction(self.notify), )


class EventLogger(Persistent):
    """Locatable event logger."""

    implements(IEventTarget, ILocation)

    def __init__(self):
        self.__parent__ = None
        self.__name__ = None

    def notify(self, event):
        logging.debug('Event: %r' % event)


def setUp():
    """Register the EventLogFacet factory."""
    registerFacetFactory(FacetFactory(EventLogFacet,
        name='eventlog', title=_('Event Log'), facet_name='eventlog'))

