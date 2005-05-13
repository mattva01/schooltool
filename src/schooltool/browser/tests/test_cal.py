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
Tests for SchoolTool-specific calendar views.

$Id$
"""

import unittest
from datetime import date, timedelta, time
from zope.testing import doctest
from zope.app.tests import setup, ztapi
from zope.publisher.browser import TestRequest
from schoolbell.app.browser.tests.setup import setUp, tearDown

from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.timetable import SequentialDaysTimetableModel


class TestDailyCalendarView(unittest.TestCase):

    def setUp(self):
        from schooltool.app import getPersonPreferences
        from schooltool.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        # set up adaptation (the view checks user preferences)
        setup.placelessSetUp()
        setup.setUpAnnotations()
        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)


        # set up the site
        from schooltool.app import SchoolToolApplication, Person
        app = SchoolToolApplication()
        from zope.app.component.site import LocalSiteManager
        app.setSiteManager(LocalSiteManager(app))
        from zope.app.component.hooks import setSite
        setSite(app)
        self.person = app['persons']['person'] = Person('person')

        # set up the timetable schema
        days = ['A', 'B', 'C']
        schema = self.createSchema(days,
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'])
        template = SchooldayTemplate()
        template.add(SchooldayPeriod('1', time(9, 0), timedelta(hours=1)))
        template.add(SchooldayPeriod('2', time(10, 15), timedelta(hours=1)))
        template.add(SchooldayPeriod('3', time(11, 30), timedelta(hours=1)))
        template.add(SchooldayPeriod('4', time(12, 30), timedelta(hours=1)))
        schema.model = SequentialDaysTimetableModel(days, {None: template})

        app.timetableSchemaService['default'] = schema

        # set up terms
        from schooltool.timetable import Term
        app['terms']['term'] = term = Term("Some term", date(2004, 9, 1),
                                           date(2004, 12, 31))
        term.add(date(2004, 11, 5))

    def tearDown(self):
        setup.placelessTearDown()

    def createSchema(self, days, *periods_for_each_day):
        """Create a timetable schema."""
        from schooltool.timetable import Timetable
        from schooltool.timetable import TimetableDay
        schema = Timetable(days)
        for day, periods in zip(days, periods_for_each_day):
            schema[day] = TimetableDay(list(periods))
        return schema

    def test_calendarRows(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.common import parse_datetime

        request = TestRequest()
        request.setPrincipal(self.person)
        view = DailyCalendarView(self.person.calendar, request)
        view.cursor = date(2004, 11, 5)

        result = list(view.calendarRows())

        def dt(timestr):
            return parse_datetime('2004-11-05 %s:00' % timestr)

        expected = [("8:00", dt('08:00'), timedelta(hours=1)),
                    ("1", dt('09:00'), timedelta(hours=1)),
                    ("10:00", dt('10:00'), timedelta(minutes=15)),
                    ("2", dt('10:15'), timedelta(hours=1)),
                    ("11:15", dt('11:15'), timedelta(minutes=15)),
                    ("3", dt('11:30'), timedelta(hours=1)),
                    ("4", dt('12:30'), timedelta(hours=1)),
                    ("13:30", dt('13:30'), timedelta(minutes=30)),
                    ("14:00", dt('14:00'), timedelta(hours=1)),
                    ("15:00", dt('15:00'), timedelta(hours=1)),
                    ("16:00", dt('16:00'), timedelta(hours=1)),
                    ("17:00", dt('17:00'), timedelta(hours=1)),
                    ("18:00", dt('18:00'), timedelta(hours=1))]

        self.assertEquals(result, expected)

    def test_calendarRows_no_periods(self):
        from schooltool.browser.cal import DailyCalendarView
        from schooltool.common import parse_datetime
        from schooltool.app import getPersonPreferences

        prefs = getPersonPreferences(self.person)
        prefs.cal_periods = False # do not show periods
        request = TestRequest()
        request.setPrincipal(self.person)
        view = DailyCalendarView(self.person.calendar, request)
        view.cursor = date(2004, 11, 5)

        result = list(view.calendarRows())

        def dt(timestr):
            return parse_datetime('2004-11-05 %s:00' % timestr)

        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDailyCalendarView))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
