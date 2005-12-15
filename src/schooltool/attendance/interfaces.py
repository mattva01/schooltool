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
Attendance tracking interfaces.

$Id$
"""
__docformat__ = 'reStructuredText'


from zope.interface import Interface
from zope.schema import Text, TextLine, Choice, List, Object
from zope.schema import Date, Datetime, Timedelta

from schooltool.course.interfaces import ISection


class IAttendance(Interface):
    """Common functions for attendance tracking."""

    def __iter__():
        """Return all recorded attendance records.

        None of the returned records will have status == UNKNOWN.
        """

    def filter(first, last):
        """Return all recorded attendance records within a given date range.

        Considers only those attendace records (ar) for which
        first <= ar.date <= last, and ar.status is ABSENT or TARDY.

        None of the returned records will have status == UNKNOWN.
        """

    def makeCalendar(first, last):
        """Return attendance incidents as calendar events.

        Considers only those attendace records (ar) for which
        first <= ar.date <= last, and ar.status is ABSENT or TARDY.
        """


class IDayAttendance(IAttendance):
    """A set of all student's day attendance records."""

    def get(date):
        """Return the attendance record for a specific day.

        Always succeeds, but the returned attendance record may be
        "unknown".
        """

    def record(date, present):
        """Record the student's absence or presence.

        You can only record the absence or presence once for a given date.
        """


class ISectionAttendance(IAttendance):
    """A set of all student's section attendance records."""

    def get(section, datetime):
        """Return the attendance record for a specific section meeting.

        Always succeeds, but the returned attendance record may be
        "unknown".
        """

    def getAllForDay(date):
        """Return all recorded attendance records for a specific day."""

    def record(section, datetime, duration, period_id, present):
        """Record the student's absence or presence.

        You can record the absence or presence only once for a given
        (section, datetime) pair.
        """


NEW = 'NEW'
ACCEPTED = 'ACCEPTED'
REJECTED = 'REJECTED'


class IAbsenceExplanation(Interface):
    """An explanation of the absence"""

    status = Choice(
        title=u"Status",
        description=u"""
        Status of the explanation: NEW, ACCEPTED, or REJECTED.
        """,
        values=[NEW, ACCEPTED, REJECTED])

    text = Text(
        title=u"Text",
        description=u"""Text of the explanation""")

    def isAccepted():
        """True if status is ACCEPTED"""

    def accept():
        """Make this explanation accepted"""

    def reject():
        """Make this explanation rejected"""


UNKNOWN = 'UNKNOWN'
PRESENT = 'PRESENT'
ABSENT = 'ABSENT'
TARDY = 'TARDY'


class IAttendanceRecord(Interface):
    """A single attendance record for a day/section."""

    date = Date(
        title=u"Date",
        description=u"""
        Date of the record.
        """)

    status = Choice(
        title=u"Status",
        description=u"""
        Attendance status (UNKNOWN, PRESENT, ABSENT, TARDY).
        """,
        values=[UNKNOWN, PRESENT, ABSENT, TARDY])

    late_arrival = Datetime(
        title=u"Date/time of late arrival",
        description=u"""
        Date and time of a late arrival.

        None if status != TARDY.
        """)

    explanations = List(
        title=u"Explanations",
        description=u"""
        A list of explanations for this record.

        Only valid if the status is ABSENT or TARDY.
        """,
        value_type=Object(schema=IAbsenceExplanation))

    def isUnknown(): """True if status == UNKNOWN."""
    def isPresent(): """True if status == PRESENT."""
    def isAbsent():  """True if status == ABSENT."""
    def isTardy():   """True if status == TARDY."""

    def isExplained():
        """Is the absence/tardy explained?

        Raises AttendanceError when status == UNKNOWN or PRESENT.
        """

    def addExplanation(text):
        """Adds a new explanation for this attendance record."""

    def makeTardy(arrived):
        """Convert an absence to a tardy.

        `arrived` is a datetime.datetime.

        Raises AttendanceError when status != ABSENT.
        """


class IDayAttendanceRecord(IAttendanceRecord):
    """A single attendance record for a day."""


class ISectionAttendanceRecord(IAttendanceRecord):
    """A single attendance record for a section."""

    section = Object(
        title=u"Section.",
        schema=ISection)

    datetime = Datetime(
        title=u"Date/time",
        description=u"""The date and time of the section meeting.""")

    duration = Timedelta(
        title=u"Duration",
        description=u"""The duration of the section meeting.""")

    period_id = TextLine(
        title=u"ID of the period.")


class AttendanceError(Exception):
    """Attendance tracking error."""

