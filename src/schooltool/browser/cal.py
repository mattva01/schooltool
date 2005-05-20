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
SchoolTool application views.

$Id$
"""

from datetime import datetime, time, timedelta
from sets import Set

from pytz import timezone

from zope.security.checker import canAccess
from zope.security.proxy import removeSecurityProxy
from zope.app.traversing.api import getPath
from zope.app.annotation.interfaces import IAnnotations

from schoolbell.app.browser.cal import DailyCalendarView as SBDailyCalView
from schoolbell.app.browser.overlay import CalendarOverlayView
from schoolbell.app.interfaces import ISchoolBellCalendar, IPerson

from schooltool.timetable import getPeriodsForDay
from schooltool.interfaces import IPersonPreferences


utc = timezone('UTC')


class DailyCalendarView(SBDailyCalView):
    """Daily calendar view for SchoolTool.

    This view differs from the original view in SchoolBell in that it can
    also show day periods instead of hour numbers.
    """

    __used_for__ = ISchoolBellCalendar

    def calendarRows(self):
        """Iterate over (title, start, duration) of time slots that make up
        the daily calendar.
        """
        person = IPerson(self.request.principal, None)
        if person is not None:
            prefs = IPersonPreferences(person)
            show_periods = prefs.cal_periods
        else:
            show_periods = False

        if show_periods:
            periods = getPeriodsForDay(self.cursor)
        else:
            periods = []
        today = datetime.combine(self.cursor, time(tzinfo=utc))
        row_ends = [today + timedelta(hours=hour + 1)
                    for hour in range(self.starthour, self.endhour)]

        # Put starts and ends of periods into row_ends
        for period in periods:
            pstart = datetime.combine(self.cursor, period.tstart)
            pstart = pstart.replace(tzinfo=self.timezone)
            pend = pstart + period.duration
            for point in row_ends:
                if pstart < point < pend:
                    row_ends.remove(point)
                if pstart not in row_ends:
                    row_ends.append(pstart)
                if pend not in row_ends:
                    row_ends.append(pend)

        if periods:
            row_ends.sort()

        def periodIsStarting(dt):
            if not periods:
                return False
            pstart = datetime.combine(self.cursor, periods[0].tstart)
            pstart = pstart.replace(tzinfo=self.timezone)
            if pstart == dt:
                return True

        start = today + timedelta(hours=self.starthour)
        for end in row_ends:
            if periodIsStarting(start):
                period = periods.pop(0)
                pstart = datetime.combine(self.cursor, period.tstart)
                pend = pstart + period.duration
                yield (period.title, start, period.duration)
            else:
                duration =  end - start
                yield ('%d:%02d' % (start.hour, start.minute), start, duration)
            start = end


class CalendarSTOverlayView(CalendarOverlayView):
    """View for the calendar overlay portlet.

    Much like the original CalendarOverlayView in SchoolBell, this view allows
    you to choose calendars to be displayed, but this one allows you to view
    timetables of the calendar owners as well.

    This view can be used with any context, but it gets rendered to an empty
    string unless context is the calendar of the authenticated user.

    Note that this view contains a self-posting form and handles submits that
    contain 'OVERLAY_APPLY' or 'OVERLAY_MORE' in the request.
    """

    show_my_timetable = True

    SHOW_TIMETABLE_KEY = 'schooltool.browser.cal.show_my_timetable'

    def items(self):
        """Return items to be shown in the calendar overlay.

        Does not include "my calendar".

        Each item is a dict with the following keys:

            'title' - title of the calendar

            'calendar' - the calendar object

            'color1', 'color2' - colors assigned to this calendar

            'id' - identifier for form controls

            'checked' - was this item checked for display (either "checked" or
            None)?

            'checked_tt' - was this calendar owner's timetable checked for
            display?
        """
        person = IPerson(self.request.principal)
        items = [(item.calendar.title,
                  {'title': item.calendar.title,
                   'id': getPath(item.calendar.__parent__),
                   'calendar': item.calendar,
                   'checked': item.show and "checked" or '',
                   'checked_tt': item.show_timetables and "checked" or '',
                   'color1': item.color1,
                   'color2': item.color2})
                 for item in person.overlaid_calendars
                 if canAccess(item.calendar, '__iter__')]
        items.sort()
        return [i[-1] for i in items]

    def update(self):
        """Process form submission."""
        if 'OVERLAY_APPLY' in self.request:
            person = IPerson(self.request.principal)
            selected = Set(self.request.get('overlay_timetables', []))
            for item in person.overlaid_calendars:
                path = getPath(item.calendar.__parent__)
                item.show_timetables = path in selected

            # The unproxied object will only be used for annotations.
            person = removeSecurityProxy(person)

            annotations = IAnnotations(person)
            annotations[self.SHOW_TIMETABLE_KEY] = bool('my_timetable'
                                                        in self.request)
        return CalendarOverlayView.update(self)

    def myTimetableShown(self):
        person = IPerson(self.request.principal)
        # The unproxied object will only be used for annotations.
        person = removeSecurityProxy(person)
        annotations = IAnnotations(person)
        return annotations.get(self.SHOW_TIMETABLE_KEY, True)
