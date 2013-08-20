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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Group Timetable caledar views.
"""
import urllib
import pytz
from datetime import datetime, timedelta
from time import strptime

from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security.interfaces import Unauthorized
from zope.security.checker import canAccess
from zope.component import getUtility
from zope.i18n import translate

import schooltool.skin.flourish.page
from schooltool.app.browser.cal import CalendarViewBase
from schooltool.app.browser.cal import DailyCalendarView
from schooltool.app.browser.cal import WeeklyCalendarView
from schooltool.app.browser.cal import MonthlyCalendarView
from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.app.browser.cal import EventForDisplay
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.calendar.utils import utcnow
from schooltool.resource.interfaces import IBookingCalendar
from schooltool.skin import flourish
from schooltool.person.interfaces import IPerson
from schooltool.app.cal import CalendarEvent
from schooltool.term.interfaces import IDateManager
from schooltool.app.browser import ViewPreferences

from schooltool.common import SchoolToolMessage as _


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


class CalendarEventBookOneResourceView(BrowserView):
    """A view to book a resource to an event."""

    @property
    def timezone(self):
        prefs = ViewPreferences(self.request)
        return prefs.timezone

    def __call__(self):
        app = ISchoolToolApplication(None)
        person = IPerson(self.request.principal, None)
        if not person:
            raise Unauthorized("Only logged in users can book resources.")
        cal = ISchoolToolCalendar(person)
        if self.request.has_key('event_id'):
            event = cal.find(self.request['event_id'])
        else:
            start_date = self.request.get('start_date')
            start_time = self.request.get('start_time')
            title = self.request.get('title')
            start_datetime = "%s %s" % (start_date, start_time)
            start_datetime = datetime(*strptime(start_datetime,
                                                "%Y-%m-%d %H:%M")[0:6])
            start_datetime = self.timezone.localize(start_datetime)
            start_datetime = start_datetime.astimezone(pytz.UTC)
            duration = timedelta(seconds=int(self.request.get('duration')))
            event = CalendarEvent(dtstart = start_datetime,
                                  duration = duration,
                                  title = title)
            cal.addEvent(event)

        if event:
            resource = app["resources"].get(self.request['resource_id'])
            if resource is not None:
                resource_calendar = ISchoolToolCalendar(resource)
                if not canAccess(resource_calendar, "addEvent"):
                    raise Unauthorized("You don't have the right to"
                                       " book this resource!")
                event.bookResource(resource)
        self.request.response.redirect(self.nextURL(event))

    def cancelURL(self, event, back_url):
        calURL = absoluteURL(event.__parent__, self.request)
        cancel_url = (
            calURL + '/delete.html' +
            '?event_id=%s' % event.unique_id +
            '&date=%s' % event.dtstart.strftime("%Y-%m-%d") +
            '&back_url=%s' % back_url +
            '&DELETE=Delete')
        return cancel_url

    def nextURL(self, event):
        """Return the URL to be displayed after the add operation."""

        app = ISchoolToolApplication(None)
        resource = app["resources"].get(self.request['resource_id'])

        back_url = self.request.get('next_url', '')
        if resource is not None and not back_url:
            back_url = urllib.quote(absoluteURL(
                ISchoolToolCalendar(resource), self.request))

        cancel_url = self.cancelURL(event, back_url)

        url = "%s/edit.html?back_url=%s&cancel_url=%s" % (
            absoluteURL(event, self.request),
            back_url,
            urllib.quote(cancel_url))
        return url



class FlourishCalendarEventBookOneResourceView(
    CalendarEventBookOneResourceView):

    def render(self, *args, **kw):
        return ''

    def update(self):
        self.__call__()

    def cancelURL(self, event, back_url):
        calURL = absoluteURL(event.__parent__, self.request)
        cancel_url = (
            calURL + '/delete-temp.html' +
            '?event_id=%s' % event.unique_id +
            '&date=%s' % event.dtstart.strftime("%Y-%m-%d") +
            '&back_url=%s' % back_url +
            '&DELETE=Delete')
        return cancel_url


class BookResourceLink(flourish.page.LinkViewlet):


    def nextURL(self):
        return urllib.quote(absoluteURL(self.context, self.request))

    @property
    def url(self):
        rc = ISchoolToolApplication(None)['resources']
        booking_calendar = IBookingCalendar(rc)
        url = absoluteURL(booking_calendar, self.request)
        url = "%s/book_one_resource.html?resource_id=%s" % (
            url, self.context.__name__)
        today = getUtility(IDateManager).today
        hour = utcnow().hour
        duration = 3600
        url = "%s&start_date=%s&start_time=%s:00&duration=%s&title=%s" % (
            url, today.isoformat(), hour, duration,
            translate(_("Unnamed Event"), context=self.request))
        url = "%s&next_url=%s" % (url, self.nextURL())
        return url
