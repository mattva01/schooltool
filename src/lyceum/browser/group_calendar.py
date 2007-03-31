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
Merged calendar for groups.

$Id$
"""
from zope.security.proxy import removeSecurityProxy

from schooltool.app.browser.cal import CalendarViewBase
from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.app.browser.cal import EventForDisplay


class GroupTimetableCalendarViewBase(CalendarViewBase):

    def eventForDisplayFactory(self, event):
        return EventForDisplay(event, self.request, '#9db8d2', '#7590ae',
                               self.context, self.timezone)

    def getEvents(self, start_dt, end_dt):
        """Get a list of EventForDisplay objects for a selected time interval.

        `start_dt` and `end_dt` (datetime objects) are bounds (half-open) for
        the result.
        """
        group = self.context.__parent__

        sources = set()
        for member in group.members:
            ct = ICompositeTimetables(member)
            objs = ct.collectTimetableSourceObjects()
            for obj in objs:
                sources.add(obj)

        for source in sources:
            calendar = removeSecurityProxy(ISchoolToolCalendar(source))
            for event in calendar.expand(start_dt, end_dt):
                yield self.eventForDisplayFactory(event)

    def canAddEvents(self):
        """No one can add events to a group calendar."""
        return False

    def canRemoveEvents(self):
        """No one can remove events from a group calendar."""
        return False


class DailyGroupTimetableCalendarView(DailyCalendarView,
                                      GroupTimetableCalendarViewBase):
    pass


class WeeklyGroupTimetableCalendarView(WeeklyCalendarView,
                                       GroupTimetableCalendarViewBase):
    pass


class MonthlyGroupTimetableCalendarView(MonthlyCalendarView,
                                        GroupTimetableCalendarViewBase):
    pass


class YearlyGroupTimetableCalendarView(YearlyCalendarView,
                                       GroupTimetableCalendarViewBase):
    pass
