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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Period and time slot schedule templates.
Template scheduling over dates.
"""

from persistent import Persistent
from zope.interface import implements, implementer
from zope.component import adapts, adapter
from zope.container.contained import Contained
from zope.container.ordered import OrderedContainer
from zope.container.contained import containedEvent
from zope.event import notify

from schooltool.common import DateRange
from schooltool.timetable import interfaces
from schooltool.schoolyear.interfaces import ISchoolYear


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


class PeriodWithTime(Persistent, Contained):
    implements(interfaces.IPeriodWithTime)

    title = None
    activity_type = None
    tstart = None
    duration = None

    def __init__(self, title, tstart, duration, activity_type=None):
        Contained.__init__(self)
        self.title = title
        self.tstart = tstart
        self.duration = duration
        self.activity_type = activity_type


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
        return u'%d' % weekday

    def getWeekDay(self, weekday):
        assert self.templates is not None
        key = self.getWeekDayKey(weekday)
        return self.templates.get(key, None)

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
        skipped_schooldays = len(schooldays.iter(skip_dates))
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


class Schooldays(object):
    adapts(interfaces.ISchedule)
    implements(interfaces.ISchooldays)

    def __init__(self, context):
        # XXX: maybe use ITermContainer instead?
        self.schedule = context
        self.schoolyear = ISchoolYear(context)

    def __contains__(self, date):
        for term in self.schoolyear.values():
            if date in term:
                return term.isSchoolday(date)
        return False

    def __iter__(self):
        schedule = self.schedule
        dates = DateRange(schedule.first, schedule.last)
        return self.iterDates(dates)

    def iterDates(self, dates):
        for date in dates:
            if date in self:
                yield date


@adapter(interfaces.IDayTemplateSchedule)
@implementer(interfaces.ISchedule)
def getScheduledTemplatesSchedule(day_templates):
    return day_templates.__parent__
