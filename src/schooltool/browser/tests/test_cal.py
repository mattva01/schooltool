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

from schooltool.browser.tests import AppSetupMixin, RequestStub, setPath
from datetime import datetime, date, time, timedelta

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

class TestWeeklyCalendarView(unittest.TestCase):

    def test_update(self):
        from schooltool.browser.cal import WeeklyCalendarView

        view = WeeklyCalendarView(None)
        view.request = RequestStub()
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = RequestStub(args={'date': '2004-08-18'})
        view.update()
        self.assertEquals(view.cursor, date(2004, 8, 18))

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingView))
    suite.addTest(unittest.makeSuite(TestWeeklyCalendarView))
    return suite


if __name__ == '__main__':
    unittest.main()
