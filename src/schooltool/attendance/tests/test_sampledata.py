#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Unit tests for schooltool.attendance.sampledata.

$Id$
"""

__docformat__ = 'reStructuredText'

import unittest
import datetime
import random

from zope.testing import doctest
from zope.interface.verify import verifyObject
from zope.app.testing import ztapi, setup

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable.interfaces import ITimetables


class TermStub(object):
    first = datetime.date(2005, 9, 1)
    last = datetime.date(2005, 9, 14)

    def __iter__(self):
        date = self.first
        while date <= self.last:
            yield date
            date += datetime.date.resolution

    def isSchoolday(self, date):
        return date.day % 2 == 1


class SectionStub(object):
    members = ()
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name


class TimetableCalendarEventStub(object):
    def __init__(self, dtstart, duration, period_id):
        self.dtstart = dtstart
        self.duration = duration
        self.period_id = period_id


class FakeTimetablesAdapter(object):
    def __init__(self, section):
        self.section = section
    def makeTimetableCalendar(self, first, last):
        events = []
        while first <= last:
            dtstart = datetime.datetime.combine(first, datetime.time(9, 30))
            duration = datetime.timedelta(minutes=45)
            period_id = 'p1'
            e = TimetableCalendarEventStub(dtstart, duration, period_id)
            events.append(e)
            first += datetime.timedelta(2)
        return events


class FakeAttendanceRecord(object):
    def __init__(self):
        self.hasExplanations = False
        self.accepted = False
        self.rejected = False

    def makeTardy(self, datetime):
        print "Tardy at %s" % datetime

    def addExplanation(self, explanation):
        self.hasExplanations = True

    def acceptExplanation(self):
        self.accepted = True

    def rejectExplanation(self):
        self.rejected = True


class FakeAttendanceAdapter(object):
    def __init__(self, person):
        self.person = person

    def record(self, section, dtstart, duration, period_id, present):
        print "%s was %s on %s (%s, %s)" % (self.person,
                    {True: 'present', False: 'absent'}[present], dtstart,
                    period_id, section)

    def get(self, section, datetime):
        return FakeAttendanceRecord()


class FakeDayAttendanceAdapter(object):
    def __init__(self, person):
        self.person = person

    def record(self, date, present):
        print "%s was %s on %s" % (self.person,
                                   {True: 'present',
                                    False: 'absent'}[present],
                                   date)

def doctest_SectionAttendancePlugin_explainAttendanceRecord():
    """Tests for SectionAttendancePlugin.explainAttendanceRecord.

        >>> from schooltool.attendance.sampledata import SectionAttendancePlugin
        >>> plugin = SectionAttendancePlugin()

    Whether an attendance record will be explained or not depends on
    the explanation_rate.

        >>> plugin.rng = random.Random(42)
        >>> plugin.explanation_rate = 1
        >>> for i in range(100):
        ...     ar = FakeAttendanceRecord()
        ...     plugin.explainAttendanceRecord(ar)
        ...     assert(ar.hasExplanations)

    The explanation being accepted depends on the excuse_rate:

        >>> plugin.excuse_rate = 1
        >>> for i in range(100):
        ...     ar = FakeAttendanceRecord()
        ...     plugin.explainAttendanceRecord(ar)
        ...     assert(ar.hasExplanations)
        ...     assert(ar.accepted)

     Rejection depends on reject_rate:

        >>> plugin.excuse_rate = 0
        >>> plugin.reject_rate = 1
        >>> for i in range(100):
        ...     ar = FakeAttendanceRecord()
        ...     plugin.explainAttendanceRecord(ar)
        ...     assert(ar.hasExplanations)
        ...     assert(ar.rejected)

    """


def doctest_SectionAttendancePlugin_generateDayAttendance():
    """Tests for SectionAttendancePlugin.generateDayAttendance

        >>> from schooltool.attendance.sampledata import SectionAttendancePlugin
        >>> plugin = SectionAttendancePlugin()

        >>> app = {'terms': {'2005-fall': TermStub()},
        ...        'persons': {'student_Jon': 'Jon',
        ...                    'student_Ian': 'Ian',
        ...                    'teacher_Ann': 'Ann'}}
        >>> plugin.app = app
        >>> plugin.term = app['terms']['2005-fall']
        >>> plugin.start_date = plugin.term.last - datetime.timedelta(days=3)
        >>> plugin.end_date = plugin.term.last
        >>> plugin.rng = random.Random(42)
        >>> plugin.day_absence_rate = 1


    Persons need to be adaptable to IDayAttendance

        >>> from schooltool.attendance.interfaces import IDayAttendance
        >>> ztapi.provideAdapter(None, IDayAttendance,
        ...                      FakeDayAttendanceAdapter)

    Only students are marked as absent/present:

        >>> print sorted(plugin.generateDayAttendance().items())
        Jon was absent on 2005-09-11
        Ian was absent on 2005-09-11
        Jon was absent on 2005-09-13
        Ian was absent on 2005-09-13
        [('2005-09-11', ['Jon', 'Ian']),
         ('2005-09-13', ['Jon', 'Ian'])]

    Unless the abscence rate is 0:

        >>> plugin.day_absence_rate = 0
        >>> print sorted(plugin.generateDayAttendance().items())
        Jon was present on 2005-09-11
        Ian was present on 2005-09-11
        Jon was present on 2005-09-13
        Ian was present on 2005-09-13
        [('2005-09-11', []),
         ('2005-09-13', [])]

    """


def doctest_SectionAttendancePlugin_generateSectionAttendance():
    """Tests for SectionAttendancePlugin.generateDayAttendance

        >>> from schooltool.attendance.sampledata import SectionAttendancePlugin
        >>> plugin = SectionAttendancePlugin()

    The plugin wants an application object with 'sections' and 'terms'
    containers.  It is easier to use stubs:

        >>> term = TermStub()
        >>> app = {'terms': {'2005-fall': term},
        ...        'sections': {'s1': SectionStub('s1'),
        ...                     's2': SectionStub('s2')}}

        >>> app['sections']['s1'].members = ['Jon', 'Ian']
        >>> app['sections']['s2'].members = ['Ann']
        >>> plugin.app = app
        >>> plugin.term = term
        >>> plugin.start_date = term.first
        >>> plugin.end_date = term.last
        >>> plugin.rng = random.Random(42)
        >>> plugin.day_absences = []

    The "sections" need to be adaptable to ITimetables

        >>> ztapi.provideAdapter(None, ITimetables, FakeTimetablesAdapter)

    And section members need to be adaptable to ISectionAttendance

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> ztapi.provideAdapter(None, ISectionAttendance,
        ...                      FakeAttendanceAdapter)

    Now we can generate some sample data

        >>> plugin.generateSectionAttendance()
        Ann was present on 2005-09-01 09:30:00 (p1, s2)
        Ann was absent on 2005-09-03 09:30:00 (p1, s2)
        Tardy at 2005-09-03 09:45:00
        Ann was present on 2005-09-05 09:30:00 (p1, s2)
        Ann was present on 2005-09-07 09:30:00 (p1, s2)
        Ann was present on 2005-09-09 09:30:00 (p1, s2)
        Ann was absent on 2005-09-11 09:30:00 (p1, s2)
        Tardy at 2005-09-11 09:45:00
        Ann was absent on 2005-09-13 09:30:00 (p1, s2)
        Tardy at 2005-09-13 09:45:00
        Jon was present on 2005-09-01 09:30:00 (p1, s1)
        Ian was present on 2005-09-01 09:30:00 (p1, s1)
        Jon was present on 2005-09-03 09:30:00 (p1, s1)
        Ian was present on 2005-09-03 09:30:00 (p1, s1)
        Jon was absent on 2005-09-05 09:30:00 (p1, s1)
        Tardy at 2005-09-05 09:45:00
        Ian was present on 2005-09-05 09:30:00 (p1, s1)
        Jon was present on 2005-09-07 09:30:00 (p1, s1)
        Ian was present on 2005-09-07 09:30:00 (p1, s1)
        Jon was present on 2005-09-09 09:30:00 (p1, s1)
        Ian was present on 2005-09-09 09:30:00 (p1, s1)
        Jon was present on 2005-09-11 09:30:00 (p1, s1)
        Ian was present on 2005-09-11 09:30:00 (p1, s1)
        Jon was present on 2005-09-13 09:30:00 (p1, s1)
        Ian was present on 2005-09-13 09:30:00 (p1, s1)

    Let's shift the start date a bit, and reset the rng:

        >>> plugin.start_date = term.last - datetime.timedelta(days=3)
        >>> plugin.rng = random.Random(42)
        >>> plugin.generateSectionAttendance()
        Ann was present on 2005-09-11 09:30:00 (p1, s2)
        Ann was absent on 2005-09-13 09:30:00 (p1, s2)
        Tardy at 2005-09-13 09:45:00
        Jon was present on 2005-09-11 09:30:00 (p1, s1)
        Ian was present on 2005-09-11 09:30:00 (p1, s1)
        Jon was present on 2005-09-13 09:30:00 (p1, s1)
        Ian was absent on 2005-09-13 09:30:00 (p1, s1)
        Tardy at 2005-09-13 09:45:00

    If there was a day abscence - the student should not be present in
    any of the section events (even if absence_rate is zero):

        >>> plugin.absence_rate = 0
        >>> plugin.rng = random.Random(42)
        >>> plugin.day_absences = {'2005-09-11': ['Jon'],
        ...                        '2005-09-13': ['Ian']}
        >>> plugin.generateSectionAttendance()
        Ann was present on 2005-09-11 09:30:00 (p1, s2)
        Ann was present on 2005-09-13 09:30:00 (p1, s2)
        Jon was absent on 2005-09-11 09:30:00 (p1, s1)
        Ian was present on 2005-09-11 09:30:00 (p1, s1)
        Jon was present on 2005-09-13 09:30:00 (p1, s1)
        Ian was absent on 2005-09-13 09:30:00 (p1, s1)

    """


def doctest_SectionAttendancePlugin_generate():
    r"""Tests for SectionAttendancePlugin

        >>> from schooltool.attendance.sampledata \
        ...     import SectionAttendancePlugin
        >>> plugin = SectionAttendancePlugin()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    Generate just sets up some attributes of the plugin and delegates
    the generation of data to it's methods.

    Let's stub those methods:

        >>> def generateDayAttendanceStub():
        ...     print 'Generating day attendance data'
        ...     return 'day_attendance_data'
        >>> def generateSectionAttendanceStub():
        ...     print 'Generating section attendance data'
        >>> plugin.generateDayAttendance = generateDayAttendanceStub
        >>> plugin.generateSectionAttendance = generateSectionAttendanceStub

        >>> term = TermStub()
        >>> app = {'terms': {'2005-fall': term}}

    And generate the sample data:

        >>> plugin.generate(app, 42)
        Generating day attendance data
        Generating section attendance data

        >>> plugin.app is app
        True

        >>> plugin.term is term
        True

        >>> plugin.start_date
        datetime.date(2005, 9, 1)

        >>> plugin.end_date
        datetime.date(2005, 9, 14)

        >>> plugin.rng
        <random.Random object at ...>

        >>> plugin.day_absences
        'day_attendance_data'

    Now if we set the only_last_n_days attribute, the start_date
    should get shifted:

        >>> plugin.only_last_n_days = 2
        >>> plugin.generate(app, 42)
        Generating day attendance data
        Generating section attendance data

        >>> plugin.start_date
        datetime.date(2005, 9, 13)

        >>> plugin.end_date
        datetime.date(2005, 9, 14)

    """


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS |
                   doctest.REPORT_NDIFF)
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setup.placelessSetUp,
                                tearDown=setup.placelessTearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
