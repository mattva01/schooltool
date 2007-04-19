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
Group Timetable caledar views.

$Id$
"""
from datetime import datetime, timedelta
from time import strptime

from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.browser.cal import CalendarViewBase
from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.app.browser.cal import EventForDisplay
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.person.interfaces import IPerson
from schooltool.app.cal import CalendarEvent


class BookingCalendarViewBase(CalendarViewBase):

    def getEvents(self, start_dt, end_dt):
        """Get a list of EventForDisplay objects for a selected time interval.

        `start_dt` and `end_dt` (datetime objects) are bounds (half-open) for
        the result.
        """
        for calendar, color1, color2 in self.getCalendars():
            for event in calendar.expand(start_dt, end_dt):
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

import urllib
class CalendarEventBookOneResourceView(BrowserView):
    """A view to book a resource to an event."""
    errors = ()
    update_status = None

    def __call__(self):
        self.update_status = ''
        app = ISchoolToolApplication(None)
        cal = ISchoolToolCalendar(IPerson(self.request.principal))
        if self.request.has_key('event_id'):
            event = cal.find(self.request['event_id'])
        else:
            start_date = self.request.get('start_date')
            start_time = self.request.get('start_time')
            title = self.request.get('title')
            start_datetime = "%s %s" % (start_date, start_time)
            start_datetime = datetime(*strptime(start_datetime,
                                                "%Y-%m-%d %H:%M:%S")[0:6])
            duration = timedelta(seconds=int(self.request.get('duration')))
            event = CalendarEvent(dtstart = start_datetime,
                                  duration = duration,
                                  title = title)
            cal.addEvent(event)

        if event:
            for res_id, resource in app["resources"].items():
                if res_id == self.request['resource_id']:
                    event.bookResource(resource)
        self.request.response.redirect(self.nextURL(event))

    def nextURL(self, event):
        """Return the URL to be displayed after the add operation."""
        calURL = absoluteURL(event.__parent__, self.request)
        cancel_url = calURL+'/delete.html?event_id=%s&date=%s' % (
            event.unique_id,
            event.dtstart.strftime("%Y-%m-%d"))
        url = "%s/edit.html?cancel_url=%s" % (absoluteURL(event, self.request),
                                               urllib.quote(cancel_url))
        return url
