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
from schooltool.views.tests import RequestStub, setPath
from schooltool.tests.helpers import dedent, diff

__metaclass__ = type


class DatetimeStub:

    def utcnow(self):
        return datetime.datetime(2004, 1, 2, 3, 4, 5)


class TestSchooldayModelCalendarView(unittest.TestCase):

    def setUp(self):
        from schooltool.cal import SchooldayModel
        from schooltool.views.cal import SchooldayModelCalendarView
        self.sm = SchooldayModel(datetime.date(2003, 9, 1),
                                 datetime.date(2003, 9, 30))
        setPath(self.sm, '/calendar')
        self.view = SchooldayModelCalendarView(self.sm)
        self.view.datetime_hook = DatetimeStub()

    def do_test(self, expected):
        request = RequestStub("http://localhost/calendar")
        result = self.view.render(request)
        expected = "\r\n".join(expected.splitlines()) # normalize line endings
        self.assertEquals(request.headers['Content-Type'],
                          "text/calendar; charset=UTF-8")
        self.assertEquals(result, expected, "\n" + diff(expected, result))

    def test_get_empty(self):
        self.do_test(dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20030901
            DTEND;VALUE=DATE:20030930
            DTSTAMP:20040102T030405Z
            END:VEVENT
            END:VCALENDAR
        """))

    def test_get(self):
        from schooltool.cal import daterange
        self.sm.addWeekdays(0, 1, 2, 3, 4) # Mon to Fri
        expected = dedent("""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/calendar@localhost
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20030901
            DTEND;VALUE=DATE:20030930
            DTSTAMP:20040102T030405Z
            END:VEVENT
        """)
        for date in daterange(self.sm.first, self.sm.last):
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
        self.do_test(expected + "END:VCALENDAR")

    def test_put(self):
        from schooltool.cal import daterange
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
        for date in daterange(self.sm.first, self.sm.last):
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
            DTEND;VALUE=DATE:20040913
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
            DTSTART;VALUE=DATE:20041001
            END:VEVENT
            END:VCALENDAR
        """)
        calendar = "\r\n".join(calendar.splitlines()) # normalize line endings
        self._test_put_error(calendar,
                     errmsg="School day outside school period")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayModelCalendarView))
    return suite

if __name__ == '__main__':
    unittest.main()
