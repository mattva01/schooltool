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
Schedule and timetabling interfaces
"""

import pytz

import zope.schema
from zope.annotation.interfaces import IAnnotatable
from zope.interface import Interface, Attribute
from zope.container.constraints import contains
from zope.container.interfaces import IContainer, IOrderedContainer
from zope.container.interfaces import IContained

from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.app.utils import vocabulary

from schooltool.common import SchoolToolMessage as _


#
#  Schedule
#

activity_types = vocabulary(
    [("lesson", _("Lesson")),
     ("homeroom", _("Homeroom")),
     ("free", _("Free")),
     ("lunch", _("Lunch")),
     ])


class IPeriod(IContained):
    """A period of activity."""

    title = zope.schema.TextLine(
        title=u"Title of the period.",
        required=False)

    activity_type = zope.schema.Choice(
        title=_("Activity type."),
        required=True,
        default="lesson",
        vocabulary=activity_types)


class IMeeting(Interface):
    """A meeting represents a lesson or other scheduled activity."""

    dtstart = zope.schema.Datetime(
        title=u"Time of the start of the event",
        required=True)

    duration = zope.schema.Timedelta(
        title=u"Timedelta of the duration of the event",
        required=True)

    period = zope.schema.Object(
        title=u"The period to schedule.",
        schema=IPeriod,
        required=False)

    meeting_id = zope.schema.TextLine(
        title=u"Unique identifier of a meeting (lesson)",
        description=u"""
        The meeting_id is an arbitrary identifier of a meeting (lesson),
        the intended use is to mark meetings that are scheduled over several
        periods.
        """,
        required=False)


class ISchedule(Interface):
    """A schedule of meetings."""

    title = zope.schema.TextLine(
        title=u"Title of the timetalbe.",
        required=True)

    first = zope.schema.Date(
        title=u"First scheduled day.",
        required=True)

    last = zope.schema.Date(
        title=u"Last scheduled day.",
        required=True)

    timezone = zope.schema.Choice(
        title=_("Time Zone"),
        description=_("Meetings time zone."),
        values=pytz.common_timezones)

    def iterMeetings(date, until_date):
        """Yields lists of meetings for the given date range."""


class IScheduleContainer(IContainer, ISchedule):
    """A container of schedules.

    The container itself is as a big composite schedule.
    """
    contains(ISchedule)

#
#  Day templates
#

class IDayTemplate(IOrderedContainer):
    title = zope.schema.TextLine(
        title=u"Title of the day.",
        required=False)


class IDayTemplateContainer(IOrderedContainer):
    """Ordered container of day templates."""
    contains(IDayTemplate)


class ITimeSlot(IContained):
    """Time slot designated for an activity."""

    tstart = zope.schema.Time(
        title=u"Time of the start of the event",
        required=True)

    duration = zope.schema.Timedelta(
        title=u"Timedelta of the duration of the event",
        required=True)

    activity_type = zope.schema.Choice(
        title=_("Activity type"),
        required=True,
        default="lesson",
        vocabulary=activity_types)


class IPeriodWithTime(IPeriod, ITimeSlot):
    """A period with time slot for scheduling."""


class IDayTemplateSchedule(IContained):
    """Day templates scheduled by date."""

    templates = zope.schema.Object(
        title=u"The template container.",
        schema=IDayTemplateContainer,
        required=True)

    def iterDates(dates):
        """Yield day templates for given dates."""


class ICalendarDayTemplates(IDayTemplateSchedule):
    """Day templates."""

    starting_index = zope.schema.Int(
        title=u"Starting date should start as Nth day",
        default=0,
        required=True)

    def getDay(schedule, date):
        """Get template for the given date."""


class IWeekDayTemplates(IDayTemplateSchedule):
    """Iterator of day templates."""

    def getWeekDayKey(weekday):
        """Get weekday template container key."""

    def getWeekDay(weekday):
        """Get weekday template."""


class ISchooldays(Interface):
    """XXX: should be moved to term, as schooldays are defined there."""

    def iterDates(dates):
        """Iterate dates that are schooldays."""

    def __iter__():
        """Yield all schoolday dates."""

    def __contains__(date):
        """Return whether the date is a schoolday."""


class ISchoolDayTemplates(IDayTemplateSchedule):
    """Iterator that rotates on schooldays (as opposed to rotating on
    calendar days)"""

    starting_index = zope.schema.Int(
        title=u"Starting date should start as Nth day",
        default=0,
        required=True)


#
#  Timetabling
#


class ITimetable(ISchedule):
    """The schedule of meetings built from day templates."""

    periods = zope.schema.Object(
        title=u"Periods.",
        schema=IDayTemplateSchedule,
        required=True)

    time_slots = zope.schema.Object(
        title=u"Time slots.",
        schema=IDayTemplateSchedule,
        required=True)


class ITimetableContainerBase(Interface):

    default = zope.schema.Object(
        title=u"The default timetable.",
        schema=ITimetable,
        required=False)


class ITimetableContainer(IContainer, ITimetableContainerBase):
    """A container of timetables."""
    contains(ITimetable)


class ISelectedPeriodsScheduleRead(ISchedule):

    timetable = zope.schema.Object(
        title=u"Timetable to filter meetings from.",
        schema=ITimetable,
        required=False)

    periods = Attribute(
        """Iterate only over meetings for these periods.""")

    consecutive_periods_as_one = zope.schema.Bool(
        title=u"Treat consecutive periods as one meeting.",
        default=False,
        required=False)

    def hasPeriod(period):
        """Is the period added to this schedule."""


class ISelectedPeriodsScheduleWrite(Interface):

    def addPeriod(period):
        """Schedule meetings for this period."""

    def removePeriod(period):
        """Unschedule meeting for this period."""


class ISelectedPeriodsSchedule(ISelectedPeriodsScheduleRead,
                               ISelectedPeriodsScheduleWrite):
    """Schedule composed of meetings from another schedule with
    selected periods only."""

    def addPeriod(period):
        """Schedule meetings for this period."""

    def removePeriod(period):
        """Unschedule meeting for this period."""


#
#  Calendar
#


class IScheduledCalendarEvent(IMeeting, ISchoolToolCalendarEvent):
    """Calendar event that forms a schedule."""

    schedule = zope.schema.Object(
        title=u"Schedule that generated this event.",
        schema=ISchedule,
        required=False)


#
#  Integration
#


class IHaveSchedule(IAnnotatable):
    """Marker interface for objects that schedule existing timetables."""


class IHaveTimetables(IAnnotatable):
    """Marker interface for objects that have timetables."""
