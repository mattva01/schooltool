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
from pprint import pprint

from pytz import utc, timezone
from zope.testing import doctest
from zope.app.testing import ztapi, setup
from zope.publisher.browser import TestRequest
from zope.interface import implements, Interface
from zope.component import adapts, provideAdapter
from zope.app.testing.setup import setUpAnnotations

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.timetable import ITimetables
from schooltool.timetable import TimetableActivity
from schooltool.timetable.model import TimetableCalendarEvent
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.course.interfaces import ISection
from schooltool.relationship.tests import setUpRelationships
from schooltool.attendance.tests import stubProcessDefinition
from schooltool.testing.util import fakePath
from schooltool.attendance.interfaces import NEW, ACCEPTED, REJECTED


class ApplicationStub(object):
    implements(ISchoolToolApplication, IApplicationPreferences)

    timezone = 'UTC'


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


class CalendarEventViewletManagerStub(object):
    pass


class EventForDisplayStub(object):
    def __init__(self, event, tz=utc):
        self.context = event
        self.dtstarttz = event.dtstart.astimezone(tz)


class SectionStub(object):
    implements(ISection)

    members = ()


class PersonStub(object):
    pass


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

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> from schooltool.attendance.interfaces import IDayAttendance
        >>> from schooltool.attendance.attendance import getSectionAttendance
        >>> from schooltool.attendance.attendance import getDayAttendance
        >>> from schooltool.person.interfaces import IPerson
        >>> ztapi.provideAdapter(IPerson, ISectionAttendance,
        ...                      getSectionAttendance)
        >>> ztapi.provideAdapter(IPerson, IDayAttendance,
        ...                      getDayAttendance)

    We'll need timetabling too:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    Let's set up a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     RealtimeAttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> fakePath(section, '/section/absentology')
        >>> view = RealtimeAttendanceView(section, TestRequest())
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'

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


class SectionAttendanceStub(object):
    def __init__(self, person):
        self.person = person

    def getAllForDay(self, date):
        return ['s_%s_%s_%s' % (self.person, date, c) for c in 'a', 'b']


class DayAttendanceStub(object):
    def __init__(self, person):
        self.person = person

    def get(self, date):
        return 'd_%s_%s' % (self.person, date)


def doctest_RealtimeAttendanceView_getDaysAttendanceRecords():
    r"""Tests for RealtimeAttendanceView.getDaysAttendanceRecords.

        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> from schooltool.attendance.interfaces import IDayAttendance
        >>> ztapi.provideAdapter(None, ISectionAttendance,
        ...                      SectionAttendanceStub)
        >>> ztapi.provideAdapter(None, IDayAttendance,
        ...                      DayAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...         import RealtimeAttendanceView
        >>> view = RealtimeAttendanceView(None, None)

        >>> view.getDaysAttendanceRecords('stud1', datetime.date(2006, 1, 3))
        ['s_stud1_2006-01-03_a', 's_stud1_2006-01-03_b', 'd_stud1_2006-01-03']

    """


def doctest_RealtimeAttendanceView_studentStatus():
    r"""Tests for RealtimeAttendanceView.studentStatus

    First, let's register getSectionAttendance as an adapter:

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> from schooltool.attendance.interfaces import IDayAttendance
        >>> from schooltool.attendance.attendance import getSectionAttendance
        >>> from schooltool.attendance.attendance import getDayAttendance
        >>> from schooltool.person.interfaces import IPerson
        >>> ztapi.provideAdapter(IPerson, ISectionAttendance,
        ...                      getSectionAttendance)
        >>> ztapi.provideAdapter(IPerson, IDayAttendance,
        ...                      getDayAttendance)


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

        >>> from schooltool.attendance.interfaces import ISectionAttendance
        >>> from schooltool.attendance.attendance import getSectionAttendance
        >>> from schooltool.person.interfaces import IPerson
        >>> ztapi.provideAdapter(IPerson, ISectionAttendance,
        ...                      getSectionAttendance)

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


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()
    setUpAnnotations()
    setUpRelationships()
    app = ApplicationStub()
    ztapi.provideAdapter(None, ISchoolToolApplication, lambda x: app)
    stubProcessDefinition()


def tearDown(test):
    setup.placelessTearDown()


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
