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

from zope.testing import doctest
from zope.interface.verify import verifyObject
from zope.app.testing import ztapi, setup

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable.interfaces import ITimetables


class TermStub(object):
    first = datetime.date(2005, 9, 1)
    last = datetime.date(2005, 9, 14)

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

class FakeAttendanceAdapter(object):
    def __init__(self, person):
        self.person = person
    def record(self, section, dtstart, duration, period_id, present):
        print "%s was %s on %s (%s, %s)" % (self.person,
                    {True: 'present', False: 'absent'}[present], dtstart,
                    period_id, section)


def doctest_SectionAttendancePlugin():
    r"""Tests for SectionAttendancePlugin

        >>> from schooltool.attendance.sampledata \
        ...     import SectionAttendancePlugin
        >>> plugin = SectionAttendancePlugin()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    The plugin wants an application object with 'sections' and 'terms'
    containers.  It is easier to use stubs:

        >>> app = {'terms': {'2005-fall': TermStub()},
        ...        'sections': {'s1': SectionStub('s1'),
        ...                     's2': SectionStub('s2')}}

        >>> app['sections']['s1'].members = ['Jon', 'Ian']
        >>> app['sections']['s2'].members = ['Ann']

    The "sections" need to be adaptable to ITimetables

        >>> ztapi.provideAdapter(None, ITimetables, FakeTimetablesAdapter)

    And section members need to be adaptable to ISectionAttendance

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> ztapi.provideAdapter(None, ISectionAttendance,
        ...                      FakeAttendanceAdapter)

    Now we can generate some sample data

        >>> plugin.generate(app, seed=42)
        Ann was present on 2005-09-01 09:30:00 (p1, s2)
        Ann was present on 2005-09-03 09:30:00 (p1, s2)
        Ann was present on 2005-09-05 09:30:00 (p1, s2)
        Ann was present on 2005-09-07 09:30:00 (p1, s2)
        Ann was present on 2005-09-09 09:30:00 (p1, s2)
        Ann was present on 2005-09-11 09:30:00 (p1, s2)
        Ann was present on 2005-09-13 09:30:00 (p1, s2)
        Jon was present on 2005-09-01 09:30:00 (p1, s1)
        Jon was present on 2005-09-03 09:30:00 (p1, s1)
        Jon was present on 2005-09-05 09:30:00 (p1, s1)
        Jon was present on 2005-09-07 09:30:00 (p1, s1)
        Jon was present on 2005-09-09 09:30:00 (p1, s1)
        Jon was present on 2005-09-11 09:30:00 (p1, s1)
        Jon was present on 2005-09-13 09:30:00 (p1, s1)
        Ian was present on 2005-09-01 09:30:00 (p1, s1)
        Ian was present on 2005-09-03 09:30:00 (p1, s1)
        Ian was present on 2005-09-05 09:30:00 (p1, s1)
        Ian was present on 2005-09-07 09:30:00 (p1, s1)
        Ian was present on 2005-09-09 09:30:00 (p1, s1)
        Ian was absent on 2005-09-11 09:30:00 (p1, s1)
        Ian was present on 2005-09-13 09:30:00 (p1, s1)

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setup.placelessSetUp,
                                tearDown=setup.placelessTearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
