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
Unit tests for the schooltool.timetable.model module.

$Id$
"""

import calendar
import unittest
from datetime import date, time, timedelta, datetime
from pprint import pformat

from pytz import UTC
from zope.interface.verify import verifyObject
from zope.app.testing.placelesssetup import PlacelessSetup
from zope.app.testing import ztapi

from schooltool.app.rest.testing import NiceDiffsMixin
from schooltool.testing.util import diff
from schooltool.timetable.tests.test_timetable import TermStub


class TimetablePhysicallyLocatableAdapterStub:
    def __init__(self, tt):
        self.tt = tt
    def getPath(self):
        return '/tt/%s' % id(self.tt)


class BaseTestTimetableModel:

    def extractCalendarEvents(self, cal, daterange):
        result = []
        for d in daterange:
            dt = datetime.combine(d, time(0, 0, tzinfo=UTC))
            dt1 = dt + d.resolution
            calday = cal.expand(dt, dt1)
            events = []
            for event in calday:
                events.append(event)
            result.append(dict([(event.dtstart, event.title)
                           for event in events]))
        return result


class SequentialTestSetupMixin:

    def createTimetable(self):
        """Create a simple timetable.

              Period | Day A    Day B
              ------ : -------  ---------
              Green  : English  Biology
              Blue   : Math     Geography

        """
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.timetable import TimetableActivity
        #from schooltool.component import getOptions
        tt = Timetable(('A', 'B'))
        #setPath(tt, '/path/to/tt')
        #getOptions(tt).timetable_privacy = 'public'
        periods = ('Green', 'Blue')
        tt["A"] = TimetableDay(periods)
        tt["B"] = TimetableDay(periods)
        tt["A"].add("Green", TimetableActivity("English"))
        tt["A"].add("Blue", TimetableActivity("Math"))
        tt["B"].add("Green", TimetableActivity("Biology"))
        tt["B"].add("Blue", TimetableActivity("Geography"))
        return tt


class TestSequentialDaysTimetableModel(PlacelessSetup,
                                       NiceDiffsMixin,
                                       unittest.TestCase,
                                       BaseTestTimetableModel,
                                       SequentialTestSetupMixin):

    def setUp(self):
        from zope.app.traversing.interfaces import IPhysicallyLocatable
        from schooltool.timetable.interfaces import ITimetable
        PlacelessSetup.setUp(self)

        ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
                             TimetablePhysicallyLocatableAdapterStub)

    def createModel(self):
        """Create a simple sequential timetable model.

        Days A and B are alternated.

        Green period occurs at 9:00-10:30 on all days.
        Blue period occurs at 11:00-12:30 on all days except Fridays, when it
        occurs at 10:30-12:00.
        """
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
        from schooltool.timetable import SequentialDaysTimetableModel

        t, td = time, timedelta
        template1 = SchooldayTemplate()
        template1.add(SchooldayPeriod('Green', t(9, 0), td(minutes=90)))
        template1.add(SchooldayPeriod('Blue', t(11, 0), td(minutes=90)))
        template2 = SchooldayTemplate()
        template2.add(SchooldayPeriod('Green', t(9, 0), td(minutes=90)))
        template2.add(SchooldayPeriod('Blue', t(10, 30), td(minutes=90)))

        model = SequentialDaysTimetableModel(("A", "B"),
                                             {None: template1,
                                              calendar.FRIDAY: template2})
        return model

    def test_interface(self):
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable.interfaces import IWeekdayBasedTimetableModel

        model = SequentialDaysTimetableModel(("A","B"), {None: 3})
        verifyObject(IWeekdayBasedTimetableModel, model)

    def test_eq(self):
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable import WeeklyTimetableModel
        model = SequentialDaysTimetableModel(("A","B"), {1: 2, None: 3})
        model2 = SequentialDaysTimetableModel(("A","B"), {1: 2, None: 3})
        model3 = WeeklyTimetableModel(("A","B"), {1: 2, None: 3})
        model4 = SequentialDaysTimetableModel(("A"), {1: 2, None: 3})

        self.assertEqual(model, model2)
        self.assertNotEqual(model2, model3)
        self.assertNotEqual(model2, model4)
        self.assert_(not model2 != model)

        model.exceptionDays[date(2005, 7, 7)] = object()
        self.assertNotEqual(model, model2)

        del model.exceptionDays[date(2005, 7, 7)]
        self.assertEqual(model, model2)
        model.exceptionDayIds[date(2005, 7, 7)] = 'Monday'
        self.assertNotEqual(model, model2)

    def test_createCalendar(self):
        from schooltool.calendar.interfaces import ICalendar

        tt = self.createTimetable()
        model = self.createModel()
        schooldays = TermStub()

        cal = model.createCalendar(schooldays, tt)
        verifyObject(ICalendar, cal)

        # The calendar is functionally derived, therefore everything
        # in it (including unique calendar event IDs) must not change
        # if it is regenerated.
        cal2 = model.createCalendar(schooldays, tt)
        self.assertEquals(list(cal), list(cal2))

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [{datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 20, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 21, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 10, 30, tzinfo=UTC): "Geography"},
                    {}, {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 25, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 26, 11, 0, tzinfo=UTC): "Math"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_createCalendar_exceptionDays(self):
        from schooltool.timetable.term import Term
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod

        tt = self.createTimetable()
        model = self.createModel()
        schooldays = Term('Sample', date(2003, 11, 20), date(2003, 11, 26))
        schooldays.addWeekdays(0, 1, 2, 3, 4, 5) # Mon-Sat

        # Add an exception day
        exception = SchooldayTemplate()
        t, td = time, timedelta
        exception.add(SchooldayPeriod('Green', t(6, 0), td(minutes=90)))
        exception.add(SchooldayPeriod('Blue', t(8, 0), td(minutes=90)))
        model.exceptionDays[date(2003, 11, 22)] = exception

        # Run the calendar generation
        cal = model.createCalendar(schooldays, tt)

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [{datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 20, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 21, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 10, 30, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 22, 6, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 22, 8, 0, tzinfo=UTC): "Math"},
                    {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 25, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 26, 11, 0, tzinfo=UTC): "Geography"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_schooldayStrategy_getDayId(self):
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable.term import Term
        from schooltool.timetable import SchooldayTemplate

        term = Term('Sample', date(2005, 6, 27), date(2005, 7, 10))
        term.addWeekdays(0, 1, 2, 3, 4)

        template = SchooldayTemplate()
        model = SequentialDaysTimetableModel(('A', 'B', 'C'), {None: template})

        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen) for d in term
                if term.isSchoolday(d)]

        self.assertEqual(days, ['A', 'B', 'C', 'A', 'B',
                                'C', 'A', 'B', 'C', 'A'])

        self.assertEqual(model.getDayId(term, date(2005, 6, 27)), 'A')
        self.assertEqual(model.getDayId(term, date(2005, 6, 29)), 'C')
        self.assertEqual(model.getDayId(term, date(2005, 7, 1)), 'B')

        term.add(date(2005, 7, 2))
        model.exceptionDayIds[date(2005, 7, 2)] = "X"
        model.exceptionDayIds[date(2005, 7, 4)] = "Y"
        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen)
                for d in term
                if term.isSchoolday(d)]

        # Effectively, exception day ids get inserted into the normal
        # sequence of day ids, instead of replacing some day ids.
        self.assertEqual(days, ['A', 'B', 'C', 'A', 'B', 'X',
                                'Y', 'C', 'A', 'B', 'C'])


    def test_periodsInDay_originalPeriodsInDay(self):
        from schooltool.calendar.interfaces import ICalendar
        from schooltool.timetable import SchooldayPeriod
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod

        tt = self.createTimetable()
        model = self.createModel()
        schooldays = TermStub()

        # Add an exception day
        exception = SchooldayTemplate()
        t, td = time, timedelta
        exception.add(SchooldayPeriod('Green', t(6, 0), td(minutes=90)))
        exception.add(SchooldayPeriod('Blue', t(8, 0), td(minutes=90)))
        model.exceptionDays[date(2003, 11, 21)] = exception

        self.assertEqual(
            model.periodsInDay(schooldays, tt, date(2003, 11, 20)),
            [SchooldayPeriod("Green", time(9, 0), timedelta(minutes=90)),
             SchooldayPeriod("Blue", time(11, 0), timedelta(minutes=90))])

        self.assertEqual(
            model.originalPeriodsInDay(schooldays, tt, date(2003, 11, 21)),
            [SchooldayPeriod("Green", time(9, 0), timedelta(minutes=90)),
             SchooldayPeriod("Blue", time(10, 30), timedelta(minutes=90))])

        self.assertEqual(
            model.periodsInDay(schooldays, tt, date(2003, 11, 21)),
            [SchooldayPeriod("Green", time(6, 0), timedelta(minutes=90)),
             SchooldayPeriod("Blue", time(8, 0), timedelta(minutes=90))])

        self.assertEqual(
            model.periodsInDay(schooldays, tt, date(2003, 11, 22)),
            [])


class TestSequentialDayIdBasedTimetableModel(PlacelessSetup,
                                             unittest.TestCase,
                                             SequentialTestSetupMixin,
                                             BaseTestTimetableModel):

    def setUp(self):
        from zope.app.traversing.interfaces import IPhysicallyLocatable
        from schooltool.timetable.interfaces import ITimetable
        PlacelessSetup.setUp(self)

        ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
                             TimetablePhysicallyLocatableAdapterStub)

    def createDayTemplates(self):
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
        t, td = time, timedelta
        template1 = SchooldayTemplate()
        template1.add(SchooldayPeriod('Green', t(9, 0), td(minutes=90)))
        template1.add(SchooldayPeriod('Blue', t(11, 0), td(minutes=90)))
        template2 = SchooldayTemplate()
        template2.add(SchooldayPeriod('Green', t(11, 0), td(minutes=90)))
        template2.add(SchooldayPeriod('Blue', t(13, 0), td(minutes=90)))
        return template1, template2

    def test_createCalendar(self):
        from schooltool.calendar.interfaces import ICalendar
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
        from schooltool.timetable.model import \
             SequentialDayIdBasedTimetableModel

        tt = self.createTimetable()
        template1, template2 = self.createDayTemplates()

        model = SequentialDayIdBasedTimetableModel(('A', 'B'),
                                                   {'A': template1,
                                                    'B': template2})
        schooldays = TermStub()

        cal = model.createCalendar(schooldays, tt)
        verifyObject(ICalendar, cal)

        # The calendar is functionally derived, therefore everything
        # in it (including unique calendar event IDs) must not change
        # if it is regenerated.
        cal2 = model.createCalendar(schooldays, tt)
        self.assertEquals(list(cal), list(cal2))

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [{datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 20, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 21, 11, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 21, 13, 0, tzinfo=UTC): "Geography"},
                    {}, {},
                    {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 24, 11, 0, tzinfo=UTC): "Math"},
                    {datetime(2003, 11, 25, 11, 0, tzinfo=UTC): "Biology",
                     datetime(2003, 11, 25, 13, 0, tzinfo=UTC): "Geography"},
                    {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "English",
                     datetime(2003, 11, 26, 11, 0, tzinfo=UTC): "Math"}]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_verification(self):
        from schooltool.timetable.model import \
             SequentialDayIdBasedTimetableModel

        tt = self.createTimetable()
        template1, template2 = self.createDayTemplates()

        self.assertRaises(AssertionError,
                          SequentialDayIdBasedTimetableModel,
                          ('A', 'B'),
                          {'A': template1,'Z': template2})

        SequentialDayIdBasedTimetableModel(
            ('A', 'Z'),
            {'A': template1, 'Z': template2})

    def test__getUsualTemplateForDay(self):
        from schooltool.timetable.model import \
             SequentialDayIdBasedTimetableModel

        tt = self.createTimetable()
        template1, template2 = self.createDayTemplates()
        model = SequentialDayIdBasedTimetableModel(
            ('A', 'Z'),
            {'A': template1, 'Z': template2})
        self.assertEqual(model._getUsualTemplateForDay(date(2005, 7, 20), 'A'),
                         template1)
        self.assertEqual(model._getUsualTemplateForDay(date(2005, 7, 21), 'Z'),
                         template2)
        self.assertRaises(KeyError, model._getUsualTemplateForDay,
                          date(2005, 7, 21), 'B')


class TestWeeklyTimetableModel(PlacelessSetup,
                               unittest.TestCase,
                               BaseTestTimetableModel):

    def setUp(self):
        from zope.app.traversing.interfaces import IPhysicallyLocatable
        from schooltool.timetable.interfaces import ITimetable
        PlacelessSetup.setUp(self)
        ztapi.provideAdapter(ITimetable, IPhysicallyLocatable,
                             TimetablePhysicallyLocatableAdapterStub)

    def test(self):
        from schooltool.timetable import WeeklyTimetableModel
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.timetable import TimetableActivity
        from schooltool.timetable.term import Term
        from schooltool.timetable.interfaces import IWeekdayBasedTimetableModel

        days = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
        tt = Timetable(days)

        periods = ('1', '2', '3', '4')
        for day_id in days:
            tt[day_id] = TimetableDay(periods)

        tt["Monday"].add("1", TimetableActivity("English"))
        tt["Monday"].add("2", TimetableActivity("History"))
        tt["Monday"].add("3", TimetableActivity("Biology"))
        tt["Monday"].add("4", TimetableActivity("Physics"))

        tt["Tuesday"].add("1", TimetableActivity("Geography"))
        tt["Tuesday"].add("2", TimetableActivity("Math"))
        tt["Tuesday"].add("3", TimetableActivity("English"))
        tt["Tuesday"].add("4", TimetableActivity("Music"))

        tt["Wednesday"].add("1", TimetableActivity("English"))
        tt["Wednesday"].add("2", TimetableActivity("History"))
        tt["Wednesday"].add("3", TimetableActivity("Biology"))
        tt["Wednesday"].add("4", TimetableActivity("Physics"))

        tt["Thursday"].add("1", TimetableActivity("Chemistry"))
        tt["Thursday"].add("2", TimetableActivity("English"))
        tt["Thursday"].add("3", TimetableActivity("English"))
        tt["Thursday"].add("4", TimetableActivity("Math"))

        tt["Friday"].add("1", TimetableActivity("Geography"))
        tt["Friday"].add("2", TimetableActivity("Drawing"))
        tt["Friday"].add("4", TimetableActivity("Math"))

        t, td = time, timedelta
        template = SchooldayTemplate()
        template.add(SchooldayPeriod('1', t(9, 0), td(minutes=45)))
        template.add(SchooldayPeriod('2', t(9, 50), td(minutes=45)))
        template.add(SchooldayPeriod('3', t(10, 50), td(minutes=45)))
        template.add(SchooldayPeriod('4', t(12, 0), td(minutes=45)))

        model = WeeklyTimetableModel(day_templates={None: template})
        verifyObject(IWeekdayBasedTimetableModel, model)

        # Add an exception day
        exception = SchooldayTemplate()
        t, td = time, timedelta
        exception.add(SchooldayPeriod('1', t(6, 0), td(minutes=45)))
        exception.add(SchooldayPeriod('2', t(7, 0), td(minutes=45)))
        exception.add(SchooldayPeriod('3', t(8, 0), td(minutes=45)))
        exception.add(SchooldayPeriod('4', t(9, 0), td(minutes=45)))
        model.exceptionDays[date(2003, 11, 22)] = exception
        model.exceptionDayIds[date(2003, 11, 22)] = "Monday"

        schooldays = Term('Sample', date(2003, 11, 20), date(2003, 11, 26))
        schooldays.addWeekdays(0, 1, 2, 3, 4, 5) # Mon-Sat

        cal = model.createCalendar(schooldays, tt)

        result = self.extractCalendarEvents(cal, schooldays)

        expected = [
            {datetime(2003, 11, 20, 9, 0, tzinfo=UTC): "Chemistry",
             datetime(2003, 11, 20, 9, 50, tzinfo=UTC): "English",
             datetime(2003, 11, 20, 10, 50, tzinfo=UTC): "English",
             datetime(2003, 11, 20, 12, 00, tzinfo=UTC): "Math"},
            {datetime(2003, 11, 21, 9, 0, tzinfo=UTC): "Geography",
             datetime(2003, 11, 21, 9, 50, tzinfo=UTC): "Drawing",
             # skip! datetime(2003, 11, 21, 10, 50): "History",
             datetime(2003, 11, 21, 12, 00, tzinfo=UTC): "Math"},
            # An exceptional working Saturday, with a Monday's timetable
            {datetime(2003, 11, 22, 6, 0, tzinfo=UTC): "English",
             datetime(2003, 11, 22, 7, 0, tzinfo=UTC): "History",
             datetime(2003, 11, 22, 8, 0, tzinfo=UTC): "Biology",
             datetime(2003, 11, 22, 9, 0, tzinfo=UTC): "Physics"},
            {},
            {datetime(2003, 11, 24, 9, 0, tzinfo=UTC): "English",
             datetime(2003, 11, 24, 9, 50, tzinfo=UTC): "History",
             datetime(2003, 11, 24, 10, 50, tzinfo=UTC): "Biology",
             datetime(2003, 11, 24, 12, 00, tzinfo=UTC): "Physics"},
            {datetime(2003, 11, 25, 9, 0, tzinfo=UTC): "Geography",
             datetime(2003, 11, 25, 9, 50, tzinfo=UTC): "Math",
             datetime(2003, 11, 25, 10, 50, tzinfo=UTC): "English",
             datetime(2003, 11, 25, 12, 00, tzinfo=UTC): "Music"},
            {datetime(2003, 11, 26, 9, 0, tzinfo=UTC): "English",
             datetime(2003, 11, 26, 9, 50, tzinfo=UTC): "History",
             datetime(2003, 11, 26, 10, 50, tzinfo=UTC): "Biology",
             datetime(2003, 11, 26, 12, 00, tzinfo=UTC): "Physics"},
            ]

        self.assertEqual(expected, result,
                         diff(pformat(expected), pformat(result)))

    def test_not_enough_days(self):
        from schooltool.timetable import WeeklyTimetableModel
        from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
        from schooltool.timetable import Timetable, TimetableDay
        template = SchooldayTemplate()
        template.add(SchooldayPeriod('1', time(8), timedelta(minutes=30)))
        days = ["Mon", "Tue"]
        model = WeeklyTimetableModel(days, {None: template})
        day = date(2003, 11, 20)    # 2003-11-20 is a Thursday
        self.assert_(model.schooldayStrategy(day, None) is None)

        tt = Timetable(days)
        for day_id in days:
            tt[day_id] = TimetableDay()
        schooldays = TermStub()
        self.assertEquals(model.periodsInDay(schooldays, tt, day), [])

        model.createCalendar(schooldays, tt)

    def test_schooldayStrategy(self):
        from schooltool.timetable import WeeklyTimetableModel
        from schooltool.timetable.term import Term
        from schooltool.timetable import SchooldayTemplate

        term = Term('Sample', date(2005, 6, 27), date(2005, 7, 10))
        term.addWeekdays(0, 1, 2, 3, 4, 5) # Mon-Sat

        template = SchooldayTemplate()
        model = WeeklyTimetableModel(day_templates={None: template})
        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen) for d in term]

        self.assertEqual(days,
                         ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', None, None,
                          'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', None, None])

        model.exceptionDayIds[date(2005, 7, 2)] = "Wednesday"
        model.exceptionDayIds[date(2005, 7, 4)] = "Thursday"

        dgen = model._dayGenerator()
        days = [model.schooldayStrategy(d, dgen) for d in term]

        self.assertEqual(days,
                         ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', 'Wednesday', None,
                          'Thursday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', None, None])


class TestTimetableCalendarEvent(unittest.TestCase):

    def test(self):
        from schooltool.timetable import TimetableCalendarEvent
        from schooltool.timetable.interfaces import ITimetableCalendarEvent

        period_id = 'Mathematics'
        activity = object()

        ev = TimetableCalendarEvent(datetime(2004, 10, 13, 12),
                                    timedelta(45), "Math",
                                    period_id=period_id, activity=activity)
        verifyObject(ITimetableCalendarEvent, ev)
        for attr in ['period_id', 'activity']:
            self.assertRaises(AttributeError, setattr, ev, attr, object())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSequentialDaysTimetableModel))
    suite.addTest(unittest.makeSuite(TestSequentialDayIdBasedTimetableModel))
    suite.addTest(unittest.makeSuite(TestWeeklyTimetableModel))
    suite.addTest(unittest.makeSuite(TestTimetableCalendarEvent))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
