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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Tests for calendaring related timetabling views.
"""
import unittest
from pytz import timezone
from datetime import timedelta, time, date, datetime

from zope.publisher.browser import TestRequest

from schooltool.common import parse_datetime
from schooltool.person.interfaces import IPersonPreferences
from schooltool.person.person import Person
from schooltool.term.interfaces import ITermContainer
from schooltool.testing.util import NiceDiffsMixin
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.tests.test_cal import dt
from schooltool.app.browser.testing import layeredTestTearDown
from schooltool.app.browser.testing import layeredTestSetup
from schooltool.app.browser.testing import makeLayeredSuite
from schooltool.app.testing import app_functional_layer

try:
    from schooltool.timetable.interfaces import ITimetableSchemaContainer
    from schooltool.timetable.schema import TimetableSchema
    from schooltool.timetable.model import SequentialDaysTimetableModel
    from schooltool.timetable import SchooldaySlot
    from schooltool.timetable import SchooldayTemplate
except:
    pass # XXX: tests not refactored yet

class TestDailyTimetableCalendarRowsView(NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        layeredTestSetup()
        app = ISchoolToolApplication(None)
        self.person = app['persons']['person'] = Person('person')

        # set up schoolyear
        from schooltool.schoolyear.schoolyear import SchoolYear
        from schooltool.schoolyear.interfaces import ISchoolYearContainer
        ISchoolYearContainer(app)['2004'] = SchoolYear("2004", date(2004, 9, 1), date(2004, 12, 31))

        # set up the timetable schema
        days = ['A', 'B', 'C']
        schema = self.createSchema(days,
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'])
        schema.timezone = 'Europe/London'
        template = SchooldayTemplate()
        template.add(SchooldaySlot(time(8, 0), timedelta(hours=1)))
        template.add(SchooldaySlot(time(10, 15), timedelta(hours=1)))
        template.add(SchooldaySlot(time(11, 30), timedelta(hours=1)))
        template.add(SchooldaySlot(time(12, 30), timedelta(hours=2)))
        schema.model = SequentialDaysTimetableModel(days, {None: template})

        ITimetableSchemaContainer(app)['default'] = schema

        # set up terms
        from schooltool.term.term import Term
        terms = ITermContainer(app)
        terms['term'] = term = Term("Some term", date(2004, 9, 1),
                                    date(2004, 12, 31))
        term.add(date(2004, 11, 5))

    def tearDown(self):
        layeredTestTearDown()

    def createSchema(self, days, *periods_for_each_day):
        """Create a timetable schema."""
        from schooltool.timetable.schema import TimetableSchemaDay
        schema = TimetableSchema(days, title="A Schema")
        for day, periods in zip(days, periods_for_each_day):
            schema[day] = TimetableSchemaDay(list(periods))
        return schema

    def test_calendarRows(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView
        from schooltool.app.security import Principal

        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyTimetableCalendarRowsView(ISchoolToolCalendar(self.person), request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        expected = [("1", dt('08:00'), timedelta(hours=1)),
                    ("9:00", dt('09:00'), timedelta(hours=1)),
                    ("10:00", dt('10:00'), timedelta(minutes=15)),
                    ("2", dt('10:15'), timedelta(hours=1)),
                    ("11:15", dt('11:15'), timedelta(minutes=15)),
                    ("3", dt('11:30'), timedelta(hours=1)),
                    ("4", dt('12:30'), timedelta(hours=2)),
                    ("14:30", dt('14:30'), timedelta(minutes=30)),
                    ("15:00", dt('15:00'), timedelta(hours=1)),
                    ("16:00", dt('16:00'), timedelta(hours=1)),
                    ("17:00", dt('17:00'), timedelta(hours=1)),
                    ("18:00", dt('18:00'), timedelta(hours=1))]

        self.assertEquals(result, expected)

    def test_calendarRows_otherTZ(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView
        from schooltool.app.security import Principal

        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyTimetableCalendarRowsView(ISchoolToolCalendar(self.person), request)

        km = timezone('Asia/Kamchatka')
        view.getPersonTimezone = lambda: km

        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        kmdt = lambda arg: km.localize(parse_datetime('2004-11-05 %s:00' %
                                                      arg))

        expected = [('8:00', kmdt('8:00'), timedelta(0, 3600)),
                    ('9:00', kmdt('9:00'), timedelta(0, 3600)),
                    ('10:00', kmdt('10:00'),timedelta(0, 3600)),
                    ('11:00', kmdt('11:00'),timedelta(0, 3600)),
                    ('12:00', kmdt('12:00'),timedelta(0, 3600)),
                    ('13:00', kmdt('13:00'),timedelta(0, 3600)),
                    ('14:00', kmdt('14:00'),timedelta(0, 3600)),
                    ('15:00', kmdt('15:00'),timedelta(0, 3600)),
                    ('16:00', kmdt('16:00'),timedelta(0, 3600)),
                    ('17:00', kmdt('17:00'),timedelta(0, 3600)),
                    ('18:00', kmdt('18:00'),timedelta(0, 3600)),
                    ('19:00', kmdt('19:00'),timedelta(0, 3600)),
                    ('1',  kmdt("20:00"), timedelta(0, 3600)),
                    ('21:00', kmdt("21:00"), timedelta(0, 4500)),
                    ('2',  kmdt("22:15"), timedelta(0, 3600)),
                    ('23:15', kmdt("23:15"), timedelta(0, 900)),
                    ('3', kmdt("23:30"), timedelta(0, 1800))]

        self.assertEquals(result, expected)

    def test_calendarRows_no_periods(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView
        from schooltool.person.preference import getPersonPreferences
        from schooltool.app.security import Principal

        prefs = getPersonPreferences(self.person)
        prefs.cal_periods = False # do not show periods
        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyTimetableCalendarRowsView(ISchoolToolCalendar(self.person), request)

        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)

    def test_calendarRows_default(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView
        request = TestRequest()
        # do not set the principal
        view = DailyTimetableCalendarRowsView(ISchoolToolCalendar(self.person), request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19, events=[]))

        # the default is not to show periods
        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)

    def test_getPersonTimezone(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView

        request = TestRequest()
        view = DailyTimetableCalendarRowsView(ISchoolToolCalendar(self.person), request)

        # when there is no principal - the default timezone should be
        # returned
        self.assertEquals(view.getPersonTimezone(), timezone('UTC'))

    def test_getPeriods(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView

        request = TestRequest()
        view = DailyTimetableCalendarRowsView(ISchoolToolCalendar(self.person), request)

        # if no user has logged we should get an empty list
        self.assertEquals(view.getPeriods(date(2005, 1, 1)), [])

        # same if our user doesn't want to see periods in his calendar
        request.setPrincipal(self.person)
        IPersonPreferences(self.person).cal_periods = False
        self.assertEquals(view.getPeriods(date(2005, 1, 1)), [])

        # if currently logged in user wants to see periods, the
        # parameter is passed to getPeriodsForDay method.
        view.getPeriodsForDay = lambda cursor: ("Yep", cursor)
        IPersonPreferences(self.person).cal_periods = True
        self.assertEquals(view.getPeriods(date(2005, 1, 1)),
                          ("Yep", date(2005, 1, 1)))


class TestDailyTimetableCalendarRowsView_getPeriodsForDay(NiceDiffsMixin,
                                                 unittest.TestCase):

    def setUp(self):
        layeredTestSetup()
        app = ISchoolToolApplication(None)

        from schooltool.schoolyear.schoolyear import SchoolYear
        from schooltool.schoolyear.interfaces import ISchoolYearContainer
        ISchoolYearContainer(app)['2004-2005'] = SchoolYear("2004-2005", date(2004, 9, 1), date(2005, 8, 1))

        from schooltool.term.term import Term
        self.term1 = Term('Sample', date(2004, 9, 1), date(2004, 12, 20))
        self.term1.schooldays = [('A', time(9,0), timedelta(minutes=115)),
                                 ('B', time(11,0), timedelta(minutes=115)),
                                 ('C', time(13,0), timedelta(minutes=115)),
                                 ('D', time(15,0), timedelta(minutes=115)),]
        self.term2 = Term('Sample', date(2005, 1, 1), date(2005, 6, 1))
        self.term2.schooldays = []
        terms = ITermContainer(app)
        terms['2004-fall'] = self.term1
        terms['2005-spring'] = self.term2

        class TimetableModelStub:
            def periodsInDay(this, schooldays, ttschema, date):
                if date not in schooldays:
                    raise "This date is not in the current term!"
                if ttschema == self.tt:
                    return schooldays.schooldays
                else:
                    return []

        tt = TimetableSchema([])
        tt.model = TimetableModelStub()
        tt.timezone = 'Europe/London'
        self.tt = tt
        ttschemas = ITimetableSchemaContainer(app)
        ttschemas['default'] = tt
        self.app = app

    def tearDown(self):
        layeredTestTearDown()

    def test_getPeriodsForDay_sameTZ(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView

        view = DailyTimetableCalendarRowsView(None, TestRequest())
        uk = timezone('Europe/London')
        view.getPersonTimezone = lambda: uk
        delta = timedelta(minutes=115)
        ukdt = lambda *args: uk.localize(datetime(*args))
        self.assertEquals(view.getPeriodsForDay(date(2004, 10, 14)),
                          [('A', ukdt(2004, 10, 14,  9, 0), delta),
                           ('B', ukdt(2004, 10, 14, 11, 0), delta),
                           ('C', ukdt(2004, 10, 14, 13, 0), delta),
                           ('D', ukdt(2004, 10, 14, 15, 0), delta)])

        # However, if there is no time period, we return []
        self.assertEquals(view.getPeriodsForDay(date(2005, 10, 14)),
                          [])

        # If there is no timetable schema, we return []
        ITimetableSchemaContainer(self.app).default_id = None
        self.assertEquals(view.getPeriodsForDay(date(2004, 10, 14)),
                          [])

    def test_getPeriodsForDay_otherTZ(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView

        view = DailyTimetableCalendarRowsView(None, TestRequest())
        # Auckland is 12h ahead of London
        view.getPersonTimezone = lambda: timezone('Pacific/Auckland')
        uk = timezone('Europe/London')

        delta = timedelta(minutes=115)
        td = timedelta
        ukdt = lambda *args: uk.localize(datetime(*args))
        self.assertEquals(view.getPeriodsForDay(date(2004, 10, 14)),
                          [('B', ukdt(2004, 10, 13, 12, 0), td(minutes=55)),
                           ('C', ukdt(2004, 10, 13, 13, 0), delta),
                           ('D', ukdt(2004, 10, 13, 15, 0), delta),
                           ('A', ukdt(2004, 10, 14, 9, 0), delta),
                           ('B', ukdt(2004, 10, 14, 11, 0), td(minutes=60))])

        # However, if there is no time period, we return []
        self.assertEquals(view.getPeriodsForDay(date(2005, 10, 14)),
                          [])

        # If there is no timetable schema, we return []
        ITimetableSchemaContainer(self.app).default_id = None
        self.assertEquals(view.getPeriodsForDay(date(2004, 10, 14)),
                          [])

    def test_getPeriodsForLastDayOfTerm(self):
        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView

        view = DailyTimetableCalendarRowsView(None, TestRequest())
        # We need the start date and the end date different
        view.getPersonTimezone = lambda: timezone('America/Chicago')
        self.assertEquals(view.getPeriodsForDay(date(2005, 6, 1)), [])

    def test_getPeriodsForDayBetweenTerms(self):
        from schooltool.term.term import Term
        term3 = Term('Sample', date(2005, 6, 2), date(2005, 8, 1))
        ITermContainer(self.app)['2005-autumn'] = term3
        term3.schooldays = [('A', time(9,0), timedelta(minutes=115))]
        self.term2.schooldays = [('B', time(10,0), timedelta(minutes=115))]

        from schooltool.timetable.browser.cal import DailyTimetableCalendarRowsView

        view = DailyTimetableCalendarRowsView(None, TestRequest())
        # We need the start date and the end date different
        view.getPersonTimezone = lambda: timezone('America/Chicago')
        self.assertEquals(len(view.getPeriodsForDay(date(2005, 6, 1))), 1)


def test_suite():
    suite = unittest.TestSuite()
    # XXX: tests not refactored yet
    #suite.addTest(makeLayeredSuite(TestDailyTimetableCalendarRowsView,
    #                               app_functional_layer))
    #suite.addTest(makeLayeredSuite(TestDailyTimetableCalendarRowsView_getPeriodsForDay,
    #                               app_functional_layer))
    return suite
