#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.browser.cal

$Id$
"""

import urllib
import re
import unittest
from logging import INFO
from datetime import datetime, date, timedelta
from pprint import pformat

from zope.testing.doctestunit import DocTestSuite
from zope.interface import directlyProvides
from schooltool.browser.tests import RequestStub, setPath
from schooltool.browser.tests import TraversalTestMixin
from schooltool.browser.tests import HTMLDocument
from schooltool.browser.tests import assertRedirectedTo
from schooltool.browser.tests import assertHasHiddenField
from schooltool.browser.tests import assertHasSubmitButton
from schooltool.tests.utils import AppSetupMixin, NiceDiffsMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.helpers import diff
from schooltool.common import dedent

__metaclass__ = type


class TimetableStub:

    def __init__(self):
        self.exceptions = []


class TimetableActivityStub:

    def __init__(self, timetable=None):
        self.timetable = timetable


def createEvent(dtstart, duration, title, **kw):
    """Create a CalendarEvent.

      >>> e = createEvent('2004-01-02 14:45:50', '5min', 'title')
      >>> e == CalendarEvent(datetime(2004, 1, 2, 14, 45, 50),
      ...                    timedelta(minutes=5), 'title')
      True

      >>> e = createEvent('2004-01-02 14:45', '3h', 'title')
      >>> e == CalendarEvent(datetime(2004, 1, 2, 14, 45), timedelta(hours=3),
      ...                    'title')
      True

      >>> e = createEvent('2004-01-02', '2d', 'title')
      >>> e == CalendarEvent(datetime(2004, 1, 2), timedelta(days=2),
      ...                    'title')
      True

    createEvent is very strict about the format of it arguments, and terse in
    error reporting, but it's OK, as it is only used in unit tests.
    """
    from schooltool.cal import CalendarEvent
    from schooltool.common import parse_datetime
    if dtstart.count(':') == 0:         # YYYY-MM-DD
        dtstart = parse_datetime(dtstart+' 00:00:00') # add hh:mm:ss
    elif dtstart.count(':') == 1:       # YYYY-MM-DD HH:MM
        dtstart = parse_datetime(dtstart+':00') # add seconds
    else:                               # YYYY-MM-DD HH:MM:SS
        dtstart = parse_datetime(dtstart)
    dur = timedelta(0)
    for part in duration.split('+'):
        part = part.strip()
        if part.endswith('d'):
            dur += timedelta(days=int(part.rstrip('d')))
        elif part.endswith('h'):
            dur += timedelta(hours=int(part.rstrip('h')))
        elif part.endswith('sec'):
            dur += timedelta(seconds=int(part.rstrip('sec')))
        else:
            dur += timedelta(minutes=int(part.rstrip('min')))
    return CalendarEvent(dtstart, dur, title, **kw)


def createCalendar(events=()):
    """Create a calendar with events.

      >>> e = createEvent('2004-01-02 14:45', '5', 'title')
      >>> c = createCalendar([e])
      >>> list(c) == [e]
      True

    """
    from schooltool.cal import Calendar
    calendar = Calendar()
    for event in events:
        calendar.addEvent(event)
    return calendar


class TestBookingView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def createView(self):
        from schooltool.browser.cal import BookingView
        view = BookingView(self.resource)
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.teacher)
        content = view.render(request)
        self.assert_('Book' in content)

    def test_book(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager,
                              args={'conflicts': 'ignore',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'BOOK': 'Book'})
        content = view.render(request)
        self.assert_('2004-08-10 19:01:00' not in content)
        self.assert_('19:01:00' not in content)
        self.assert_('2004-08-10' in content)
        self.assert_('19:01' in content)
        self.assert_('61' in content)

    def test_owner(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager,
                              args={'owner': 'teacher',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        content = view.render(request)
        self.assert_("This user does not exist" not in content)

        ev1 = iter(self.teacher.calendar).next()
        self.assert_(ev1.owner is self.teacher,
                     "%r is not %r" % (ev1.owner, self.teacher))

    def test_owner_forbidden(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.teacher,
                              args={'owner': 'manager',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        content = view.render(request)
        ev1 = iter(self.teacher.calendar).next()
        self.assert_(ev1.owner is self.teacher,
                     "%r is not %r" % (ev1.owner, self.teacher))

    def test_owner_wrong_name(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager,
                              args={'owner': 'whatever',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        content = view.render(request)
        self.assert_("This user does not exist" in content)
        self.assert_("2004-08-10" in content)
        self.assert_("19:01" in content)
        self.assert_("61" in content)

    def test_confirm_book(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.teacher,
                              args={'conflicts': 'ignore',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        content = view.render(request)
        self.assert_('Resource booked' in content)
        self.assertEquals(view.error, "")
        self.assertEquals(request.applog,
                [(self.teacher,
                  u'/resources/resource (Kitchen sink) booked by'
                  u' /persons/teacher (Prof. Bar) at 2004-08-10 19:01:00'
                  u' for 1:01:00', INFO)])

        self.assertEquals(len(list(self.teacher.calendar)), 1)
        self.assertEquals(len(list(self.resource.calendar)), 1)
        ev1 = iter(self.teacher.calendar).next()
        ev2 = iter(self.resource.calendar).next()
        self.assertEquals(ev1, ev2)
        self.assert_(ev1.context is self.resource,
                     "%r is not %r" % (ev1.context, self.resource))
        self.assert_(ev1.owner is self.teacher,
                     "%r is not %r" % (ev1.owner, self.teacher))

    def test_conflict(self):
        ev = createEvent('2004-08-10 19:00', '1h', "Some event")
        self.resource.calendar.addEvent(ev)
        self.assertEquals(len(list(self.teacher.calendar)), 0)
        self.assertEquals(len(list(self.resource.calendar)), 1)

        view = self.createView()
        request = RequestStub(authenticated_user=self.teacher,
                              args={'start_date': '2004-08-10',
                                    'start_time': '19:20',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        view.render(request)
        self.assertEquals(request.applog, [])
        self.assertEquals(view.error,
                          "The resource is busy at the specified time.")


class TestCalendarDay(unittest.TestCase):

    def test(self):
        from schooltool.browser.cal import CalendarDay
        day1 = CalendarDay(date(2004, 8, 5))
        day2 = CalendarDay(date(2004, 7, 15), ["abc", "def"])
        self.assertEquals(day1.date, date(2004, 8, 5))
        self.assertEquals(day1.events, [])
        self.assertEquals(day2.date, date(2004, 7, 15))
        self.assertEquals(day2.events, ["abc", "def"])

        self.assert_(day1 > day2 and not day1 < day2)
        self.assertEquals(day2, CalendarDay(date(2004, 7, 15)))


class TestCalendarViewBase(AppSetupMixin, unittest.TestCase):

    def assertEqualEventLists(self, result, expected):
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_update(self):
        from schooltool.browser.cal import CalendarViewBase
        from schooltool.model import Person

        view = CalendarViewBase(None)
        view.request = RequestStub()
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = RequestStub(args={'date': '2004-08-18'})
        view.update()
        self.assertEquals(view.cursor, date(2004, 8, 18))

    def test_urls(self):
        from schooltool.browser.cal import CalendarViewBase
        from schooltool.model import Person

        person = self.app['persons'].new('boss', title="Da Boss")
        cal = createCalendar()
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        view = CalendarViewBase(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 12)

        prefix = 'http://localhost:7001/persons/boss/'
        self.assertEquals(view.calURL("foo"),
                          prefix + 'calendar/foo.html?date=2004-08-12')
        self.assertEquals(view.calURL("bar", date(2005, 3, 22)),
                          prefix + 'calendar/bar.html?date=2005-03-22')

    def test_getDays(self):
        from schooltool.browser.cal import CalendarViewBase

        e0 = createEvent('2004-08-10 11:00', '1h', "e0")
        e1 = createEvent('2004-08-11 12:00', '1h', "e1", privacy="hidden")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = self.person.calendar
        for e in [e0, e1, e2, e3, e4, e5, e6, e7, e8]:
            cal.addEvent(e)

        view = CalendarViewBase(cal)
        view.request = RequestStub(authenticated_user=self.person)

        start = date(2004, 8, 10)
        days = view.getDays(start, start)
        self.assertEquals(len(days), 0)

        start = date(2004, 8, 10)
        end = date(2004, 8, 16)
        days = view.getDays(start, end)

        self.assertEquals(len(days), 6)
        for i, day in enumerate(days):
            self.assertEquals(day.date, date(2004, 8, 10 + i))

        self.assertEqualEventLists(days[0].events, [e5, e0])            # 10
        self.assertEqualEventLists(days[1].events, [e5, e2, e1])        # 11
        self.assertEqualEventLists(days[2].events, [e5, e7, e3])        # 12
        self.assertEqualEventLists(days[3].events, [e5, e7, e3, e6])    # 13
        self.assertEqualEventLists(days[4].events, [])                  # 14
        self.assertEqualEventLists(days[5].events, [e8, e4])            # 15

        start = date(2004, 8, 11)
        end = date(2004, 8, 12)
        days = view.getDays(start, end)
        self.assertEquals(len(days), 1)
        self.assertEquals(days[0].date, start)
        self.assertEqualEventLists(days[0].events, [e5, e2, e1])

        # Check that the hidden event is excluded for another person
        view.request = RequestStub(authenticated_user=self.person2)
        start = date(2004, 8, 11)
        end = date(2004, 8, 12)
        days = view.getDays(start, end)

        self.assertEqualEventLists(days[0].events, [e5, e2])            # 11

    def test_iterEvents(self):
        from schooltool.browser.cal import CalendarViewBase
        from schooltool.model import Person
        from schooltool.cal import DailyRecurrenceRule
        from schooltool.timetable import TimetableCalendarEvent

        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')

        cal = createCalendar()
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        tcal = createCalendar()
        tcal.__parent__ = person
        tcal.__name__ = 'timetable-calendar'

        ccal = createCalendar()
        ccal.__parent__ = person
        ccal.__name__ = 'composite-calendar'

        person.makeTimetableCalendar = lambda: tcal
        person.makeCompositeCalendar = lambda: ccal

        view = CalendarViewBase(cal)

        result = list(view.iterEvents(date(2004, 8, 12), date(2004, 8, 13)))
        self.assertEquals(result, [])

        ev1 = createEvent('2004-08-12 12:00', '1h', 'ev1')
        tt = TimetableStub()
        act = TimetableActivityStub(tt)
        ev_tt = TimetableCalendarEvent(datetime(2004, 8, 12, 13, 0),
                                       timedelta(hours=1), "Math",
                                       unique_id="uniq",
                                       period_id="period 1",
                                       activity=act)
        ev3 = createEvent('2004-01-01 9:00', '1h', 'coffee',
                          recurrence=DailyRecurrenceRule(), unique_id="42")
        ev3_1 = ev3.replace(dtstart=datetime(2004, 8, 12, 9, 0))
        ev3_2 = ev3.replace(dtstart=datetime(2004, 8, 13, 9, 0))
        ev4 = createEvent('2004-08-12 17:00', '1h', 'ev4')
        cal.addEvent(ev1)
        cal.addEvent(ev3)
        tcal.addEvent(ev_tt)
        ccal.addEvent(ev4)

        result = list(view.iterEvents(date(2004, 8, 12), date(2004, 8, 13)))
        result.sort()
        expected = [ev3_1, ev1, ev_tt, ev4, ev3_2]
        self.assertEquals(result, expected,
                          diff(pformat(result), pformat(expected)))
        self.assert_(result[2].__class__ is TimetableCalendarEvent)

    def test_getWeek(self):
        from schooltool.browser.cal import CalendarViewBase, CalendarDay

        cal = createCalendar()
        view = CalendarViewBase(cal)
        self.assertEquals(view.first_day_of_week, 0) # Monday by default

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 9), date(2004, 8, 11), date(2004, 8, 15)):
            week = view.getWeek(dt)
            self.assertEquals(week,
                              [CalendarDay(date(2004, 8, 9)),
                               CalendarDay(date(2004, 8, 16))])

        dt = date(2004, 8, 16)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 16)),
                           CalendarDay(date(2004, 8, 23))])

    def test_getWeek_first_day_of_week(self):
        from schooltool.browser.cal import CalendarViewBase, CalendarDay

        cal = createCalendar()
        view = CalendarViewBase(cal)
        view.first_day_of_week = 2 # Wednesday

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 11), date(2004, 8, 14), date(2004, 8, 17)):
            week = view.getWeek(dt)
            self.assertEquals(week, [CalendarDay(date(2004, 8, 11)),
                                     CalendarDay(date(2004, 8, 18))],
                              "%s: %s -- %s"
                              % (dt, week[0].date, week[1].date))

        dt = date(2004, 8, 10)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 4)),
                           CalendarDay(date(2004, 8, 11))])

        dt = date(2004, 8, 18)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 18)),
                           CalendarDay(date(2004, 8, 25))])

    def test_getMonth(self):
        from schooltool.browser.cal import CalendarViewBase, CalendarDay

        cal = createCalendar()
        view = CalendarViewBase(cal)

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        weeks = view.getMonth(date(2004, 8, 11))
        self.assertEquals(len(weeks), 6)
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds,
                          [(date(2004, 7, 26), date(2004, 8, 2)),
                           (date(2004, 8, 2), date(2004, 8, 9)),
                           (date(2004, 8, 9), date(2004, 8, 16)),
                           (date(2004, 8, 16), date(2004, 8, 23)),
                           (date(2004, 8, 23), date(2004, 8, 30)),
                           (date(2004, 8, 30), date(2004, 9, 6))])

        # October 2004 ends with a Sunday, so we use it to check that
        # no days from the next month are included.
        weeks = view.getMonth(date(2004, 10, 1))
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds[4],
                          (date(2004, 10, 25), date(2004, 11, 1)))

        # Same here, just check the previous month.
        weeks = view.getMonth(date(2004, 11, 1))
        bounds = [(d1.date, d2.date) for d1, d2 in weeks]
        self.assertEquals(bounds[0],
                          (date(2004, 11, 1), date(2004, 11, 8)))

    def test_getYear(self):
        from schooltool.browser.cal import CalendarViewBase

        cal = createCalendar()
        view = CalendarViewBase(cal)

        def getMonthStub(dt):
            return dt
        view.getMonth = getMonthStub

        year = view.getYear(date(2004, 03, 04))
        self.assertEquals(len(year), 4)
        months = []
        for quarter in year:
            self.assertEquals(len(quarter), 3)
            months.extend(quarter)
        for i, month in enumerate(months):
            self.assertEquals(month, date(2004, i+1, 1))

    def test_renderEvent(self):
        from schooltool.auth import ACL
        from schooltool.interfaces import IACLOwner
        from schooltool.browser.cal import CalendarViewBase
        cal = createCalendar()
        directlyProvides(cal, IACLOwner)
        cal.acl = ACL()
        view = CalendarViewBase(cal)
        view.request = RequestStub()
        e = createEvent('2004-01-02 14:30', '30min', u'\u263B')
        result = view.renderEvent(e, e.dtstart.date())
        self.assert_(isinstance(result, unicode))


class TestWeeklyCalendarView(AppSetupMixin, unittest.TestCase):

    def test_prev_next(self):
        from schooltool.browser.cal import WeeklyCalendarView
        view = WeeklyCalendarView(None)
        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevWeek(), date(2004, 8, 11))
        self.assertEquals(view.nextWeek(), date(2004, 8, 25))

    def test_render(self):
        from schooltool.browser.cal import WeeklyCalendarView

        person = self.app['persons'].new('boss', title="Da Boss")
        cal = createCalendar([createEvent('2004-08-11 12:00', '1h',
                                          "Stuff happens")])
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        view = WeeklyCalendarView(cal)
        view.authorization = lambda x, y: True
        request = RequestStub(args={'date': '2004-08-12'})
        content = view.render(request)
        self.assert_("Da Boss" in content, content)
        self.assert_("Stuff happens" in content)

    def test_getCurrentWeek(self):
        from schooltool.browser.cal import WeeklyCalendarView

        view = WeeklyCalendarView(None)
        view.cursor = "works"
        view.getWeek = lambda x: "really " + x
        self.assertEquals(view.getCurrentWeek(), "really works")

    def test_dayTitle(self):
        from schooltool.browser.cal import WeeklyCalendarView

        view = WeeklyCalendarView(None)
        dt = datetime(2004, 7, 1)
        self.assertEquals(view.dayTitle(dt), "Thursday, 2004-07-01")


class TestDailyCalendarView(AppSetupMixin, NiceDiffsMixin, unittest.TestCase):

    def test_update(self):
        from schooltool.browser.cal import DailyCalendarView

        view = DailyCalendarView(None)
        view.request = RequestStub()
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = RequestStub(args={'date': '2004-08-18'})
        view.update()
        self.assertEquals(view.cursor, date(2004, 8, 18))

    def test__setRange(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.model import Person

        cal = createCalendar()
        cal.__parent__ = Person(title="Da Boss")
        view = DailyCalendarView(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 16)

        def do_test(events, expected):
            view.starthour, view.endhour = 8, 19
            view._setRange(events)
            self.assertEquals((view.starthour, view.endhour), expected)

        do_test([], (8, 19))

        events = [createEvent('2004-08-16 7:00', '1min', 'workout')]
        do_test(events, (7, 19))

        events = [createEvent('2004-08-15 8:00', '1d', "long workout")]
        do_test(events, (0, 19))

        events = [createEvent('2004-08-16 20:00', '30min', "late workout")]
        do_test(events, (8, 21))

        events = [createEvent('2004-08-16 20:00', '5h', "long late workout")]
        do_test(events, (8, 24))

    def test_dayEvents(self):
        from schooltool.browser.cal import DailyCalendarView
        ev1 = createEvent('2004-08-12 12:00', '2h', "ev1")
        ev2 = createEvent('2004-08-12 13:00', '2h', "ev2")
        ev3 = createEvent('2004-08-12 14:00', '2h', "ev3")
        ev4 = createEvent('2004-08-11 14:00', '3d', "ev4")
        cal = self.person.calendar
        for e in [ev1, ev2, ev3, ev4]:
            cal.addEvent(e)
        view = DailyCalendarView(cal)
        view.request = RequestStub(authenticated_user=self.person)
        result = view.dayEvents(date(2004, 8, 12))
        expected = [ev4, ev1, ev2, ev3]
        fmt = lambda x: '[%s]' % ', '.join([e.title for e in x])
        self.assertEquals(result, expected,
                          '%s != %s' % (fmt(result), fmt(expected)))

    def test_getColumns(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.model import Person

        cal = createCalendar()
        cal.__parent__ = Person(title="Da Boss")
        cal.__parent__.makeTimetableCalendar = lambda: createCalendar()
        view = DailyCalendarView(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 12)

        self.assertEquals(view.getColumns(), 1)

        cal.addEvent(createEvent('2004-08-12 12:00', '2h', "Meeting"))
        self.assertEquals(view.getColumns(), 1)

        #
        #  Three events:
        #
        #  12 +--+
        #  13 |Me|+--+    <--- overlap
        #  14 +--+|Lu|+--+
        #  15     +--+|An|
        #  16         +--+
        #
        #  Expected result: 2

        cal.addEvent(createEvent('2004-08-12 13:00', '2h', "Lunch"))
        cal.addEvent(createEvent('2004-08-12 14:00', '2h', "Another meeting"))
        self.assertEquals(view.getColumns(), 2)

        #
        #  Four events:
        #
        #  12 +--+
        #  13 |Me|+--+    +--+ <--- overlap
        #  14 +--+|Lu|+--+|Ca|
        #  15     +--+|An|+--+
        #  16         +--+
        #
        #  Expected result: 3

        cal.addEvent(createEvent('2004-08-12 13:00', '2h',
                                 "Call Mark during lunch"))
        self.assertEquals(view.getColumns(), 3)

        #
        #  Events that do not overlap in real life, but overlap in our view
        #
        #    +-------------+-------------+-------------+
        #    | 12:00-12:30 | 12:30-13:00 | 12:00-12:00 |
        #    +-------------+-------------+-------------+
        #
        #  Expected result: 3

        cal.clear()
        cal.addEvent(createEvent('2004-08-12 12:00', '30min', "a"))
        cal.addEvent(createEvent('2004-08-12 12:30', '30min', "b"))
        cal.addEvent(createEvent('2004-08-12 12:00', '0min', "c"))
        self.assertEquals(view.getColumns(), 3)

    def test_getColumns_periods(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.model import Person
        from schooltool.common import parse_datetime

        cal = createCalendar()
        cal.__parent__ = Person(title="Da Boss")
        cal.__parent__.makeTimetableCalendar = lambda: createCalendar()
        view = DailyCalendarView(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 12)
        view.calendarRows = lambda: iter([
            ("B", parse_datetime('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetime('2004-08-12 13:00:00'), timedelta(hours=2)),
             ])
        cal.addEvent(createEvent('2004-08-12 09:00', '2h', "Whatever"))
        cal.addEvent(createEvent('2004-08-12 11:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 11:10', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:00', '2m', "Phone call"))
        cal.addEvent(createEvent('2004-08-12 12:30', '3h', "Nap"))
        self.assertEquals(view.getColumns(), 5)

    def test_getHours(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.model import Person

        cal = createCalendar()
        cal.__parent__ = Person(title="Da Boss")
        cal.__parent__.makeTimetableCalendar = lambda: createCalendar()
        view = DailyCalendarView(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 12)
        view.starthour = 10
        view.endhour = 16
        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '10:00', 'cols': (None,)},
                           {'time': '11:00', 'cols': (None,)},
                           {'time': '12:00', 'cols': (None,)},
                           {'time': '13:00', 'cols': (None,)},
                           {'time': '14:00', 'cols': (None,)},
                           {'time': '15:00', 'cols': (None,)},])

        ev1 = createEvent('2004-08-12 12:00', '2h', "Meeting")
        cal.addEvent(ev1)
        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '10:00', 'cols': (None,)},
                           {'time': '11:00', 'cols': (None,)},
                           {'time': '12:00', 'cols': (ev1,)},
                           {'time': '13:00', 'cols': ('',)},
                           {'time': '14:00', 'cols': (None,)},
                           {'time': '15:00', 'cols': (None,)},])

        #
        #  12 +--+
        #  13 |Me|+--+
        #  14 +--+|Lu|
        #  15 |An|+--+
        #  16 +--+
        #

        ev2 = createEvent('2004-08-12 13:00', '2h', "Lunch")
        ev3 = createEvent('2004-08-12 14:00', '2h', "Another meeting")
        cal.addEvent(ev2)
        cal.addEvent(ev3)

        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '10:00', 'cols': (None, None)},
                           {'time': '11:00', 'cols': (None, None)},
                           {'time': '12:00', 'cols': (ev1, None)},
                           {'time': '13:00', 'cols': ('', ev2)},
                           {'time': '14:00', 'cols': (ev3, '')},
                           {'time': '15:00', 'cols': ('', None)},])

        ev4 = createEvent('2004-08-11 14:00', '3d', "Visit")
        cal.addEvent(ev4)

        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '0:00', 'cols': (ev4, None, None)},
                           {'time': '1:00', 'cols': ('', None, None)},
                           {'time': '2:00', 'cols': ('', None, None)},
                           {'time': '3:00', 'cols': ('', None, None)},
                           {'time': '4:00', 'cols': ('', None, None)},
                           {'time': '5:00', 'cols': ('', None, None)},
                           {'time': '6:00', 'cols': ('', None, None)},
                           {'time': '7:00', 'cols': ('', None, None)},
                           {'time': '8:00', 'cols': ('', None, None)},
                           {'time': '9:00', 'cols': ('', None, None)},
                           {'time': '10:00', 'cols': ('', None, None)},
                           {'time': '11:00', 'cols': ('', None, None)},
                           {'time': '12:00', 'cols': ('', ev1, None)},
                           {'time': '13:00', 'cols': ('', '', ev2)},
                           {'time': '14:00', 'cols': ('', ev3, '')},
                           {'time': '15:00', 'cols': ('', '', None)},
                           {'time': '16:00', 'cols': ('', None, None)},
                           {'time': '17:00', 'cols': ('', None, None)},
                           {'time': '18:00', 'cols': ('', None, None)},
                           {'time': '19:00', 'cols': ('', None, None)},
                           {'time': '20:00', 'cols': ('', None, None)},
                           {'time': '21:00', 'cols': ('', None, None)},
                           {'time': '22:00', 'cols': ('', None, None)},
                           {'time': '23:00', 'cols': ('', None, None)}])

    def test_rowspan(self):
        from schooltool.browser.cal import DailyCalendarView
        view = DailyCalendarView(None)
        view.starthour = 10
        view.endhour = 18
        view.cursor = date(2004, 8, 12)

        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1d', "Long")), 6)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-11 12:00', '3d', "Very")), 8)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '10min', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1h+1sec', "")), 2)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 09:00', '3h', "")), 2)

    def test_rowspan_periods(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.common import parse_datetime
        view = DailyCalendarView(None)
        view.calendarRows = lambda: iter([
            ("8", parse_datetime('2004-08-12 08:00:00'), timedelta(hours=1)),
            ("A", parse_datetime('2004-08-12 09:00:00'), timedelta(hours=1)),
            ("B", parse_datetime('2004-08-12 10:00:00'), timedelta(hours=3)),
            ("C", parse_datetime('2004-08-12 13:00:00'), timedelta(hours=2)),
            ("D", parse_datetime('2004-08-12 15:00:00'), timedelta(hours=1)),
            ("16", parse_datetime('2004-08-12 16:00:00'), timedelta(hours=1)),
            ("17", parse_datetime('2004-08-12 17:00:00'), timedelta(hours=1)),
             ])
        view.cursor = date(2004, 8, 12)
        view.starthour = 8
        view.endhour = 18

        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1d', "Long")), 5)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-11 12:00', '3d', "Very")), 7)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '10min', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 12:00', '1h+1sec', "")), 2)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 13:00', '2h', "")), 1)
        self.assertEquals(view.rowspan(
                            createEvent('2004-08-12 09:00', '3h', "")), 2)

    def test_render(self):
        from schooltool.browser.cal import DailyCalendarView

        cal = createCalendar([createEvent('2004-08-12 12:00', '1h',
                                          "Stuff happens")])
        person = self.app['persons'].new('boss', title="Da Boss")
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        view = DailyCalendarView(cal)
        view.authorization = lambda x, y: True
        request = RequestStub(args={'date': '2004-08-12'})
        content = view.render(request)
        self.assert_("Da Boss" in content)
        self.assert_("Stuff happens" in content)


class TestMonthlyCalendarView(AppSetupMixin, unittest.TestCase):

    def test_render(self):
        from schooltool.browser.cal import MonthlyCalendarView

        person = self.app['persons'].new('boss', title="Da Boss")
        person.calendar.addEvent(createEvent('2004-08-11 12:00', '1h',
                                             "Stuff happens"))

        view = MonthlyCalendarView(person.calendar)
        request = RequestStub(authenticated_user=person,
                              args={'date': '2004-08-12'})
        content = view.render(request)
        self.assert_("Da Boss" in content)
        self.assert_("Stuff happens" in content)

    def test_prev_next(self):
        from schooltool.browser.cal import MonthlyCalendarView
        view = MonthlyCalendarView(None)
        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevMonth(), date(2004, 7, 1))
        self.assertEquals(view.nextMonth(), date(2004, 9, 1))

    def test_getCurrentMonth(self):
        from schooltool.browser.cal import MonthlyCalendarView

        view = MonthlyCalendarView(None)
        view.cursor = "works"
        view.getMonth = lambda x: "really " + x
        self.assertEquals(view.getCurrentMonth(), "really works")


class TestYearlyCalendarView(AppSetupMixin, unittest.TestCase):

    def test_render(self):
        from schooltool.browser.cal import YearlyCalendarView

        person = self.app['persons'].new('boss', title="Da Boss")
        cal = createCalendar([createEvent('2004-08-11 12:00', '1h',
                                          "Stuff happens")])
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        view = YearlyCalendarView(cal)
        view.authorization = lambda x, y: True
        request = RequestStub(args={'date': '2004-08-12'})
        content = view.render(request)

    def test_prev_next(self):
        from schooltool.browser.cal import YearlyCalendarView
        view = YearlyCalendarView(None)
        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevYear(), date(2003, 1, 1))
        self.assertEquals(view.nextYear(), date(2005, 1, 1))


class TestCalendarView(AppSetupMixin, unittest.TestCase, TraversalTestMixin):

    def test_traverse(self):
        from schooltool.browser.cal import CalendarView
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.browser.cal import WeeklyCalendarView
        from schooltool.browser.cal import MonthlyCalendarView
        from schooltool.browser.cal import YearlyCalendarView
        from schooltool.browser.cal import EventAddView
        from schooltool.browser.cal import EventEditView
        from schooltool.browser.cal import EventDeleteView
        from schooltool.browser.acl import ACLView
        context = self.person.calendar
        view = CalendarView(context)
        self.assertTraverses(view, 'daily.html', DailyCalendarView, context)
        self.assertTraverses(view, 'weekly.html', WeeklyCalendarView, context)
        self.assertTraverses(view, 'monthly.html', MonthlyCalendarView,
                             context)
        self.assertTraverses(view, 'yearly.html', YearlyCalendarView, context)
        self.assertTraverses(view, 'add_event.html', EventAddView, context)
        self.assertTraverses(view, 'edit_event.html', EventEditView, context)
        self.assertTraverses(view, 'delete_event.html', EventDeleteView,
                             context)
        self.assertTraverses(view, 'acl.html', ACLView,
                             context.acl)

    def test_render(self):
        from schooltool.browser.cal import CalendarView
        from schooltool.model import Person

        cal = createCalendar()
        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        view = CalendarView(cal)
        request = RequestStub()
        view.authorization = lambda x, y: True
        view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(
            request.headers['location'],
            'http://localhost:7001/persons/boss/calendar/daily.html')


class TestEventViewBase(AppSetupMixin, unittest.TestCase):

    def createView(self):
        from schooltool.browser.cal import EventViewBase
        view = EventViewBase(self.person.calendar)
        return view

    def test_getLocations(self):
        view = self.createView()
        locations = list(view.getLocations())
        self.assertEquals(locations, ['Inside', 'Outside'])

    def test_customized_location(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'location': '',
                                    'location_other': 'Moon',
                                    'duration': '50'},
                              method='POST',
                              authenticated_user=self.manager)

        def processStub(dtstart, duration, title, location):
            self.assertEquals(location, 'Moon')
        view.process = processStub

        content = view.render(request)

    def test_getRecurrenceRule(self):
        from schooltool.cal import DailyRecurrenceRule, WeeklyRecurrenceRule
        from schooltool.cal import MonthlyRecurrenceRule, YearlyRecurrenceRule

        def makeRule(**kwargs):
            view = self.createView()
            args = {'title': 'Hacking',
                    'start_date': '2004-08-13',
                    'start_time': '15:30',
                    'duration': '50'}
            args.update(kwargs)
            request = RequestStub(args=args, method='POST',
                                  authenticated_user=self.manager)
            view.request = request
            view.update()
            return view.getRecurrenceRule()

        # Rule is not returned when the checkbox is unchecked
        rule = makeRule(recurrence_type='daily', interval="1",
                        recurrence_shown="yes",)
        assert rule is None

        rule = makeRule(recurrence="on", recurrence_shown="yes")
        assert rule is None, rule

        rule = makeRule(recurrence='checked', recurrence_shown="yes",
                        recurrence_type='daily', interval="2")
        self.assertEquals(rule, DailyRecurrenceRule(interval=2))

        rule = makeRule(recurrence='checked', recurrence_type='weekly',
                        interval="3", recurrence_shown="yes",)
        self.assertEquals(rule, WeeklyRecurrenceRule(interval=3))

        rule = makeRule(recurrence='checked', recurrence_type='monthly',
                        interval="1", recurrence_shown="yes",)
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1))

        rule = makeRule(recurrence='checked', recurrence_type='yearly',
                        interval="", recurrence_shown="yes",)
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1))

        rule = makeRule(recurrence='checked', recurrence_type='yearly',
                        interval="1", recurrence_shown="yes",
                        until='2004-01-02', count="3", range="until")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1,
                                                     until=date(2004, 1, 2)))

        rule = makeRule(recurrence='checked', recurrence_type='yearly',
                        interval="1", recurrence_shown="yes",
                        until='2004-01-02', count="3", range="count")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1, count=3),
                          rule.__dict__)

        rule = makeRule(recurrence='checked', recurrence_type='yearly',
                        interval="1", recurrence_shown="yes",
                        until='2004-01-02', count="3", range="forever")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1))

        rule = makeRule(recurrence='checked', recurrence_type='yearly',
                        interval="1", recurrence_shown="yes",
                        until='2004-01-02', count="3")
        self.assertEquals(rule, YearlyRecurrenceRule(interval=1))

        rule = makeRule(recurrence='checked', recurrence_type='daily',
                        interval="1", recurrence_shown="yes",
                        exceptions="2004-01-01\n2004-01-02")
        dates = (date(2004, 1, 1), date(2004, 1, 2))
        self.assertEquals(rule, DailyRecurrenceRule(interval=1,
                                                    exceptions=dates))

        rule = makeRule(recurrence='checked', recurrence_type='weekly',
                        interval="1", recurrence_shown="yes",
                        weekdays="2")
        self.assertEquals(rule, WeeklyRecurrenceRule(interval=1,
                                                     weekdays=(2, )))

        rule = makeRule(recurrence='checked', recurrence_type='weekly',
                        interval="1", recurrence_shown="yes",
                        weekdays=["1", "2"])
        self.assertEquals(rule, WeeklyRecurrenceRule(interval=1,
                                                     weekdays=(1, 2)))

        rule = makeRule(recurrence='checked', recurrence_type='monthly',
                        interval="1", recurrence_shown="yes",
                        monthly="monthday")
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1,
                                                      monthly="monthday"))

        rule = makeRule(recurrence='checked', recurrence_type='monthly',
                        interval="1", recurrence_shown="yes",
                        monthly="weekday")
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1,
                                                      monthly="weekday"))

        rule = makeRule(recurrence='checked', recurrence_type='monthly',
                        interval="1", recurrence_shown="yes",
                        monthly="lastweekday")
        self.assertEquals(rule, MonthlyRecurrenceRule(interval=1,
                                                      monthly="lastweekday"))

    def test_getMonthDay(self):
        view = self.createView()
        self.assertEquals(view.getMonthDay(), "??")
        view.date_widget.value = date(2004, 1, 1)
        self.assertEquals(view.getMonthDay(), "1")
        view.date_widget.value = date(2004, 2, 28)
        self.assertEquals(view.getMonthDay(), "28")

    def test_getWeekDay(self):
        view = self.createView()
        self.assertEquals(view.getWeekDay(), "same weekday")

        def test_date(dt, expected):
            view.date_widget.value = dt
            self.assertEquals(view.getWeekDay(), expected)

        test_date(date(2004, 10, 1), "1st Friday")
        test_date(date(2004, 10, 13), "2nd Wednesday")
        test_date(date(2004, 10, 16), "3rd Saturday")
        test_date(date(2004, 10, 26), "4th Tuesday")
        test_date(date(2004, 10, 28), "4th Thursday")
        test_date(date(2004, 10, 29), "5th Friday")
        test_date(date(2004, 10, 31), "5th Sunday")

    def test_getLastWeekDay(self):
        view = self.createView()
        self.assertEquals(view.getLastWeekDay(), "last weekday")
        view.date_widget.value = date(2004, 10, 24)
        self.assertEquals(view.getLastWeekDay(), None)
        view.date_widget.value = date(2004, 10, 25)
        self.assertEquals(view.getLastWeekDay(), "Last Monday")
        view.date_widget.value = date(2004, 10, 31)
        self.assertEquals(view.getLastWeekDay(), "Last Sunday")


class TestEventAddView(AppSetupMixin, unittest.TestCase):

    def createView(self):
        from schooltool.browser.cal import EventAddView
        view = EventAddView(self.person.calendar)
        view.authorization = lambda x, y: True
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub()
        content = view.render(request)
        self.assert_('Add event' in content)

    def test_render_default_privacy(self):
        self.app.new_event_privacy = 'private'
        view = self.createView()
        request = RequestStub(args={})
        content = view.render(request)

        doc = HTMLDocument(content)
        op = doc.query('//select[@name="privacy"]'
                       '//option[@value="private" and @selected="selected"]')
        assert len(op) == 1, 'private not selected'

    def test_render_args(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'location_other': 'Kitchen',
                                    'duration': '50', 'privacy': 'hidden'})
        content = view.render(request)
        self.assert_('Add event' in content)
        self.assert_('Hacking' in content)
        self.assert_('Kitchen' in content)
        self.assert_('2004-08-13' in content)
        self.assert_('15:30' in content)
        self.assert_('50' in content)

        doc = HTMLDocument(content)
        op = doc.query('//select[@name="privacy"]'
                       '//option[@value="hidden" and @selected="selected"]')
        assert len(op) == 1, 'hidden not selected'

    def test_post(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'location': 'Kitchen',
                                    'duration': '50',
                                    'privacy': 'private',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-13')

        events = list(self.person.calendar)
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0].title, 'Hacking')
        self.assertEquals(events[0].location, 'Kitchen')
        self.assertEquals(events[0].dtstart, datetime(2004, 8, 13, 15, 30))
        self.assertEquals(events[0].duration, timedelta(minutes=50))
        self.assertEquals(events[0].privacy, "private")
        assert events[0].recurrence is None

    def test_post_recurrent(self):
        from schooltool.interfaces import IDailyRecurrenceRule
        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'location': 'Kitchen',
                                    'duration': '50',
                                    'recurrence': 'checked',
                                    'recurrence_shown': 'yes',
                                    'recurrence_type': 'daily',
                                    'interval': '2',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-13')

        events = list(self.person.calendar)
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0].title, 'Hacking')
        self.assertEquals(events[0].location, 'Kitchen')
        self.assertEquals(events[0].dtstart, datetime(2004, 8, 13, 15, 30))
        self.assertEquals(events[0].duration, timedelta(minutes=50))
        assert IDailyRecurrenceRule.providedBy(events[0].recurrence)

    def test_post_errors(self):
        view = self.createView()
        request = RequestStub(args={'title': '',
                                    'start_date': '2004-12-13',
                                    'start_time': '15:30',
                                    'duration': '50',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)
        self.assert_('This field is required' in content)

        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-31-13',
                                    'start_time': '15:30',
                                    'duration': '50'},
                              method='POST')
        content = view.render(request)
        self.assert_('Invalid date' in content)

        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'duration': '100h'},
                              method='POST')
        content = view.render(request)
        self.assert_('Invalid value' in content)

        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'duration': '100',
                                    'recurrence_type' : 'daily',
                                    'recurrence': 'on',
                                    'recurrence_shown': 'yes',
                                    'range': 'count',
                                    'until': '2004-01-01'},
                              method='POST')
        content = view.render(request)
        assert 'This field is required' in content

        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'duration': '100',
                                    'recurrence_type' : 'daily',
                                    'recurrence': 'on',
                                    'recurrence_shown': 'yes',
                                    'range': 'until',
                                    'count': '23'},
                              method='POST')
        content = view.render(request)
        assert 'This field is required' in content


class EventTimetableTestHelpers:

    def createTTCal(self, person, events):
        ttcal = createCalendar()
        person.makeTimetableCalendar = lambda: ttcal
        for event in events:
            ttcal.addEvent(event)
        return ttcal

    def createTimetableEvent(self):
        from schooltool.timetable import TimetableCalendarEvent
        period = "P1"
        tt = TimetableStub()
        act = TimetableActivityStub(tt)
        ev = TimetableCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                    timedelta(hours=1), "Math",
                                    unique_id="uniq",
                                    period_id=period,
                                    activity=act)
        return ev

    def createDummyEvent(self, unique_id):
        from schooltool.timetable import TimetableCalendarEvent
        return TimetableCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                      timedelta(minutes=1), "A",
                                      period_id="foo", activity=object())

    def initTTCalendar(self, obj):
        """Add some dummies and a TT event to an application object's calendar.

        The event is created by calling self.createTimetableEvent().

        Adds events to the object's calendar and to its timetable.
        Returns the timetable calendar of the object.
        """
        obj.addEvent(self.createDummyEvent("a"))
        obj.addEvent(self.createDummyEvent("b"))
        ttcal = self.createTTCal(obj.__parent__,
                                 [self.createDummyEvent('c'),
                                  self.createTimetableEvent(),
                                  self.createDummyEvent('d')])
        return ttcal


def assertField(doc, name, value, more=""):
    """Assert that a field has a value.

    Raises an error unless the document contains an input element with
    a given name and value.

    An additional xpath attribute query can be passed as optional arg.
    """
    r = doc.query('//form//input[@name="%s" and @value="%s" %s]' %
                  (name, value, more))
    assert len(r) == 1, "%s != %s" % (name, value)


def assertNoField(doc, name, value, more=""):
    """Assert that there is no field with a given name and value.

    Raises an error if the document contains an input element with
    a given name and value.

    An additional xpath attribute query can be passed as optional arg.
    """
    r = doc.query('//form//input[@name="%s" and @value="%s" %s]' %
                  (name, value, more))
    assert len(r) == 0, "%s == %s" % (name, value)


class TestEventEditView(AppSetupMixin, EventTimetableTestHelpers,
                        unittest.TestCase):

    def setUp(self):
        from schooltool.cal import DailyRecurrenceRule
        self.setUpSampleApp()
        self.ev1 = createEvent('2004-08-15 12:00', '1h', "ev1",
                               location="Hell", unique_id="other")
        self.ev2 = createEvent('2004-08-12 13:00', '2h', "ev2",
                               unique_id="pick me", location="Heaven",
                               recurrence=DailyRecurrenceRule(interval=2))
        self.person.calendar.addEvent(self.ev1)
        self.person.calendar.addEvent(self.ev2)

    def createView(self):
        from schooltool.browser.cal import EventEditView
        view = EventEditView(self.person.calendar)
        view.authorization = lambda x, y: True
        view.isManager = lambda: True
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "pick me"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertNoField(doc, 'start_date', '2004-08-15')
        assertNoField(doc, 'title', 'ev1')

        assertField(doc, 'title', 'ev2')
        assertField(doc, 'start_date', '2004-08-12')
        assertField(doc, 'start_time', '13:00')
        assertField(doc, 'location_other', 'Heaven')
        assertField(doc, 'duration', '120')

        ch = doc.query('//input[@name="recurrence" and @checked="checked"]')
        assert len(ch) == 1, 'recurrence not checked'
        op = doc.query('//select[@name="recurrence_type"]'
                       '//option[@value="daily" and @selected="selected"]')
        assert len(op) == 1, 'daily not selected'

        assertField(doc, 'interval', '2')

        op = doc.query('//select[@name="privacy"]'
                       '//option[@value="public" and @selected="selected"]')
        assert len(op) == 1, 'public not selected'

    def test_render_range_forever(self):
        from schooltool.cal import DailyRecurrenceRule
        event = createEvent('2004-10-21 21:00', '2h', "ev3",
                            unique_id="123",
                            recurrence=DailyRecurrenceRule())
        self.person.calendar.addEvent(event)

        view = self.createView()
        request = RequestStub(args={'event_id': "123"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertField(doc, 'range', 'forever', 'and @checked="checked"')

    def test_render_range_count(self):
        from schooltool.cal import DailyRecurrenceRule
        event = createEvent('2004-10-21 21:00', '2h', "ev3",
                            unique_id="123",
                            recurrence=DailyRecurrenceRule(count=3))
        self.person.calendar.addEvent(event)

        view = self.createView()
        request = RequestStub(args={'event_id': "123"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertField(doc, 'range', 'count', 'and @checked="checked"')
        assertField(doc, 'count', '3')


    def test_render_range_until(self):
        from schooltool.cal import DailyRecurrenceRule
        event = createEvent(
            '2004-10-21 21:00', '2h', "ev3", unique_id="123",
            recurrence=DailyRecurrenceRule(until=date(2004, 10, 22)))
        self.person.calendar.addEvent(event)

        view = self.createView()
        request = RequestStub(args={'event_id': "123"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertField(doc, 'range', 'until', 'and @checked="checked"')
        assertField(doc, 'until', '2004-10-22')

    def test_render_weekly(self):
        from schooltool.cal import WeeklyRecurrenceRule
        event = createEvent(
            '2004-10-21 21:00', '2h', "ev3", unique_id="123",
            recurrence=WeeklyRecurrenceRule(weekdays=(1, 2)))
        self.person.calendar.addEvent(event)

        view = self.createView()
        request = RequestStub(args={'event_id': "123"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertField(doc, 'weekdays', '3', 'and @checked="checked"')
        assertField(doc, 'weekdays', '1', 'and @checked="checked"')
        assertField(doc, 'weekdays', '2', 'and @checked="checked"')

    def test_render_monthly(self):
        from schooltool.cal import MonthlyRecurrenceRule
        event = createEvent(
            '2004-10-28 21:00', '2h', "ev3", unique_id="123",
            recurrence=MonthlyRecurrenceRule(monthly="lastweekday"))
        self.person.calendar.addEvent(event)

        view = self.createView()
        request = RequestStub(args={'event_id': "123"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertField(doc, 'monthly', 'lastweekday', 'and @checked="checked"')

    def test_render_norecur(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "other"})
        content = view.render(request)

        doc = HTMLDocument(content)

        assertField(doc, 'start_date', '2004-08-15')
        assertField(doc, 'title', 'ev1')

        assertNoField(doc, 'title', 'ev2')
        assertNoField(doc, 'start_date', '2004-08-12')
        assertNoField(doc, 'start_time', '13:00')
        assertNoField(doc, 'location_other', 'Heaven')
        assertNoField(doc, 'duration', '120')

        ch = doc.query('//input[@name="recurrence" and @checked="checked"]')
        assert len(ch) == 0, 'recurrence checked'

    def test_render_exceptions(self):
        from schooltool.cal import DailyRecurrenceRule
        event = createEvent(
            '2004-10-21 21:00', '2h', "ev3", unique_id="123",
            recurrence=DailyRecurrenceRule(exceptions=(date(2004, 10, 22),
                                                       date(2004, 12, 12))))
        self.person.calendar.addEvent(event)

        view = self.createView()
        request = RequestStub(args={'event_id': "123"})
        content = view.render(request)

        assert '2004-10-22\n2004-12-12</textarea' in content

    def test_render_nonexistent(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "nonexistent"})
        content = view.render(request)

        self.assert_("This event does not exist." in content)

    def test(self):
        from schooltool.cal import WeeklyRecurrenceRule
        view = self.createView()
        request = RequestStub(args={'event_id': "pick me",
                                    'title': 'Changed',
                                    'location': 'Inbetween',
                                    'start_date': '2004-08-16',
                                    'start_time': '13:30',
                                    'duration': '70',
                                    'recurrence': 'on',
                                    'recurrence_type': 'weekly',
                                    'interval':'2',
                                    'exceptions': '2004-01-01\n2004-02-02',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)

        events = list(self.person.calendar)
        self.assertEquals(len(events), 2)
        self.assert_(self.ev1 in events)
        self.assert_(self.ev2 not in events)

        self.person.calendar.removeEvent(self.ev1)
        new_ev = list(self.person.calendar)[0]
        self.assertEquals(new_ev.title, 'Changed')
        self.assertEquals(new_ev.location, 'Inbetween')
        self.assertEquals(new_ev.dtstart, datetime(2004, 8, 16, 13, 30))
        self.assertEquals(new_ev.duration, timedelta(minutes=70))
        self.assertEquals(new_ev.unique_id, "pick me")
        self.assertEquals(
            new_ev.recurrence,
            WeeklyRecurrenceRule(interval=2,
                                 exceptions=((date(2004, 1, 1),
                                              date(2004, 2, 2)))))

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-16')

    def test_nosubmit(self):
        from schooltool.cal import WeeklyRecurrenceRule
        view = self.createView()
        request = RequestStub(args={'event_id': "pick me",
                                    'title': 'Changed',
                                    'location': 'Inbetween',
                                    'start_date': '2004-08-16',
                                    'start_time': '13:30',
                                    'duration': '70',
                                    'recurrence': 'on',
                                    'recurrence_type': 'weekly',
                                    'interval':'2',
                                    'exceptions': '2004-01-01\n2004-02-02'},
                              method='POST')
        content = view.render(request)

        events = list(self.person.calendar)
        self.assertEquals(len(events), 2)
        self.assert_(self.ev1 in events)
        self.assert_(self.ev2 in events)

    def test_norecur(self):
        from schooltool.cal import WeeklyRecurrenceRule
        view = self.createView()
        request = RequestStub(args={'event_id': "pick me",
                                    'title': 'Changed',
                                    'location': 'Inbetween',
                                    'start_date': '2004-08-16',
                                    'start_time': '13:30',
                                    'duration': '70',
                                    'recurrence_shown': 'yes',
                                    'recurrence_type': 'weekly',
                                    'interval':'2',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)

        events = list(self.person.calendar)
        self.assertEquals(len(events), 2)
        self.assert_(self.ev1 in events)
        self.assert_(self.ev2 not in events)

        self.person.calendar.removeEvent(self.ev1)
        new_ev = iter(self.person.calendar).next()
        self.assertEquals(new_ev.recurrence, None)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-16')

    def test_render_tt_event(self):
        view = self.createView()
        ttcal = self.initTTCalendar(view.context)

        request = RequestStub(args={'event_id': "uniq"})
        content = view.render(request)

        self.assert_('timetable event' in content)
        self.assert_('2004-08-12' in content)
        self.assert_('12:00' in content)
        self.assert_('Math' in content)

    def test_tt_getRecurrenceRule(self):

        view = self.createView()
        ttcal = self.initTTCalendar(view.context)

        request = RequestStub(args={'event_id': "uniq",
                                    'recurrence': 'on',
                                    'recurrence_shown': 'yes',
                                    'recurrence_type': 'daily'})
        view.request = request
        view.update()
        self.assertEqual(view.getRecurrenceRule(), None)

    def test_change_tt_event(self):
        view = self.createView()
        ttcal = self.initTTCalendar(view.context)

        request = RequestStub(args={'event_id': "uniq",
                                    'title': 'Changed',
                                    'location': 'Inbetween',
                                    'start_date': '2004-08-16',
                                    'start_time': '13:30',
                                    'duration': '70',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-16')

        event = ttcal.find('uniq')
        exceptions = event.activity.timetable.exceptions
        self.assertEquals(len(exceptions), 1)

        exc = exceptions[0]
        self.assertEquals(exc.date, date(2004, 8, 12))
        self.assertEquals(exc.period_id, "P1")
        self.assert_(exc.activity is event.activity)

        self.assertEquals(exc.replacement.title, 'Changed')
        self.assertEquals(exc.replacement.location, 'Inbetween')
        self.assertEquals(exc.replacement.dtstart,
                          datetime(2004, 8, 16, 13, 30))
        self.assertEquals(exc.replacement.duration, timedelta(minutes=70))
        self.assertEquals(exc.replacement.unique_id, event.unique_id)

    def test_edit_exceptional_event(self):
        from schooltool.timetable import TimetableException
        from schooltool.timetable import ExceptionalTTCalendarEvent
        view = self.createView()
        ttcal = self.initTTCalendar(view.context)
        event = ttcal.find('uniq')
        calendar = view.context.__parent__.makeTimetableCalendar()

        exc = TimetableException(date=event.dtstart,
                                 period_id=event.period_id,
                                 activity=event.activity)
        exc_ev = ExceptionalTTCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                            timedelta(minutes=1), "A",
                                            unique_id="uniq",
                                            exception=exc)
        exc.replacement = exc_ev
        calendar.removeEvent(event)
        calendar.addEvent(exc_ev)

        request = RequestStub(args={'event_id': "uniq",
                                    'title': 'Changed',
                                    'location': 'Inbetween',
                                    'start_date': '2004-08-16',
                                    'start_time': '13:30',
                                    'duration': '70',
                                    'SUBMIT': 'Save'},
                              method='POST')
        content = view.render(request)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-16')

        self.assert_(exc.replacement is not exc_ev)
        self.assert_(exc.replacement.exception is exc)
        self.assertEquals(exc.replacement.title, 'Changed')
        self.assertEquals(exc.replacement.location, 'Inbetween')
        self.assertEquals(exc.replacement.dtstart,
                          datetime(2004, 8, 16, 13, 30))
        self.assertEquals(exc.replacement.duration, timedelta(minutes=70))
        self.assertEquals(exc.replacement.unique_id, event.unique_id)

    def test_update_timetable_event_permission_checking(self):
        from schooltool.browser import Unauthorized
        view = self.createView()
        view.request = RequestStub(args={'event_id': '123'})
        event = createEvent('2004-08-16 13:45', '5 min', 'Anything',
                            unique_id='123')
        view._findOrdinaryEvent = lambda uid: None
        view._findTimetableEvent = lambda uid: event

        # Manager
        view.isManager = lambda: True
        view.update()
        assert view.event is event
        assert view.tt_event

        # Not manager
        view.isManager = lambda: False
        self.assertRaises(Unauthorized, view.update)

    def test_process_timetable_event_permission_checking(self):
        from schooltool.browser import Unauthorized
        view = self.createView()
        view.event = createEvent('2004-08-16 13:45', '5 min', 'Anything')
        view.tt_event = True

        args = (datetime(2004, 8, 16, 13, 55), timedelta(minutes=5),
                'Anything *', None, "public")

        # Not a manager -- should redirect to unauthorized
        view.isManager = lambda: False
        def addTimetableExceptionStub(*args, **kw):
            self.fail("view.isManager returns False so"
                      " _addTimetableException should not get called")
        view._addTimetableException = addTimetableExceptionStub
        self.assertRaises(Unauthorized, view.process, *args)

        # Manager -- should call _addTimetableException
        view.isManager = lambda: True
        called = []
        def addTimetableExceptionStub(*args, **kw):
            called.append((args, kw))
        view._addTimetableException = addTimetableExceptionStub
        view.process(*args)
        if not called:
            self.fail("view.isManager returns True so"
                      " _addTimetableException should get called")


class TestEventDeleteView(unittest.TestCase, EventTimetableTestHelpers):

    assertHasHiddenField = assertHasHiddenField
    assertHasSubmitButton = assertHasSubmitButton

    def createView(self):
        from schooltool.model import Person
        from schooltool.browser.cal import EventDeleteView

        person = Person(title="Somebody")
        setPath(person, '/persons/somebody')
        cal = createCalendar()
        cal.__name__ = 'calendar'
        cal.__parent__ = person
        view = EventDeleteView(cal)
        view.authorization = lambda x, y: True
        view.isManager = lambda: True
        return view

    def test(self):
        from schooltool.cal import CalendarEvent
        ev1 = CalendarEvent(datetime(2004, 8, 12, 12, 0),
                            timedelta(hours=1), "ev1")
        ev2 = CalendarEvent(datetime(2004, 8, 12, 13, 0),
                            timedelta(hours=1), "ev2",
                            unique_id="pick me")
        view = self.createView()
        cal = view.context
        cal.addEvent(ev1)
        cal.addEvent(ev2)

        request = RequestStub(args={'event_id': "pick me",
                                    'date': "2004-08-14"})
        content = view.render(request)

        self.assertEquals(list(cal), [ev1])

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-14')

    def test_no_such_event(self):
        view = self.createView()
        ttcal = self.createTTCal(view.context.__parent__, [])
        request = RequestStub(args={'event_id': "nosuchid",
                                    'date': "2004-08-14"})
        content = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-14')

    def test_tt_event(self):
        view = self.createView()
        ttcal = self.initTTCalendar(view.context)

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-14"})
        content = view.render(request)

        self.assertEquals(len(list(ttcal)), 3)
        self.assertNotEquals(request.code, 302)
        self.assert_("add an exception" in content)

        doc = HTMLDocument(content)
        self.assertHasHiddenField(doc, 'event_id', 'uniq')
        self.assertHasHiddenField(doc, 'date', '2004-08-14')
        self.assertHasSubmitButton(doc, 'CONFIRM')
        self.assertHasSubmitButton(doc, 'CANCEL')

    def test_tt_event_confirm(self):
        view = self.createView()
        ttcal = self.initTTCalendar(view.context)
        event = ttcal.find('uniq')
        tt = event.activity.timetable

        request = RequestStub(args={'event_id': "uniq", 'CONFIRM': 'Confirm',
                                    'date': "2004-08-14"})
        content = view.render(request)

        self.assertEquals(len(list(ttcal)), 3)
        self.assertEquals(len(tt.exceptions), 1)

        exc = tt.exceptions[0]
        self.assertEquals(exc.date, date(2004, 8, 12))
        self.assertEquals(exc.period_id, "P1")
        self.assert_(exc.activity is event.activity)
        self.assert_(exc.replacement is None)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-14')

    def test_tt_event_cancel(self):
        view = self.createView()
        ev = self.createTimetableEvent()
        ttcal = self.createTTCal(view.context.__parent__, [ev])
        request = RequestStub(args={'event_id': "uniq", 'CANCEL': 'Cancel',
                                    'date': "2004-08-14"})
        content = view.render(request)
        self.assertEquals(ev.activity.timetable.exceptions, [])
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-14')

    def test_delete_exceptional_event(self):
        from schooltool.timetable import TimetableException
        from schooltool.timetable import ExceptionalTTCalendarEvent
        view = self.createView()
        ttcal = self.initTTCalendar(view.context)
        event = ttcal.find('uniq')

        calendar = view.context.__parent__.makeTimetableCalendar()

        exc = TimetableException(date=event.dtstart,
                                 period_id=event.period_id,
                                 activity=event.activity)
        exc_ev = ExceptionalTTCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                            timedelta(minutes=1), "A",
                                            unique_id="uniq",
                                            exception=exc)
        exc.replacement = exc_ev
        calendar.removeEvent(event)
        calendar.addEvent(exc_ev)

        request = RequestStub(args={'event_id': "uniq", 'CONFIRM': 'Confirm',
                                    'date': "2004-08-14"})
        content = view.render(request)

        self.assertEquals(len(list(ttcal)), 3)

        self.assertEquals(exc.date, datetime(2004, 8, 12, 12, 0))
        self.assertEquals(exc.period_id, "P1")
        self.assert_(exc.activity is event.activity)
        self.assert_(exc.replacement is None)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-14')


class TestEventDeleteViewWithRepeatingEvents(unittest.TestCase):

    assertRedirectedTo = assertRedirectedTo
    assertHasHiddenField = assertHasHiddenField
    assertHasSubmitButton = assertHasSubmitButton

    def createView(self, events=()):
        from schooltool.model import Person
        from schooltool.browser.cal import EventDeleteView

        person = Person(title="Somebody")
        setPath(person, '/persons/somebody')
        cal = createCalendar(events)
        cal.__name__ = 'calendar'
        cal.__parent__ = person
        view = EventDeleteView(cal)
        view.authorization = lambda x, y: True
        return view

    def test_repeating_event(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(count=5))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-14"})
        content = view.render(request)

        # Nothing is deleted, and we aren't redirected anywhere
        self.assertEquals(list(view.context), [ev1])
        self.assertNotEquals(request.code, 302)

        doc = HTMLDocument(content)
        self.assertHasHiddenField(doc, 'event_id', 'uniq')
        self.assertHasHiddenField(doc, 'date', '2004-08-14')
        self.assertHasSubmitButton(doc, 'CURRENT')
        self.assertHasSubmitButton(doc, 'FUTURE')
        self.assertHasSubmitButton(doc, 'ALL')
        self.assertHasSubmitButton(doc, 'CANCEL')

    def test_repeating_event_cancel(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(count=5))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-14",
                                    'CANCEL': 'cancel'})
        content = view.render(request)

        # Nothing is deleted, we are redirected to calendar for 2004-08-14
        self.assertEquals(list(view.context), [ev1])
        self.assertRedirectedTo(request,
                                'http://localhost:7001/persons/somebody/'
                                'calendar/daily.html?date=2004-08-14')

    def test_repeating_event_all(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(count=5))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-14",
                                    'ALL': 'all'})
        content = view.render(request)

        # The event is deleted, we are redirected to calendar for 2004-08-14
        self.assertEquals(list(view.context), [])
        self.assertRedirectedTo(request,
                                'http://localhost:7001/persons/somebody/'
                                'calendar/daily.html?date=2004-08-14')

    def test_repeating_event_future(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(count=5))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-14",
                                    'FUTURE': 'future'})
        content = view.render(request)

        ev1prime = ev1.replace(recurrence=DailyRecurrenceRule(
                                    until=date(2004, 8, 13)))

        # The event is modified, we are redirected to calendar for 2004-08-14
        self.assertEquals(list(view.context), [ev1prime])
        self.assertRedirectedTo(request,
                                'http://localhost:7001/persons/somebody/'
                                'calendar/daily.html?date=2004-08-14')

    def test_repeating_event_future_last_occurrence(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(count=5))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-12",
                                    'FUTURE': 'future'})
        content = view.render(request)

        # The event is modified, we are redirected to calendar for 2004-08-12
        self.assertEquals(list(view.context), [])
        self.assertRedirectedTo(request,
                                'http://localhost:7001/persons/somebody/'
                                'calendar/daily.html?date=2004-08-12')

    def test_repeating_event_current(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(
                                count=5, exceptions=[date(2004, 8, 13)]))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-14",
                                    'CURRENT': 'current'})
        content = view.render(request)

        new_recurrence = ev1.recurrence.replace(exceptions=[date(2004, 8, 13),
                                                            date(2004, 8, 14)])
        ev1prime = ev1.replace(recurrence=new_recurrence)

        # The event is modified, we are redirected to calendar for 2004-08-14
        self.assertEquals(list(view.context), [ev1prime])
        self.assertRedirectedTo(request,
                                'http://localhost:7001/persons/somebody/'
                                'calendar/daily.html?date=2004-08-14')

    def test_repeating_event_current_last_occurrence(self):
        from schooltool.cal import DailyRecurrenceRule
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(
                                count=2, exceptions=[date(2004, 8, 13)]))
        view = self.createView([ev1])

        request = RequestStub(args={'event_id': "uniq",
                                    'date': "2004-08-12",
                                    'CURRENT': 'current'})
        content = view.render(request)

        # The event is modified, we are redirected to calendar for 2004-08-12
        self.assertEquals(list(view.context), [])
        self.assertRedirectedTo(request,
                                'http://localhost:7001/persons/somebody/'
                                'calendar/daily.html?date=2004-08-12')

    def test_deleteOneOccurrence(self):
        from schooltool.cal import DailyRecurrenceRule
        view = self.createView()
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(
                                count=5, exceptions=[date(2004, 8, 13)]))

        self.assertEquals(view._deleteOneOccurrence(ev1, date(2004, 8, 13)),
                          ev1)

        self.assertEquals(view._deleteOneOccurrence(ev1, date(2004, 8, 14)),
                          ev1.replace(recurrence=DailyRecurrenceRule(
                                count=5, exceptions=[date(2004, 8, 13),
                                                     date(2004, 8, 14)])))

    def test_deleteFutureOccurrences(self):
        from schooltool.cal import DailyRecurrenceRule
        view = self.createView()
        ev1 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(
                                count=5, exceptions=[date(2004, 8, 13)]))

        self.assertEquals(view._deleteFutureOccurrences(ev1,
                                                        date(2004, 8, 14)),
                          ev1.replace(recurrence=DailyRecurrenceRule(
                                until=date(2004, 8, 13),
                                exceptions=[date(2004, 8, 13)])))

        ev2 = createEvent('2004-08-12 14:35', '5 min', 'Repeating',
                          unique_id='uniq',
                          recurrence=DailyRecurrenceRule(
                                until=date(2004, 8, 16),
                                exceptions=[date(2004, 8, 13)]))

        self.assertEquals(view._deleteFutureOccurrences(ev2,
                                                        date(2004, 8, 14)),
                          ev2.replace(recurrence=DailyRecurrenceRule(
                                until=date(2004, 8, 13),
                                exceptions=[date(2004, 8, 13)])))

        self.assertEquals(view._deleteFutureOccurrences(ev2,
                                                        date(2004, 8, 17)),
                          ev2)

        self.assertEquals(view._deleteFutureOccurrences(ev2,
                                                        date(2004, 8, 20)),
                          ev2)


class TestEventDeleteViewPermissionChecking(AppSetupMixin, unittest.TestCase):

    assertRedirectedTo = assertRedirectedTo

    def test_ordinary_events(self):
        self.setUpCalendar(person_to_add_to_acl=self.person)
        # Only persons who have access to the calendar may remove ordinary
        # calendar events.  Managers always have access to calendars.
        self.assertCanDelete(self.person, self.createOrdinaryEvent())
        self.assertCanDelete(self.manager, self.createOrdinaryEvent())
        self.assertCannotDelete(self.person2, self.createOrdinaryEvent())

    def test_timetable_events(self):
        self.setUpCalendar(person_to_add_to_acl=self.person)
        # Only managers may remove timetable events.
        self.assertCannotDelete(self.person, self.createTimetableEvent())
        self.assertCanDelete(self.manager, self.createTimetableEvent())
        self.assertCannotDelete(self.person2, self.createTimetableEvent())

    def setUpCalendar(self, person_to_add_to_acl):
        from schooltool.interfaces import ModifyPermission
        self.calendar = self.person.calendar
        self.calendar.acl.add((person_to_add_to_acl, ModifyPermission))

    def createOrdinaryEvent(self):
        event = createEvent('2004-08-12 14:35', '5 min', 'Ordinary')
        self.calendar.addEvent(event)
        return event.unique_id

    def createTimetableEvent(self):
        from schooltool.timetable import TimetableCalendarEvent
        self.timetable = TimetableStub()
        act = TimetableActivityStub(self.timetable)
        self.ttevent = TimetableCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                              timedelta(hours=1), "Math",
                                              period_id="P1", activity=act)
        self.person.makeTimetableCalendar = self.makeTimetableCalendarStub
        return self.ttevent.unique_id

    def makeTimetableCalendarStub(self):
        ttevent = self.ttevent
        id_tup = (ttevent.dtstart.date(), ttevent.period_id, ttevent.activity)
        for exc in self.timetable.exceptions:
            if (exc.date, exc.period_id, exc.activity) == id_tup:
                if exc.replacement is None:
                    return createCalendar()
                else:
                    return createCalendar([exc.replacement])
        return createCalendar([self.ttevent])

    def combinedCalendar(self):
        """Combine the ordinary and timetable calendars."""
        calendar = self.person.makeTimetableCalendar()
        calendar.update(self.calendar)
        return calendar

    def assertCanDelete(self, user, event_id):
        from schooltool.browser import absoluteURL
        result, request = self.tryToDelete(user, event_id)
        url = absoluteURL(request, self.calendar, 'daily.html?date=2004-08-14')
        self.assertRedirectedTo(request, url)
        # If the event was deleted, calendar.find will raise KeyError
        calendar = self.combinedCalendar()
        self.assertRaises(KeyError, calendar.find, event_id)

    def assertCannotDelete(self, user, event_id):
        from schooltool.browser import absoluteURL
        result, request = self.tryToDelete(user, event_id)
        delete_url = absoluteURL(request, self.calendar,
                                 'delete_event.html?date=%s&event_id=%s'
                                 % ('2004-08-14', event_id))
        quoted_url = urllib.quote(delete_url)
        url = 'http://localhost:7001/?forbidden=1&url=%s' % quoted_url
        self.assertRedirectedTo(request, url)
        # If the event was not deleted, calendar.find will not raise KeyError
        self.assert_(self.combinedCalendar().find(event_id))

    def tryToDelete(self, user, event_id):
        from schooltool.browser.cal import EventDeleteView
        from schooltool.browser import absoluteURL
        view = EventDeleteView(self.calendar)
        url = absoluteURL(RequestStub(), self.calendar,
                          'delete_event.html?date=2004-08-14&event_id=%s'
                          % event_id)
        request = RequestStub(url, authenticated_user=user,
                              args={'event_id': str(event_id),
                                    'date': "2004-08-14",
                                    'CONFIRM': 'Yes'})
        result = view.render(request)
        return result, request


class TestCalendarEventView(TraversalTestMixin, XMLCompareMixin,
                            unittest.TestCase):

    def createView(self, ev=None):
        from schooltool.cal import ACLCalendar
        from schooltool.browser.cal import CalendarEventView
        if ev is None:
            ev = self.createOrdinaryEvent()
        view = CalendarEventView(ev, ACLCalendar())
        return view

    def createOrdinaryEvent(self):
        ev = createEvent('2004-12-01 12:01', '1h', 'Main event',
                         unique_id="id!")
        return ev

    def createTimetableEvent(self):
        from schooltool.timetable import TimetableCalendarEvent
        tt_ev = TimetableCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                       timedelta(minutes=1), "A",
                                       period_id="foo", activity=object())
        return tt_ev

    def createTimetableExceptionEvent(self):
        from schooltool.timetable import TimetableException
        from schooltool.timetable import ExceptionalTTCalendarEvent
        exc = TimetableException(date=date(2003, 11, 26), period_id='Green',
                                 activity=object())
        exc_ev = ExceptionalTTCalendarEvent(datetime(2004, 8, 12, 12, 0),
                                            timedelta(minutes=1), "A",
                                            exception=exc)
        return exc_ev

    def createInheritedEvent(self):
        from schooltool.cal import InheritedCalendarEvent
        return InheritedCalendarEvent(self.createOrdinaryEvent())

    # canEdit is tested in TestCalendarEventPermissionChecking

    def test_cssClass(self):
        def class_of(event):
            return self.createView(event).cssClass()
        self.assertEquals(class_of(self.createOrdinaryEvent()), 'event')
        self.assertEquals(class_of(self.createTimetableEvent()), 'tt_event')
        self.assertEquals(class_of(self.createTimetableExceptionEvent()),
                          'exc_event')
        self.assertEquals(class_of(self.createInheritedEvent()), 'comp_event')

    def test_duration(self):
        view = self.createView()
        self.assertEquals(view.duration(), '12:01&ndash;13:01')

        ev = createEvent('2004-12-01 12:01', '1d', 'Long event')
        view = self.createView(ev)
        self.assertEquals(view.duration(),
                          '2004-12-01 12:01&ndash;2004-12-02 12:01')

    def test_full(self):
        view = self.createView()
        request = RequestStub()
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <h3>
                Main event
              </h3>
              12:01--13:01
            </div>
            """)

        view.canEdit = lambda: True
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <div class="dellink">
                <a href="delete_event.html?date=2004-12-02&amp;event_id=id%21">
                  [delete]
                </a>
                <div>
                  Public
                </div>
              </div>
              <h3>
                <a href="edit_event.html?date=2004-12-02&amp;event_id=id%21">
                  Main event
                </a>
              </h3>
              12:01--13:01
            </div>
            """)

        ev = createEvent('2004-12-01 12:01', '1h', 'Main event',
                         unique_id="id", location="Office")
        view = self.createView(ev)
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <h3>
                Main event
              </h3>
              12:01--13:01
              (Office)
            </div>
            """)

        ev = createEvent('2004-12-01 12:01', '1h', 'Main event',
                         unique_id="id", location="Office",
                         privacy="private")
        view = self.createView(ev)
        view.canView = lambda: False
        content = view.full(request, date(2004, 12, 2))
        self.assertEqualsXML(content.replace('&ndash;', '--'), """
            <div class="calevent">
              <h3>
                Busy
              </h3>
              12:01--13:01
            </div>
            """)

    def test_short(self):
        request = RequestStub()
        view = self.createView()
        view.canView = lambda: True
        self.assertEquals(view.short(request),
                          'Main event (12:01&ndash;13:01)')

        ev = createEvent('2004-12-01 12:01', '1d', 'Long event')
        view = self.createView(ev)
        view.canView = lambda: True
        self.assertEquals(view.short(request),
                          'Long event (Dec&nbsp;01&ndash;Dec&nbsp;02)')

        view = self.createView()
        view.canView = lambda: False
        self.assertEquals(view.short(request),
                          'Busy (12:01&ndash;13:01)')


    def test_editLink_and_deleteLink(self):
        ev = createEvent('2004-12-01 12:01', '1h', 'Repeating event',
                         unique_id="s@me=id")
        view = self.createView(ev)
        view.date = date(2004, 12, 2)
        params = 'date=2004-12-02&event_id=s%40me%3Did'
        self.assertEquals(view.deleteLink(), 'delete_event.html?' + params)
        self.assertEquals(view.editLink(), 'edit_event.html?' + params)


class TestCalendarEventPermissionChecking(AppSetupMixin, unittest.TestCase):

    def test_canEdit(self):
        from schooltool.interfaces import ModifyPermission
        from schooltool.browser.cal import CalendarEventView
        ev = createEvent('2004-11-03 14:32', '1h', 'Nothing of importance')
        cal = self.person.calendar
        cal.addEvent(ev)
        cal.acl.add((self.person, ModifyPermission))
        view = CalendarEventView(ev, cal)

        anonymous = None
        def canEdit(user):
            view.request = RequestStub(authenticated_user=user)
            return view.canEdit()

        assert not canEdit(anonymous)
        assert canEdit(self.person)
        assert not canEdit(self.person2)
        assert canEdit(self.manager)

    def test_canView(self):
        from schooltool.interfaces import ViewPermission
        from schooltool.browser.cal import CalendarEventView
        ev = createEvent('2004-11-03 14:32', '1h', 'Nothing of importance',
                         privacy="private")
        self.person.calendar.addEvent(ev)
        self.person.calendar.acl.add((self.person, ViewPermission))
        self.person.calendar.acl.add((self.person2, ViewPermission))
        view = CalendarEventView(ev, self.person.calendar)

        anonymous = None
        def canView(user):
            view.request = RequestStub(authenticated_user=user)
            return view.canView()

        assert not canView(anonymous)
        assert canView(self.person)
        assert not canView(self.person2)
        assert canView(self.manager)

        view.context = view.context.replace(privacy="public")

        assert canView(anonymous)
        assert canView(self.person)
        assert canView(self.person2)
        assert canView(self.manager)

    def test_isHidden(self):
        from schooltool.interfaces import ViewPermission
        from schooltool.browser.cal import CalendarEventView
        ev = createEvent('2004-11-03 14:32', '1h', 'Nothing of importance',
                         privacy="hidden")
        self.person.calendar.addEvent(ev)
        self.person.calendar.acl.add((self.person, ViewPermission))
        self.person.calendar.acl.add((self.person2, ViewPermission))
        view = CalendarEventView(ev, self.person.calendar)

        anonymous = None
        def isHidden(user):
            view.request = RequestStub(authenticated_user=user)
            return view.isHidden()

        assert isHidden(anonymous)
        assert not isHidden(self.person)
        assert isHidden(self.person2)
        assert not isHidden(self.manager)

        view.context = view.context.replace(privacy="public")

        assert not isHidden(anonymous)
        assert not isHidden(self.person)
        assert not isHidden(self.person2)
        assert not isHidden(self.manager)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingView))
    suite.addTest(unittest.makeSuite(TestCalendarDay))
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(unittest.makeSuite(TestWeeklyCalendarView))
    suite.addTest(unittest.makeSuite(TestDailyCalendarView))
    suite.addTest(unittest.makeSuite(TestMonthlyCalendarView))
    suite.addTest(unittest.makeSuite(TestYearlyCalendarView))
    suite.addTest(unittest.makeSuite(TestCalendarView))
    suite.addTest(unittest.makeSuite(TestEventViewBase))
    suite.addTest(unittest.makeSuite(TestEventAddView))
    suite.addTest(unittest.makeSuite(TestEventEditView))
    suite.addTest(unittest.makeSuite(TestEventDeleteView))
    suite.addTest(unittest.makeSuite(TestEventDeleteViewWithRepeatingEvents))
    suite.addTest(unittest.makeSuite(TestEventDeleteViewPermissionChecking))
    suite.addTest(unittest.makeSuite(TestCalendarEventView))
    suite.addTest(unittest.makeSuite(TestCalendarEventPermissionChecking))
    suite.addTest(DocTestSuite('schooltool.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main()
