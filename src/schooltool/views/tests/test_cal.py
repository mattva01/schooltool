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
Unit tests for schooltool.views.cal

$Id$
"""

import unittest
import datetime
import libxml2
from zope.interface import directlyProvides
from zope.testing.doctestunit import DocTestSuite
from schooltool.views.tests import RequestStub, setPath
from schooltool.tests.utils import RegistriesSetupMixin, NiceDiffsMixin
from schooltool.tests.utils import XMLCompareMixin
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
        self.assertEquals(request.headers['Content-Type'],
                          "text/calendar; charset=UTF-8")
        self.assertEquals(result, expected, "\n" + diff(expected, result))


class TestSchooldayModelCalendarView(CalendarTestBase):

    def setUp(self):
        from schooltool.cal import SchooldayModel
        from schooltool.views.cal import SchooldayModelCalendarView
        self.sm = SchooldayModel(datetime.date(2003, 9, 1),
                                 datetime.date(2003, 9, 30))
        setPath(self.sm, '/calendar')
        self.view = SchooldayModelCalendarView(self.sm)
        self.view.datetime_hook = DatetimeStub()
        libxml2.registerErrorHandler(lambda ctx, error: None, None)

    def test_get_empty(self):
        self.do_test_get(dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/calendar@localhost
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
            UID:school-period-/calendar@localhost
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
                    UID:schoolday-%s-/calendar@localhost
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
            UID:school-period-/calendar@localhost
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
        request = RequestStub("http://localhost/calendar", method="PUT",
                              headers={"Content-Type": "text/calendar"},
                              body=calendar)
        result = self.view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(self.sm.first, datetime.date(2004, 9, 1))
        self.assertEquals(self.sm.last, datetime.date(2004, 9, 30))
        for date in self.sm:
            if date == datetime.date(2004, 9, 12):
                self.assert_(self.sm.isSchoolday(date))
            else:
                self.assert_(not self.sm.isSchoolday(date))

    def _test_put_error(self, body, content_type='text/calendar', errmsg=None):
        self.sm.add(datetime.date(2003, 9, 15))
        request = RequestStub("http://localhost/calendar", method="PUT",
                              headers={"Content-Type": content_type},
                              body=body)
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
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
            UID:school-period-/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20040901
            DTEND;VALUE=DATE:20040930
            END:VEVENT
            BEGIN:VEVENT
            UID:school-period-/calendar@localhost
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
            UID:school-period-/calendar@localhost
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
            UID:school-period-/calendar@localhost
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
            UID:school-period-/calendar@localhost
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
        request = RequestStub("http://localhost/calendar", method="PUT",
                              headers={"Content-Type": "text/xml"},
                              body=body)
        result = self.view.render(request)
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
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
        from schooltool.views.cal import CalendarReadView
        return CalendarReadView(context)

    def _create(self):
        from schooltool.cal import Calendar
        context = Calendar()
        setPath(context, '/calendar')
        self.view = self._newView(context)
        self.view.datetime_hook = DatetimeStub()
        return context

    def test_get_empty(self):
        self._create()
        self.do_test_get("")

    def test_get_empty(self):
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
            UID:1668453774-/calendar@localhost
            SUMMARY:Quick Lunch
            DTSTART:20030902T154000
            DURATION:PT20M
            DTSTAMP:20040102T030405Z
            END:VEVENT
            BEGIN:VEVENT
            UID:-1822792810-/calendar@localhost
            SUMMARY:Long\\nLunch
            DTSTART:20030903T120000
            DURATION:PT1H
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """))


class TestCalendarView(TestCalendarReadView):

    def _newView(self, context):
        from schooltool.views.cal import CalendarView
        return CalendarView(context)

    def test_put_empty(self):
        from schooltool.cal import CalendarEvent
        request = RequestStub("http://localhost/calendar", method="PUT",
                              headers={"Content-Type": "text/calendar"},
                              body="")
        cal = self._create()
        cal.addEvent(CalendarEvent(datetime.date(2003, 9, 1),
                                   datetime.timedelta(1),
                                   "Delete me"))
        result = self.view.render(request)
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
        events = list(cal)
        expected = []
        self.assertEquals(sorted(events), sorted(expected))

    def test_put(self):
        from schooltool.cal import CalendarEvent
        calendar = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:1668453774-/calendar@localhost
            SUMMARY:Quick Lunch
            DTSTART:20030902T154000
            DURATION:PT20M
            DTSTAMP:20040102T030405Z
            END:VEVENT
            BEGIN:VEVENT
            UID:-1822792810-/calendar@localhost
            SUMMARY:Long\\nLunch
            DTSTART:20030903T120000
            DURATION:PT1H
            DTSTAMP:20040102T030405Z
            END:VEVENT
            BEGIN:VEVENT
            UID:1234idontcare-/calendar@localhost
            SUMMARY:Something else
            DTSTART;VALUE=DATE:20030904
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        request = RequestStub("http://localhost/calendar", method="PUT",
                              headers={"Content-Type": "text/calendar"},
                              body=calendar)
        cal = self._create()
        cal.addEvent(CalendarEvent(datetime.date(2003, 9, 1),
                                   datetime.timedelta(1),
                                   "Delete me"))
        result = self.view.render(request)
        self.assertEquals(result, "Calendar imported")
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'], "text/plain")
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
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['Content-Type'], "text/plain")

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
            UID:school-period-/calendar@localhost
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


class TestAllCalendarsView(XMLCompareMixin, unittest.TestCase):

    def createApp(self):
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Group, Person
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['groups'].new("students", title="Students")
        app['groups'].new("teachers", title="Teachers")
        app['persons'].new("john", title="John")
        app['persons'].new("smith", title="Smith")
        return app

    def test(self):
        from schooltool.views.cal import AllCalendarsView
        context = self.createApp()
        view = AllCalendarsView(context)
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
                <li><a href="http://localhost:8080/groups/students/calendar">
                    Students</a></li>
                <li><a href="http://localhost:8080/groups/teachers/calendar">
                    Teachers</a></li>
              </ul>
              <h2>Persons</h2>
              <ul>
                <li><a href="http://localhost:8080/persons/john/calendar">
                    John</a></li>
                <li><a href="http://localhost:8080/persons/smith/calendar">
                    Smith</a></li>
              </ul>
            </body>
            </html>
        """
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['Content-Type'],
                          "text/html; charset=UTF-8")
        self.assertEqualsXML(result, expected)


class TestModuleSetup(RegistriesSetupMixin, unittest.TestCase):

    def test(self):
        from schooltool.interfaces import ISchooldayModel, ICalendar
        from schooltool.views.cal import SchooldayModelCalendarView
        from schooltool.views.cal import CalendarView
        from schooltool.component import getView
        import schooltool.views.cal
        schooltool.views.cal.setUp()

        def viewClass(iface):
            """Return the view class registered for an interface."""
            cls = type(iface.getName(), (), {})
            obj = cls()
            directlyProvides(obj, iface)
            return getView(obj).__class__

        self.assert_(viewClass(ISchooldayModel) is SchooldayModelCalendarView)
        self.assert_(viewClass(ICalendar) is CalendarView)


def test_suite():
    import schooltool.views.cal
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(schooltool.views.cal))
    suite.addTest(unittest.makeSuite(TestSchooldayModelCalendarView))
    suite.addTest(unittest.makeSuite(TestCalendarReadView))
    suite.addTest(unittest.makeSuite(TestCalendarView))
    suite.addTest(unittest.makeSuite(TestAllCalendarsView))
    suite.addTest(unittest.makeSuite(TestModuleSetup))
    return suite

if __name__ == '__main__':
    unittest.main()
