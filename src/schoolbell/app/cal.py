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
    """A persistent calendar."""

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
        if event.unique_id in self.events:
            raise ValueError('an event with this unique_id already exists')
        self.events[event.unique_id] = event

    def removeEvent(self, event):
        del self.events[event.unique_id]

    def clear(self):
        self.events.clear()

    def find(self, unique_id):
        return self.events[unique_id]

    def expand(self, first, last):
        raise NotImplementedError() # XXX
