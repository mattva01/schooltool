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


class TestCalendarViewBase(unittest.TestCase):

    def test_update(self):
        from schooltool.browser.cal import CalendarViewBase

        view = CalendarViewBase(None)
        view.request = RequestStub()
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = RequestStub(args={'date': '2004-08-18'})
        view.update()
        self.assertEquals(view.cursor, date(2004, 8, 18))


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

    def test_getDays(self):
        from schooltool.browser.cal import WeeklyCalendarView

        view = WeeklyCalendarView(None)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 11)

        self.assertEquals(view.getDays(),
                          [date(2004, 8, d) for d in range(9, 16)])

    def test_dayEvents(self):
        from schooltool.browser.cal import WeeklyCalendarView
        from schooltool.cal import CalendarEvent, Calendar

        cal = Calendar()
        view = WeeklyCalendarView(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 11)
        e1 = CalendarEvent(datetime(2004, 8, 11, 12, 0),
                           timedelta(hours=1),
                           "first event")
        cal.addEvent(e1)
        e2 = CalendarEvent(datetime(2004, 8, 11, 11, 0),
                           timedelta(hours=1),
                           "second event")
        cal.addEvent(e2)

        self.assertEquals(view.dayEvents(view.cursor),
                          [e2, e1])


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

    def test_getWeeks(self):
        from schooltool.browser.cal import MonthlyCalendarView

        view = MonthlyCalendarView(None)
        view.request = RequestStub()
        view.update()

        view.cursor = date(2004, 8, 11)
        weeks = view.getWeeks()
        self.assertEquals(weeks,
                          [[date(2004, 7, d) for d in range(26, 32)]
                           + [date(2004, 8, 1)],
                           [date(2004, 8, d) for d in range(2, 9)],
                           [date(2004, 8, d) for d in range(9, 16)],
                           [date(2004, 8, d) for d in range(16, 23)],
                           [date(2004, 8, d) for d in range(23, 30)],
                           [date(2004, 8, d) for d in range(30, 32)]
                           + [date(2004, 9, d) for d in range(1, 6)]])

        # October 2004 ends with a Sunday, so we use it to check that
        # no days from the next month are included.
        view.cursor = date(2004, 10, 1)
        weeks = view.getWeeks()
        self.assertEquals(weeks[-1][-1].month, 10)

        # Same here, just check the previous month.
        view.cursor = date(2004, 11, 1)
        weeks = view.getWeeks()
        self.assertEquals(weeks[0][0].month, 11)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingView))
    suite.addTest(unittest.makeSuite(TestCalendarViewBase))
    suite.addTest(unittest.makeSuite(TestWeeklyCalendarView))
    suite.addTest(unittest.makeSuite(TestMonthlyCalendarView))
    return suite


if __name__ == '__main__':
    unittest.main()
