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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool calendar views.
"""

import datetime

from zope.component import subscribers
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.i18n import translate
from schooltool.app.browser import ViewPreferences, same
from schooltool.app.browser.interfaces import ICalendarProvider
from schooltool.calendar.utils import parse_date, week_start
from schooltool.common import SchoolToolMessage as _
from schooltool.app.browser.report import ReportPDFView


SANS = 'Arial_Normal'
SANS_OBLIQUE = 'Arial_Italic'
SANS_BOLD = 'Arial_Bold'
SERIF = 'Times_New_Roman'


class DailyPDFCalendarView(ReportPDFView):
    """The daily view of a calendar in PDF."""

    template=ViewPageTemplateFile('templates/cal_rml.pt')

    title_template = _("Daily calendar for %s")
    subtitle = u""

    @property
    def owner(self):
        return self.context.__parent__.title

    @property
    def title(self):
        return translate(
            self.title_template, context=self.request) % self.owner

    def getDate(self):
        if 'date' in self.request:
            return parse_date(self.request['date'])
        else:
            return datetime.date.today()

    def dayTitle(self, date):
        from schooltool.app.browser.cal import day_of_week_names
        day_of_week_msgid = day_of_week_names[date.weekday()]
        day_of_week = translate(day_of_week_msgid, context=self.request)
        return "%s, %s" % (date.isoformat(), day_of_week)


    def getCalendars(self):
        """Get a list of calendars to display."""
        providers = subscribers((self.context, self.request), ICalendarProvider)

        coloured_calendars = []
        for provider in providers:
            coloured_calendars += provider.getCalendars()

        calendars = [calendar for (calendar, color1, color2)
                     in coloured_calendars]
        return calendars

    def tables(self):
        return [self.buildDayTable(self.getDate())]

    def eventTags(self, event):
        tags = []
        if event.recurrence:
            tags.append(translate(_("recurrent"), context=self.request))
        if (not same(event.__parent__, self.context)
            and event.__parent__ is not None):
            # We have an event from an overlaid calendar.
            tag = translate(_('from the calendar of ${calendar_owner}',
                              mapping={'calendar_owner':
                                       event.__parent__.__parent__.title}),
                            context=self.request)
            # We assume that event.__parent__ is a Calendar which belongs to
            # an object with a title.
            tags.append(tag)
        return tags

    def buildDayTable(self, date):
        """Return the table containing info about events that day."""
        events = self.dayEvents(date)

        rows = []
        for event in events:
            if event.allday:
                time_text = translate(_("all day"), context=self.request)
            else:
                start = event.dtstart.astimezone(self.getTimezone())
                dtend = start + event.duration
                time_text = "%s-%s" % (start.strftime('%H:%M'),
                                            dtend.strftime('%H:%M'))

            row = {
                'title': event.title,
                'description': event.description,
                'location': event.location,
                'time': time_text,
                'resources': ', '.join([
                    resource.title for resource in event.resources]),
                'tags': ', '.join(self.eventTags(event)),
                }

            rows.append(row)

        return {
            'title': self.dayTitle(date),
            'rows': rows,
            }

    def dayEvents(self, date):
        """Return a list of events that should be shown.

        All-day events are placed in front.
        """
        allday_events = []
        events = []
        tz = self.getTimezone()
        start = tz.localize(datetime.datetime.combine(date, datetime.time(0)))
        end = start + datetime.timedelta(days=1)

        for calendar in self.getCalendars():
            for event in calendar.expand(start, end):
                if (same(event.__parent__, self.context)
                      and not same(calendar, self.context)):
                    # We may have overlaid resource booking events appearing
                    # twice (once for self.context and another time for the
                    # other calendar).  We can recognize such dupes by
                    # checking that their __parent__ does not match the
                    # calendar they are coming from.
                    continue
                if event.allday:
                    allday_events.append(event)
                else:
                    events.append(event)

        allday_events.sort()
        events.sort()
        return allday_events + events

    def getTimezone(self):
        """Return the timezone for the PDF report."""
        prefs = ViewPreferences(self.request)
        return prefs.timezone


class WeeklyPDFCalendarView(DailyPDFCalendarView):

    title_template = _("Weekly calendar for %s")

    @property
    def subtitle(self):
        date = self.getDate()
        year, week = date.isocalendar()[:2]
        start = week_start(date, 0) # TODO: first_day_of_week
        end = (start + datetime.timedelta(weeks=1) -
               datetime.timedelta(days=1))
        template = translate(_("Week %d (%s - %s), %d"), context=self.request)
        return template % (week, start, end, year)

    def tables(self):
        start = week_start(self.getDate(), 0) # TODO: first_day_of_week
        return [self.buildDayTable(start + datetime.timedelta(days=weekday))
                for weekday in range(7)]


class MonthlyPDFCalendarView(WeeklyPDFCalendarView):

    title_template = _("Monthly calendar for %s")

    @property
    def subtitle(self):
        from schooltool.app.browser.cal import month_names
        date = self.getDate()
        month_name = translate(month_names[date.month], context=self.request)
        return "%s, %d" % (month_name, date.year)

    def tables(self):
        date = self.getDate()
        day = datetime.date(date.year, date.month, 1)
        tables = []
        while day.month == date.month:
            tables.append(self.buildDayTable(day))
            day = day + datetime.timedelta(days=1)
        return tables
