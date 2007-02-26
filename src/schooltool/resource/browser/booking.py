#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Resource Booking caledar views.

$Id$
"""
from schooltool.app.browser.cal import CalendarViewBase
from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView


class BookingCalendarViewBase(CalendarViewBase):

    def getEvents(self, start_dt, end_dt):
        """Get a list of EventForDisplay objects for a selected time interval.

        `start_dt` and `end_dt` (datetime objects) are bounds (half-open) for
        the result.
        """
        for calendar, color1, color2 in self.getCalendars():
            for event in calendar.expand(start_dt, end_dt):
                from schooltool.app.browser.cal import EventForDisplay
                yield EventForDisplay(event, self.request, color1, color2,
                                      calendar, self.timezone)

    def canAddEvents(self):
        """No one can add events to a booking calendar."""
        return False

    def canRemoveEvents(self):
        """No one can remove events from a booking calendar."""
        return False


class DailyBookingCalendarView(DailyCalendarView, BookingCalendarViewBase):
    pass


class WeeklyBookingCalendarView(WeeklyCalendarView, BookingCalendarViewBase):
    pass


class MonthlyBookingCalendarView(MonthlyCalendarView, BookingCalendarViewBase):
    pass


class YearlyBookingCalendarView(YearlyCalendarView, BookingCalendarViewBase):
    pass
