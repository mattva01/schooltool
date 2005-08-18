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
Upgrade to generation 5.

Moving to TZ aware events requires copying the old events to new non-naive
events.

$Id: evolve5.py 3254 2005-03-09 19:19:26Z alga $
"""

from pytz import timezone

from zope.app.publication.zopepublication import ZopePublication
from zope.app.generations.utility import findObjectsProviding
from schoolbell.app.interfaces import ICalendarOwner
from schoolbell.app.cal import CalendarEvent, Calendar

utc = timezone('UTC')

def evolve(context):
    root = context.connection.root().get(ZopePublication.root_name, None)
    for owner in findObjectsProviding(root, ICalendarOwner):
        new_calendar = Calendar(owner)
        for event in owner.calendar:
            ev = CalendarEvent(event.dtstart.replace(tzinfo=utc),
                               event.duration,
                               event.title,
                               description=event.description,
                               location=event.location,
                               unique_id=event.unique_id,
                               recurrence=event.recurrence)
            new_calendar.addEvent(ev)
        owner.calendar = new_calendar
