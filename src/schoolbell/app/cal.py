#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
SchoolBell calendaring objects.

$Id$
"""
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app.location.interfaces import ILocation

from schoolbell.calendar.interfaces import IEditCalendar


class Calendar(Persistent):

    implements(IEditCalendar, ILocation)

    __name__ = None
    __parent__ = None

    def __init__(self):
        self.events = PersistentDict()

    def __iter__(self):
        return self.events.itervalues()

    def __len__(self):
        return len(self.events)

    def addEvent(self, event):
        self.events[event.unique_id] = event

    def _removeEvent(self, event):
        del self.events[event.unique_id]

    def removeEvent(self, event):
        self._removeEvent(event)
        # In SchoolTool resource booking works as follows:
        #   1. A CalendarEvent is created with owner == the user who booked
        #      the resource and context == the resource.
        #   2. That event is added to both the owner's calendar and the
        #      resource's calendar.
        # When that event is removed from either the owner's or the resource's
        # calendar, it should be removed from the other one as well.  It would
        # be nice to move the extra logic into schooltool.booking, if possible.
        ## XXX Disabled for now.
        ##owner_calendar = context_calendar = None
        ##if event.owner is not None:
        ##    owner_calendar = event.owner.calendar
        ##if event.context is not None:
        ##    context_calendar = event.context.calendar
        ##if self is owner_calendar or self is context_calendar:
        ##    if owner_calendar is not None and owner_calendar is not self:
        ##        owner_calendar._removeEvent(event)
        ##    if context_calendar is not None and context_calendar is not self:
        ##        context_calendar._removeEvent(event)

    def update(self, calendar):
        for event in calendar:
            self.events[event.unique_id] = event

    def clear(self):
        self.events.clear()

    def find(self, unique_id):
        return self.events[unique_id]

    def expand(self, first, last):
        raise NotImplementedError() # XXX
