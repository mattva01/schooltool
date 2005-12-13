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


from zope.interface import Interface, Attribute


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


UNKNOWN = 'UNKNOWN'
PRESENT = 'PRESENT'
ABSENT = 'ABSENT'
TARDY = 'TARDY'


class IAttendanceRecord(Interface):
    """A single attendance record for a day/section."""

    date = Attribute("""
        Date of the record.
        """)

    status = Attribute("""
        Attendance status (UNKNOWN, PRESENT, ABSENT, TARDY).
        """)

    late_arrival = Attribute("""
        Time of a late arrival.

        None if status != TARDY.
        """)

    def isUnknown(): """True if status == UNKNOWN."""
    def isPresent(): """True if status == PRESENT."""
    def isAbsent():  """True if status == ABSENT."""
    def isTardy():   """True if status == TARDY."""

    def isExplained():
        """Is the absence/tardy explained?

        Raises AttendanceError when status == UNKNOWN or PRESENT.
        """

    def makeTardy(arrived):
        """Convert an absence to a tardy.

        `arrived` is a datetime.time.

        Raises AttendanceError when status != ABSENT.
        """


class IDayAttendanceRecord(IAttendanceRecord):
    """A single attendance record for a day."""


class ISectionAttendanceRecord(IAttendanceRecord):
    """A single attendance record for a section."""

    section = Attribute("""The section object.""")

    datetime = Attribute("""The date and time of the section meeting.""")

    duration = Attribute("""The duration of the section meeting.""")

    period_id = Attribute("""The name of the period.""")


class AttendanceError(Exception):
    """Attendance tracking error."""

