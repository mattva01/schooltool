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
from datetime import datetime, date, time, timedelta

from zope.app.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy
from zope.security.checker import canAccess

from schooltool.app.browser import ViewPreferences
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.person.interfaces import IPerson


class DailyCalendarRowsView(BrowserView):
    """Daily calendar rows view."""

    def calendarRows(self, cursor, starthour, endhour):
        """Iterate over (title, start, duration) of time slots that make up
        the daily calendar.

        Returns a generator.
        """
        today = datetime.combine(cursor, time(tzinfo=utc))
        row_ends = [today + timedelta(hours=hour + 1)
                    for hour in range(starthour, endhour)]

        start = today + timedelta(hours=starthour)
        for end in row_ends:
            duration = end - start
            yield (self.rowTitle(start.hour, start.minute), start, duration)
            start = end

    def rowTitle(self, hour, minute):
        """Return the row title as HH:MM or H:MM am/pm."""
        prefs = ViewPreferences(self.request)
        return time(hour, minute).strftime(prefs.timeformat)


class CalendarListView(BrowserView):
    """A simple view that can tell which calendars should be displayed."""

    __used_for__ = ISchoolToolCalendar

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """
        yield (self.context, '#9db8d2', '#7590ae')
        user = IPerson(self.request.principal, None)
        if user is None:
            return

        unproxied_context = removeSecurityProxy(self.context)
        unproxied_calendar = removeSecurityProxy(ISchoolToolCalendar(user))
        if unproxied_context is unproxied_calendar:
            for item in user.overlaid_calendars:
                if item.show and canAccess(item.calendar, '__iter__'):
                    yield (item.calendar, item.color1, item.color2)
