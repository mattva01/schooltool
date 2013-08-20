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
Schedule and timetabling interfaces
"""

import pytz

import zope.schema
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import Interface, Attribute
from zope.container.constraints import contains
from zope.container.interfaces import IContainer, IOrderedContainer
from zope.container.interfaces import IContained

from schooltool.app.interfaces import ISchoolToolCalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IHaveCalendar
from schooltool.app.utils import vocabulary
from schooltool.calendar.interfaces import ICalendar

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
        unique within the schedule that generated it.
        """,
        required=False)

    def clone(dtstart=None, duration=None,
              period=None, meeting_id=None):
        """Return a copy of the meeting with replaced given values."""


class ISchedule(Interface):
    """A schedule of meetings."""

    title = zope.schema.TextLine(
        title=u"Title of the timetable",
        required=True)

    first = zope.schema.Date(
        title=_("First scheduled day"),
        required=True)

    last = zope.schema.Date(
        title=_("Last scheduled day"),
        required=True)

    timezone = zope.schema.Choice(
        title=u"Time Zone",
        description=u"Meetings time zone",
        values=pytz.common_timezones,
        required=True)

    def iterMeetings(date, until_date=None):
        """Yields meetings for the given date range."""


class IMeetingException(IMeeting):
    """A persistent exception meeting."""


class IScheduleExceptions(Interface):

    # XXX: if exception values were objects instead of meeting lists
    #      we could log additional info, like reason for the exception
    exceptions = zope.schema.Dict(
        title=_("Exceptions"),
        description=_("Exceptions by date."),
        key_type=zope.schema.Date(
            title=_("Exception date")),
        value_type=zope.schema.List(
            title=_("Meetings"),
            value_type = zope.schema.Object(
                title=_("Meeting"),
                schema=IMeetingException),
            ),
        )

    def iterOriginalMeetings(date, until_date=None):
        """Yields meetings disregarding exception dates."""


class IScheduleWithExceptions(ISchedule, IScheduleExceptions):
    """Schedule with exception days."""


class IScheduleContainer(IContainer, IScheduleWithExceptions):
    """A container of schedules.

    The container itself is as a big composite schedule.
    """
    contains(ISchedule)

    first = zope.schema.Date(
        title=u"First scheduled day",
        required=False)

    last = zope.schema.Date(
        title=u"Last scheduled day",
        required=False)


#
#  Day templates
#

class IDayTemplate(IOrderedContainer):
    title = zope.schema.TextLine(
        title=u"Title of the day",
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
        required=False,
        default="lesson",
        vocabulary=activity_types)


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


class ITimetable(IScheduleWithExceptions):
    """The schedule of meetings built from day templates."""

    periods = zope.schema.Object(
        title=u"Periods",
        schema=IDayTemplateSchedule,
        required=True)

    time_slots = zope.schema.Object(
        title=u"Time slots",
        schema=IDayTemplateSchedule,
        required=True)


class ITimetableContainerBase(Interface):

    default = zope.schema.Object(
        title=u"The default timetable",
        schema=ITimetable,
        required=False)


class ITimetableContainer(IContainer, ITimetableContainerBase):
    """A container of timetables."""
    contains(ITimetable)


class ISelectedPeriodsScheduleRead(ISchedule):

    timetable = zope.schema.Object(
        title=u"Timetable to filter meetings from",
        schema=ITimetable,
        required=False)

    periods = Attribute(
        """Iterate only over meetings for these periods.""")

    consecutive_periods_as_one = zope.schema.Bool(
        title=_("Treat consecutive periods as one meeting"),
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


class IScheduleCalendarEvent(IMeeting, ISchoolToolCalendarEvent):
    """Calendar event that forms a schedule."""

    schedule = zope.schema.Object(
        title=u"Schedule that generated this event.",
        schema=ISchedule,
        required=False)


class IImmutableScheduleCalendar(ICalendar):
    """Calendar representation of a schedule."""


class IScheduleCalendar(ISchoolToolCalendar):
    """Persistent calendar of a schedule."""

    def updateSchedule(schedule):
        """Update calendar with events from this schedule."""

    def removeSchedule(schedule):
        """Remove events generated by this schedule."""


#
#  Integration
#


class IHaveSchedule(IAttributeAnnotatable, IHaveCalendar):
    """Marker interface for objects that schedule existing timetables."""


class IHaveTimetables(IAttributeAnnotatable):
    """Marker interface for objects that have timetables."""


#
#  Security
#


class IScheduleParentCrowd(Interface):
    """A crowd object that is used on a schedule's parent.

    This is just a marker interface.
    """

    def contains(principal):
        """Return True if principal is in the crowd."""
