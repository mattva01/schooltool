#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Period and time slot schedule templates.
Template scheduling over dates.
"""

from persistent import Persistent
from zope.interface import implements, implementer
from zope.component import adapter
from zope.container.contained import Contained
from zope.container.ordered import OrderedContainer
from zope.container.contained import containedEvent
from zope.event import notify

from schooltool.common import DateRange
from schooltool.timetable import interfaces


class DayTemplate(OrderedContainer):
    implements(interfaces.IDayTemplate)

    title = None

    def __init__(self, title=u''):
        OrderedContainer.__init__(self)
        self.title = title


class DayTemplateContainer(OrderedContainer):
    implements(interfaces.IDayTemplateContainer)


class TimeSlot(Persistent, Contained):
    implements(interfaces.ITimeSlot)

    tstart = None
    duration = None
    activity_type = None

    def __init__(self, tstart, duration, activity_type=None):
        Contained.__init__(self)
        self.tstart = tstart
        self.duration = duration
        self.activity_type = activity_type

    def __cmp__(self, other):
        return cmp((self.tstart, self.duration),
                   (other.tstart, other.duration))


class DayTemplateSchedule(Persistent, Contained):
    """Day templates scheduled by date."""
    implements(interfaces.IDayTemplateSchedule)

    templates = None

    def initTemplates(self):
        self.templates, event = containedEvent(
            DayTemplateContainer(), self, 'templates')
        notify(event)

    def iterDates(self, dates):
        for date in dates:
            yield None


class CalendarDayTemplates(DayTemplateSchedule):
    implements(interfaces.ICalendarDayTemplates)

    starting_index = 0

    def getDay(self, schedule, date):
        assert self.templates
        days_passed = (date - schedule.first).days
        keys = self.templates.keys()
        n = (self.templates.starting_index + days_passed) % len(keys)
        return self.templates[keys[n]]

    def iterDates(self, dates):
        if not self.templates:
            for date in dates:
                yield None
            return
        schedule = interfaces.ISchedule(self)
        scheduled_dates = DateRange(schedule.first, schedule.last)
        for date in dates:
            if date not in scheduled_dates:
                yield None
            else:
                day = self.getDay(schedule, date)
                yield day


class WeekDayTemplates(DayTemplateSchedule):
    implements(interfaces.IWeekDayTemplates)

    def getWeekDayKey(self, weekday):
        return unicode(weekday)

    def getWeekDay(self, weekday):
        return self.templates.get(unicode(weekday), None)

    def iterDates(self, dates):
        if not self.templates:
            for date in dates:
                yield None
            return
        schedule = interfaces.ISchedule(self)
        schooldays = interfaces.ISchooldays(schedule)
        scheduled_dates = DateRange(schedule.first, schedule.last)
        for date in dates:
            if (date not in scheduled_dates or
                date not in schooldays):
                yield None
            else:
                day = self.getWeekDay(date.weekday())
                yield day


class SchoolDayTemplates(DayTemplateSchedule):
    implements(interfaces.ISchoolDayTemplates)

    starting_index = 0

    def getDayIndex(self, schedule, schooldays, date):
        assert self.templates
        day_index = self.starting_index
        if date == schedule.first:
            return day_index

        if date > schedule.first:
            skip_dates = DateRange(schedule.first, date - date.resolution)
        else:
            skip_dates = DateRange(date + date.resolution, schedule.first)
        skipped_schooldays = len(list(schooldays.iterDates(skip_dates)))
        if date < schedule.first:
            skipped_schooldays = -skipped_schooldays

        day_index = (day_index + skipped_schooldays) % len(self.templates)
        return day_index

    def iterDates(self, dates):
        if not self.templates:
            for date in dates:
                yield None
            return
        schedule = interfaces.ISchedule(self)
        scheduled_dates = DateRange(schedule.first, schedule.last)
        schooldays = interfaces.ISchooldays(schedule)
        prev_index = None
        prev_date = None
        for date in dates:
            if (prev_date is not None and
                date - prev_date != date.resolution):
                # This is not the next day, reset day index
                prev_index = None

            if (date not in scheduled_dates or
                date not in schooldays):
                # Not a scheduled schoolday
                yield None
            else:
                if prev_index is None:
                    day_index = self.getDayIndex(schedule, schooldays, date)
                else:
                    day_index = (prev_index + 1) % len(self.templates)
                keys = self.templates.keys()
                yield self.templates[keys[day_index]]
                prev_index = day_index
            prev_date = date


@adapter(interfaces.IDayTemplateSchedule)
@implementer(interfaces.ISchedule)
def getScheduledTemplatesSchedule(day_templates):
    return day_templates.__parent__
