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


class TestSchooldayModelCalendarView(unittest.TestCase):

    def setUp(self):
        from schooltool.cal import SchooldayModel
        from schooltool.views.cal import SchooldayModelCalendarView
        self.sm = SchooldayModel(datetime.date(2003, 9, 1),
                                 datetime.date(2003, 10, 1))
        setPath(self.sm, '/calendar')
        self.view = SchooldayModelCalendarView(self.sm)
        self.request = RequestStub("http://localhost/calendar")

    def do_test(self, expected):
        result = self.view.render(self.request)
        expected = "\r\n".join(expected.splitlines()) # normalize line endings
        self.assertEquals(self.request.headers['Content-Type'],
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
            END:VEVENT
        """)
        for date in daterange(self.sm.start, self.sm.end):
            if date.weekday() not in (5, 6):
                s = date.strftime("%Y%m%d")
                expected += dedent("""
                    BEGIN:VEVENT
                    UID:schoolday-%s-/calendar@localhost
                    SUMMARY:Schoolday
                    DTSTART;VALUE=DATE:%s
                    END:VEVENT
                """ % (s, s))
        self.do_test(expected + "END:VCALENDAR")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchooldayModelCalendarView))
    return suite

if __name__ == '__main__':
    unittest.main()
