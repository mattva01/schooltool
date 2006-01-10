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
Unit tests for schooltool.attendance.sparkline

$Id$
"""

import unittest
import datetime

from pytz import utc, timezone
from zope.testing import doctest
from zope.app.testing import setup, ztapi

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.app import getApplicationPreferences
from schooltool.calendar.simple import ImmutableCalendar, SimpleCalendarEvent
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.term import Term
from schooltool.testing import setup as stsetup
from schooltool.attendance.interfaces import UNKNOWN, PRESENT, ABSENT, TARDY
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import IDayAttendance


def setUp(test):
    setup.placefulSetUp()
    stsetup.setupCalendaring()


def tearDown(test):
    setup.placefulTearDown()


def show_image_as_text(img, extracolors={}):
    r"""Represent a small PIL image as ASCII text.

    The image should be 24-bit RGB data.

    Each pixel is represented by a single character:

        # -- black
        - -- white
        R/G/B/C/M/Y -- bright red/green/blue/cyan/magenta/yellow
        ? -- all other colors

    You can override or extend the mapping by passing in ``extracolors``,
    which is a mapping of colors (3-character long strings '\xRR\xGG\xBB')
    to characters.

    Example:

        show_img(img, extracolors={'\x80\x80\x80': '+'})

    """
    w, h = img.size
    data = img.tostring()
    assert len(data) == w*h*3
    colormap = {'\x00\x00\x00': '#',
                '\xFF\x00\x00': 'R',
                '\x00\xFF\x00': 'G',
                '\x00\x00\xFF': 'B',
                '\x00\xFF\xFF': 'C',
                '\xFF\x00\xFF': 'M',
                '\xFF\xFF\x00': 'Y',
                '\xFF\xFF\xFF': '-'}
    colormap.update(extracolors)
    unknown_colours = set()
    for i in range(0, w*h*3, 3):
        if data[i:i+3] not in colormap:
            unknown_colours.add(data[i:i+3])
    for j in range(0, w*h*3, w*3):
        print ''.join(colormap.get(data[i:i+3], '?')
                      for i in range(j, j+w*3, 3))
    if unknown_colours:
        print "Unrecognized colors:"
        for c in sorted(unknown_colours):
            print r"  '\x%02X\x%02X\x%02X'" % tuple(map(ord, c))


class AttendanceRecordStub:
    def __init__(self, status, explained=None, section=None):
        self.status = status
        self.explained = explained
        self.section = section

    def isUnknown(self):
        return self.status == UNKNOWN
    def isPresent(self):
        return self.status == PRESENT
    def isAbsent(self):
        return self.status == ABSENT
    def isTardy(self):
        return self.status == TARDY
    def isExplained(self):
        return self.explained

    def __str__(self):
        expl = ''
        if self.explained:
            expl = ' (%s)' % self.explained
        return str(self.status) + expl


class SectionAttendanceStub:
    def __init__(self, section):
        self.section = section

    def getAllForDay(self, date):
        result = []
        if date == datetime.date(2005, 9, 29):
            result.append(AttendanceRecordStub(UNKNOWN, section=self.section))
        if date == datetime.date(2005, 10, 4):
            result.append(AttendanceRecordStub(UNKNOWN, section=self.section))
            result.append(AttendanceRecordStub(TARDY, 'lazy',
                                               section=self.section))
            result.append(AttendanceRecordStub(ABSENT, section=self.section))
        if date == datetime.date(2005, 10, 6):
            result.append(AttendanceRecordStub(PRESENT, section=self.section))
        if date == datetime.date(2005, 10, 11):
            result.append(AttendanceRecordStub(TARDY, 'ill',
                                               section=self.section))
        if date == datetime.date(2005, 10, 20):
            result.append(AttendanceRecordStub(ABSENT, section=self.section))
        return result


class DayAttendanceStub:
    def get(self, day):
        if day == datetime.date(2005, 9, 20):
            return AttendanceRecordStub(UNKNOWN)
        if day == datetime.date(2005, 9, 22):
            return AttendanceRecordStub(PRESENT)
        if day == datetime.date(2005, 9, 27):
            return AttendanceRecordStub(ABSENT, 'birthday')
        if day == datetime.date(2005, 9, 29):
            return AttendanceRecordStub(PRESENT)
        if day == datetime.date(2005, 10, 4):
            return AttendanceRecordStub(UNKNOWN)
        if day == datetime.date(2005, 10, 6):
            return AttendanceRecordStub(PRESENT)
        if day == datetime.date(2005, 10, 11):
            return AttendanceRecordStub(PRESENT)
        if day == datetime.date(2005, 10, 13):
            return AttendanceRecordStub(ABSENT)
        if day == datetime.date(2005, 10, 18):
            return AttendanceRecordStub(UNKNOWN)
        if day == datetime.date(2005, 10, 20):
            return AttendanceRecordStub(PRESENT)
        unknown = AttendanceRecordStub(UNKNOWN)
        return unknown


class PersonStub:
    def __init__(self, section):
        self.section_attendance = SectionAttendanceStub(section)

    def __conform__(self, iface):
        if iface is ISectionAttendance:
            return self.section_attendance
        if iface is IDayAttendance:
            return DayAttendanceStub()


class CalendarStub:
    events = [datetime.datetime(2005, 9, 29, 9, 0, tzinfo=utc),
              datetime.datetime(2005, 10, 4, 9, 0, tzinfo=utc),
              datetime.datetime(2005, 10, 6, 9, 0, tzinfo=utc),
              datetime.datetime(2005, 10, 11, 9, 0, tzinfo=utc),
              datetime.datetime(2005, 10, 20, 9, 0, tzinfo=utc)]

    def expand(self, from_time, to_time):
        for ev in self.events:
            if from_time <= ev <= to_time:
                return [ev]
        return []


class TimetablesStub:
    def makeTimetableCalendar(self):
        return CalendarStub()


class SectionStub:

    timetables = TimetablesStub()

    def __conform__(self, iface):
        if iface is ITimetables:
            return self.timetables


def doctest_AttendanceSparkline():
    r"""Tests for AttendanceSparkline

    Create simple sparkline:

        >>> section = SectionStub()
        >>> person = PersonStub(section)
        >>> date = datetime.date(2005, 10, 25)
        >>> from schooltool.attendance.sparkline import AttendanceSparkline
        >>> sparkline = AttendanceSparkline(person, section, date)

    Test AttendanceSparkline.getLastSchooldays.

    We need schooltool application for timezone preference and terms.

        >>> app = stsetup.setupSchoolToolSite()
        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                     IApplicationPreferences,
        ...                     getApplicationPreferences)
        >>> prefs = IApplicationPreferences(app)
        >>> prefs.timezone = 'UTC'
        >>> term = Term('test-term', datetime.date(2005, 9, 16),
        ...             datetime.date(2005, 11, 1))
        >>> term.addWeekdays(1, 3)
        >>> app['terms']['test-term'] = term

    Take look at last 12 schooldays (we should get only 10):

        >>> last_days = sparkline.getLastSchooldays(12)
        >>> for day in last_days:
        ...     print day
        2005-09-20
        2005-09-22
        2005-09-27
        2005-09-29
        2005-10-04
        2005-10-06
        2005-10-11
        2005-10-13
        2005-10-18
        2005-10-20

    Test AttendanceSparkline.getRecordsForDay:

        >>> records = sparkline.getRecordsForDay(datetime.date(2005, 10, 4))
        >>> for record in records:
        ...     print record
        UNKNOWN
        TARDY (lazy)
        ABSENT

    Test AttendanceSparkline.getWorstRecordForDay:

        >>> record = sparkline.getWorstRecordForDay(datetime.date(2005, 10, 4))
        >>> print record
        ABSENT

    Test AttendanceSparkline.getData:

        >>> data = sparkline.getData()
        >>> for item in data:
        ...     print item
        ('dot', 'black', '+')
        ('half', 'black', '+')
        ('half', 'black', '-')
        ('dot', 'black', '+')
        ('full', 'yellow', '-')
        ('full', 'black', '+')
        ('full', 'black', '-')
        ('half', 'yellow', '-')
        ('dot', 'black', '+')
        ('full', 'red', '-')

    """


def doctest_AttendanceSparkline_render():
    r"""Tests for AttendanceSparkline render* methods.

        >>> from schooltool.attendance.sparkline import AttendanceSparkline
        >>> sparkline = AttendanceSparkline('person', 'section', 'date')
        >>> sparkline.getData = lambda: [('dot', 'black', '+'),
        ...                              ('half', 'black', '+'),
        ...                              ('half', 'black', '-'),
        ...                              ('dot', 'black', '+'),
        ...                              ('full', 'green', '-'),
        ...                              ('full', 'black', '+'),
        ...                              ('full', 'black', '-'),
        ...                              ('half', 'green', '-'),
        ...                              ('dot', 'black', '+'),
        ...                              ('full', 'red', '-')]
        >>> sparkline.colors = {'black': '#000000', 'red': '#ff0000',
        ...                     'green': '#00ff00'}

    Test AttendanceSparkline.render and renderAsPngData:

        >>> sparkline.width = 14
        >>> png = sparkline.render()
        >>> png
        <PIL.Image.Image instance ...>

        >>> show_image_as_text(png)
        ---------------------------##-------------
        ---------------------------##-------------
        ---------------------------##-------------
        ---------------##----------##-------------
        ---------------##----------##-------------
        ---------------##----------##-------------
        ------------##-##-##-##-GG-##-##-GG-##-RR-
        ------------------##----GG----##-GG----RR-
        ------------------##----GG----##-GG----RR-
        ------------------##----GG----##-GG----RR-
        ------------------------GG----##-------RR-
        ------------------------GG----##-------RR-

        >>> png_data = sparkline.renderAsPngData()
        >>> print png_data.encode('base64')
        iVBORw0KGgoAAAANSUhEUgAAACoAAAAMCAIAAACbVLgnAAAAtklEQVR4nGL8//8/A1UBIyMjAwMD
        kcYCAAAA//9ioq7dpAIAAAAA//8aYOsBAAAA//8izXpGRkZI2FILAAAAAP//GmDfAwAAAP//GmDr
        AQAAAP//Isp6zDCHiyAYDIyMDDjUwKQQ5jAyMjAyMjAwAAAAAP//YiHGenguwsxOxIjgkQIAAAD/
        /xrgwAcAAAD//xpg6wEAAAD//yIq8DEBSWXlfwacigEAAAD//xpg3wMAAAD//wMABnIaNUZ2BAMA
        AAAASUVORK5CYII=
        <BLANKLINE>

    """


def doctest_AttendanceSparkline_sectionMeetsOn():
    """Tests for AttendanceSparkline.sectionMeetsOn.

        >>> from schooltool.attendance.sparkline import AttendanceSparkline
        >>> as = AttendanceSparkline(None, None, None)

    Europe/Vilnius is a good timezone for unit tests, because its UTC offset
    has changed historically, which lets you catch certain timezone-related
    bugs.

        >>> tz = timezone('Europe/Vilnius')

    On 2005-07-28 the UTC offset is +03:00, and the school day starts on
    2005-07-27 21:00 UTC and ends on 2005-07-28 21:00 UTC

    On 2005-12-28 the UTC offset is +02:00, and the school day starts on
    2005-12-27 22:00 UTC and ends on 2005-12-28 22:00 UTC

        >>> section_calendar = ImmutableCalendar([
        ...     SimpleCalendarEvent(datetime.datetime(2005, 7, 27, 21, 30),
        ...                         datetime.timedelta(hours=1),
        ...                         '2005-07-28 EEST'),
        ...     SimpleCalendarEvent(datetime.datetime(2005, 7, 30, 19, 30),
        ...                         datetime.timedelta(hours=1),
        ...                         '2005-07-30 EEST'),
        ...     SimpleCalendarEvent(datetime.datetime(2005, 12, 27, 22, 30),
        ...                         datetime.timedelta(hours=1),
        ...                         '2005-12-28 EET'),
        ...     SimpleCalendarEvent(datetime.datetime(2005, 12, 30, 20, 30),
        ...                         datetime.timedelta(hours=1),
        ...                         '2005-12-30 EET'),
        ... ])

        >>> as.sectionMeetsOn(datetime.date(2005, 7, 27), tz, section_calendar)
        False
        >>> as.sectionMeetsOn(datetime.date(2005, 7, 28), tz, section_calendar)
        True
        >>> as.sectionMeetsOn(datetime.date(2005, 7, 29), tz, section_calendar)
        False
        >>> as.sectionMeetsOn(datetime.date(2005, 7, 30), tz, section_calendar)
        True
        >>> as.sectionMeetsOn(datetime.date(2005, 7, 31), tz, section_calendar)
        False

        >>> as.sectionMeetsOn(datetime.date(2005, 12, 27), tz, section_calendar)
        False
        >>> as.sectionMeetsOn(datetime.date(2005, 12, 28), tz, section_calendar)
        True
        >>> as.sectionMeetsOn(datetime.date(2005, 12, 29), tz, section_calendar)
        False
        >>> as.sectionMeetsOn(datetime.date(2005, 12, 30), tz, section_calendar)
        True
        >>> as.sectionMeetsOn(datetime.date(2005, 12, 31), tz, section_calendar)
        False

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
