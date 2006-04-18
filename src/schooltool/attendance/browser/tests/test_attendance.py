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
from schooltool.attendance.interfaces import IAttendancePreferences
from schooltool.term.daterange import DateRange
from schooltool.timetable import ITimetables
from schooltool.timetable import TimetableActivity
from schooltool.timetable.model import TimetableCalendarEvent
from schooltool.calendar.simple import ImmutableCalendar
from schooltool.calendar.simple import SimpleCalendarEvent
from schooltool.calendar.utils import utcnow, stub_utcnow
from schooltool.course.interfaces import ISection
from schooltool.testing.util import fakePath
from schooltool.relationship.tests import setUpRelationships
from schooltool.attendance.tests import stubProcessDefinition
from schooltool.attendance.interfaces import NEW, ACCEPTED, REJECTED
from schooltool.attendance.interfaces import PRESENT, ABSENT, TARDY, UNKNOWN
from schooltool.attendance.interfaces import IHomeroomAttendance
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.attendance.interfaces import IHomeroomAttendanceRecord
from schooltool.attendance.interfaces import ISectionAttendanceRecord
from schooltool.attendance.interfaces import AttendanceError
from schooltool import SchoolToolMessage as _


some_dt = datetime.datetime(2006, 4, 14, 12, 13, tzinfo=utc)


class TermStub(object):
    def __init__(self, y, m1, d1, m2, d2):
        self.first = datetime.date(y, m1, d1)
        self.last = datetime.date(y, m2, d2)
    def __str__(self):
        return '<TermStub: %s..%s>' % (self.first, self.last)


class AttendancePreferencesStub(object):
    adapts(ISchoolToolApplication)
    implements(IAttendancePreferences)
    def __init__(self):
        self.attendanceRetroactiveTimeout = 60
        self.attendanceStatusCodes = {'001': 'excused', '002': 'unexcused'}


class SchoolToolApplicationStub(object):
    adapts(None)
    implements(ISchoolToolApplication)
    _terms = {'2004-fall': TermStub(2004, 9, 1, 12, 22),
              '2005-spring': TermStub(2005, 2, 1, 5, 21),
              '2005-fall': TermStub(2005, 9, 1, 12, 22),
              '2006-spring': TermStub(2006, 2, 1, 5, 21)}
    _attendancePrefs = AttendancePreferencesStub()
    def __init__(self, context):
        pass
    def __getitem__(self, name):
        return {'terms': self._terms}[name]
    def __conform__(self, it):
        if it is IAttendancePreferences:
            return self._attendancePrefs


class ApplicationPreferencesStub(object):
    adapts(ISchoolToolApplication)
    implements(IApplicationPreferences)
    timezone = 'UTC'
    def __init__(self, context):
        pass


class TimetableDayStub(object):
    def __init__(self, periods, homeroom_period_ids):
        self.periods = periods
        self.homeroom_period_ids = homeroom_period_ids


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
                        'D1': TimetableDayStub(['A', 'D'], []),
                        'D2': TimetableDayStub(['B', 'C'], ['B']),
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


class BaseAttendanceRecordStub(object):
    explanations = ()
    def __init__(self, section, dt, status, person=None, explained=False):
        self.section = section
        self.date = dt.date()
        self.late_arrival = dt + datetime.timedelta(minutes=15)
        self.datetime = dt
        self.status = status
        self._explained = explained
    def isAbsent(self): return self.status == ABSENT
    def isTardy(self): return self.status == TARDY
    def isExplained(self): return self._explained

    def _raiseError(self, *args):
        raise AttendanceError("An error")

    def acceptExplanation(self, code):
        print "Accepted explanation"


class SectionAttendanceRecordStub(BaseAttendanceRecordStub):
    implements(ISectionAttendanceRecord)


class HomeroomAttendanceRecordStub(BaseAttendanceRecordStub):
    implements(IHomeroomAttendanceRecord)


class SectionAttendanceStub(object):
    adapts(None)
    implements(ISectionAttendance)

    factory = SectionAttendanceRecordStub

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
        return [self.factory(sections.next(),
                             utc.localize(datetime.datetime.combine(day, time)),
                             status.next(), day < midpoint)
                for day in DateRange(first, last)]

    def get(self, section, datetime):
        return 's_%s_%s-%s' % (self.person, datetime, section)

    def record(self, section, datetime, duration, period_id, present):
        print 'Recording: %s -> %s' % (self.get(section, datetime), present)

    def getAllForDay(self, date):
        return ['s_%s_%s_%s' % (self.person, date, c) for c in 'a', 'b']


class HomeroomAttendanceStub(SectionAttendanceStub):
    implements(IHomeroomAttendance)

    factory = HomeroomAttendanceRecordStub

    def __init__(self, person):
        self.person = person
        self._records = getattr(person, '_homeroom_attendance_records', [])

    def get(self, section, datetime):
        return 'h_%s_%s-%s' % (self.person, datetime, section)

    def getAllForDay(self, date):
        return ['h_%s_%s_%s' % (self.person, date, c) for c in 'a', 'b']


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
    from schooltool.attendance.attendance import getHomeroomAttendance
    from schooltool.person.interfaces import IPerson
    ztapi.provideAdapter(IPerson, ISectionAttendance, getSectionAttendance)
    ztapi.provideAdapter(IPerson, IHomeroomAttendance, getHomeroomAttendance)


def doctest_AttendancePreferencesView():
    r"""Test for AttendancePreferencesView.

    We need to setup a SchoolToolApplication site:

        >>> app = ISchoolToolApplication(None)
        >>> prefs = IAttendancePreferences(app)
        >>> from zope.app.form.interfaces import IInputWidget
        >>> from zope.app.form.browser.textwidgets import IntWidget
        >>> from zope.schema.interfaces import IInt
        >>> ztapi.browserViewProviding(IInt, IntWidget, IInputWidget)

    Make sure we can create a view:

        >>> request = TestRequest()
        >>> from schooltool.attendance.browser.attendance import AttendancePreferencesView
        >>> view = AttendancePreferencesView(app, request)

    Check setting retroactive timeout value:

        >>> prefs.attendanceRetroactiveTimeout
        60
        >>> request = TestRequest(form={
        ...     'UPDATE_SUBMIT': 'Update',
        ...     'field.attendanceRetroactiveTimeout': '10'})
        >>> view = AttendancePreferencesView(app, request)
        >>> view.update()
        >>> prefs.attendanceRetroactiveTimeout
        10

    Now we can setup a post and add/edit/remove codes:

        >>> def printCodes():
        ...     print '\n'.join(map(str, sorted(prefs.attendanceStatusCodes.items())))

        >>> printCodes()
        ('001', 'excused')
        ('002', 'unexcused')

        >>> request = TestRequest(form={
        ...     'UPDATE_SUBMIT': 'Update',
        ...     'key_002': '003',
        ...     'value_002': 'discarded'})
        >>> view = AttendancePreferencesView(app, request)
        >>> view.update()
        >>> printCodes()
        ('001', 'excused')
        ('003', 'discarded')

        >>> request = TestRequest(form={
        ...     'ADD': 'Add',
        ...     'new_key': '404',
        ...     'new_value': 'discarded'})
        >>> view = AttendancePreferencesView(app, request)
        >>> view.update()
        >>> printCodes()
        ('001', 'excused')
        ('003', 'discarded')
        >>> view.error
        'Description fields must be unique'

        >>> request = TestRequest(form={
        ...     'ADD': 'Add',
        ...     'new_key': '404',
        ...     'new_value': 'not found'})
        >>> view = AttendancePreferencesView(app, request)
        >>> view.update()
        >>> printCodes()
        ('001', 'excused')
        ('003', 'discarded')
        ('404', 'not found')

        >>> request = TestRequest(form={
        ...     'REMOVE_003': 'Remove'})
        >>> view = AttendancePreferencesView(app, request)
        >>> view.update()
        >>> printCodes()
        ('001', 'excused')
        ('404', 'not found')

    """


def doctest_getCurrentSectionMeeting():
    r"""Doctest for getCurrentSectionMeeting

        >>> from schooltool.attendance.browser.attendance \
        ...     import getCurrentSectionMeeting

        >>> section = StubTimetables(None)

    On a day with no meetings you get None

        >>> dt = utc.localize(datetime.datetime(2005, 12, 12, 9, 30))
        >>> print getCurrentSectionMeeting(section, dt)
        None

    The timetable for 2005-12-14 looks like this:

        >>> date = datetime.date(2005, 12, 14)
        >>> for ev in section.makeTimetableCalendar(date, date):
        ...     dtend = ev.dtstart + ev.duration
        ...     print '%s--%s %s' % (ev.dtstart.strftime('%Y-%m-%d %H:%M'),
        ...                          dtend.strftime('%H:%M'), ev.title)
        2005-12-14 10:00--10:45 Math
        2005-12-14 11:00--11:45 Arts

    Let's poke around then

        >>> datetimes = []
        >>> for time in ('9:30, 10:00, 10:30, 10:45, '
        ...              '10:50, 11:00, 11:30, 11:45, 11:50').split(', '):
        ...     h, m = map(int, time.split(':'))
        ...     dt = utc.localize(datetime.datetime(2005, 12, 14, h, m))
        ...     datetimes.append(dt)

        >>> for dt in datetimes:
        ...     ev = getCurrentSectionMeeting(section, dt)
        ...     print '%s %s' % (dt.strftime('%H:%M'), ev.title)
        09:30 Math
        10:00 Math
        10:30 Math
        10:45 Arts
        10:50 Arts
        11:00 Arts
        11:30 Arts
        11:45 Arts
        11:50 Arts

    Same thing happens if you change the ordering of events returned by
    makeTimetableCalendar:

        >>> section.makeTimetableCalendar = lambda *a: \
        ...     reversed(list(StubTimetables(None).makeTimetableCalendar(*a)))

        >>> for dt in datetimes:
        ...     ev = getCurrentSectionMeeting(section, dt)
        ...     print '%s %s' % (dt.strftime('%H:%M'), ev.title)
        09:30 Math
        10:00 Math
        10:30 Math
        10:45 Arts
        10:50 Arts
        11:00 Arts
        11:30 Arts
        11:45 Arts
        11:50 Arts

    And what if you have overlapping periods?

        >>> section.makeTimetableCalendar = lambda *a: ImmutableCalendar([
        ...     TimetableCalendarEvent(
        ...         datetime.datetime(2005, 12, 14, 10, 00, tzinfo=utc),
        ...         datetime.timedelta(minutes=45),
        ...         "Math", day_id='D1', period_id="A",
        ...         activity=None),
        ...     TimetableCalendarEvent(
        ...         datetime.datetime(2005, 12, 14, 10, 45, tzinfo=utc),
        ...         datetime.timedelta(minutes=15),
        ...         "Lunch break", day_id='D1', period_id="B",
        ...         activity=None),
        ...     TimetableCalendarEvent(
        ...         datetime.datetime(2005, 12, 14, 11, 00, tzinfo=utc),
        ...         datetime.timedelta(minutes=45),
        ...         "Arts", day_id='D1', period_id="D",
        ...         activity=None),
        ...     TimetableCalendarEvent(
        ...         datetime.datetime(2005, 12, 14, 11, 40, tzinfo=utc),
        ...         datetime.timedelta(minutes=45),
        ...         "Noise", day_id='D1', period_id="Q",
        ...         activity=None),
        ...     ])

        >>> for ev in section.makeTimetableCalendar(date, date):
        ...     dtend = ev.dtstart + ev.duration
        ...     print '%s--%s %s' % (ev.dtstart.strftime('%Y-%m-%d %H:%M'),
        ...                          dtend.strftime('%H:%M'), ev.title)
        2005-12-14 10:00--10:45 Math
        2005-12-14 10:45--11:00 Lunch break
        2005-12-14 11:00--11:45 Arts
        2005-12-14 11:40--12:25 Noise

        >>> for dt in datetimes:
        ...     ev = getCurrentSectionMeeting(section, dt)
        ...     print '%s %s' % (dt.strftime('%H:%M'), ev.title)
        09:30 Math
        10:00 Math
        10:30 Math
        10:45 Lunch break
        10:50 Lunch break
        11:00 Arts
        11:30 Arts
        11:45 Noise
        11:50 Noise

    What if you use outlandish timezones, and cross the date line?

        >>> tokyo = timezone('Pacific/Rarotonga')
        >>> dt = datetimes[0].astimezone(tokyo)

        >>> dt.astimezone(utc) == datetimes[0]
        True
        >>> dt.date() != datetimes[0].date()
        True

        >>> for dt in datetimes:
        ...     ev = getCurrentSectionMeeting(section, dt.astimezone(tokyo))
        ...     print '%s %s' % (dt.strftime('%H:%M'), ev.title)
        09:30 Math
        10:00 Math
        10:30 Math
        10:45 Lunch break
        10:50 Lunch break
        11:00 Arts
        11:30 Arts
        11:45 Noise
        11:50 Noise

    """


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

def doctest_AttendanceView():
    r"""Tests for AttendanceView.

        >>> from schooltool.attendance.browser.attendance import AttendanceView
        >>> request = TestRequest()
        >>> view = AttendanceView(None, request)

    Calling the view during or before the section meeting should
    update the form and render the realtime template:

        >>> def update():
        ...     print "Updated form."
        >>> def realtime_template():
        ...     return "The real-time template"
        >>> view.update = update
        >>> view.realtime_template = realtime_template
        >>> view.sectionMeetingFinished = lambda: False
        >>> view.verifyParameters = lambda: True

        >>> view()
        Updated form.
        'The real-time template'

    Calling the view some time after the section meeting should
    update the form and render the retroactive template:

        >>> def retro_update():
        ...     print "Updated retro form."
        >>> def retro_template():
        ...     return "The retro template"
        >>> view.retro_update = retro_update
        >>> view.retro_template = retro_template
        >>> view.sectionMeetingFinished = lambda: True

        >>> view()
        Updated retro form.
        'The retro template'

    Unless verifyParameters raises NoSectionMeetingToday exception:

        >>> from schooltool.attendance.browser.attendance \
        ...      import NoSectionMeetingToday
        >>> def verify_parameters():
        ...     raise NoSectionMeetingToday
        >>> view.verifyParameters = verify_parameters
        >>> def nsmt_template():
        ...     return "The nsmt template"
        >>> view.no_section_meeting_today_template = nsmt_template

        >>> view()
        'The nsmt template'

    """


def doctest_AttendanceView_listMembers():
    r"""Test for AttendanceView.listMembers

    First, let's register getSectionAttendance as an adapter:

        >>> setUpAttendanceAdapters()

    We'll need timetabling too:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    Let's set up a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     AttendanceView, getPeriodEventForSection
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> fakePath(section, '/section/absentology')
        >>> view = AttendanceView(section, TestRequest())
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


def doctest_AttendanceView_getDaysAttendanceRecords():
    r"""Tests for AttendanceView.getDaysAttendanceRecords.

        >>> provideAdapter(SectionAttendanceStub)
        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)

        >>> from schooltool.attendance.browser.attendance \
        ...         import AttendanceView
        >>> view = AttendanceView(None, None)

        >>> view.getDaysAttendanceRecords('stud1', datetime.date(2006, 1, 3))
        ['s_stud1_2006-01-03_a', 's_stud1_2006-01-03_b',
         'h_stud1_2006-01-03_a', 'h_stud1_2006-01-03_b']

    """


def doctest_AttendanceView_studentStatus():
    r"""Tests for AttendanceView.studentStatus

    First, let's register getSectionAttendance as an adapter:

        >>> setUpAttendanceAdapters()

    We will need a view

        >>> from schooltool.attendance.browser.attendance import \
        ...     AttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> view = AttendanceView(section, TestRequest())
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


def doctest_AttendanceView_update():
    r"""Tests for AttendanceView.update

    Let's set up the section attendance adapter:

        >>> setUpAttendanceAdapters()

    We'll need timetabling stubbed too:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    Let's create a section and a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     AttendanceView, getPeriodEventForSection
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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.homeroom = False

        >>> view.update()

        >>> view.error
        u'The arrival time you entered is invalid.  Please use HH:MM format'

    """


def doctest_AttendanceView_update_homeroom():
    r"""Tests for AttendanceView.update

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    The ``update`` method is able to tell the difference between regular
    section meetings and the homeroom meeting.

        >>> from schooltool.attendance.browser.attendance import AttendanceView
        >>> from schooltool.attendance.browser.attendance \
        ...     import getPeriodEventForSection
        >>> section = SectionStub()
        >>> request = TestRequest()
        >>> view = AttendanceView(section, request)

    The 'C' period on 2005-12-15 is a regular section meeting

        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.update()
        >>> view.homeroom
        False

    The 'B' period, on the other hand, is the homeroom period

        >>> view.period_id = 'B'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'B')
        >>> view.update()
        >>> view.homeroom
        True

    """


def doctest_AttendanceView_update_homeroom():
    r"""Tests for AttendanceView.update

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    The ``update`` method is able to tell the difference between regular
    section meetings and the homeroom meeting.

        >>> from schooltool.attendance.browser.attendance \
        ...     import AttendanceView, getPeriodEventForSection
        >>> section = SectionStub()
        >>> request = TestRequest()
        >>> view = AttendanceView(section, request)

    The 'C' period on 2005-12-15 is a regular section meeting

        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'C')
        >>> view.update()

    The 'B' period, on the other hand, is the homeroom period

        >>> view.period_id = 'B'
        >>> view.meeting = getPeriodEventForSection(section, view.date, 'B')
        >>> view.update()

    """


def doctest_AttendanceView_update_set_homeroom():
    r"""Tests for AttendanceView.update

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    We will also need attendance adapters.

        >>> setUpAttendanceAdapters()

    The AttendanceView is used both for regular section meetings,
    and for homeroom attendance.

        >>> from schooltool.attendance.browser.attendance \
        ...     import AttendanceView, getPeriodEventForSection
        >>> section = SectionStub()
        >>> request = TestRequest()
        >>> view = AttendanceView(section, request)

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
        >>> view.meeting = getPeriodEventForSection(section, view.date,
        ...                                         view.period_id)
        >>> view.homeroom = True

    If you mark some absences, they will be recorded as homeroom
    absences, not just section absences.

        >>> view.request = TestRequest(form={'ABSENT': 'Absent',
        ...                                  'p1_check': 'on'})
        >>> view.update()

        >>> list(IHomeroomAttendance(person1))
        [HomeroomAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(IHomeroomAttendance(person2))
        [HomeroomAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), PRESENT)]

    We can see that section attendance data was recorded too:

        >>> list(ISectionAttendance(person1))
        [SectionAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), ABSENT)]
        >>> list(ISectionAttendance(person2))
        [SectionAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), PRESENT)]

    """


def doctest_AttendanceView_retro_update():
    r"""This is an update method for the retroactive attendance form.

    We'll need some timetabling and attendance adapters:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)
        >>> setUpAttendanceAdapters()

    The AttendanceView is used both for regular section meetings,
    and for homeroom attendance.

        >>> from schooltool.attendance.browser.attendance \
        ...     import AttendanceView, getPeriodEventForSection
        >>> section = SectionStub()
        >>> request = TestRequest()
        >>> view = AttendanceView(section, request)

    We will need several persons:

        >>> from schooltool.person.person import Person
        >>> person1 = Person('person1', title='Person1')
        >>> person1.__name__ = 'p1'
        >>> person2 = Person('person2', title='Person2')
        >>> person2.__name__ = 'p2'
        >>> person3 = Person('person3', title='Person3')
        >>> person3.__name__ = 'p3'
        >>> person4 = Person('person4', title='Person4')
        >>> person4.__name__ = 'p4'
        >>> section.members = [person1, person2, person3, person4]

    The 'B' period is the homeroom period:

        >>> view.date = datetime.date(2005, 12, 15)
        >>> view.period_id = 'B'
        >>> view.meeting = getPeriodEventForSection(section, view.date,
        ...                                         view.period_id)
        >>> view.homeroom = True

    Let's say the first person was present, the other was absent, the
    third was tardy, and we're undecided about the last one:

        >>> view.request = TestRequest(form={'p1': 'P', 'p2': 'A',
        ...                                  'p3': 'T', 'p3_tardy': '10:10',
        ...                                  'p4': 'U'})
        >>> view.retro_update()

    When there's no submit in the request, nothing happens:

        >>> list(ISectionAttendance(person1))
        []

    Now we press the submit button:

        >>> view.request = TestRequest(form={'p1': 'P', 'p2': 'A',
        ...                                  'p3': 'T', 'p3_tardy': '10:10',
        ...                                  'p4': 'U', 'SUBMIT': 'Go!'})
        >>> view.retro_update()

        >>> list(ISectionAttendance(person1))
        [SectionAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), PRESENT)]

        >>> list(ISectionAttendance(person2))
        [SectionAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), ABSENT)]

        >>> list(ISectionAttendance(person3))
        [SectionAttendanceRecord(<...SectionStub...>,
             datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), TARDY)]
        >>> list(ISectionAttendance(person3))[0].late_arrival
        datetime.datetime(2005, 12, 15, 10, 10, tzinfo=<UTC>)

        >>> list(ISectionAttendance(person4))
        []

    The homeroom records are updated as well:

        >>> list(IHomeroomAttendance(person1))
        [HomeroomAttendanceRecord(<...SectionStub...>,
         datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), PRESENT)]

        >>> list(IHomeroomAttendance(person2))
        [HomeroomAttendanceRecord(<...SectionStub...>,
         datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), ABSENT)]

        >>> list(IHomeroomAttendance(person3))
        [HomeroomAttendanceRecord(<...SectionStub...>,
         datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>), TARDY)]

        >>> list(IHomeroomAttendance(person4))
        []

    Let's test the error handling of the arrival times:

        >>> view.period_id = 'C'
        >>> view.meeting = getPeriodEventForSection(section, view.date,
        ...                                         view.period_id)
        >>> view.homeroom = False
        >>> view.request = TestRequest(form={'p1': 'P', 'p1_tardy': '12:34',
        ...                                  'p2': 'T', 'p2_tardy': '',
        ...                                  'p3': 'T', 'p3_tardy': '10 mins',
        ...                                  'p4': 'T', 'p4_tardy': '10:10',
        ...                                  'SUBMIT': 'Go!'})
        >>> view.retro_update()
        >>> view.arrivals
        {'p4': datetime.datetime(2005, 12, 15, 10, 10, tzinfo=<UTC>)}
        >>> pprint(view.arrival_errors)
        {'p1': u'Arrival times only apply to tardy students',
         'p2': u'You need to provide the arrival time',
         'p3': u'The arrival time you entered is invalid.
                 Please use HH:MM format'}

    When there were errors, even the valid record was not updated:

        >>> list(ISectionAttendance(person4))
        []

    """

def doctest_AttendanceView_getAttendanceRecord():
    r"""Tests for AttendanceView._getAttendanceRecord

        >>> from schooltool.attendance.browser.attendance \
        ...         import AttendanceView
        >>> request = TestRequest()
        >>> view = AttendanceView('math', request)

        >>> from schooltool.timetable.model import TimetableCalendarEvent
        >>> person = 'jonas'
        >>> view.date = datetime.date(2005, 1, 16)
        >>> view.period_id = 'p4'
        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 1, 16, 10, 25, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)

        >>> view._getAttendanceRecord(SectionAttendanceStub(person))
        's_jonas_2005-01-16 10:25:00+00:00-math'

        >>> view._getAttendanceRecord(HomeroomAttendanceStub(person))
        'h_jonas_2005-01-16 10:25:00+00:00-math'

    """


def doctest_AttendanceView_record():
    r"""Tests for AttendanceView._record

        >>> provideAdapter(SectionAttendanceStub)
        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)

        >>> from schooltool.attendance.browser.attendance \
        ...         import AttendanceView
        >>> request = TestRequest()
        >>> view = AttendanceView('math', request)

        >>> from schooltool.timetable.model import TimetableCalendarEvent
        >>> person = 'jonas'
        >>> view.date = datetime.date(2005, 1, 16)
        >>> view.period_id = 'p4'
        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2005, 1, 16, 10, 25, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)

        >>> attendance = ISectionAttendance(person)
        >>> view._record(attendance, False)
        Recording: s_jonas_2005-01-16 10:25:00+00:00-math -> False

    """


def doctest_AttendanceView_getArrival():
    r"""Tests for AttendanceView.getArrival

    We'll need person preferences for a timezone:

        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.person.preference import getPersonPreferences
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> ztapi.provideAdapter(IPerson, IPersonPreferences,
        ...                      getPersonPreferences)


    Let's create a section and a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     AttendanceView
        >>> from schooltool.course.section import Section
        >>> section = Section()

    If no arrival time was entered in the form, current time with
    timezone is returned:

        >>> view = AttendanceView(section, TestRequest())
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
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 29)
        >>> view.getArrival()
        datetime.datetime(2005, 12, 29, 22, 13,
                          tzinfo=<DstTzInfo 'Europe/Vilnius' EET+2:00:00 STD>)

    If the time in the request is invalid, we just pass the ValueError along:

        >>> request = TestRequest(form={'arrival': '2212'})
        >>> request.setPrincipal(user)
        >>> view = AttendanceView(section, request)
        >>> view.date = datetime.date(2005, 12, 29)
        >>> view.getArrival()
        Traceback (most recent call last):
          ...
        ValueError: need more than 1 value to unpack

    """


def doctest_AttendanceView_publishTraverse():
    r"""Tests for AttendanceView.publishTraverse

        >>> from schooltool.attendance.browser.attendance \
        ...          import AttendanceView

    Now we can try the typical case:

        >>> request = TestRequest()
        >>> section = 'section'
        >>> view = AttendanceView(section, request)
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

        >>> view = AttendanceView(section, request)
        >>> view.publishTraverse(request, "some time last week")
        Traceback (most recent call last):
          ...
        NotFound: Object: 'section', name: 'some time last week'

    """


def doctest_AttendanceView_verifyParameters():
    r"""Tests for AttendanceView.verifyParameters

        >>> from schooltool.attendance.browser.attendance \
        ...          import AttendanceView

    We need an ITimetables adapter in order to verify that a given
    period is valid for a given day:

        >>> ztapi.provideAdapter(None, ITimetables, StubTimetables)

    What if we try to render the view without specifying both the
    date and the period id?  We try to find the closest section meeting
    for today, but there aren't any.

        >>> request = TestRequest()
        >>> section = 'section'
        >>> view = AttendanceView(section, request)
        >>> view.__name__ = 'attendance'
        >>> view.date, view.period_id
        (None, None)

        >>> view.verifyParameters()
        Traceback (most recent call last):
          ...
        NoSectionMeetingToday

    What if we specify incomplete data?

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

    If everything is fine, verifyParameters saves the meeting
    (timetable calendar event), and if it is a homeroom period:

        >>> view.meeting
        <schooltool.timetable.model.TimetableCalendarEvent object at ...>
        >>> view.meeting.period_id
        'B'
        >>> view.meeting.dtstart
        datetime.datetime(2005, 12, 15, 10, 0, tzinfo=<UTC>)
        >>> view.homeroom
        True

    Let's try a non-homeroom period:

        >>> view.period_id = 'C'
        >>> view.verifyParameters()
        >>> view.meeting.period_id
        'C'
        >>> view.meeting.dtstart
        datetime.datetime(2005, 12, 15, 11, 0, tzinfo=<UTC>)
        >>> view.homeroom
        False

    """


def doctest_AttendanceView_sectionMeetingFinished():
    """Tests for AttendanceView.sectionMeetingFinished

    This method tells us whether to show the realtime or retroactive
    attendance form.

        >>> from schooltool.attendance.browser.attendance import AttendanceView

        >>> section = object()
        >>> view = AttendanceView(section, TestRequest())
        >>> now = datetime.datetime(2006, 4, 14, 12, 0, tzinfo=utc)
        >>> stub_utcnow(now)

    If the meeting is still in progress, sectionMeetingFinished,
    obviously, returns false:

        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2006, 4, 14, 11, 50, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)
        >>> view.sectionMeetingFinished()
        False

    Well before the meeting, it also returns False:

        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2006, 4, 14, 13, 00, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)
        >>> view.sectionMeetingFinished()
        False

    Immediately after the meeting, it also returns False:

        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2006, 4, 14, 11, 14, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)
        >>> view.sectionMeetingFinished()
        False

    However, 1 hour after the meeting has finished, it returns True:

        >>> view.meeting = TimetableCalendarEvent(
        ...     datetime.datetime(2006, 4, 14, 10, 14, tzinfo=utc),
        ...     datetime.timedelta(minutes=45),
        ...     "Math", day_id='D1', period_id="p4",
        ...     activity=None)
        >>> view.sectionMeetingFinished()
        True

    """

def doctest_AttendanceView_findClosestMeeting():
    r"""Tests for AttendanceView.findClosestMeeting

        >>> from schooltool.attendance.browser.attendance \
        ...          import AttendanceView

        >>> request = TestRequest()
        >>> section = 'section'
        >>> view = AttendanceView(section, request)

    If we have date and period_id in the request, then we're processing a form
    and should use them.

        >>> request.form['date'] = '2005-10-12'
        >>> request.form['period_id'] = 'quux'
        >>> view.findClosestMeeting()
        >>> view.date
        datetime.date(2005, 10, 12)
        >>> view.period_id
        'quux'

    Otherwise look at the current date and time.

        >>> del request.form['date']
        >>> del request.form['period_id']

        >>> from schooltool.attendance.browser import attendance
        >>> real_getCurrentSectionMeeting = attendance.getCurrentSectionMeeting
        >>> asked_for = [None, None]
        >>> def getCurrentSectionMeeting_stub(section, time, asked_for=asked_for):
        ...     asked_for[:] = time, section
        ...     return TimetableCalendarEvent(
        ...         datetime.datetime(2005, 12, 14, 10, 00, tzinfo=utc),
        ...         datetime.timedelta(minutes=45),
        ...         "Math", day_id='D1', period_id="qwerty", activity=None)
        >>> attendance.getCurrentSectionMeeting = getCurrentSectionMeeting_stub

        >>> before = utc.localize(datetime.datetime.utcnow())
        >>> view.findClosestMeeting()
        >>> after = utc.localize(datetime.datetime.utcnow())

        >>> before <= asked_for[0] <= after
        True
        >>> asked_for[1] == section
        True

        >>> before.date() <= view.date <= after.date()
        True
        >>> view.period_id
        'qwerty'

    If there are no meetings, raise NoSectionMeetingToday

        >>> attendance.getCurrentSectionMeeting = lambda *args: None
        >>> view.findClosestMeeting()
        Traceback (most recent call last):
          ...
        NoSectionMeetingToday

    Done

        >>> attendance.getCurrentSectionMeeting = real_getCurrentSectionMeeting

    """


def doctest_StudentAttendanceView():
    r"""Tests for StudentAttendanceView.

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(None, request)

    Calling the view should update the form and render the template:

        >>> def update():
        ...     print "Updated form."
        >>> def template():
        ...     return "The template"
        >>> view.update = update
        >>> view.template = template

        >>> view()
        Updated form.
        'The template'

    """


def doctest_StudentAttendanceView_parseArrivalTime():
    r"""Tests for AttendanceView.parseArrivalTime

    We'll need person preferences for a timezone:

        >>> from schooltool.person.interfaces import IPerson
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.person.preference import getPersonPreferences
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> ztapi.provideAdapter(IPerson, IPersonPreferences,
        ...                      getPersonPreferences)


    Let's create a section and a view:

        >>> from schooltool.attendance.browser.attendance import \
        ...     StudentAttendanceView

    If no arrival time was passed None is returned:

        >>> view = StudentAttendanceView(None, TestRequest())
        >>> arrival = view.parseArrivalTime(None, "")
        >>> arrival is None
        True

    However if some time was given it should get parsed and combined
    with the date:

        >>> from schooltool.person.person import Person
        >>> user = Person('user')
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> IPersonPreferences(user).timezone = 'Europe/Vilnius'

        >>> request = TestRequest()
        >>> request.setPrincipal(user)
        >>> view = StudentAttendanceView(None, request)
        >>> date = datetime.date(2005, 12, 29)
        >>> view.parseArrivalTime(date, '22:13')
        datetime.datetime(2005, 12, 29, 22, 13,
                          tzinfo=<DstTzInfo 'Europe/Vilnius' EET+2:00:00 STD>)

    If the time is invalid, we just pass the ValueError along:

        >>> view = StudentAttendanceView(None, request)
        >>> date = datetime.date(2005, 12, 29)
        >>> view.parseArrivalTime(date, '2213')
        Traceback (most recent call last):
          ...
        ValueError: need more than 1 value to unpack

    """


def doctest_StudentAttendanceView_makeTardy():
    r"""Tests for StudentAttendanceView.makeTardy

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.errors = []

        >>> ar = HomeroomAttendanceRecordStub(None,
        ...          datetime.datetime(2006, 1, 29, tzinfo=utc), ABSENT)
        >>> def makeTardy(dt):
        ...     print "Made tardy %s" % dt
        >>> ar.makeTardy = makeTardy
        >>> view.parseArrivalTime = lambda date, time: "%s %s" % (date, time)

        >>> view._makeTardy(ar, "22:15", {'absence': 'THIS ABSENCE'})
        Made tardy 2006-01-29 22:15
        True
        >>> view.errors
        []

        >>> ar.makeTardy = ar._raiseError
        >>> view._makeTardy(ar, "22:15", {'absence': 'THIS ABSENCE'})
        False

        >>> for err in view.errors:
        ...     print translate(err)
        Could not convert THIS ABSENCE absence intoa homeroom tardy

    Only homeroom attendance records can be converted into tardies:

        >>> view.errors = []
        >>> view._makeTardy("tsmee", "22:15", {'absence': 'THIS ABSENCE'})
        False

        >>> for err in view.errors:
        ...     print translate(err)
        THIS ABSENCE is not a homeroom absence, only homeroom absences can be
        converted into tardies

    If we supply an invalid time - tardy_error is set:

        >>> def valueError(date, time):
        ...     raise ValueError()
        >>> view.parseArrivalTime = valueError
        >>> view._makeTardy(ar, "22:15", {'absence': 'THIS ABSENCE'})
        False

        >>> view.tardy_error
        u'The arrival time you entered is invalid.  Please use HH:MM format'

    If no arrival_time was provided a different error message should
    appear:

        >>> view.parseArrivalTime = lambda date, time: None
        >>> view._makeTardy(ar, "", {'absence': 'THIS ABSENCE'})
        False

        >>> view.tardy_error
        u'You must provide a valid arrival time.'

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

        >>> ar = HomeroomAttendanceRecordStub(SectionStub('math17'),
        ...             datetime.datetime(2006, 1, 14, 17, 3, tzinfo=utc), ABSENT)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14 17:03: absent from homeroom

        >>> ar = HomeroomAttendanceRecordStub(SectionStub('math17'),
        ...             datetime.datetime(2006, 1, 14, 17, 3, tzinfo=utc), TARDY)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14 17:03: late for homeroom, arrived on 17:18

        >>> ar = SectionAttendanceRecordStub(SectionStub('math17'),
        ...             datetime.datetime(2006, 1, 14, 17, 3, tzinfo=utc), ABSENT)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14 17:03: absent from math17

        >>> ar = SectionAttendanceRecordStub(SectionStub('math17'),
        ...             datetime.datetime(2006, 1, 14, 17, 3, tzinfo=utc), TARDY)
        >>> print translate(view.formatAttendanceRecord(ar))
        2006-01-14 17:03: late for math17, arrived on 17:18

    """


def doctest_StudentAttendanceView_interleaveAttendanceRecords():
    r"""Tests for StudentAttendanceView.interleaveAttendanceRecords

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

    Let's use trivial stubs

        >>> class ARStub(object):
        ...     def __init__(self, datetime):
        ...         self.datetime = datetime
        ...         self.date = datetime
        ...     def __repr__(self):
        ...         return '%s%d' % (self.prefix, self.date)
        >>> class HAR(ARStub):
        ...     prefix = 'h'
        >>> class SAR(ARStub):
        ...     prefix = 's'

        >>> day = [HAR(d) for d in 1, 2, 5, 6, 7, 8]
        >>> section = [SAR(d) for d in 2, 2, 3, 4, 5, 8, 9, 10, 11]
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [h1, h2, s2, s2, s3, s4, h5, s5, h6, h7, h8, s8, s9, s10, s11]

        >>> day = [HAR(d) for d in 2, 5, 6, 7, 8]
        >>> section = [SAR(d) for d in 1, 3, 4, 4, 5, 5]
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [s1, h2, s3, s4, s4, h5, s5, s5, h6, h7, h8]

        >>> day = []
        >>> section = [SAR(d) for d in 1, 2]
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [s1, s2]

        >>> day = [HAR(d) for d in 2, 5, 6]
        >>> section = []
        >>> print list(view.interleaveAttendanceRecords(day, section))
        [h2, h5, h6]

        >>> day = []
        >>> section = []
        >>> print list(view.interleaveAttendanceRecords(day, section))
        []

    """


def doctest_StudentAttendanceView_unresolvedAttendanceRecords():
    r"""Test for StudentAttendanceView.unresolvedAttendanceRecords

        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)
        >>> provideAdapter(SectionAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> student = PersonStub()
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(student, request)

    Simple case first: when there are no recorded absences/tardies, we get an
    empty list.

        >>> student._homeroom_attendance_records = []
        >>> student._section_attendance_records = []
        >>> list(view.unresolvedAttendanceRecords())
        []

    An unresolved absence is marked by an attendance record that is
    tardy or absent and is not yet explained:

        >>> absences = [True, True, False, False]
        >>> tardies = [False, False, True, False]
        >>> explanations = [True, False, False, False]

        >>> class AttendanceRecordStub(object):
        ...     def __init__(self, absent, tardy, explained):
        ...         self.isAbsent = lambda: absent
        ...         self.isTardy = lambda: tardy
        ...         self.isExplained = lambda: explained

        >>> ars = []
        >>> for absent, tardy, explained in zip(absences, tardies, explanations):
        ...      ars.append(AttendanceRecordStub(absent, tardy, explained))
        >>> student._homeroom_attendance_records = ars
        >>> result = list(view.unresolvedAttendanceRecords())
        >>> [ar in result for ar in ars]
        [False, True, True, False]

    """


def doctest_StudentAttendanceView_pigeonHoleAttendanceRecords():
    """Tests for StudentAttendanceView.pigeonHoleAttendanceRecords

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

        >>> class AttendanceRecordStub(object):
        ...     def __init__(self, name, year, month, day):
        ...         self.name = name
        ...         self.date = datetime.date(year, month, day)
        ...     def __repr__(self):
        ...         return self.name

    When given an empty list the method returns an empty list:

        >>> attendance_records = []
        >>> view.unresolvedAttendanceRecords = lambda : attendance_records
        >>> view.pigeonHoleAttendanceRecords()
        []

    If there are any attendance records they are placed into sublists
    by their date:

        >>> attendance_records = [AttendanceRecordStub('ar1', 2005, 1, 1),
        ...                       AttendanceRecordStub('ar2', 2005, 1, 1),
        ...                       AttendanceRecordStub('ar3', 2005, 1, 2),
        ...                       AttendanceRecordStub('ar4', 2005, 1, 2),
        ...                       AttendanceRecordStub('ar5', 2005, 1, 3),
        ...                       AttendanceRecordStub('ar6', 2005, 1, 4)]
        >>> view.unresolvedAttendanceRecords = lambda : attendance_records
        >>> view.pigeonHoleAttendanceRecords()
        [[ar1, ar2], [ar3, ar4], [ar5], [ar6]]

    """


def doctest_StudentAttendanceView_inheritsFrom():
    """Tests for StudentAttendanceView.inheritsFrom.

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

    If student was absent on the homeroom period, homeroom attendance
    record should cover all of associated section attendance records:

        >>> view.inheritsFrom(HomeroomAttendanceRecordStub(
        ...                       None,
        ...                       datetime.datetime(2005, 1, 1),
        ...                       ABSENT),
        ...                   None)
        True

    If student was late to the homeroom only attendance records with
    arrival time upto the late_arival + 5 minutes should be considered
    as inheriting:

        >>> hr_ar = HomeroomAttendanceRecordStub(None,
        ...             datetime.datetime(2005, 1, 1, 10, 15),
        ...             TARDY)
        >>> section_ar = SectionAttendanceRecordStub(None,
        ...                 datetime.datetime(2005, 1, 1, 10, 15),
        ...                 TARDY)

        >>> view.inheritsFrom(hr_ar, section_ar)
        True

        >>> section_ar.late_arrival += datetime.timedelta(minutes=5)
        >>> view.inheritsFrom(hr_ar, section_ar)
        True

        >>> section_ar.late_arrival += datetime.timedelta(minutes=1)
        >>> view.inheritsFrom(hr_ar, section_ar)
        False

    """


def doctest_StudentAttendanceView_getInheritingRecords():
    """Tests for StudentAttendanceView.getInheritingRecords

        >>> hr_ar = HomeroomAttendanceRecordStub(None,
        ...             datetime.datetime(2005, 1, 1, 10, 15),
        ...             TARDY)
        >>> class HomeroomAttendanceStub(object):
        ...     adapts(None)
        ...     implements(IHomeroomAttendance)
        ...     def __init__(self, person):
        ...         pass
        ...     def getHomeroomPeriodForRecord(self, record):
        ...         if record.date == hr_ar.date:
        ...             return hr_ar

        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

    If there are no attendance records, return an empty list:

        >>> view.getInheritingRecords(hr_ar, [])
        []


    If not, only records that have the hr_ar as their parent homeroom
    period and should inherit from it are returned:

        >>> section = SectionStub("English")
        >>> section_records = [SectionAttendanceRecordStub(section,
        ...                        datetime.datetime(2005, 1, 1, 10, 15),
        ...                        TARDY),
        ...                    SectionAttendanceRecordStub(section,
        ...                        datetime.datetime(2005, 1, 2, 10, 15),
        ...                        TARDY),
        ...                    SectionAttendanceRecordStub(section,
        ...                        datetime.datetime(2005, 1, 1, 10, 21),
        ...                        TARDY)]
        >>> [translate(view.formatAttendanceRecord(ar))
        ...  for ar in view.getInheritingRecords(hr_ar, section_records)]
        [u'2005-01-01 10:15: late for English, arrived on 10:30']

    """


def doctest_StudentAttendanceView_hasParentHomeroom():
    """Tests for StudentAttendanceView.hasParentHomeroom

        >>> hr_ar = HomeroomAttendanceRecordStub(None,
        ...             datetime.datetime(2005, 1, 1, 10, 15),
        ...             TARDY)
        >>> class HomeroomAttendanceStub(object):
        ...     adapts(None)
        ...     implements(IHomeroomAttendance)
        ...     def __init__(self, person):
        ...         pass
        ...     def getHomeroomPeriodForRecord(self, record):
        ...         if record.date == hr_ar.date:
        ...             return hr_ar

        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)

    If there are no other attendance records, return False:

        >>> section = SectionStub("English")
        >>> section_ar = SectionAttendanceRecordStub(section,
        ...                  datetime.datetime(2005, 1, 1, 10, 15),
        ...                  TARDY)
        >>> view.hasParentHomeroom(section_ar, [section_ar])
        False

    If there is a homeroom given attendance record inherits from return True:

        >>> records = [hr_ar,
        ...            SectionAttendanceRecordStub(section,
        ...                datetime.datetime(2005, 1, 2, 10, 15),
        ...                TARDY),
        ...            SectionAttendanceRecordStub(section,
        ...                datetime.datetime(2005, 1, 1, 10, 21),
        ...                TARDY)]
        >>> view.hasParentHomeroom(section_ar, records)
        True

    Unless you were too late:

        >>> section_ar2 = SectionAttendanceRecordStub(section,
        ...                   datetime.datetime(2005, 1, 1, 10, 21),
        ...                   TARDY)
        >>> view.hasParentHomeroom(section_ar2, records)
        False

    """


def doctest_StudentAttendanceView_hideInheritingRecords():
    """Tests for StudentAttendanceView.hideInheritingRecords

    Method removes all section attendance records that have a parent
    homeroom attendance record from the list:

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> days = [['hr1', 'ar1', 'hr1ar1'], ['hr2', 'hr2ar1', 'hr2ar2', 'ar3']]

    Method hasParentHomeroom is used when checking whether attendance
    record is inheriting from any of attendance records in the day:

        >>> view.hasParentHomeroom = lambda ar, day: [
        ...                              rec for rec in day
        ...                              if rec != ar and ar.startswith(rec)]
        >>> view.hideInheritingRecords(days)
        [['hr1', 'ar1'],
         ['hr2', 'ar3']]

    """


def doctest_StudentAttendanceView_flattenDays():
    r"""Tests for StudentAttendanceView.flattenDays

    Flatten day takes a list of days and puts all the attendance
    records into a flat list with dicts for each attendance record:

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> days = [['ar1'], ['ar4', 'ar5']]
        >>> view.makeId = lambda x: "Id for %s" % x
        >>> view.formatAttendanceRecord = lambda x: "Text for %s" % x
        >>> view.outstandingExplanation = lambda x: "Explanations for %s" % x
        >>> view.flattenDays(days)
        [{'text': 'Text for ar1',
          'attendance_record': 'ar1',
          'explanation': 'Explanations for ar1',
          'id': 'Id for ar1',
          'day': ['ar1']},
         {'text': 'Text for ar4',
          'attendance_record': 'ar4',
          'explanation': 'Explanations for ar4',
          'id': 'Id for ar4',
          'day': ['ar4', 'ar5']},
         {'text': 'Text for ar5',
          'attendance_record': 'ar5',
          'explanation': 'Explanations for ar5',
          'id': 'Id for ar5',
          'day': ['ar4', 'ar5']}]

    """


def doctest_StudentAttendanceView_unresolvedAbsencesForDisplay():
    r"""Tests for StudentAttendanceView.unresolvedAbsencesForDisplay

    This method takes a list of pigenholed attendance records, removes
    inheriting attendance records from it and flattens the resulting
    list of days:

        >>> from schooltool.attendance.browser.attendance import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)
        >>> view.pigeonHoleAttendanceRecords = lambda: 'list of days'
        >>> def hideInheritingRecords(days):
        ...     return "%s without ineriting records" % days
        >>> view.hideInheritingRecords = hideInheritingRecords
        >>> def flattenDays(days):
        ...     return "Flattened %s." % days
        >>> view.flattenDays = flattenDays
        >>> view.unresolvedAbsencesForDisplay()
        'Flattened list of days without ineriting records.'

    """


def doctest_StudentAttendanceView_unresolvedAbsences():
    r"""Tests for StudentAttendanceView.unresolvedAbsences

    We shall use some simple attendance adapters for this test

        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)
        >>> provideAdapter(SectionAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> student = PersonStub()
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(student, request)

    Simple case first: when there are no recorded absences/tardies, we get an
    empty list.

        >>> student._homeroom_attendance_records = []
        >>> student._section_attendance_records = []
        >>> list(view.unresolvedAbsences())
        []

    Let's create some attendances.

        >>> first = datetime.date(2006, 1, 21)
        >>> last = datetime.date(2006, 1, 28)
        >>> time = datetime.time(9, 30)
        >>> sections = itertools.cycle([SectionStub('math42'),
        ...                             SectionStub('grammar3'),
        ...                             SectionStub('relativity97')])
        >>> dts = [utc.localize(datetime.datetime.combine(day, time))
        ...        for day in DateRange(first, last)]
        >>> statii = 5*[PRESENT, ABSENT, TARDY, PRESENT]

        >>> student._homeroom_attendance_records = [
        ...         HomeroomAttendanceRecordStub(None,
        ...                 dt,
        ...                 status,
        ...                 'person',
        ...                 dt.date() >= datetime.date(2006, 1, 26))
        ...         for dt, status in zip(dts, statii)]

        >>> student._section_attendance_records = [
        ...         SectionAttendanceRecordStub(section,
        ...                 dt,
        ...                 status,
        ...                 'person',
        ...                 dt.date() >= datetime.date(2006, 1, 26))
        ...         for section, dt, status in zip(sections, dts, statii)]

        >>> for absence in view.unresolvedAbsences():
        ...     print translate(absence['text'])
        2006-01-22 09:30: absent from homeroom
        2006-01-22 09:30: absent from grammar3
        2006-01-23 09:30: late for homeroom, arrived on 09:45
        2006-01-23 09:30: late for relativity97, arrived on 09:45

    """


def doctest_StudentAttendanceView_absencesForTerm():
    r"""Tests for StudentAttendanceView.absencesForTerm

    We shall use some simple attendance adapters for this test

        >>> provideAdapter(HomeroomAttendanceStub, provides=IHomeroomAttendance)
        >>> provideAdapter(SectionAttendanceStub)

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> student = PersonStub()
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(student, request)

        >>> term = TermStub(2006, 2, 20, 3, 7)
        >>> for a in view.absencesForTerm(term):
        ...     print translate(a)
        2006-02-21 09:30: absent from homeroom
        2006-02-21 09:30: absent from grammar3
        2006-02-22 09:30: late for homeroom, arrived on 09:45
        2006-02-22 09:30: late for relativity97, arrived on 09:45
        2006-02-25 09:30: absent from homeroom
        2006-02-25 09:30: absent from relativity97
        2006-02-26 09:30: late for homeroom, arrived on 09:45
        2006-02-26 09:30: late for math42, arrived on 09:45
        2006-03-01 09:30: absent from homeroom
        2006-03-01 09:30: absent from math42
        2006-03-02 09:30: late for homeroom, arrived on 09:45
        2006-03-02 09:30: late for grammar3, arrived on 09:45
        2006-03-05 09:30: absent from homeroom
        2006-03-05 09:30: absent from grammar3
        2006-03-06 09:30: late for homeroom, arrived on 09:45
        2006-03-06 09:30: late for relativity97, arrived on 09:45

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
        >>> a = AttendanceRecord(None, some_dt, ABSENT, 'person')
        >>> p = AttendanceRecord(None, some_dt, PRESENT, 'person')
        >>> t = AttendanceRecord(None, some_dt, UNKNOWN, 'person')
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
        >>> a = AttendanceRecord(None, some_dt, ABSENT, 'person')
        >>> p = AttendanceRecord(None, some_dt, PRESENT, 'person')
        >>> t = AttendanceRecord(None, some_dt, UNKNOWN, 'person')
        >>> t.status = TARDY

        >>> class TermStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name
        ...         self.title = name
        ...         self.first = name
        ...         self.last = name

        >>> class HomeroomAttendanceStub(object):
        ...     adapts(None)
        ...     implements(IHomeroomAttendance)
        ...     def __init__(self, context):
        ...         pass
        ...     def filter(self, first, last):
        ...         return {'term1': [p, p, p, a, p, a, t, t, a, p, p],
        ...                 'term2': [a, a, p, t, p],
        ...                 'term3': [p, p, p]}[first]
        >>> provideAdapter(HomeroomAttendanceStub)
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
        ...     print ('%(title)s  %(homeroom_absences)d %(homeroom_tardies)d'
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

        >>> from schooltool.attendance.attendance import HomeroomAttendanceRecord
        >>> dt = utc.localize(datetime.datetime(2006, 1, 29, 14, 30))
        >>> a = HomeroomAttendanceRecord(SectionStub(u'Some section \u1234'),
        ...                              dt, ABSENT, 'person')

        >>> view.makeId(a)
        'h_2006-01-29_14:30:00+00:00_homeroom'

        >>> from schooltool.attendance.attendance import SectionAttendanceRecord
        >>> a = SectionAttendanceRecord(SectionStub(u'Some section \u1234'),
        ...                             dt, ABSENT, 'person')

        >>> view.makeId(a)
        's_2006-01-29_14:30:00+00:00_U29tZSBzZWN0aW9uIOGItA=='

    """


def doctest_StudentAttendanceView_outstandingExplanation():
    r"""Tests for StudentAttendanceView.outstandingExplanation

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> view = StudentAttendanceView(None, None)


        >>> from schooltool.attendance.attendance import HomeroomAttendanceRecord
        >>> a = HomeroomAttendanceRecord(None,
        ...         datetime.datetime(2006, 1, 29, tzinfo=utc),
        ...         ABSENT, 'person')

        >>> print view.outstandingExplanation(a)
        None

        >>> a.addExplanation('Burumburum')
        >>> print view.outstandingExplanation(a)
        Burumburum

        >>> a.rejectExplanation()
        Rejected explanation
        >>> print view.outstandingExplanation(a)
        None

        >>> a.addExplanation('Qua qua')
        >>> print view.outstandingExplanation(a)
        Qua qua

        >>> a.acceptExplanation('001')
        Accepted explanation
        >>> print view.outstandingExplanation(a)
        None

    """


def doctest_StudentAttendanceView_update():
    r"""Tests for StudentAttendanceView.update

        >>> from schooltool.attendance.browser.attendance \
        ...        import StudentAttendanceView
        >>> request = TestRequest()
        >>> view = StudentAttendanceView(None, request)
        >>> def _process(ar, text, explanation, resolve, code, late_arrival):
        ...     print ar
        ...     if explanation: print 'Explaining %s: %s' % (text, explanation)
        ...     if resolve == 'accept':
        ...         print 'Accepting %s (code %r)' % (text, code)
        ...     if resolve == 'reject': print 'Rejecting %s' % text
        ...     if resolve == 'tardy': print 'Converting %s to tardy on %s' % (text, late_arrival)
        >>> view._process = _process
        >>> view.unresolvedAbsences = lambda: [
        ...     {'id': 'ar123', 'attendance_record': '<ar123>',
        ...      'text': 'Attendance Record #123', 'day': ['<ar124>']},
        ...     {'id': 'ar124', 'attendance_record': '<ar124>',
        ...      'text': 'Attendance Record #124', 'day': ['<ar123>']},
        ...     {'id': 'ar125', 'attendance_record': '<ar125>',
        ...      'text': 'Attendance Record #125', 'day': []},
        ... ]
        >>> view.getInheritingRecords = lambda ar, day: []
        >>> view.formatAttendanceRecord = lambda ar: ar

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
        >>> request.form['field.code'] = 'excused'
        >>> request.form['resolve'] = 'accept'
        >>> view.update()
        <ar123>
        Explaining Attendance Record #123: yada yada
        Accepting Attendance Record #123 (code '001')
        <ar125>
        Explaining Attendance Record #125: yada yada
        Accepting Attendance Record #125 (code '001')

   If attendance record has inheriting attendance records - they
   should be updated too:

        >>> request.form = {}
        >>> request.form['UPDATE'] = u'Do it!'
        >>> request.form['ar123'] = 'on'
        >>> request.form['explanation'] = 'yada yada'
        >>> request.form['field.code'] = 'excused'
        >>> request.form['resolve'] = 'accept'
        >>> view.getInheritingRecords = lambda ar, day: ['<ar126>', '<ar127>']
        >>> view.update()
        <ar123>
        Explaining Attendance Record #123: yada yada
        Accepting Attendance Record #123 (code '001')
        <ar126>
        Explaining <ar126>: yada yada
        Accepting <ar126> (code '001')
        <ar127>
        Explaining <ar127>: yada yada
        Accepting <ar127> (code '001')

    Make tardy should not be inherited, as this form should allow only
    homeroom periods to be converted into tardies:

        >>> request.form = {}
        >>> request.form['UPDATE'] = u'Do it!'
        >>> request.form['ar123'] = 'on'
        >>> request.form['resolve'] = 'tardy'
        >>> request.form['tardy_time'] = '15:56'
        >>> view.getInheritingRecords = lambda ar, day: ['<ar126>', '<ar127>']
        >>> view.update()
        <ar123>
        Converting Attendance Record #123 to tardy on 15:56

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
        >>> view._makeTardy = print_and_return_True('makeTardy')

        >>> ar = 'attendance_record'
        >>> text = 'THIS ABSENCE'
        >>> view._process(ar, text, '', 'ignore', '', '')

    Nothing happened.

        >>> view.statuses
        []

    Let's add an explanation; nothing else

        >>> view._process(ar, text, 'explainexplainexplain', 'ignore', '', '')
        addExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Added an explanation for THIS ABSENCE

    Let's accept an explanation; nothing else

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'accept', '001', '')
        acceptExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Resolved THIS ABSENCE

    Let's reject an explanation; nothing else

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'reject', '', '')
        rejectExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Rejected explanation for THIS ABSENCE

    Ok, now let's both add and accept an explanation

        >>> view.statuses = []
        >>> view._process(ar, text, 'gugugu', 'accept', '001', '')
        addExplanation
        acceptExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Resolved THIS ABSENCE

    Let's reject an explanation; nothing else

        >>> view.statuses = []
        >>> view._process(ar, text, 'baaaa', 'reject', '', '')
        addExplanation
        rejectExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Rejected explanation for THIS ABSENCE

    Let's make this absence into a tardy:

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'tardy', '', '15:23')
        makeTardy
        >>> for status in view.statuses:
        ...     print translate(status)
        Made THIS ABSENCE a tardy

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

        >>> view._process(ar, text, 'explainexplainexplain', 'ignore', '', '')
        addExplanation
        >>> view.statuses
        []

    You cannot accept/reject anything if addExplanation fails

        >>> view._process(ar, text, 'explainexplainexplain', 'accept', '001', '')
        addExplanation
        >>> view._process(ar, text, 'explainexplainexplain', 'reject', '', '')
        addExplanation
        >>> view.statuses
        []

    Ok, suppose you could add an explanation, but accept/reject borks

        >>> view._addExplanation = print_and_return_True('addExplanation')
        >>> view._acceptExplanation = print_and_return_False('acceptExplanation')
        >>> view._rejectExplanation = print_and_return_False('rejectExplanation')

        >>> view._process(ar, text, 'explainexplainexplain', 'accept', '001', '')
        addExplanation
        acceptExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Added an explanation for THIS ABSENCE

        >>> view.statuses = []
        >>> view._process(ar, text, 'explainexplainexplain', 'reject', '', '')
        addExplanation
        rejectExplanation
        >>> for status in view.statuses:
        ...     print translate(status)
        Added an explanation for THIS ABSENCE

    Ok, suppose you did not add an explanation, and accept/reject borks

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'accept', '001', '')
        acceptExplanation
        >>> view.statuses
        []

        >>> view.statuses = []
        >>> view._process(ar, text, '', 'reject', '', '')
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

        >>> ar = HomeroomAttendanceRecordStub(None,
        ...         datetime.datetime(2006, 1, 29, tzinfo=utc),
        ...         ABSENT)

        >>> def addExplanation(explanation):
        ...     print "Added explanation:", explanation
        >>> ar.addExplanation = addExplanation
        >>> view._addExplanation(ar, 'Bububu', {'absence': 'THIS ABSENCE'})
        Added explanation: Bububu
        True
        >>> view.errors
        []

        >>> ar.addExplanation = ar._raiseError
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

        >>> ar = HomeroomAttendanceRecordStub(None,
        ...          datetime.datetime(2006, 1, 29, tzinfo=utc), ABSENT)
        >>> view._acceptExplanation(ar, '001', {'absence': 'THIS ABSENCE'})
        Accepted explanation
        True
        >>> view.errors
        []

        >>> ar.acceptExplanation = ar._raiseError
        >>> view._acceptExplanation(ar, '001', {'absence': 'THIS ABSENCE'})
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

        >>> ar = HomeroomAttendanceRecordStub(None,
        ...          datetime.datetime(2006, 1, 29, tzinfo=utc), ABSENT)
        >>> def rejectExplanation():
        ...     print "Rejected explanation"
        >>> ar.rejectExplanation = rejectExplanation
        >>> view._rejectExplanation(ar, {'absence': 'THIS ABSENCE'})
        Rejected explanation
        True
        >>> view.errors
        []

        >>> ar.rejectExplanation = ar._raiseError
        >>> view._rejectExplanation(ar, {'absence': 'THIS ABSENCE'})
        False

        >>> for err in view.errors:
        ...     print translate(err)
        There are no outstanding explanations to reject for THIS ABSENCE

    """


def doctest_AttendancePanelView_getItems():
    r"""Tests for AttendancePanelView.getItems.

        >>> from schooltool.attendance.browser.attendance import \
        ...     AttendancePanelView
        >>> from schooltool.attendance.interfaces import IUnresolvedAbsenceCache

    We'll need a few stubs:

        >>> class PersonStub(object):
        ...     def __init__(self, title):
        ...         self.title = title.capitalize()
        ...     def __repr__(self):
        ...         return self.title

        >>> har = HomeroomAttendanceRecordStub(None, some_dt, None)
        >>> sar = SectionAttendanceRecordStub(None, some_dt, None)

        >>> class AppStub(object):
        ...     implements(IUnresolvedAbsenceCache)
        ...     def __iter__(self): # from IUnresolvedAbsenceCache
        ...         return iter([('person', [har, sar, sar]),
        ...                      ('archangel', [sar]),
        ...                      ('zorro', [har])])
        ...     def __getitem__(self, key):
        ...         if key == 'persons':
        ...             return {'person': PersonStub('person'),
        ...                     'archangel': PersonStub('archangel'),
        ...                     'zorro': PersonStub('zorro')}

        >>> app = AppStub()
        >>> request = TestRequest()
        >>> view = AttendancePanelView(app, request)

        >>> for item in view.getItems(''):
        ...     print item['person'], item['title']
        ...     print ('HR: %d, section: %d'
        ...            % (item['hr_absences'], item['section_absences']))
        Person Person
        HR: 1, section: 2
        Archangel Archangel
        HR: 0, section: 1
        Zorro Zorro
        HR: 1, section: 0

    Check filtering:

        >>> for item in view.getItems('zo'):
        ...     print item['person'], item['title']
        ...     print ('HR: %d, section: %d'
        ...            % (item['hr_absences'], item['section_absences']))
        Zorro Zorro
        HR: 1, section: 0

    """


def doctest_AttendancePanelView_update():
    r"""Tests for AttendancePanelView.update.

        >>> from schooltool.attendance.browser.attendance import \
        ...     AttendancePanelView
        >>> from schooltool.attendance.interfaces import IUnresolvedAbsenceCache

        >>> app = None
        >>> request = TestRequest()
        >>> view = AttendancePanelView(app, request)
        >>> def getItemsStub(search_str):
        ...     print 'getItems(%r)' % search_str
        ...     return [{'title': 'Person'},
        ...             {'title': 'Archangel'},
        ...             {'title': 'Zorro'}]
        >>> view.getItems = getItemsStub

    We call update():

        >>> view.update()
        getItems('')

        >>> view.batch.start
        0
        >>> view.batch.size
        10
        >>> [item['title'] for item in view.batch]
        ['Archangel', 'Person', 'Zorro']

    Let's chect that arguments in the request are reacted to:

        >>> request.form['batch_start'] = 2
        >>> request.form['batch_size'] = 2
        >>> view.update()
        getItems('')
        >>> view.batch.start
        2
        >>> view.batch.size
        2
        >>> [item['title'] for item in view.batch]
        ['Zorro']

    Test searching:

        >>> request.form['SEARCH'] = 'FoO'
        >>> view.update()
        getItems('FoO')
        >>> request.form['SEARCH']
        'FoO'

    If CLEAR_SEARCH is set, SEARCH will be reset:

        >>> request.form['CLEAR_SEARCH'] = 'Clear'
        >>> view.update()
        getItems('')
        >>> request.form['SEARCH']
        ''

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
