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

import unittest
from logging import INFO
from datetime import datetime, date, time, timedelta

from schooltool.browser.tests import AppSetupMixin, RequestStub, setPath
from schooltool.tests.utils import NiceDiffsMixin

__metaclass__ = type


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
                                    'start': '2004-08-10 19:01:00',
                                    'mins': '61',
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
        self.assert_("Only managers can set the owner" not in content)
        self.assert_("Invalid owner: teacher" not in content)

        ev1 = iter(self.teacher.calendar).next()
        self.assert_(ev1.owner is self.teacher,
                     "%r is not %r" % (ev1.owner, self.teacher))

    def test_owner_forbidden(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.teacher,
                              args={'owner': 'whatever',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        content = view.render(request)
        self.assert_("Only managers can set the owner" in content)
        self.assert_("2004-08-10" in content)
        self.assert_("19:01" in content)
        self.assert_("61" in content)

    def test_owner_wrong_name(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager,
                              args={'owner': 'whatever',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61',
                                    'CONFIRM_BOOK': 'Book'})
        content = view.render(request)
        self.assert_("Invalid owner: whatever" in content)
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
        from schooltool.cal import CalendarEvent
        from schooltool.common import parse_datetime
        ev = CalendarEvent(parse_datetime('2004-08-10 19:00:00'),
                           timedelta(hours=1), "Some event")
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
        self.assertEquals(view.error, "The resource is busy at specified time")


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


class TestCalendarViewBase(unittest.TestCase):

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
        from schooltool.cal import Calendar
        from schooltool.model import Person

        cal = Calendar()
        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')
        cal.__parent__ = person

        view = CalendarViewBase(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 12)

        prefix = 'http://localhost:7001/persons/boss/'
        self.assertEquals(view.calURL("foo"),
                          prefix + 'calendar_foo.html?date=2004-08-12')
        self.assertEquals(view.calURL("bar", date(2005, 3, 22)),
                          prefix + 'calendar_bar.html?date=2005-03-22')

    def test_getDays(self):
        from schooltool.browser.cal import CalendarViewBase, CalendarDay
        from schooltool.cal import CalendarEvent, Calendar

        cal = Calendar()
        view = CalendarViewBase(cal)
        view.cursor = date(2004, 8, 11)

        def calEvent(name, dt, hours=1):
            event = CalendarEvent(dt, timedelta(hours=hours), name)
            cal.addEvent(event)
            return event

        e0 = calEvent("zeroth", datetime(2004, 8, 10, 11, 0))
        e1 = calEvent("second", datetime(2004, 8, 11, 12, 0))
        e2 = calEvent("first", datetime(2004, 8, 11, 11, 0))
        e3 = calEvent("long", datetime(2004, 8, 12, 23, 0), hours=4)
        e4 = calEvent("last", datetime(2004, 8, 15, 11, 0))

        start = date(2004, 8, 10)
        end = date(2004, 8, 16)
        days = view.getDays(start, end)

        self.assertEquals(len(days), 6)
        for i, day in enumerate(days): 
            self.assertEquals(day.date, date(2004, 8, 10 + i))

        self.assertEquals(days[0].events, [e0])
        self.assertEquals(days[1].events, [e2, e1])
        self.assertEquals(days[2].events, [e3])
        self.assertEquals(days[3].events, [])
        self.assertEquals(days[4].events, [])
        self.assertEquals(days[5].events, [e4])

class TestWeeklyCalendarView(unittest.TestCase):

    def test_prev_next(self):
        from schooltool.browser.cal import WeeklyCalendarView
        view = WeeklyCalendarView(None)
        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevWeek(), date(2004, 8, 11))
        self.assertEquals(view.nextWeek(), date(2004, 8, 25))

    def test_render(self):
        from schooltool.browser.cal import WeeklyCalendarView
        from schooltool.cal import CalendarEvent, Calendar
        from schooltool.model import Person

        cal = Calendar()
        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')
        cal.__parent__ = person
        cal.addEvent(CalendarEvent(datetime(2004, 8, 11, 12, 0),
                                   timedelta(hours=1),
                                   "Stuff happens"))

        view = WeeklyCalendarView(cal)
        view.authorization = lambda x, y: True
        view.cursor = date(2004, 8, 12)
        request = RequestStub()
        content = view.render(request)
        self.assert_("Da Boss" in content)
        self.assert_("Stuff happens" in content)

    def test_getWeek(self):
        from schooltool.browser.cal import WeeklyCalendarView
        from schooltool.cal import Calendar

        cal = Calendar()
        view = WeeklyCalendarView(cal)

        for cursor in (date(2004, 8, 9), date(2004, 8, 11), date(2004, 8, 15)):
            view.getDays = GetDaysStub()
            view.cursor = cursor
            week = view.getWeek()
            self.assertEquals(week, None)
            self.assertEquals(view.getDays.bounds,
                              [(date(2004, 8, 9), date(2004, 8, 15))])


class TestMonthlyCalendarView(NiceDiffsMixin, unittest.TestCase):

    def test_render(self):
        from schooltool.browser.cal import MonthlyCalendarView
        from schooltool.cal import CalendarEvent, Calendar
        from schooltool.model import Person

        cal = Calendar()
        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')
        cal.__parent__ = person
        cal.addEvent(CalendarEvent(datetime(2004, 8, 11, 12, 0),
                                   timedelta(hours=1),
                                   "Stuff happens"))

        view = MonthlyCalendarView(cal)
        view.authorization = lambda x, y: True
        view.cursor = date(2004, 8, 12)
        request = RequestStub()
        content = view.render(request)
        self.assert_("Da Boss" in content)
        self.assert_("Stuff happens" in content)

    def test_prev_next(self):
        from schooltool.browser.cal import MonthlyCalendarView
        view = MonthlyCalendarView(None)
        view.cursor = date(2004, 8, 18)
        self.assertEquals(view.prevMonth(), date(2004, 7, 1))
        self.assertEquals(view.nextMonth(), date(2004, 9, 1))

    def test_getMonth(self):
        from schooltool.browser.cal import MonthlyCalendarView
        from schooltool.cal import Calendar

        cal = Calendar()
        view = MonthlyCalendarView(cal)

        view.cursor = date(2004, 8, 11)
        view.getDays = GetDaysStub()
        weeks = view.getMonth()
        self.assertEquals(weeks, [None] * 6)
        self.assertEquals(view.getDays.bounds,
                          [(date(2004, 7, 26), date(2004, 8, 2)),
                           (date(2004, 8, 2), date(2004, 8, 9)),
                           (date(2004, 8, 9), date(2004, 8, 16)),
                           (date(2004, 8, 16), date(2004, 8, 23)),
                           (date(2004, 8, 23), date(2004, 8, 30)),
                           (date(2004, 8, 30), date(2004, 9, 6))])

        # October 2004 ends with a Sunday, so we use it to check that
        # no days from the next month are included.
        view.cursor = date(2004, 10, 1)
        view.getDays = GetDaysStub()
        weeks = view.getMonth()
        self.assertEquals(weeks, [None] * 5)
        self.assertEquals(view.getDays.bounds[4],
                          (date(2004, 10, 25), date(2004, 11, 1)))

        # Same here, just check the previous month.
        view.cursor = date(2004, 11, 1)
        view.getDays = GetDaysStub()
        weeks = view.getMonth()
        self.assertEquals(weeks, [None] * 5)
        self.assertEquals(view.getDays.bounds[0],
                          (date(2004, 11, 1), date(2004, 11, 8)))
        weeks = view.getMonth()


class GetDaysStub:

    def __init__(self):
        self.bounds = []

    def __call__(self, start, end):
        self.bounds.append((start, end))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingView))
    suite.addTest(unittest.makeSuite(TestCalendarDay))
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(unittest.makeSuite(TestWeeklyCalendarView))
    suite.addTest(unittest.makeSuite(TestMonthlyCalendarView))
    return suite


if __name__ == '__main__':
    unittest.main()
