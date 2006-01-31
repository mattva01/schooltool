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
Tests for SchoolTool attendance views

$Id$
"""

import unittest
import datetime
import itertools
import logging
from pprint import pprint

from pytz import utc, timezone
from zope.testing import doctest
from zope.app.testing import ztapi, setup
from zope.publisher.browser import TestRequest
from zope.interface import implements, Interface
from zope.component import adapts, provideAdapter
from zope.app.testing.setup import setUpAnnotations
from zope.i18n import translate

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.timetable import ITimetables
from schooltool.timetable import TimetableActivity
from schooltool.timetable.model import TimetableCalendarEvent
from schooltool.timetable.term import DateRange
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.course.interfaces import ISection
from schooltool.testing.util import fakePath
from schooltool.relationship.tests import setUpRelationships
from schooltool.attendance.tests import stubProcessDefinition
from schooltool.attendance.interfaces import NEW, ACCEPTED, REJECTED
from schooltool.attendance.interfaces import PRESENT, ABSENT, TARDY, UNKNOWN
from schooltool.attendance.interfaces import IDayAttendance
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import IDayAttendanceRecord
from schooltool.attendance.interfaces import ISectionAttendanceRecord
from schooltool.attendance.interfaces import AttendanceError
from schooltool import SchoolToolMessage as _


class TermStub(object):
    def __init__(self, y, m1, d1, m2, d2):
        self.first = datetime.date(y, m1, d1)
        self.last = datetime.date(y, m2, d2)
    def __str__(self):
        return '<TermStub: %s..%s>' % (self.first, self.last)


class SchoolToolApplicationStub(object):
    adapts(None)
    implements(ISchoolToolApplication)
    _terms = {'2004-fall': TermStub(2004, 9, 1, 12, 22),
              '2005-spring': TermStub(2005, 2, 1, 5, 21),
              '2005-fall': TermStub(2005, 9, 1, 12, 22),
              '2006-spring': TermStub(2006, 2, 1, 5, 21)}
    def __init__(self, context):
        pass
    def __getitem__(self, name):
        return {'terms': self._terms}[name]


class ApplicationPreferencesStub(object):
    adapts(ISchoolToolApplication)
    implements(IApplicationPreferences)
    timezone = 'UTC'
    def __init__(self, context):
        pass


class TimetableDayStub(object):
    def __init__(self, periods, homeroom_period_id):
        self.periods = periods
        self.homeroom_period_id = homeroom_period_id


class TimetableStub(object):
    def __init__(self, days):
        self._days = days
    def __getitem__(self, day_id):
        return self._days[day_id]


class TimetableActivityStub(object):
    def __init__(self, timetable, title):
        self.timetable = timetable
        self.title = title


class StubTimetables(object):
    adapts(Interface)
    implements(ITimetables)
    def __init__(self, context):
        self.context = context
        self._tt = TimetableStub({
                        'D1': TimetableDayStub(['A', 'D'], None),
                        'D2': TimetableDayStub(['B', 'C'], 'B'),
                   })

    def makeTimetableCalendar(self, first, last):
        events = [
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 14, 10, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Math", day_id='D1', period_id="A",
                activity=TimetableActivityStub(self._tt, "Math")),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 14, 11, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Arts", day_id='D1', period_id="D",
                activity=TimetableActivityStub(self._tt, "Arts")),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Math", day_id='D2', period_id="B",
                activity=TimetableActivityStub(self._tt, "Math")),
            TimetableCalendarEvent(
                datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
                datetime.timedelta(minutes=45),
                "Arts", day_id='D2', period_id="C",
                activity=TimetableActivityStub(self._tt, "Arts")),
            ]
        return ImmutableCalendar([e for e in events
                                  if first <= e.dtstart.date() <= last])


class DayAttendanceRecordStub(object):
    implements(IDayAttendanceRecord)
    def __init__(self, date, status, explained=False):
        self.date = date
        self.status = status
        self._explained = explained
    def isAbsent(self): return self.status == ABSENT
    def isTardy(self): return self.status == TARDY
    def isExplained(self): return self._explained
    def addExplanation(self, expl):
        print "Added explanation: %s" % expl
    def acceptExplanation(self):
        print "Accepted explanation"
    def rejectExplanation(self):
        print "Rejected explanation"
    def raiseError(self, *args):
        raise AttendanceError


class SectionAttendanceRecordStub(object):
    implements(ISectionAttendanceRecord)
    def __init__(self, section, datetime, status, explained=False):
        self.section = section
        self.date = datetime.date()
        self.datetime = datetime
        self.status = status
        self._explained = explained
    def isAbsent(self): return self.status == ABSENT
    def isTardy(self): return self.status == TARDY
    def isExplained(self): return self._explained


class DayAttendanceStub(object):
    adapts(None)
    implements(IDayAttendance)

    def __init__(self, person):
        self.person = person
        self._records = getattr(person, '_day_attendance_records', [])

    def __iter__(self):
        return iter(self._records)

    def filter(self, first, last):
        status = itertools.cycle([PRESENT, ABSENT, TARDY, PRESENT])
        midpoint = first + (last - first) / 2
        return [DayAttendanceRecordStub(day, status.next(), day < midpoint)
                for day in DateRange(first, last)]

    def get(self, date):
        return 'd_%s_%s' % (self.person, date)

    def record(self, date, present):
        print 'Recording: %s -> %s' % (self.get(date), present)


class SectionAttendanceStub(object):
    adapts(None)
    implements(ISectionAttendance)

    def __init__(self, person):
        self.person = person
        self._records = getattr(person, '_section_attendance_records', [])

    def __iter__(self):
        return iter(self._records)

    def filter(self, first, last):
        status = itertools.cycle([PRESENT, ABSENT, TARDY, PRESENT])
        sections = itertools.cycle([SectionStub('math42'),
                                    SectionStub('grammar3'),
                                    SectionStub('relativity97')])
        time = datetime.time(9, 30)
        midpoint = first + (last - first) / 2
        return [SectionAttendanceRecordStub(sections.next(),
                      utc.localize(datetime.datetime.combine(day, time)),
                      status.next(), day < midpoint)
                for day in DateRange(first, last)]

    def get(self, section, datetime):
        return 's_%s_%s-%s' % (self.person, datetime, section)

    def record(self, section, datetime, duration, period_id, present):
        print 'Recording: %s -> %s' % (self.get(section, datetime), present)

    def getAllForDay(self, date):
        return ['s_%s_%s_%s' % (self.person, date, c) for c in 'a', 'b']


class CalendarEventViewletManagerStub(object):
    pass


class EventForDisplayStub(object):
    def __init__(self, event, tz=utc):
        self.context = event
        self.dtstarttz = event.dtstart.astimezone(tz)


class SectionStub(object):
    implements(ISection)

    members = ()

    def __init__(self, title='a_section'):
        self.__name__ = title
        self._title = title

    @property
    def label(self):
        return _('$title', mapping={'title': self._title})


class PersonStub(object):
    pass


def print_and_return_True(text):
    def inner(*args):
        print text
        return True
    return inner


def print_and_return_False(text):
    def inner(*args):
        print text
        return False
    return inner


def setUpAttendanceAdapters():
    from schooltool.attendance.attendance import getSectionAttendance
    from schooltool.attendance.attendance import getDayAttendance
    from schooltool.person.interfaces import IPerson
    ztapi.provideAdapter(IPerson, ISectionAttendance, getSectionAttendance)
    ztapi.provideAdapter(IPerson, IDayAttendance, getDayAttendance)


def doctest_getPeriodEventForSection():
    r"""Doctest for getPeriodEventForSection

    When traversing to the realtime attendance form, we want to verify
    that the section has the given period takes place on the given
    date.  We have a utility function for that:

        >>> from schooltool.attendance.browser.attendance \
        ...     import getPeriodEventForSection

        >>> section = StubTimetables(None)

    Now we can try our helper function:

        >>> for date in [datetime.date(2005, 12, d) for d in (14, 15, 16)]:
        ...     for period_id in 'A', 'B', 'C', 'D':
        ...         result = getPeriodEventForSection(section, date, period_id)
        ...         print date, period_id, result and result.dtstart
        2005-12-14 A 2005-12-14 10:00:00+00:00
        2005-12-14 B None
        2005-12-14 C None
        2005-12-14 D 2005-12-14 11:00:00+00:00
        2005-12-15 A None
        2005-12-15 B 2005-12-15 10:00:00+00:00
        2005-12-15 C 2005-12-15 11:00:00+00:00
        2005-12-15 D None
        2005-12-16 A None
        2005-12-16 B None
        2005-12-16 C None
        2005-12-16 D None

    """


def doctest_AttendanceCalendarEventViewlet():
    r"""Tests for AttendanceCalendarEventViewlet

        >>> from schooltool.attendance.browser.attendance \
        ...     import AttendanceCalendarEventViewlet
        >>> viewlet = AttendanceCalendarEventViewlet()
        >>> viewlet.request = TestRequest()

    Viewlets have a ``manager`` attribute that points to the viewlet manager.

        >>> viewlet.manager = CalendarEventViewletManagerStub()

    CalendarEventViewletManagerStub exports an ``event`` attribute, which
    provides IEventForDisplay.  Section meeting events are all
    ITimetableCalendarEvent.

        >>> section = SectionStub()
        >>> fakePath(section, u'/sections/math4a')
        >>> activity = TimetableActivity(title="Math", owner=section)
        >>> section_event = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 12, 16, 16, 15, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D3', period_id="P4", activity=activity)
        >>> viewlet.manager.event = EventForDisplayStub(section_event)

    The viewlet knows how to compute a link to the section attendance form

        >>> viewlet.attendanceLink()
        'http://127.0.0.1/sections/math4a/attendance/2005-12-16/P4'

    The date in the link depends on the configured timezone

        >>> tokyo = timezone('Asia/Tokyo')
        >>> viewlet.manager.event = EventForDisplayStub(section_event, tokyo)
        >>> viewlet.manager.event.dtstarttz
        datetime.datetime(2005, 12, 17, 1, 15, ...)
        >>> viewlet.attendanceLink()
        'http://127.0.0.1/sections/math4a/attendance/2005-12-17/P4'

    If the event is not a section meeting event, the link is empty

        >>> person = PersonStub()
        >>> activity = TimetableActivity(title="Math study", owner=person)
        >>> nonsection_event = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 12, 16, 16, 15, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     activity.title, day_id='D3', period_id="P3", activity=activity)
        >>> viewlet.manager.event = EventForDisplayStub(nonsection_event)
        >>> viewlet.attendanceLink()

    The link is also empty if the event is not a timetable event.

        >>> random_event = SimpleCalendarEvent(
        ...     datetime.datetime(2005, 12, 16, 16, 15, tzinfo=utc),
        ...     datetime.timedelta(minutes=15),
        ...     "Snacks")
        >>> viewlet.manager.event = EventForDisplayStub(random_event)
        >>> viewlet.attendanceLink()

    """


def doctest_RealtimeAttendanceView_listMembers():
    r"""Test for RealtimeAttendanceView.listMembers

    First, let's register getSectionAttendance as an adapter:

        >>> setUpAttendanceAdapters()

    We'll need timetabling too:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    Let's set up a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     RealtimeAttendanceView, getPeriodEventForSection
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> fakePath(section, '/section/absentology')
        >>> view = RealtimeAttendanceView(section, TestRequest())
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date,
        ...                                         view.period_id)
        >>> view.homeroom = False

    If the section does not have any members, listMembers returns an
    empty list:

        >>> view.listMembers()
        []

    Let's add some students:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person, PersonContainer
        >>> person1 = Person('person1', title='Person1')
        >>> person2 = Person('person2', title='Person2')
        >>> person3 = Person('person3', title='Person3')
        >>> person4 = Person('person4', title='Person4')

        >>> persons = PersonContainer()
        >>> persons[''] = person1
        >>> persons[''] = person2
        >>> persons[''] = person3
        >>> persons[''] = person4

        >>> section.members.add(person1)
        >>> section.members.add(person2)


    These members should appear in the output

        >>> pprint(view.listMembers())
        [RealtimeInfo(u'person1', 'Person1', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person1&date=2005-12-15'),
         RealtimeInfo(u'person2', 'Person2', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person2&date=2005-12-15')]

    So should transitive members:

        >>> form = Group('Form1')
        >>> form.members.add(person3)
        >>> form.members.add(person4)
        >>> section.members.add(form)

        >>> pprint(view.listMembers())
        [RealtimeInfo(u'person1', 'Person1', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person1&date=2005-12-15'),
         RealtimeInfo(u'person2', 'Person2', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person2&date=2005-12-15'),
         RealtimeInfo(u'person3', 'Person3', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person3&date=2005-12-15'),
         RealtimeInfo(u'person4', 'Person4', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person4&date=2005-12-15')]

    Let's add an absence record to one person:

        >>> attendance = ISectionAttendance(person4)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)

    Now the members' list displays a new status:

        >>> pprint(view.listMembers())
        [RealtimeInfo(u'person1', 'Person1', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person1&date=2005-12-15'),
         RealtimeInfo(u'person2', 'Person2', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person2&date=2005-12-15'),
         RealtimeInfo(u'person3', 'Person3', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person3&date=2005-12-15'),
         RealtimeInfo(u'person4', 'Person4', 'attendance-absent', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person4&date=2005-12-15')]

    Let's add some absences in this period:

        >>> attendance = ISectionAttendance(person4)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', False)

        >>> attendance = ISectionAttendance(person2)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', False)
        >>> ar = attendance.get(section,
        ...            datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc))
        >>> ar.makeTardy(datetime.datetime(2005, 12, 15, 11, 05, tzinfo=utc))

        >>> attendance = ISectionAttendance(person3)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', True)

        >>> pprint(view.listMembers())
        [RealtimeInfo(u'person1', 'Person1', 'attendance-clear', ' ', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person1&date=2005-12-15'),
         RealtimeInfo(u'person2', 'Person2', 'attendance-absent', 'T', True, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person2&date=2005-12-15'),
         RealtimeInfo(u'person3', 'Person3', 'attendance-present', '+', True, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person3&date=2005-12-15'),
         RealtimeInfo(u'person4', 'Person4', 'attendance-absent', '-', False, 'http://127.0.0.1/section/absentology/@@sparkline.png?person=person4&date=2005-12-15')]

    """


def doctest_RealtimeAttendanceView_getDaysAttendanceRecords():
    r"""Tests for RealtimeAttendanceView.getDaysAttendanceRecords.

        >>> provideAdapter(SectionAttendanceStub)
        >>> provideAdapter(DayAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...         import RealtimeAttendanceView
        >>> view = RealtimeAttendanceView(None, None)

        >>> view.getDaysAttendanceRecords('stud1', datetime.date(2006, 1, 3))
        ['s_stud1_2006-01-03_a', 's_stud1_2006-01-03_b', 'd_stud1_2006-01-03']

    """


def doctest_RealtimeAttendanceView_studentStatus():
    r"""Tests for RealtimeAttendanceView.studentStatus

    First, let's register getSectionAttendance as an adapter:

        >>> setUpAttendanceAdapters()

    We will need a view

        >>> from schooltool.attendance.browser.attendance import \
        ...     RealtimeAttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> view = RealtimeAttendanceView(section, TestRequest())
        >>> view.date = datetime.date(2005, 12, 15)

    Let's add some members to the group:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person, PersonContainer
        >>> person1 = Person('person1', title='Person1')
        >>> person2 = Person('person2', title='Person2')
        >>> person3 = Person('person3', title='Person3')
        >>> person4 = Person('person4', title='Person4')

        >>> persons = PersonContainer()
        >>> persons[''] = person1
        >>> persons[''] = person2
        >>> persons[''] = person3
        >>> persons[''] = person4

        >>> section.members.add(person1)
        >>> section.members.add(person2)

    Initially the student's absence is 'clear' (no records):

        >>> view.studentStatus(person1)
        'attendance-clear'

    Let's record an unexplained absence for the student:

        >>> attendance = ISectionAttendance(person1)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)

    Now that the student has an unexplained absence, and no presence
    records, the status is 'absent':

        >>> view.studentStatus(person1)
        'attendance-absent'

    If we add a presence record for the same day, the status becomes 'alert':

        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', True)
        >>> view.studentStatus(person1)
        'attendance-alert'

    Let's take another student.  It's a good student, she's been
    present to all sections:

        >>> attendance = ISectionAttendance(person2)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', True)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', True)
        >>> view.studentStatus(person2)
        'attendance-present'

    Let's take another yet student.  He's broken his leg and is
    excused for the whole two months:

        >>> attendance = ISectionAttendance(person3)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 11, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'C', False)
        >>> for record in attendance.getAllForDay(view.date):
        ...     record.addExplanation("Broken leg")
        ...     record.explanations[-1].status = ACCEPTED
        >>> view.studentStatus(person3)
        'attendance-explained'

    Yet another student was tardy.  The status shows that he's been absent:

        >>> attendance = ISectionAttendance(person4)
        >>> attendance.record(
        ...     section, datetime.datetime(2005, 12, 15, 10, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45), 'B', False)
        >>> ar = attendance.getAllForDay(view.date).next()
        >>> ar.makeTardy(datetime.datetime(2005, 12, 15, 10, 9, tzinfo=utc))
        >>> view.studentStatus(person4)
        'attendance-absent'

    """


def doctest_RealtimeAttendanceView_update():
    r"""Tests for RealtimeAttendanceView.update

    Let's set up the section attendance adapter:

        >>> setUpAttendanceAdapters()

    We'll need timetabling stubbed too:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    Let's create a section and a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     RealtimeAttendanceView
        >>> from schooltool.course.section import Section
        >>> class MySection(Section):
        ...     def __repr__(self): return '<Section>'
        >>> section = MySection()

    Let's add some members to the section:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person, PersonContainer
        >>> person1 = Person('person1', title='Person1')
        >>> person2 = Person('person2', title='Person2')
        >>> person3 = Person('person3', title='Person3')
        >>> person4 = Person('person4', title='Person4')
        >>> person5 = Person('person5', title='Person5')

        >>> persons = PersonContainer()
        >>> persons[''] = person1
        >>> persons[''] = person2
        >>> persons[''] = person3
        >>> persons[''] = person4
        >>> persons[''] = person5

        >>> section.members.add(person1)
        >>> section.members.add(person2)
        >>> section.members.add(person3)
        >>> section.members.add(person4)
        >>> section.members.add(person5)

    Let's call update with an empty request:

        >>> request = TestRequest()
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()

    The students don't have attendance data for this section yet, so a
    flag is set on the view:

        >>> view.unknowns
        True

    Let's instantiate the view:

        >>> request = TestRequest(form={'person1_check': 'on',
        ...                             'person2_check': 'on',
        ...                             'person5_check': 'on',
        ...                             'ABSENT': 'Make absent'})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

    Now we can call update:

        >>> view.update()

    Now all students have attendance data set, so the status is changed:

        >>> view.unknowns
        False

    Let's see the attendance data for these persons:

        >>> records = list(ISectionAttendance(person1))
        >>> len(records)
        1
        >>> pprint(records)
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person2))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person3))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]
        >>> list(ISectionAttendance(person4))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]
        >>> list(ISectionAttendance(person5))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]

    Let's call the view again, nothing changed:

        >>> request = TestRequest(form={'ABSENT': 'Make absent'})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()

        >>> list(ISectionAttendance(person1))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person2))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person3))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]
        >>> list(ISectionAttendance(person4))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]

    If we call an absent person absent again, nothing breaks:

        >>> request = TestRequest(form={'ABSENT': 'Make absent',
        ...                             'person1_check': 'on'})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()

        >>> list(ISectionAttendance(person1))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person2))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person3))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]
        >>> list(ISectionAttendance(person4))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]

    If we call a present person absent, nothing breaks:

        >>> request = TestRequest(form={'ABSENT': 'Make absent',
        ...                             'person3_check': 'on'})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()

    But the person remains present.  We can silently ignore this error
    because the checkbox is disabled.

        >>> list(ISectionAttendance(person3))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]

    Now, let's try to make a present person and an absent person
    tardy, but without a specified time:

        >>> tick = datetime.datetime.utcnow().replace(tzinfo=utc)
        >>> request = TestRequest(form={'TARDY': 'Make tardy',
        ...                             'person3_check': 'on',
        ...                             'person1_check': 'on',
        ...                             'arrival': ''})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()
        >>> tock = datetime.datetime.utcnow().replace(tzinfo=utc)

    The status of the present person must be unchanged:

        >>> list(ISectionAttendance(person3))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), PRESENT)]

    But the previously absent person must have changed to tardy:

        >>> list(ISectionAttendance(person1))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), TARDY)]

    The arrival time is the time when the form was submitted:

        >>> ar = iter(ISectionAttendance(person1)).next()
        >>> tick <= ar.late_arrival <= tock
        True

    If the arrival time is incorrect, the error attribute on the view is set:

        >>> request = TestRequest(form={'TARDY': 'Make tardy',
        ...                             'person2_check': 'on',
        ...                             'arrival': '12:20'})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()

        >>> list(ISectionAttendance(person2))
        [SectionAttendanceRecord(<Section>,
              datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>), TARDY)]

        >>> ar = iter(ISectionAttendance(person2)).next()
        >>> ar.late_arrival
        datetime.datetime(2005, 12, 15, 12, 20, tzinfo=<UTC>)

    If the arrival time is incorrect, the error attribute on the view is set:

        >>> request = TestRequest(form={'TARDY': 'Make tardy',
        ...                             'person5_check': 'on',
        ...                             'arrival': '2200'})
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

        >>> view.update()

        >>> view.error
        u'The arrival time you entered is invalid.  Please use HH:MM format'

    """


def doctest_RealtimeAttendanceView_update_homeroom():
    r"""Tests for RealtimeAttendanceView.update

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    The ``update`` method is able to tell the difference between regular
    section meetings and the homeroom meeting.

        >>> from schooltool.attendance.browser.attendance \
        ...     import RealtimeAttendanceView
        >>> section = SectionStub()
        >>> request = TestRequest()
        >>> view = RealtimeAttendanceView(section, request)

    The 'C' period on 2005-12-15 is a regular section meeting

        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.update()
        >>> view.homeroom
        False

    The 'B' period, on the other hand, is the homeroom period

        >>> view.period_id = 'B'
        >>> view.update()
        >>> view.homeroom
        True

    """


def doctest_RealtimeAttendanceView_update_set_homeroom():
    r"""Tests for RealtimeAttendanceView.update

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    We will also need attendance adapters.

        >>> setUpAttendanceAdapters()

    The RealtimeAttendanceView is used both for regular section meetings,
    and for homeroom attendance.

        >>> from schooltool.attendance.browser.attendance \
        ...     import RealtimeAttendanceView
        >>> section = SectionStub()
        >>> request = TestRequest()
        >>> view = RealtimeAttendanceView(section, request)

    We will need at least one person.

        >>> from schooltool.person.person import Person
        >>> person1 = Person('person1', title='Person1')
        >>> person1.__name__ = 'p1'
        >>> person2 = Person('person2', title='Person1')
        >>> person2.__name__ = 'p2'
        >>> section.members = [person1, person2]

    The 'B' period is the homeroom period

        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'B'
        >>> view.update()
        >>> view.homeroom
        True

    If you mark some absences, they will be recorded as day absences, not
    section absences.

        >>> view.request = TestRequest(form={'ABSENT': 'Absent',
        ...                                  'p1_check': 'on'})
        >>> view.update()

        >>> list(IDayAttendance(person1))
        [DayAttendanceRecord(datetime.date(2005, 12, 15), ABSENT)]
        >>> list(IDayAttendance(person2))
        [DayAttendanceRecord(datetime.date(2005, 12, 15), PRESENT)]

    We can see that there is no section attendance data:

        >>> list(ISectionAttendance(person1))
        []
        >>> list(ISectionAttendance(person2))
        []

    """


def doctest_RealtimeAttendanceView_getAttendance():
    r"""Tests for RealtimeAttendanceView._getAttendance

        >>> provideAdapter(SectionAttendanceStub)
        >>> provideAdapter(DayAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...         import RealtimeAttendanceView
        >>> request = TestRequest()
        >>> view = RealtimeAttendanceView('math', request)

        >>> from schooltool.timetable.model import TimetableCalendarEvent
        >>> person = 'jonas'
        >>> view.date = datetime.date(2005, 1, 16)
        >>> view.period_id = 'p4'
        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 1, 16, 10, 25, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)

        >>> view.homeroom = True
        >>> view._getAttendance(person)
        'd_jonas_2005-01-16'

        >>> view.homeroom = False
        >>> view._getAttendance(person)
        's_jonas_2005-01-16 10:25:00+00:00-math'

    """


def doctest_RealtimeAttendanceView_record():
    r"""Tests for RealtimeAttendanceView._record

        >>> provideAdapter(SectionAttendanceStub)
        >>> provideAdapter(DayAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...         import RealtimeAttendanceView
        >>> request = TestRequest()
        >>> view = RealtimeAttendanceView('math', request)

        >>> from schooltool.timetable.model import TimetableCalendarEvent
        >>> person = 'jonas'
        >>> view.date = datetime.date(2005, 1, 16)
        >>> view.period_id = 'p4'
        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 1, 16, 10, 25, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)

        >>> view.homeroom = True
        >>> view._record(person, True)
        Recording: d_jonas_2005-01-16 -> True

        >>> view.homeroom = False
        >>> view._record(person, False)
        Recording: s_jonas_2005-01-16 10:25:00+00:00-math -> False

    """


def doctest_RealtimeAttendanceView_getArrival():
    r"""Tests for RealtimeAttendanceView.getArrival

    We'll need person preferences for a timezone:

        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.person.preference import getPersonPreferences
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> ztapi.provideAdapter(IPerson, IPersonPreferences,
        ...                      getPersonPreferences)


    Let's create a section and a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     RealtimeAttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()

    If no arrival time was entered in the form, current time with
    timezone is returned:

        >>> view = RealtimeAttendanceView(section, TestRequest())
        >>> tick = datetime.datetime.utcnow().replace(tzinfo=utc)
        >>> arrival = view.getArrival()
        >>> tock = datetime.datetime.utcnow().replace(tzinfo=utc)

        >>> tick <= arrival <= tock
        True

    However if the time was entered in the form, that time in on the
    date we're modifying attendance on, with the timezone of the
    user's preference is returned:


        >>> from schooltool.person.person import Person
        >>> user = Person('user')
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> IPersonPreferences(user).timezone = 'Europe/Vilnius'

        >>> request = TestRequest(form={'arrival': '22:13'})
        >>> request.setPrincipal(user)
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 29)
        >>> view.getArrival()
        datetime.datetime(2005, 12, 29, 22, 13,
                          tzinfo=<DstTzInfo 'Europe/Vilnius' EET+2:00:00 STD>)

    If the time in the request is invalid, we just pass the ValueError along:

        >>> request = TestRequest(form={'arrival': '2212'})
        >>> request.setPrincipal(user)
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 29)
        >>> view.getArrival()
        Traceback (most recent call last):
          ...
        ValueError: need more than 1 value to unpack

    """


def doctest_RealtimeAttendanceView_publishTraverse():
    r"""Tests for RealtimeAttendanceView.publishTraverse

        >>> from schooltool.attendance.browser.attendance \
        ...          import RealtimeAttendanceView

    Now we can try the typical case:

        >>> request = TestRequest()
        >>> section = 'section'
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.date, view.period_id
        (None, None)

        >>> view.publishTraverse(request, '2005-12-15') is view
        True
        >>> view.date, view.period_id
        (datetime.date(2005, 12, 15), None)

        >>> view.publishTraverse(request, 'B') is view
        True
        >>> view.date, view.period_id
        (datetime.date(2005, 12, 15), 'B')

    If you try to traverse too much, you get an error

        >>> view.publishTraverse(request, 'quux')
        Traceback (most recent call last):
          ...
        NotFound: Object: 'section', name: 'quux'

    What if the date is invalid?

        >>> view = RealtimeAttendanceView(section, request)
        >>> view.publishTraverse(request, "some time last week")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'section', name: 'some time last week'

    """


def doctest_RealtimeAttendanceView_verifyParameters():
    r"""Tests for RealtimeAttendanceView.verifyParameters

        >>> from schooltool.attendance.browser.attendance \
        ...          import RealtimeAttendanceView

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    What if we try to render the view without specifying both the
    date and the period id?

        >>> request = TestRequest()
        >>> section = 'section'
        >>> view = RealtimeAttendanceView(section, request)
        >>> view.__name__ = 'attendance'
        >>> view.date, view.period_id
        (None, None)

        >>> view.verifyParameters()
        Traceback (most recent call last):
          ...
        NotFound: Object: 'section', name: 'attendance'

        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.verifyParameters()
        Traceback (most recent call last):
          ...
        NotFound: Object: 'section', name: 'attendance'

    What if the period is invalid?

        >>> view.period_id = 'QUUX'
        >>> view.verifyParameters()
        Traceback (most recent call last):
          ...
        NotFound: Object: 'section', name: 'attendance'

    And now suppose everything is fine

        >>> view.period_id = 'B'
        >>> view.verifyParameters()

    """


def doctest_StudentAttendanceView_term_for_detailed_summary():
    r"""Tests for StudentAttendanceView.term_for_detailed_summary

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(None, request)

    Empty request:

        >>> print view.term_for_detailed_summary
        None

        >>> request.form['term'] = ''
        >>> print view.term_for_detailed_summary
        None

    Invalid request:

        >>> request.form['term'] = 'no-such-term'
        >>> print view.term_for_detailed_summary
        None

    Term name in the request:

        >>> request.form['term'] = '2005-fall'
        >>> print view.term_for_detailed_summary
        <TermStub: 2005-09-01..2005-12-22>

    """


def doctest_StudentAttendanceView_formatAttendanceRecord():
    r"""Tests for StudentAttendanceView.formatAttendanceRecord

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

        >>> ar = DayAttendanceRecordStub(datetime.date(2006, 1, 14), ABSENT)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14: absent from homeroom

        >>> ar = DayAttendanceRecordStub(datetime.date(2006, 1, 14), TARDY)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14: late for homeroom

        >>> ar = SectionAttendanceRecordStub(SectionStub('math17'),
        ...             datetime.datetime(2006, 1, 14, 17, 3, tzinfo=utc), ABSENT)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14 17:03: absent from math17

        >>> ar = SectionAttendanceRecordStub(SectionStub('math17'),
        ...             datetime.datetime(2006, 1, 14, 17, 3, tzinfo=utc), TARDY)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14 17:03: late for math17

    """


def doctest_StudentAttendanceView_interleaveAttendanceRecords():
    r"""Tests for StudentAttendanceView.interleaveAttendanceRecords

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

    Let's use trivial stubs

        >>> class ARStub(object):
        ...     def __init__(self, date):
        ...         self.date = date
        ...     def __repr__(self):
        ...         return '%s%d' % (self.prefix, self.date)
        >>> class DAR(ARStub):
        ...     prefix = 'd'
        >>> class SAR(ARStub):
        ...     prefix = 's'

        >>> day = [DAR(d) for d in 1, 2, 5, 6, 7, 8]
        >>> section = [SAR(d) for d in 2, 2, 3, 4, 5, 8, 9, 10, 11]
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [d1, d2, s2, s2, s3, s4, d5, s5, d6, d7, d8, s8, s9, s10, s11]

        >>> day = [DAR(d) for d in 2, 5, 6, 7, 8]
        >>> section = [SAR(d) for d in 1, 3, 4, 4, 5, 5]
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [s1, d2, s3, s4, s4, d5, s5, s5, d6, d7, d8]

        >>> day = []
        >>> section = [SAR(d) for d in 1, 2]
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [s1, s2]

        >>> day = [DAR(d) for d in 2, 5, 6]
        >>> section = []
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [d2, d5, d6]

        >>> day = []
        >>> section = []
        >>> print list(view.interleaveAttendanceRecords(day, section))
        []

    """


def doctest_StudentAttendanceView_unresolvedAbsences():
    r"""Tests for StudentAttendanceView.unresolvedAbsences

    We shall use some simple attendance adapters for this test

        >>> provideAdapter(DayAttendanceStub)
        >>> provideAdapter(SectionAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> student = PersonStub()
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(student, request)

    Simple case first: when there are no recorded absences/tardies, we get an
    empty list.

        >>> student._day_attendance_records = []
        >>> student._section_attendance_records = []
        >>> list(view.unresolvedAbsences())
        []

    Let's create some attendances.

        >>> first = datetime.date(2006, 1, 21)
        >>> last = datetime.date(2006, 1, 28)
        >>> status = itertools.cycle([PRESENT, ABSENT, TARDY, PRESENT])
        >>> student._day_attendance_records = [
        ...         DayAttendanceRecordStub(day, status.next(),
        ...                                 day >= datetime.date(2006, 1, 26))
        ...         for day in DateRange(first, last)]
        >>> status = itertools.cycle([PRESENT, ABSENT, TARDY, PRESENT])
        >>> sections = itertools.cycle([SectionStub('math42'),
        ...                             SectionStub('grammar3'),
        ...                             SectionStub('relativity97')])
        >>> time = datetime.time(9, 30)
        >>> student._section_attendance_records = [
        ...         SectionAttendanceRecordStub(sections.next(),
        ...                 utc.localize(datetime.datetime.combine(day, time)),
        ...                 status.next(), day >= datetime.date(2006, 1, 26))
        ...         for day in DateRange(first, last)]

        >>> for absence in view.unresolvedAbsences():
        ...     print translate(absence['text'])
        2006-01-22: absent from homeroom
        2006-01-22 09:30: absent from grammar3
        2006-01-23: late for homeroom
        2006-01-23 09:30: late for relativity97

    """


def doctest_StudentAttendanceView_absencesForTerm():
    r"""Tests for StudentAttendanceView.absencesForTerm

    We shall use some simple attendance adapters for this test

        >>> provideAdapter(DayAttendanceStub)
        >>> provideAdapter(SectionAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> student = PersonStub()
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(student, request)

        >>> term = TermStub(2006, 2, 20, 3, 7)
        >>> for a in view.absencesForTerm(term):
        ...     print translate(a)
        2006-02-21: absent from homeroom
        2006-02-21 09:30: absent from grammar3
        2006-02-22: late for homeroom
        2006-02-22 09:30: late for relativity97
        2006-02-25: absent from homeroom
        2006-02-25 09:30: absent from relativity97
        2006-02-26: late for homeroom
        2006-02-26 09:30: late for math42
        2006-03-01: absent from homeroom
        2006-03-01 09:30: absent from math42
        2006-03-02: late for homeroom
        2006-03-02 09:30: late for grammar3
        2006-03-05: absent from homeroom
        2006-03-05 09:30: absent from grammar3
        2006-03-06: late for homeroom
        2006-03-06 09:30: late for relativity97

    """


def doctest_StudentAttendanceView_terms():
    r"""Tests for StudentAttendanceView.terms

    A little stubbing

        >>> provideAdapter(SchoolToolApplicationStub)

    and we can test that StudentAttendanceView.terms returns all the terms
    in chronological order

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> for term in view.terms():
        ...     print term.first, '--', term.last
        2004-09-01 -- 2004-12-22
        2005-02-01 -- 2005-05-21
        2005-09-01 -- 2005-12-22
        2006-02-01 -- 2006-05-21

    """


def doctest_StudentAttendanceView_countAbsences():
    r"""Tests for StudentAttendanceView.countAbsences

        >>> from schooltool.attendance.attendance import AttendanceRecord
        >>> a = AttendanceRecord(ABSENT)
        >>> p = AttendanceRecord(PRESENT)
        >>> t = AttendanceRecord(UNKNOWN)
        >>> t.status = TARDY

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.countAbsences([])
        (0, 0)
        >>> view.countAbsences([a, p, a, t])
        (2, 1)

    """


def doctest_StudentAttendanceView_summaryPerTerm():
    r"""Tests for StudentAttendanceView.summaryPerTerm

    We shall use some simple attendance adapters for this test

        >>> from schooltool.attendance.attendance import AttendanceRecord
        >>> a = AttendanceRecord(ABSENT)
        >>> p = AttendanceRecord(PRESENT)
        >>> t = AttendanceRecord(UNKNOWN)
        >>> t.status = TARDY

        >>> class TermStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name
        ...         self.title = name
        ...         self.first = name
        ...         self.last = name

        >>> class DayAttendanceStub(object):
        ...     adapts(None)
        ...     implements(IDayAttendance)
        ...     def __init__(self, context):
        ...         pass
        ...     def filter(self, first, last):
        ...         return {'term1': [p, p, p, a, p, a, t, t, a, p, p],
        ...                 'term2': [a, a, p, t, p],
        ...                 'term3': [p, p, p]}[first]
        >>> provideAdapter(DayAttendanceStub)
        >>> class SectionAttendanceStub(object):
        ...     adapts(None)
        ...     implements(ISectionAttendance)
        ...     def __init__(self, context):
        ...         pass
        ...     def filter(self, first, last):
        ...         return {'term1': [p, p, p],
        ...                 'term2': [a, t, p, t, p],
        ...                 'term3': [p, a, p, p, a]}[first]
        >>> provideAdapter(SectionAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> student = 'pretend this is a student'
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(student, request)
        >>> view.terms = lambda: [TermStub('term1'), TermStub('term2'),
        ...                       TermStub('term3')]

        >>> for term in view.summaryPerTerm():
        ...     print ('%(title)s  %(day_absences)d %(day_tardies)d'
        ...            '  %(section_absences)d %(section_tardies)d' % term)
        term1  3 2  0 0
        term2  2 1  1 2
        term3  0 0  2 0

    """


def doctest_StudentAttendanceView_makeId():
    r"""Tests for StudentAttendanceView.makeId

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

        >>> from schooltool.attendance.attendance import DayAttendanceRecord
        >>> a = DayAttendanceRecord(datetime.date(2006, 1, 29), ABSENT)

        >>> view.makeId(a)
        'd_2006-01-29'

        >>> from schooltool.attendance.attendance import SectionAttendanceRecord
        >>> dt = utc.localize(datetime.datetime(2006, 1, 29, 14, 30))
        >>> a = SectionAttendanceRecord(SectionStub(u'Some section \u1234'),
        ...                             dt, ABSENT)

        >>> view.makeId(a)
        's_2006-01-29_14:30:00+00:00_U29tZSBzZWN0aW9uIOGItA=='

    """


def doctest_StudentAttendanceView_update():
    r"""Tests for StudentAttendanceView.update

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(None, request)
        >>> def _process(ar, text, explanation, resolve):
        ...     print ar
        ...     if explanation: print 'Explaining %s: %s' % (text, explanation)
        ...     if resolve == 'accept': print 'Accepting %s' % text
        ...     if resolve == 'reject': print 'Rejecting %s' % text
        >>> view._process = _process
        >>> view.unresolvedAbsences = lambda: [
        ...     {'id': 'ar123', 'attendance_record': '<ar123>',
        ...      'text': 'Attendance Record #123'},
        ...     {'id': 'ar124', 'attendance_record': '<ar124>',
        ...      'text': 'Attendance Record #124'},
        ...     {'id': 'ar125', 'attendance_record': '<ar125>',
        ...      'text': 'Attendance Record #125'},
        ... ]

    No 'UPDATE' button in request -- nothing happens.

        >>> view.update()

    No checkboxes in request -- nothing happens.

        >>> request.form['UPDATE'] = u'Do it!'
        >>> view.update()

    No explanation or radio buttons -- nothing significant happens

        >>> request.form['UPDATE'] = u'Do it!'
        >>> request.form['ar123'] = 'on'
        >>> request.form['ar125'] = 'on'
        >>> view.update()
        <ar123>
        <ar125>

    Let's add an explanation and accept:

        >>> request.form['UPDATE'] = u'Do it!'
        >>> request.form['ar123'] = 'on'
        >>> request.form['ar125'] = 'on'
        >>> request.form['explanation'] = 'yada yada'
        >>> request.form['resolve'] = 'accept'
        >>> view.update()
        <ar123>
        Explaining Attendance Record #123: yada yada
        Accepting Attendance Record #123
        <ar125>
        Explaining Attendance Record #125: yada yada
        Accepting Attendance Record #125

    """


def doctest_StudentAttendanceView_process():
    r"""Tests for StudentAttendanceView._process

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.errors = []
        >>> view.statuses = []
        >>> view._addExplanation = print_and_return_True('addExplanation')
        >>> view._acceptExplanation = print_and_return_True('acceptExplanation')
        >>> view._rejectExplanation = print_and_return_True('rejectExplanation')

        >>> ar = 'attendance_record'
        >>> text = 'THIS ABSENCE'
        >>> view._process(ar, text, '', 'ignore')

    Nothing happened.

        >>> view.statuses
        []

    Let's add an explanation; nothing else

        >>> view._process(ar, text, 'explainexplainexplain', 'ignore')
        addExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Added an explanation for THIS ABSENCE

    Let's accept an explanation; nothing else

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'accept')
        acceptExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Resolved THIS ABSENCE

    Let's reject an explanation; nothing else

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'reject')
        rejectExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Rejected explanation for THIS ABSENCE

    Ok, now let's both add and accept an explanation

        >>> view.statuses = []
        >>> view._process(ar, text, 'gugugu', 'accept')
        addExplanation
        acceptExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Resolved THIS ABSENCE

    Let's reject an explanation; nothing else

        >>> view.statuses = []
        >>> view._process(ar, text, 'baaaa', 'reject')
        addExplanation
        rejectExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Rejected explanation for THIS ABSENCE

    """


def doctest_StudentAttendanceView_process_error_handling():
    r"""Tests for StudentAttendanceView._process

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.errors = []
        >>> view.statuses = []
        >>> view._addExplanation = print_and_return_False('addExplanation')
        >>> view._acceptExplanation = print_and_return_True('acceptExplanation')
        >>> view._rejectExplanation = print_and_return_True('rejectExplanation')

        >>> ar = 'attendance_record'
        >>> text = 'THIS ABSENCE'

    Let's add an explanation, when you cannot add an explanation

        >>> view._process(ar, text, 'explainexplainexplain', 'ignore')
        addExplanation
        >>> view.statuses
        []

    You cannot accept/reject anything if addExplanation fails

        >>> view._process(ar, text, 'explainexplainexplain', 'accept')
        addExplanation
        >>> view._process(ar, text, 'explainexplainexplain', 'reject')
        addExplanation
        >>> view.statuses
        []

    Ok, suppose you could add an explanation, but accept/reject borks

        >>> view._addExplanation = print_and_return_True('addExplanation')
        >>> view._acceptExplanation = print_and_return_False('acceptExplanation')
        >>> view._rejectExplanation = print_and_return_False('rejectExplanation')

        >>> view._process(ar, text, 'explainexplainexplain', 'accept')
        addExplanation
        acceptExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Added an explanation for THIS ABSENCE

        >>> view.statuses = []
        >>> view._process(ar, text, 'explainexplainexplain', 'reject')
        addExplanation
        rejectExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Added an explanation for THIS ABSENCE

    Ok, suppose you did not add an explanation, and accept/reject borks

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'accept')
        acceptExplanation
        >>> view.statuses
        []

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'reject')
        rejectExplanation
        >>> view.statuses
        []

    """


def doctest_StudentAttendanceView_addExplanation():
    r"""Tests for StudentAttendanceView._addExplanation

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.errors = []

        >>> ar = DayAttendanceRecordStub(datetime.date(2006, 1, 29), ABSENT)
        >>> view._addExplanation(ar, 'Bububu', {'absence': 'THIS ABSENCE'})
        Added explanation: Bububu
        True
        >>> view.errors
        []

        >>> ar.addExplanation = ar.raiseError
        >>> view._addExplanation(ar, 'Bububu', {'absence': 'THIS ABSENCE'})
        False

        >>> for err in view.errors:
        ...     print translate(err)
        Cannot add new explanation for THIS ABSENCE:
            old explanation not accepted/rejected

    """


def doctest_StudentAttendanceView_acceptExplanation():
    r"""Tests for StudentAttendanceView._acceptExplanation

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.errors = []

        >>> ar = DayAttendanceRecordStub(datetime.date(2006, 1, 29), ABSENT)
        >>> view._acceptExplanation(ar, {'absence': 'THIS ABSENCE'})
        Accepted explanation
        True
        >>> view.errors
        []

        >>> ar.acceptExplanation = ar.raiseError
        >>> view._acceptExplanation(ar, {'absence': 'THIS ABSENCE'})
        False

        >>> for err in view.errors:
        ...     print translate(err)
        There are no outstanding explanations to accept for THIS ABSENCE

    """


def doctest_StudentAttendanceView_rejectExplanation():
    r"""Tests for StudentAttendanceView._rejectExplanation

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.errors = []

        >>> ar = DayAttendanceRecordStub(datetime.date(2006, 1, 29), ABSENT)
        >>> view._rejectExplanation(ar, {'absence': 'THIS ABSENCE'})
        Rejected explanation
        True
        >>> view.errors
        []

        >>> ar.rejectExplanation = ar.raiseError
        >>> view._rejectExplanation(ar, {'absence': 'THIS ABSENCE'})
        False

        >>> for err in view.errors:
        ...     print translate(err)
        There are no outstanding explanations to reject for THIS ABSENCE

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()
    setUpAnnotations()
    setUpRelationships()
    stubProcessDefinition()
    provideAdapter(SchoolToolApplicationStub)
    provideAdapter(ApplicationPreferencesStub)
    logging.getLogger('attendance').disabled = True


def tearDown(test):
    setup.placelessTearDown()
    logging.getLogger('attendance').disabled = False


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(
            optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
            setUp=setUp, tearDown=tearDown),
        doctest.DocTestSuite(
            "schooltool.attendance.browser.attendance",
            optionflags=doctest.ELLIPSIS,
            setUp=setUp, tearDown=tearDown)
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
