#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Unit tests for RESTive term views.

$Id: test_app.py 3526 2005-04-28 17:16:47Z bskahan $
"""

import unittest
import datetime

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.app.filerepresentation.interfaces import IFileFactory
from zope.app.testing import ztapi, setup
from zope.app.traversing.interfaces import IContainmentRoot

from schooltool.testing.util import QuietLibxml2Mixin
from schooltool.common import dedent


class DatetimeStub:

    def utcnow(self):
        return datetime.datetime(2004, 1, 2, 3, 4, 5)


class TestTermView(QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        setup.setUpTraversal()
        from schooltool.timetable.term import Term, TermContainer
        from schooltool.timetable.rest.term import TermView

        self.terms = TermContainer()
        self.terms["calendar"] =  self.term = Term(
            "Test",
            datetime.date(2003, 9, 1),
            datetime.date(2003, 9, 30))

        directlyProvides(self.terms, IContainmentRoot)

        self.view = TermView(self.term, TestRequest())
        self.view.datetime_hook = DatetimeStub()
        self.setUpLibxml2()

    def tearDown(self):
        setup.placelessTearDown()
        self.tearDownLibxml2()

    def test_get_empty(self):
        self.assertEqual(
            self.view.GET(),
            dedent(u"""
                BEGIN:VCALENDAR
                PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
                VERSION:2.0
                BEGIN:VEVENT
                UID:school-period-/calendar@127.0.0.1
                SUMMARY:School Period
                DTSTART;VALUE=DATE:20030901
                DTEND;VALUE=DATE:20031001
                DTSTAMP:20040102T030405Z
                END:VEVENT
                END:VCALENDAR
            """).replace("\n", "\r\n"))

    def test_get(self):
        self.term.addWeekdays(0, 1, 2, 3, 4) # Mon to Fri
        expected = dedent(u"""
            BEGIN:VCALENDAR
            PRODID:-//SchoolTool.org/NONSGML SchoolTool//EN
            VERSION:2.0
            BEGIN:VEVENT
            UID:school-period-/calendar@127.0.0.1
            SUMMARY:School Period
            DTSTART;VALUE=DATE:20030901
            DTEND;VALUE=DATE:20031001
            DTSTAMP:20040102T030405Z
            END:VEVENT
        """)
        for date in self.term:
            if date.weekday() not in (5, 6):
                s = date.strftime("%Y%m%d")
                expected += dedent("""
                    BEGIN:VEVENT
                    UID:schoolday-%s-/calendar@127.0.0.1
                    SUMMARY:Schoolday
                    DTSTART;VALUE=DATE:%s
                    DTSTAMP:20040102T030405Z
                    END:VEVENT
                """ % (s, s))
        self.assertEqual(
            self.view.GET(),
            (expected + "END:VCALENDAR\n").replace("\n", "\r\n"))


class TestTermFileFactory(QuietLibxml2Mixin, unittest.TestCase):
    def setUp(self):
        from schooltool.timetable.term import TermContainer
        from schooltool.timetable.rest.term import TermFileFactory

        self.terms = TermContainer()
        self.fileFactory = TermFileFactory(self.terms)
        self.setUpLibxml2()


    def test_isDataICal(self):
        self.assert_(self.fileFactory.isDataICal("BEGIN:VCALENDAR"))
        self.assertEqual(self.fileFactory.isDataICal("<foo />"), False)

    def test_callText(self):
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
        # normalize line endings
        calendar = "\r\n".join(calendar.splitlines()) + "\r\n"

        term = self.fileFactory("calendar", "", calendar)

        self.assertEquals(term.title, "calendar")
        self.assertEquals(term.first, datetime.date(2004, 9, 1))
        self.assertEquals(term.last, datetime.date(2004, 9, 30))
        for date in term:
            if date == datetime.date(2004, 9, 12):
                self.assert_(term.isSchoolday(date))
            else:
                self.assert_(not term.isSchoolday(date))

    def test_callXML(self):
        body = dedent("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <title>Test.term!</title>
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
        """)

        term = self.fileFactory("calendar_from_xml", "", body)

        self.assertEquals(term.title, "Test.term!")
        self.assertEquals(term.first, datetime.date(2003, 9, 1))
        self.assertEquals(term.last, datetime.date(2003, 9, 7))
        schooldays = []
        for date in term:
            if term.isSchoolday(date):
                schooldays.append(date)
        expected = [datetime.date(2003, 9, d) for d in 1, 2, 4, 5]
        self.assertEquals(schooldays, expected)

    def test_invalid_name(self):
        from schooltool.app.rest.errors import RestError
        self.assertRaises(RestError, self.fileFactory, "foo.bar", "", "")


class TestTermFile(QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        from schooltool.timetable.term import Term, TermContainer
        from schooltool.timetable.interfaces import ITermContainer
        from schooltool.timetable.rest.term import TermFileFactory
        from schooltool.timetable.rest.term import TermFile

        ztapi.provideAdapter(ITermContainer, IFileFactory, TermFileFactory)

        self.terms = TermContainer()
        self.terms["calendar"] =  self.term = Term(
            "Test",
            datetime.date(2003, 9, 1),
            datetime.date(2003, 9, 30))


        self.file = TermFile(self.term)

        self.setUpLibxml2()

    def test_write(self):
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
        # normalize line endings
        calendar = "\r\n".join(calendar.splitlines()) + "\r\n"

        self.file.write(calendar)

        self.assertEquals(self.term.first, datetime.date(2004, 9, 1))
        self.assertEquals(self.term.last, datetime.date(2004, 9, 30))
        for date in self.term:
            if date == datetime.date(2004, 9, 12):
                self.assert_(self.term.isSchoolday(date))
            else:
                self.assert_(not self.term.isSchoolday(date))

    def test_write_xml(self):
        body = dedent("""
            <schooldays xmlns="http://schooltool.org/ns/schooldays/0.1"
                        first="2003-09-01" last="2003-09-07">
              <title>A super title!</title>
              <daysofweek>Monday Tuesday Wednesday Thursday Friday</daysofweek>
              <holiday date="2003-09-03">Holiday</holiday>
              <holiday date="2003-09-06">Holiday</holiday>
              <holiday date="2003-09-23">Holiday</holiday>
            </schooldays>
        """)

        self.file.write(body)

        self.assertEquals(self.term.first, datetime.date(2003, 9, 1))
        self.assertEquals(self.term.last, datetime.date(2003, 9, 7))
        schooldays = []
        for date in self.term:
            if self.term.isSchoolday(date):
                schooldays.append(date)
        expected = [datetime.date(2003, 9, d) for d in 1, 2, 4, 5]
        self.assertEquals(schooldays, expected)


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestTermView),
        unittest.makeSuite(TestTermFileFactory),
        unittest.makeSuite(TestTermFile)
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
