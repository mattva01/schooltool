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
SchoolBell calendar views.

$Id$
"""

from zope.app.publisher.browser import BrowserView
from schoolbell.calendar.interfaces import ICalendar
from schoolbell.calendar.simple import SimpleCalendarEvent


class PlainCalendarView(BrowserView):
    """A calendar view purely for testing purposes."""

    __used_for__ = ICalendar

    num_events = 5
    evt_range = 60*24*14 # two weeks

    def iterEvents(self):
        events = list(self.context.calendar)
        events.sort()
        return events

    def update(self):
        if 'GENERATE' in self.request:
            from datetime import datetime, timedelta
            import random
            for i in range(self.num_events):
                delta = random.randint(-self.evt_range, self.evt_range)
                dtstart = datetime.now() + timedelta(minutes=delta)
                length = timedelta(minutes=random.randint(1, 60*12))
                title = 'Event %d' % random.randint(1, 999)
                event = SimpleCalendarEvent(dtstart, length, title)
                self.context.calendar.addEvent(event)
