#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for schooltool.rest.cal

$Id$
"""

import unittest
from logging import INFO
import datetime
from schooltool.rest.tests import RequestStub, setPath, viewClass
from schooltool.tests.utils import RegistriesSetupMixin, NiceDiffsMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.tests.helpers import dedent, diff, sorted

__metaclass__ = type


class DatetimeStub:

    def utcnow(self):
        return datetime.datetime(2004, 1, 2, 3, 4, 5)


def reorder_vcal(body):
    """Sort all VEVENTs in body."""
    begin, end = "BEGIN:VEVENT", "END:VEVENT"
    marker = "%s\r\n%s" % (end, begin)
    first_idx = body.find(begin)
    if first_idx == -1:
        return body
    else:
        first_idx += len(begin)
    last_idx = body.rindex(end)
    head = body[:first_idx]
    events = body[first_idx:last_idx].split(marker)
    tail = body[last_idx:]
    events.sort()
    return head + marker.join(events) + tail


class CalendarTestBase(unittest.TestCase):

    def do_test_get(self, expected, uri='http://localhost/calendar'):
        """Bind self.view to a view before calling this."""
        request = RequestStub(uri)
        result = self.view.render(request)
        expected = "\r\n".join(expected.splitlines()) # normalize line endings
        result = reorder_vcal(result)
        expected = reorder_vcal(expected)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/calendar; charset=UTF-8")
        self.assertEquals(result, expected, "\n" + diff(expected, result))


class TestSchooldayModelCalendarView(QuietLibxml2Mixin, CalendarTestBase):

    def setUp(self):
        from schooltool.cal import SchooldayModel
        from schooltool.rest.cal import SchooldayModelCalendarView
        self.sm = SchooldayModel(datetime.date(2003, 9, 1),
                                 datetime.date(2003, 9, 30))
        setPath(self.sm, '/person/calendar')
        self.view = SchooldayModelCalendarView(self.sm)
        self.view.datetime_hook = DatetimeStub()
        self.view.authorization = lambda ctx, rq: True
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def test_get_empty(self):
        self.do_test_get(dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20030901
            DTEND;VALUE=DATE:20031001
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """))

    def test_get(self):
        self.sm.addWeekdays(0, 1, 2, 3, 4) # Mon to Fri
        expected = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20030901
            DTEND;VALUE=DATE:20031001
            DTSTAMP:20040102T030405Z
            END:VEVENT
        """)
        for date in self.sm:
            if date.weekday() not in (5, 6):
                s = date.strftime("%Y%m%d")
                expected += dedent("""
                    BEGIN:VEVENT
                    UID:schoolday-%s-/person/calendar@localhost
                    SUMMARY:Schoolday
                    DTSTART;VALUE=DATE:%s
                    DTSTAMP:20040102T030405Z
                    END:VEVENT
                """ % (s, s))
        self.do_test_get(expected + "END:VCALENDAR")

    def test_put(self):
        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20041001
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        request = RequestStub("http://localhost/person/calendar", method="PUT",
                              headers={"Content-Type": "text/calendar"},
                              body=calendar)
        result = self.view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.applog,
                          [(None, 'Schoolday Calendar /person/calendar updated',
                            INFO)])
        self.assertEquals(self.sm.first, datetime.date(2004, 9, 1))
        self.assertEquals(self.sm.last, datetime.date(2004, 9, 30))
        for date in self.sm:
            if date == datetime.date(2004, 9, 12):
                self.assert_(self.sm.isSchoolday(date))
            else:
                self.assert_(not self.sm.isSchoolday(date))

    def _test_put_error(self, body, content_type='text/calendar', errmsg=None):
        self.sm.add(datetime.date(2003, 9, 15))
        request = RequestStub("http://localhost/person/calendar", method="PUT",
                              headers={"Content-Type": content_type},
                              body=body)
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(request.applog, [])
        if errmsg:
            self.assertEquals(result, errmsg)
        self.assertEquals(self.sm.first, datetime.date(2003, 9, 1))
        self.assertEquals(self.sm.last, datetime.date(2003, 9, 30))
        self.assert_(self.sm.isSchoolday(datetime.date(2003, 9, 15)))

    def test_put_errors(self):
        self._test_put_error("Hi, Mom!", content_type="text/plain",
                             errmsg="Unsupported content type: text/plain")
        self._test_put_error("This is not iCalendar")
        self._test_put_error("BEGIN:VCALENDAR\nEND:VCALENDAR\n",
                             errmsg="School period not defined")

        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20040930
            END:VEVENT
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20040929
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self._test_put_error(calendar,
                             errmsg="Multiple definitions of school period")

        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20040930
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            DTEND;VALUE=DATE:20040914
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self._test_put_error(calendar,
                             errmsg="Schoolday longer than one day")

        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20040930
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            RDATE;VALUE=DATE:20040915
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self._test_put_error(calendar,
                     errmsg="Repeating events/exceptions not yet supported")

        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20041001
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20041001
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self._test_put_error(calendar,
                     errmsg="Schoolday outside school period")

    def test_put_xml(self):
        body = dedent("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
        """)
        request = RequestStub("http://localhost/person/calendar", method="PUT",
                              headers={"Content-Type": "text/xml"},
                              body=body)
        result = self.view.render(request)
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.applog,
                [(None, 'Schoolday Calendar /person/calendar updated', INFO)])
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(self.sm.first, datetime.date(2003, 9, 1))
        self.assertEquals(self.sm.last, datetime.date(2003, 9, 7))
        schooldays = []
        for date in self.sm:
            if self.sm.isSchoolday(date):
                schooldays.append(date)
        expected = [datetime.date(2003, 9, d) for d in 1, 2, 4, 5]
        self.assertEquals(schooldays, expected)

    def test_put_xml_errors(self):
        self._test_put_error("This is not XML", content_type="text/xml")
        self._test_put_error("<foo>Wrong XML</foo>", content_type="text/xml")
        self._test_put_error("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="20030901" last="2003-09-07">
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
            """, content_type="text/xml")
        self._test_put_error("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-31">Holiday</holiday>
            </schooldays>
            """, content_type="text/xml")
        self._test_put_error("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <daysofweek>Monday tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
            """, content_type="text/xml")


class TestCalendarReadView(NiceDiffsMixin, CalendarTestBase):

    def _newView(self, context):
        from schooltool.rest.cal import CalendarReadView
        return CalendarReadView(context)

    def _create(self):
        from schooltool.cal import Calendar
        context = Calendar()
        setPath(context, '/person/calendar')
        context.__parent__.title = "A Person"
        self.view = self._newView(context)
        self.view.datetime_hook = DatetimeStub()
        self.view.authorization = lambda ctx, rq: True
        return context

    def test_get_empty(self):
        self._create()
        self.do_test_get(dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:placeholder-/person/calendar@localhost
            SUMMARY:Empty calendar
            DTSTART;VALUE=DATE:20040102
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """))

    def test_get(self):
        from schooltool.cal import CalendarEvent
        cal = self._create()
        cal.addEvent(CalendarEvent(datetime.datetime(2003, 9, 2, 15, 40),
                                   datetime.timedelta(minutes=20),
                                   "Quick Lunch"))
        cal.addEvent(CalendarEvent(datetime.datetime(2003, 9, 3, 12, 00),
                                   datetime.timedelta(minutes=60),
                                   "Long\nLunch"))
        self.do_test_get(dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:1668453774-/person/calendar@localhost
            SUMMARY:Quick Lunch
            DTSTART:20030902T154000
            DURATION:PT20M
            DTSTAMP:20040102T030405Z
            END:VEVENT
            BEGIN:VEVENT
            UID:-1822792810-/person/calendar@localhost
            SUMMARY:Long\\nLunch
            DTSTART:20030903T120000
            DURATION:PT1H
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """))


class TestCalendarView(TestCalendarReadView):

    def _newView(self, context):
        from schooltool.rest.cal import CalendarView
        return CalendarView(context)

    def test_put_empty(self, body=""):
        from schooltool.cal import CalendarEvent
        request = RequestStub("http://localhost/person/calendar", method="PUT",
                              headers={"Content-Type": "text/calendar"},
                              body=body)
        cal = self._create()
        cal.addEvent(CalendarEvent(datetime.date(2003, 9, 1),
                                   datetime.timedelta(1),
                                   "Delete me"))
        result = self.view.render(request)
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.applog,
                          [(None,
                            'Calendar /person/calendar for A Person imported',
                            INFO)])
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        events = list(cal)
        expected = []
        self.assertEquals(sorted(events), sorted(expected))

    def test_put_placeholder(self):
        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:placeholder-/person/calendar@localhost
            SUMMARY:Empty calendar
            DTSTART;VALUE=DATE:20040103
            DTSTAMP:20040103T030405Z
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self.test_put_empty(calendar)

    def test_put(self):
        from schooltool.cal import CalendarEvent
        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:1668453774-/person/calendar@localhost
            SUMMARY:Quick Lunch
            DTSTART:20030902T154000
            DURATION:PT20M
            DTSTAMP:20040102T030405Z
            END:VEVENT
            BEGIN:VEVENT
            UID:-1822792810-/person/calendar@localhost
            SUMMARY:Long\\nLunch
            DTSTART:20030903T120000
            DURATION:PT1H
            DTSTAMP:20040102T030405Z
            END:VEVENT
            BEGIN:VEVENT
            UID:1234idontcare-/person/calendar@localhost
            SUMMARY:Something else
            DTSTART;VALUE=DATE:20030904
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        request = RequestStub("http://localhost/person/calendar", method="PUT",
                              headers={"Content-Type": "text/calendar"},
                              body=calendar)
        cal = self._create()
        cal.addEvent(CalendarEvent(datetime.date(2003, 9, 1),
                                   datetime.timedelta(1),
                                   "Delete me"))
        result = self.view.render(request)
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.applog,
                          [(None,
                            'Calendar /person/calendar for A Person imported',
                            INFO)])
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        events = list(cal)
        expected = [
            CalendarEvent(datetime.datetime(2003, 9, 2, 15, 40),
                          datetime.timedelta(minutes=20),
                          "Quick Lunch"),
            CalendarEvent(datetime.datetime(2003, 9, 3, 12, 00),
                          datetime.timedelta(minutes=60),
                          "Long\nLunch"),
            CalendarEvent(datetime.date(2003, 9, 4),
                          datetime.timedelta(days=1),
                          "Something else"),
        ]
        self.assertEquals(sorted(events), sorted(expected))

    def _test_put_error(self, body, content_type='text/calendar', errmsg=None):
        request = RequestStub("http://localhost/calendar", method="PUT",
                              headers={"Content-Type": content_type},
                              body=body)
        result = self.view.render(request)
        if errmsg:
            self.assertEquals(result, errmsg)
        self.assertEquals(request.applog, [])
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")

    def test_put_errors(self):
        self._create()
        self._test_put_error("Hi, Mom!", content_type="text/plain",
                             errmsg="Unsupported content type: text/plain")
        self._test_put_error("This is not iCalendar")

        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/person/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20040930
            END:VEVENT
            BEGIN:VEVENT
            UID:random@example.com
            SUMMARY:Doctor's appointment
            DTSTART;VALUE=DATE:20040911
            END:VEVENT
            BEGIN:VEVENT
            UID:random2@example.com
            SUMMARY:Schoolday
            DTSTART;VALUE=DATE:20040912
            RDATE;VALUE=DATE:20040915
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self._test_put_error(calendar,
                     errmsg="Repeating events/exceptions not yet supported")


class TestCalendarViewBookingEvents(unittest.TestCase):

    def setUp(self):
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Group, Person, Resource
        from schooltool.cal import CalendarEvent
        from schooltool.rest.cal import CalendarView

        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        self.person = app['persons'].new("john", title="John")
        self.resource = app['resources'].new("hall", title="Hall")
        self.view = CalendarView(self.person.calendar)
        self.view.authorization = lambda ctx, rq: True

        e = CalendarEvent(datetime.datetime(2004, 1, 1, 10, 0, 0),
                          datetime.timedelta(minutes=60),
                          "Hall booked by John",
                          self.person, self.resource)
        self.event = e
        self.resource.calendar.addEvent(e)
        self.person.calendar.addEvent(e)

    def test_put_empty(self):
        request = RequestStub("/persons/john/calendar", method="PUT", body="",
                              headers={'Content-Type': 'text/calendar'})
        self.view.render(request)

        self.assertEquals(list(self.person.calendar), [])
        self.assertEquals(list(self.resource.calendar), [])

    def test_put_unmodified(self):
        cal = dedent("""
            BEGIN:VCALENDAR\r
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN\r
            VERSION:2.0\r
            BEGIN:VEVENT\r
            UID:602343351-/persons/john/calendar@localhost\r
            SUMMARY:Hall booked by John\r
            DTSTART:20040101T100000\r
            DURATION:PT1H\r
            DTSTAMP:20040114T122211Z\r
            END:VEVENT\r
            END:VCALENDAR\r
            """)

        request = RequestStub("/persons/john/calendar", method="PUT",
                              headers={'Content-Type': 'text/calendar'},
                              body=cal)
        result = self.view.render(request)
        self.assertEquals(list(self.person.calendar), [self.event])
        self.assertEquals(list(self.resource.calendar), [self.event])

    def test_put_modified(self):
        cal = dedent("""
            BEGIN:VCALENDAR\r
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN\r
            VERSION:2.0\r
            BEGIN:VEVENT\r
            UID:602343351-/persons/john/calendar@localhost\r
            SUMMARY:Hall booked by John\r
            DTSTART:20040101T100100\r
            DURATION:PT1H\r
            DTSTAMP:20040114T122211Z\r
            END:VEVENT\r
            END:VCALENDAR\r
            """)

        request = RequestStub("/persons/john/calendar", method="PUT",
                              headers={'Content-Type': 'text/calendar'},
                              body=cal)
        result = self.view.render(request)
        self.assertEquals(len(list(self.person.calendar)), 1)
        self.assertEquals(len(list(self.resource.calendar)), 0)


class TestBookingView(RegistriesSetupMixin, QuietLibxml2Mixin,
                      unittest.TestCase):

    def setUp(self):
        from schooltool.rest.cal import BookingView
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Group, Person, Resource
        from schooltool.membership import Membership
        import schooltool.membership
        self.setUpLibxml2()
        self.setUpRegistries()
        schooltool.membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        self.person = app['persons'].new("john", title="John")
        self.resource = app['resources'].new("hall", title="Hall")
        self.manager = app['persons'].new("manager", title="Manager")
        self.managers = app['groups'].new("managers", title="Managers")
        Membership(member=self.manager, group=self.managers)
        self.view = BookingView(self.resource)
        self.view.authorization = lambda ctx, rq: True

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def test(self):
        xml = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/john"/>
              <slot start="2004-01-01 10:00:00" duration="90"/>
            </booking>
            """
        self.assertEquals(len(list(self.person.calendar)), 0)
        self.assertEquals(len(list(self.resource.calendar)), 0)
        request = RequestStub(method="POST", body=xml,
                              authenticated_user=self.manager)
        result = self.view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.applog,
                          [(self.manager,
                            "/resources/hall (Hall) booked by /persons/john"
                            " (John) at 2004-01-01 10:00:00 for 1:30:00",
                            INFO)])
        self.assertEquals(len(list(self.person.calendar)), 1)
        self.assertEquals(len(list(self.resource.calendar)), 1)
        ev1 = iter(self.person.calendar).next()
        ev2 = iter(self.resource.calendar).next()
        self.assertEquals(ev1, ev2)
        self.assert_(ev1.context is self.resource,
                     "%r is not %r" % (ev1.context, self.resource))
        self.assert_(ev1.owner is self.person,
                     "%r is not %r" % (ev1.owner, self.person))

    def test_conflict(self):
        from schooltool.cal import CalendarEvent
        from schooltool.common import parse_datetime
        xml1 = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/john"/>
              <slot start="2004-01-01 10:00:00" duration="90"/>
            </booking>
            """
        xml2 = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1"
                     conflicts="error">
              <owner path="/persons/john"/>
              <slot start="2004-01-01 10:00:00" duration="90"/>
            </booking>
            """
        ev = CalendarEvent(parse_datetime('2004-01-01 10:10:00'),
                           datetime.timedelta(hours=1), "Some event")
        self.resource.calendar.addEvent(ev)
        self.assertEquals(len(list(self.person.calendar)), 0)
        self.assertEquals(len(list(self.resource.calendar)), 1)
        for xml in xml1, xml2:
            request = RequestStub(method="POST", body=xml,
                                  authenticated_user=self.manager)
            result = self.view.render(request)
            self.assertEquals(request.code, 400)
            self.assertEquals(request.applog, [])
            self.assertEquals(result, "The resource is busy at specified time")
            self.assertEquals(len(list(self.person.calendar)), 0)
            self.assertEquals(len(list(self.resource.calendar)), 1)

        xml3 = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1"
                     conflicts="ignore">
              <owner path="/persons/john"/>
              <slot start="2004-01-01 10:00:00" duration="90"/>
            </booking>
            """
        request = RequestStub(method="POST", body=xml3,
                              authenticated_user=self.manager)
        result = self.view.render(request)
        self.assertEquals(request.code, 200)
        pevs = list(self.person.calendar)
        revs = list(self.resource.calendar)
        self.assertEquals(len(pevs), 1)
        self.assertEquals(len(revs), 2)
        self.assert_(pevs[0] in revs)

    def test_errors(self):
        nonxml = "Where am I?"
        bad_xml = "<booking />"
        bad_path_xml = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/000001"/>
              <slot start="2004-01-01 10:00:00" duration="90"/>
            </booking>
            """
        bad_date_xml = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/john"/>
              <slot start="2004-01-01 10:00" duration="90"/>
            </booking>
            """
        bad_dur_xml = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/john"/>
              <slot start="2004-01-01 10:00:00" duration="1h"/>
            </booking>
            """
        bad_owner_xml = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/"/>
              <slot start="2004-01-01 10:00:00" duration="10"/>
            </booking>
            """
        cases = [
            (nonxml, "Not valid XML"),
            (bad_xml, "Input not valid according to schema"),
            (bad_path_xml, "Invalid path: u'/persons/000001'"),
            (bad_date_xml, "'start' argument incorrect"),
            (bad_dur_xml, "'duration' argument incorrect"),
            (bad_owner_xml, "'owner' in not an ApplicationObject."),
            ]
        for xml, error in cases:
            request = RequestStub(method="POST", body=xml,
                                  authenticated_user=self.manager)
            result = self.view.render(request)
            self.assertEquals(request.code, 400)
            self.assertEquals(result, error)

        request = RequestStub()
        result = self.view.render(request)
        self.assertEquals(request.code, 404)

    def test_no_auth(self):
        xml = """
            <booking xmlns="http://schooltool.org/ns/calendar/0.1">
              <owner path="/persons/manager"/>
              <slot start="2004-01-01 10:00:00" duration="90"/>
            </booking>
            """
        request = RequestStub(method="POST", body=xml,
                              authenticated_user=self.person)
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.applog, [])
        self.assertEquals(result, "You can only book resources for yourself")


class TestAllCalendarsView(XMLCompareMixin, unittest.TestCase):

    def createApp(self):
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Group, Person, Resource
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        app['groups'].new("students", title="Students")
        app['groups'].new("teachers", title="Teachers")
        app['persons'].new("john", title="John")
        app['persons'].new("smith", title="Smith")
        app['resources'].new("room101", title="101")
        app['resources'].new("hall", title="Hall")
        return app

    def test(self):
        from schooltool.rest.cal import AllCalendarsView
        context = self.createApp()
        view = AllCalendarsView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub()
        result = view.render(request)
        expected = """
            <html>
            <head>
              <title>Calendars</title>
            </head>
            <body>
              <h1>Calendars</h1>
              <h2>Groups</h2>
              <ul>
                <li><a href="http://localhost:7001/groups/students/calendar">
                    Students (private calendar)</a>, <a
            href="http://localhost:7001/groups/students/timetable-calendar">
                    Students (timetable)</a></li>
                <li><a href="http://localhost:7001/groups/teachers/calendar">
                    Teachers (private calendar)</a>, <a
            href="http://localhost:7001/groups/teachers/timetable-calendar">
                    Teachers (timetable)</a></li>
              </ul>
              <h2>Persons</h2>
              <ul>
                <li><a href="http://localhost:7001/persons/john/calendar">
                    John (private calendar)</a>, <a
            href="http://localhost:7001/persons/john/timetable-calendar">
                    John (timetable)</a></li>
                <li><a href="http://localhost:7001/persons/smith/calendar">
                    Smith (private calendar)</a>, <a
            href="http://localhost:7001/persons/smith/timetable-calendar">
                    Smith (timetable)</a></li>
              </ul>
              <h2>Resources</h2>
              <ul>
                <li><a href="http://localhost:7001/resources/room101/calendar">
                    101 (private calendar)</a>, <a
            href="http://localhost:7001/resources/room101/timetable-calendar">
                    101 (timetable)</a></li>
                <li><a href="http://localhost:7001/resources/hall/calendar">
                    Hall (private calendar)</a>, <a
            href="http://localhost:7001/resources/hall/timetable-calendar">
                    Hall (timetable)</a></li>
              </ul>
            </body>
            </html>
        """
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")
        self.assertEqualsXML(result, expected)


class TestModuleSetup(RegistriesSetupMixin, unittest.TestCase):

    def test(self):
        from schooltool.interfaces import ISchooldayModel, ICalendar
        from schooltool.rest.cal import SchooldayModelCalendarView
        from schooltool.rest.cal import CalendarView
        import schooltool.rest.cal
        schooltool.rest.cal.setUp()

        self.assert_(viewClass(ISchooldayModel) is SchooldayModelCalendarView)
        self.assert_(viewClass(ICalendar) is CalendarView)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayModelCalendarView))
    suite.addTest(unittest.makeSuite(TestCalendarReadView))
    suite.addTest(unittest.makeSuite(TestCalendarView))
    suite.addTest(unittest.makeSuite(TestCalendarViewBookingEvents))
    suite.addTest(unittest.makeSuite(TestBookingView))
    suite.addTest(unittest.makeSuite(TestAllCalendarsView))
    suite.addTest(unittest.makeSuite(TestModuleSetup))
    return suite

if __name__ == '__main__':
    unittest.main()
