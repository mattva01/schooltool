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

import re
import unittest
from logging import INFO
from datetime import datetime, date, timedelta

from zope.testing.doctestunit import DocTestSuite
from schooltool.browser.tests import RequestStub, setPath
from schooltool.browser.tests import TraversalTestMixin
from schooltool.tests.utils import AppSetupMixin, NiceDiffsMixin
from schooltool.tests.helpers import diff
from schooltool.common import dedent

__metaclass__ = type


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
        e1 = createEvent('2004-08-11 12:00', '1h', "e1")
        e2 = createEvent('2004-08-11 11:00', '1h', "e2")
        e3 = createEvent('2004-08-12 23:00', '4h', "e3")
        e4 = createEvent('2004-08-15 11:00', '1h', "e4")
        e5 = createEvent('2004-08-10 09:00', '3d', "e5")
        e6 = createEvent('2004-08-13 00:00', '1d', "e6")
        e7 = createEvent('2004-08-12 00:00', '1d+1sec', "e7")
        e8 = createEvent('2004-08-15 00:00', '0sec', "e8")

        cal = createCalendar([e0, e1, e2, e3, e4, e5, e6, e7, e8])
        view = CalendarViewBase(cal)

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
        from schooltool.browser.cal import CalendarViewBase
        cal = createCalendar()
        view = CalendarViewBase(cal)
        view.request = RequestStub()
        e = createEvent('2004-01-02 14:30', '30min', u'\u263B')
        result = view.renderEvent(e)
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
        cal = createCalendar([ev1, ev2, ev3, ev4])
        view = DailyCalendarView(cal)
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

    def test_getHours(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.model import Person

        cal = createCalendar()
        cal.__parent__ = Person(title="Da Boss")
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
                           {'time': '14:00', 'cols': (ev3,'')},
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
                           {'time': '14:00', 'cols': ('', ev3,'')},
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

        cal = createCalendar([createEvent('2004-08-11 12:00', '1h',
                                          "Stuff happens")])
        person = self.app['persons'].new('boss', title="Da Boss")
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        view = MonthlyCalendarView(cal)
        view.authorization = lambda x, y: True
        request = RequestStub(args={'date': '2004-08-12'})
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

    def test_render_args(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'location_other': 'Kitchen',
                                    'duration': '50'})
        content = view.render(request)
        self.assert_('Add event' in content)
        self.assert_('Hacking' in content)
        self.assert_('Kitchen' in content)
        self.assert_('2004-08-13' in content)
        self.assert_('15:30' in content)
        self.assert_('50' in content)

    def test_post(self):
        view = self.createView()
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'location': 'Kitchen',
                                    'duration': '50'},
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

    def test_post_errors(self):
        view = self.createView()
        request = RequestStub(args={'title': '',
                                    'start_date': '2004-12-13',
                                    'start_time': '15:30',
                                    'duration': '50'},
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


class TestEventEditView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()
        self.ev1 = createEvent('2004-08-15 12:00', '1h', "ev1",
                               location="Hell")
        self.ev2 = createEvent('2004-08-12 13:00', '2h', "ev2",
                               unique_id="pick me", location="Heaven")
        self.person.calendar.addEvent(self.ev1)
        self.person.calendar.addEvent(self.ev2)

    def createView(self):
        from schooltool.browser.cal import EventEditView
        view = EventEditView(self.person.calendar)
        view.authorization = lambda x, y: True
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "pick me"})
        content = view.render(request)

        self.assert_('"2004-08-15"' not in content)
        self.assert_('"ev1"' not in content)

        self.assert_('"ev2"' in content)
        self.assert_('"2004-08-12"' in content)
        self.assert_('"Heaven"' in content)
        self.assert_('"13:00"' in content)
        self.assert_('"120"' in content)

    def test_render_nonexistent(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "nonexistent"})
        content = view.render(request)

        self.assert_("This event does not exist." in content)

    def test(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "pick me",
                                    'title': 'Changed',
                                    'location': 'Inbetween',
                                    'start_date': '2004-08-16',
                                    'start_time': '13:30',
                                    'duration': '70'},
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

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/johndoe/calendar/'
                          'daily.html?date=2004-08-16')


class TestEventDeleteView(unittest.TestCase):

    def createView(self):
        from schooltool.browser.cal import EventDeleteView
        cal = createCalendar()
        setPath(cal, '/persons/somebody/calendar')
        view = EventDeleteView(cal)
        view.authorization = lambda x, y: True
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

        request = RequestStub(args={'event_id': "pick me"})
        content = view.render(request)

        self.assertEquals(len(list(cal)), 1)
        self.assert_(ev1 in list(cal))
        self.assert_(ev2 not in list(cal))

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-12')

    def test_no_such_event(self):
        view = self.createView()
        request = RequestStub(args={'event_id': "nosuchid"})
        content = view.render(request)
        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html')


class TestEventSourceDecorator(unittest.TestCase):

    def test(self):
        from schooltool.browser.cal import EventSourceDecorator
        from schooltool.cal import CalendarEvent
        from schooltool.interfaces import ICalendarEvent
        from zope.interface.verify import verifyObject

        event = CalendarEvent(datetime(2004, 8, 12, 12, 0),
                              timedelta(hours=2), "Event",
                              location="foo", unique_id="bar")
        decorated = EventSourceDecorator(event, 'src')
        verifyObject(ICalendarEvent, decorated)

        self.assertEquals(decorated.source, 'src')
        self.assertEquals(decorated, event)
        self.assertEquals(hash(event), hash(decorated))
        self.assertEquals(event.unique_id, decorated.unique_id)


class TestCalendarComboMixin(unittest.TestCase):

    def test(self):
        from schooltool.browser.cal import CalendarComboMixin
        from schooltool.model import Person

        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')

        cal = createCalendar()
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        tcal = createCalendar()
        tcal.__parent__ = person
        tcal.__name__ = 'timetable-calendar'

        person.makeCalendar = lambda: tcal

        view = CalendarComboMixin(cal)

        result = list(view.iterEvents())
        self.assertEquals(result, [])

        ev1 = createEvent('2004-08-12 12:00', '1h', 'ev1')
        ev2 = createEvent('2004-08-12 13:00', '1h', 'ev2')
        cal.addEvent(ev1)
        tcal.addEvent(ev2)

        result = list(view.iterEvents())
        self.assertEquals(result, [ev1, ev2])
        self.assertEquals([e.source for e in result],
                          ['calendar', 'timetable-calendar'])


class TestComboCalendarView(AppSetupMixin, unittest.TestCase,
                            TraversalTestMixin):

    def test_traverse(self):
        from schooltool.browser.cal import ComboCalendarView
        from schooltool.browser.cal import ComboDailyCalendarView
        from schooltool.browser.cal import ComboWeeklyCalendarView
        from schooltool.browser.cal import ComboMonthlyCalendarView
        from schooltool.browser.cal import YearlyCalendarView
        from schooltool.browser.cal import EventAddView
        from schooltool.browser.cal import EventEditView
        from schooltool.browser.cal import EventDeleteView
        from schooltool.browser.acl import ACLView
        context = self.person.calendar
        view = ComboCalendarView(context)
        self.assertTraverses(view, 'daily.html', ComboDailyCalendarView,
                             context)
        self.assertTraverses(view, 'weekly.html', ComboWeeklyCalendarView,
                             context)
        self.assertTraverses(view, 'monthly.html', ComboMonthlyCalendarView,
                             context)
        self.assertTraverses(view, 'yearly.html', YearlyCalendarView, context)
        self.assertTraverses(view, 'add_event.html', EventAddView, context)
        self.assertTraverses(view, 'edit_event.html', EventEditView, context)
        self.assertTraverses(view, 'delete_event.html', EventDeleteView,
                             context)
        self.assertTraverses(view, 'acl.html', ACLView, context.acl)


class TestCalendarEventView(TraversalTestMixin, unittest.TestCase):

    def test(self):
        from schooltool.cal import CalendarEvent
        from schooltool.browser.cal import CalendarEventView
        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(hours=1), "Main event",
                           unique_id="id!")
        view = CalendarEventView(ev)
        request = RequestStub()

        content = view.render(request)
        # eat trailing whitespace and empty lines
        content = re.sub('\s+\n', '\n', content)
        expected = dedent("""
            <div class="calevent">
                <div class="dellink">
                  <a href="delete_event.html?event_id=id%21">[delete]</a>
                </div>
                <h3>
                  <a href="edit_event.html?event_id=id%21">Main event</a>
                </h3>
              12:01&ndash;13:01
            </div>
            """)
        self.assertEquals(content, expected,
                          "\n" + diff(content, expected))

        self.assertEquals(view.cssClass(), 'event')

    def test_ro(self):
        from schooltool.cal import CalendarEvent
        from schooltool.browser.cal import CalendarEventView
        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(hours=1), "Main event",
                           unique_id="id")
        view = CalendarEventView(ev)
        view.context.source = 'timetable-calendar'
        request = RequestStub()

        content = view.render(request)
        # eat trailing whitespace and empty lines
        content = re.sub('\s+\n', '\n', content)
        expected = dedent("""
                     <div class="calevent">
                       <h3>Main event</h3>
                       12:01&ndash;13:01
                     </div>
                    """)
        self.assertEquals(content, expected,
                          "\n" + diff(content, expected))

        self.assertEquals(view.cssClass(), 'ro_event')

    def test_location(self):
        from schooltool.cal import CalendarEvent
        from schooltool.browser.cal import CalendarEventView

        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(hours=1), "Main event",
                           unique_id="id", location="Office")
        view = CalendarEventView(ev)
        content = view.render(RequestStub())
        self.assert_(content, '(Office)' in content)

    def test_duration(self):
        from schooltool.cal import CalendarEvent
        from schooltool.browser.cal import CalendarEventView

        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(hours=1), "Main event")
        view = CalendarEventView(ev)
        self.assertEquals(view.duration(), '12:01&ndash;13:01')

        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(days=1), "Long event")
        view = CalendarEventView(ev)
        self.assertEquals(view.duration(),
                          '2004-12-01 12:01&ndash;2004-12-02 12:01')

    def test_short(self):
        from schooltool.cal import CalendarEvent
        from schooltool.browser.cal import CalendarEventView

        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(hours=1), "Main event")
        view = CalendarEventView(ev)
        self.assertEquals(view.short(),
                          'Main event (12:01&ndash;13:01)')

        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(days=1), "Long event")
        view = CalendarEventView(ev)
        self.assertEquals(view.short(),
                          'Long event (Dec&nbsp;01&ndash;Dec&nbsp;02)')

    def test_uniqueId(self):
        from schooltool.cal import CalendarEvent
        from schooltool.browser.cal import CalendarEventView

        ev = CalendarEvent(datetime(2004, 12, 01, 12, 01),
                           timedelta(hours=1), "Main event",
                           unique_id="Weird@stuff!")
        view = CalendarEventView(ev)
        self.assertEquals(view.uniqueId(), 'Weird%40stuff%21')


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
    suite.addTest(unittest.makeSuite(TestEventSourceDecorator))
    suite.addTest(unittest.makeSuite(TestCalendarComboMixin))
    suite.addTest(unittest.makeSuite(TestComboCalendarView))
    suite.addTest(unittest.makeSuite(TestCalendarEventView))
    suite.addTest(DocTestSuite('schooltool.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main()
