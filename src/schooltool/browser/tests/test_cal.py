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
from zope.testing.doctestunit import DocTestSuite

from logging import INFO
from pprint import pformat
from datetime import datetime, date, time, timedelta

from schooltool.browser.tests import AppSetupMixin, RequestStub, setPath
from schooltool.browser.tests import TraversalTestMixin
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

    def test_getWeek(self):
        from schooltool.browser.cal import CalendarViewBase, CalendarDay
        from schooltool.cal import Calendar

        cal = Calendar()
        view = CalendarViewBase(cal)

        def getDaysStub(start, end):
            return [CalendarDay(start), CalendarDay(end)]
        view.getDays = getDaysStub

        for dt in (date(2004, 8, 9), date(2004, 8, 11), date(2004, 8, 15)):
            week = view.getWeek(dt)
            self.assertEquals(week,
                              [CalendarDay(date(2004, 8, 9)), # ...
                               CalendarDay(date(2004, 8, 16))])

        dt = date(2004, 8, 16)
        week = view.getWeek(dt)
        self.assertEquals(week,
                          [CalendarDay(date(2004, 8, 16)),
                           CalendarDay(date(2004, 8, 23))])

    def test_getMonth(self):
        from schooltool.browser.cal import CalendarViewBase, CalendarDay
        from schooltool.cal import Calendar

        cal = Calendar()
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
        from schooltool.cal import Calendar

        cal = Calendar()
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
        cal.__name__ = 'calendar'
        cal.addEvent(CalendarEvent(datetime(2004, 8, 11, 12, 0),
                                   timedelta(hours=1),
                                   "Stuff happens"))

        view = WeeklyCalendarView(cal)
        view.authorization = lambda x, y: True
        view.cursor = date(2004, 8, 12)
        request = RequestStub()
        content = view.render(request)
        self.assert_("Da Boss" in content, content)
        self.assert_("Stuff happens" in content)

    def test_getCurrentWeek(self):
        from schooltool.browser.cal import WeeklyCalendarView

        view = WeeklyCalendarView(None)
        view.cursor = "works"
        view.getWeek = lambda x: "really " + x
        self.assertEquals(view.getCurrentWeek(), "really works")


class TestDailyCalendarView(unittest.TestCase):

    def test_update(self):
        from schooltool.browser.cal import DailyCalendarView

        view = DailyCalendarView(None)
        view.request = RequestStub()
        view.update()
        self.assertEquals(view.cursor, date.today())

        view.request = RequestStub(args={'date': '2004-08-18'})
        view.update()
        self.assertEquals(view.cursor, date(2004, 8, 18))

    def test_getColumns(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.cal import CalendarEvent, Calendar
        from schooltool.model import Person

        cal = Calendar()
        cal.__parent__ = Person(title="Da Boss")
        view = DailyCalendarView(cal)
        view.request = RequestStub()
        view.cursor = date(2004, 8, 12)

        self.assertEquals(view.getColumns(), 1)
        cal.addEvent(CalendarEvent(datetime(2004, 8, 12, 12, 0),
                                   timedelta(hours=2),
                                   "Meeting"))
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

        cal.addEvent(CalendarEvent(datetime(2004, 8, 12, 13, 0),
                                   timedelta(hours=2),
                                   "Lunch"))
        cal.addEvent(CalendarEvent(datetime(2004, 8, 12, 14, 0),
                                   timedelta(hours=2),
                                   "Another meeting"))

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
        cal.addEvent(CalendarEvent(datetime(2004, 8, 12, 13, 0),
                                   timedelta(hours=2),
                                   "Call Mark during lunch"))
        self.assertEquals(view.getColumns(), 3)

    def test_getHours(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.cal import CalendarEvent as CE, Calendar
        from schooltool.model import Person

        class CalendarEvent(CE):
            """Calendar events that can be compared to '' or None"""
            def __cmp__(self, other):
                if other is None or other == '':
                    return 1
                else:
                    return CE.__cmp__(self, other)

        cal = Calendar()
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
                           {'time': '15:00', 'cols': (None,)},],
                          pformat(result))

        ev1 = CalendarEvent(datetime(2004, 8, 12, 12, 0), timedelta(hours=2),
                            "Meeting")
        cal.addEvent(ev1)
        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '10:00', 'cols': (None,)},
                           {'time': '11:00', 'cols': (None,)},
                           {'time': '12:00', 'cols': (ev1,)},
                           {'time': '13:00', 'cols': ('',)},
                           {'time': '14:00', 'cols': (None,)},
                           {'time': '15:00', 'cols': (None,)},],
                          pformat(result))

        #
        #  12 +--+
        #  13 |Me|+--+
        #  14 +--+|Lu|
        #  15 |An|+--+
        #  16 +--+
        #

        ev2 = CalendarEvent(datetime(2004, 8, 12, 13, 0),
                            timedelta(hours=2), "Lunch")
        ev3 = CalendarEvent(datetime(2004, 8, 12, 14, 0),
                            timedelta(hours=2), "Another meeting")

        cal.addEvent(ev2)
        cal.addEvent(ev3)

        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '10:00', 'cols': (None, None)},
                           {'time': '11:00', 'cols': (None, None)},
                           {'time': '12:00', 'cols': (ev1, None)},
                           {'time': '13:00', 'cols': ('', ev2)},
                           {'time': '14:00', 'cols': (ev3,'')},
                           {'time': '15:00', 'cols': ('', None)},],
                          pformat(result))

        ev4 = CalendarEvent(datetime(2004, 8, 11, 14, 0),
                            timedelta(days=3), "Visit")

        cal.addEvent(ev4)

        result = list(view.getHours())
        self.assertEquals(result,
                          [{'time': '10:00', 'cols': (ev4, None, None)},
                           {'time': '11:00', 'cols': ('', None, None)},
                           {'time': '12:00', 'cols': ('', ev1, None)},
                           {'time': '13:00', 'cols': ('', '', ev2)},
                           {'time': '14:00', 'cols': ('', ev3,'')},
                           {'time': '15:00', 'cols': ('', '', None)},],
                          pformat(result))

    def test_rowspan(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.cal import CalendarEvent, Calendar
        view = DailyCalendarView(None)
        view.starthour = 10
        view.endhour = 18
        view.cursor = date(2004, 8, 12)

        self.assertEquals(view.rowspan(CalendarEvent(
            datetime(2004, 8, 12, 12, 0), timedelta(days=1), "Long")), 6)

        self.assertEquals(view.rowspan(CalendarEvent(
            datetime(2004, 8, 11, 12, 0), timedelta(days=3), "Very")), 8)

        self.assertEquals(view.rowspan(CalendarEvent(
            datetime(2004, 8, 12, 12, 0), timedelta(seconds=600), "")), 1)

        self.assertEquals(view.rowspan(CalendarEvent(
            datetime(2004, 8, 12, 12, 0),timedelta(seconds=3601), "")), 2)

        self.assertEquals(view.rowspan(CalendarEvent(
            datetime(2004, 8, 12, 9, 0), timedelta(hours=3), "")), 2)


class TestMonthlyCalendarView(NiceDiffsMixin, unittest.TestCase):

    def test_render(self):
        from schooltool.browser.cal import MonthlyCalendarView
        from schooltool.cal import CalendarEvent, Calendar
        from schooltool.model import Person

        cal = Calendar()
        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')
        cal.__parent__ = person
        cal.__name__ = 'calendar'
        cal.addEvent(CalendarEvent(datetime(2004, 8, 11, 12, 0),
                                   timedelta(hours=1),
                                   "Stuff happens"))

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


class TestYearlyCalendarView(NiceDiffsMixin, unittest.TestCase):

    def test_render(self):
        from schooltool.browser.cal import YearlyCalendarView
        from schooltool.cal import CalendarEvent, Calendar
        from schooltool.model import Person

        cal = Calendar()
        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')
        cal.__parent__ = person
        cal.__name__ = 'calendar'
        cal.addEvent(CalendarEvent(datetime(2004, 8, 11, 12, 0),
                                   timedelta(hours=1),
                                   "Stuff happens"))

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


class TestCalendarView(unittest.TestCase, TraversalTestMixin):

    def test_traverse(self):
        from schooltool.cal import Calendar
        from schooltool.browser.cal import CalendarView
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.browser.cal import WeeklyCalendarView
        from schooltool.browser.cal import MonthlyCalendarView
        from schooltool.browser.cal import YearlyCalendarView
        from schooltool.browser.cal import EventAddView
        context = Calendar()
        view = CalendarView(context)
        self.assertTraverses(view, 'daily.html', DailyCalendarView, context)
        self.assertTraverses(view, 'weekly.html', WeeklyCalendarView, context)
        self.assertTraverses(view, 'monthly.html', MonthlyCalendarView,
                             context)
        self.assertTraverses(view, 'yearly.html', YearlyCalendarView, context)
        self.assertTraverses(view, 'add_event.html', EventAddView, context)

    def test_render(self):
        from schooltool.browser.cal import CalendarView
        from schooltool.cal import CalendarEvent, Calendar
        from schooltool.model import Person

        cal = Calendar()
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


class TestEventAddView(unittest.TestCase):

    def setUp(self):
        from schooltool.browser.cal import EventAddView
        from schooltool.cal import Calendar

        self.cal = Calendar()
        setPath(self.cal, '/persons/somebody/calendar')
        self.view = EventAddView(self.cal)
        self.view.authorization = lambda x, y: True

    def test_render(self):
        request = RequestStub()
        content = self.view.render(request)
        self.assert_('Add event' in content)

    def test_render_args(self):
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'duration': '50'})
        content = self.view.render(request)
        self.assert_('Add event' in content)
        self.assert_('Hacking' in content)
        self.assert_('2004-08-13' in content)
        self.assert_('15:30' in content)
        self.assert_('50' in content)

    def test_post(self):
        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'duration': '50'})
        self.view.request = request
        content = self.view.do_POST(request)

        self.assertEquals(request.code, 302)
        self.assertEquals(request.headers['location'],
                          'http://localhost:7001/persons/somebody/calendar/'
                          'daily.html?date=2004-08-13')

        events = list(self.cal)
        self.assertEquals(len(events), 1)
        self.assertEquals(events[0].title, 'Hacking')
        self.assertEquals(events[0].dtstart, datetime(2004, 8, 13, 15, 30))
        self.assertEquals(events[0].duration, timedelta(minutes=50))

    def test_post_errors(self):
        request = RequestStub(args={'title': '',
                                    'start_date': '2004-31-13',
                                    'start_time': '15:30',
                                    'duration': '50'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Missing title' in content)

        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-31-13',
                                    'start_time': '15:30',
                                    'duration': '50'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Invalid date/time' in content)

        request = RequestStub(args={'title': 'Hacking',
                                    'start_date': '2004-08-13',
                                    'start_time': '15:30',
                                    'duration': '100h'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Invalid duration' in content)


class TestEventSourceDecorator(unittest.TestCase):

    def test(self):
        from schooltool.browser.cal import EventSourceDecorator
        from schooltool.cal import CalendarEvent
        from schooltool.interfaces import ICalendarEvent
        from zope.interface.verify import verifyObject

        event = CalendarEvent(datetime(2004, 8, 12, 12, 0),
                              timedelta(hours=2), "Event")
        decorated = EventSourceDecorator(event, 'src')
        verifyObject(ICalendarEvent, decorated)

        self.assertEquals(decorated.source, 'src')
        self.assertEquals(decorated, event)
        self.assertEquals(hash(event), hash(decorated))


class TestCalendarComboMixin(unittest.TestCase):

    def test(self):
        from schooltool.browser.cal import CalendarComboMixin
        from schooltool.cal import Calendar, CalendarEvent
        from schooltool.model import Person

        person = Person(title="Da Boss")
        setPath(person, '/persons/boss')

        cal = Calendar()
        cal.__parent__ = person
        cal.__name__ = 'calendar'

        tcal = Calendar()
        tcal.__parent__ = person
        tcal.__name__ = 'timetable-calendar'

        person.makeCalendar = lambda: tcal

        view = CalendarComboMixin(cal)

        result = list(view.iterEvents())
        self.assertEquals(result, [])

        ev1 = CalendarEvent(datetime(2004, 8, 12, 12, 0),
                            timedelta(hours=1), "ev1")
        ev2 = CalendarEvent(datetime(2004, 8, 12, 13, 0),
                            timedelta(hours=1), "ev2")
        cal.addEvent(ev1)
        tcal.addEvent(ev2)

        result = list(view.iterEvents())
        self.assertEquals(result, [ev1, ev2])
        self.assertEquals([e.source for e in result],
                          ['calendar', 'timetable-calendar'])


class TestComboCalendarView(unittest.TestCase, TraversalTestMixin):

    def test_traverse(self):
        from schooltool.cal import Calendar
        from schooltool.browser.cal import ComboCalendarView
        from schooltool.browser.cal import ComboDailyCalendarView
        from schooltool.browser.cal import ComboWeeklyCalendarView
        from schooltool.browser.cal import ComboMonthlyCalendarView
        from schooltool.browser.cal import YearlyCalendarView
        from schooltool.browser.cal import EventAddView
        context = Calendar()
        view = ComboCalendarView(context)
        self.assertTraverses(view, 'daily.html', ComboDailyCalendarView,
                             context)
        self.assertTraverses(view, 'weekly.html', ComboWeeklyCalendarView,
                             context)
        self.assertTraverses(view, 'monthly.html', ComboMonthlyCalendarView,
                             context)
        self.assertTraverses(view, 'yearly.html', YearlyCalendarView, context)
        self.assertTraverses(view, 'add_event.html', EventAddView, context)


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
    suite.addTest(unittest.makeSuite(TestEventAddView))
    suite.addTest(unittest.makeSuite(TestEventSourceDecorator))
    suite.addTest(unittest.makeSuite(TestCalendarComboMixin))
    suite.addTest(unittest.makeSuite(TestComboCalendarView))
    suite.addTest(DocTestSuite('schooltool.browser.cal'))
    return suite


if __name__ == '__main__':
    unittest.main()
