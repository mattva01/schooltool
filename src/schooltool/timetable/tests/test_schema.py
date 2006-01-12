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
Unit tests for the schooltool.timetable.schema module.

$Id: test_timetable.py 4822 2005-08-19 01:35:11Z srichter $
"""

import unittest
from datetime import date
from sets import Set

from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.app.testing.setup import placefulSetUp, placefulTearDown

from schooltool.timetable.interfaces import ITimetableSchema
from schooltool.timetable.interfaces import ITimetableSchemaContainer
from schooltool.timetable.interfaces import ITimetableSchemaDay
from schooltool.timetable.interfaces import ITimetableSchemaWrite
from schooltool.timetable.schema import TimetableSchema
from schooltool.timetable.schema import TimetableSchemaContainer
from schooltool.timetable.schema import TimetableSchemaDay
from schooltool.timetable.schema import getPeriodsForDay

from schooltool.testing import setup


class DayStub:
    implements(ITimetableSchemaDay)


class TestTimetableSchemaDay(unittest.TestCase):

    def test(self):
        td = TimetableSchemaDay(['a', 'b', 'c'])
        verifyObject(ITimetableSchemaDay, td)

        self.assertEquals(list(td.periods), ['a', 'b', 'c'])
        self.assertEquals(list(td.keys()), ['a', 'b', 'c'])
        self.assertEquals(list(td.items()), [('a', Set()),
                                             ('b', Set()),
                                             ('c', Set())])
        self.assertEquals(td['b'], Set())
        self.assertRaises(KeyError, td.__getitem__, 'x')


class TestTimetableSchema(unittest.TestCase):

    def test_interface(self):
        t = TimetableSchema(['one', 'two'])
        verifyObject(ITimetableSchema, t)
        verifyObject(ITimetableSchemaWrite, t)

    def test_title(self):
        days = ('Mo', 'Tu', 'We', 'Th', 'Fr')
        t = TimetableSchema(days, title="A Schema")
        self.assertEqual(t.title, "A Schema")
        t = TimetableSchema(days)
        self.assertEqual(t.title, "Schema")

    def test_keys(self):
        days = ('Mo', 'Tu', 'We', 'Th', 'Fr')
        t = TimetableSchema(days)
        self.assertEqual(t.keys(), list(days))

    def test_getitem_setitem(self):
        days = ('Mo', 'Tu', 'We', 'Th', 'Fr')
        t = TimetableSchema(days)
        self.assertRaises(KeyError, t.__getitem__, "Mo")
        self.assertRaises(KeyError, t.__getitem__, "What!?")
        self.assertRaises(TypeError, t.__setitem__, "Mo", object())
        self.assertRaises(ValueError, t.__setitem__, "Mon", DayStub())
        monday = DayStub()
        t["Mo"] = monday
        self.assertEqual(t["Mo"], monday)

    def test_items(self):
        days = ('Day 1', 'Day 2', 'Day 3')
        t = TimetableSchema(days)
        t["Day 1"] = day1 = DayStub()
        t["Day 2"] = day2 = DayStub()
        self.assertRaises(KeyError, t.items)
        t["Day 3"] = day3 = DayStub()
        self.assertEqual(t.items(),
                         [("Day 1", day1), ("Day 2", day2), ("Day 3", day3)])

    def test_createTimetable(self):
        days = ('A', 'B')
        periods1 = ('Green', 'Blue')
        periods2 = ('Green', 'Red', 'Yellow')
        tts = TimetableSchema(days)
        tts["A"] = TimetableSchemaDay(periods1)
        tts["B"] = TimetableSchemaDay(periods2, homeroom_period_id='Yellow')

        tt = tts.createTimetable()
        self.assertEquals(tt.day_ids, tts.day_ids)
        self.assert_(tt.model is tts.model)
        for day_id in tt.day_ids:
            day = tt[day_id]
            day2 = tts[day_id]
            self.assert_(day is not day2)
            self.assertEquals(day.periods, day2.periods)
            self.assertEquals(day.homeroom_period_id, day2.homeroom_period_id)
            for period in day.periods:
                self.assertEquals(list(day[period]), [])

    def test_equality(self):
        days = ('A', 'B')
        periods1 = ('Green', 'Blue')
        periods2 = ('Green', 'Red', 'Yellow')
        tts = TimetableSchema(days)
        tts["A"] = TimetableSchemaDay(periods1)
        tts["B"] = TimetableSchemaDay(periods2)
        self.assertEquals(tts, tts)
        self.assertNotEquals(tts, None)

        # Same thing
        tts2 = TimetableSchema(days)
        tts2["A"] = TimetableSchemaDay(periods1)
        tts2["B"] = TimetableSchemaDay(periods2)
        self.assertEquals(tts, tts2)

        # Swap periods in days
        tts3 = TimetableSchema(days)
        tts3["A"] = TimetableSchemaDay(periods2)
        tts3["B"] = TimetableSchemaDay(periods1)
        self.assertNotEquals(tts, tts3)

        # Add an extra day
        tts4 = TimetableSchema(days + ('C', ))
        tts4["A"] = TimetableSchemaDay(periods1)
        tts4["B"] = TimetableSchemaDay(periods1)
        tts4["C"] = TimetableSchemaDay(periods1)
        self.assertNotEquals(tts, tts4)

        # Change the model
        tts5 = TimetableSchema(days)
        tts5.model = object()
        tts5["A"] = TimetableSchemaDay(periods1)
        tts5["B"] = TimetableSchemaDay(periods2)
        self.assertNotEquals(tts, tts5)

        # Different homeroom period
        tts6 = TimetableSchema(days)
        tts6["A"] = TimetableSchemaDay(periods1)
        tts6["B"] = TimetableSchemaDay(periods2, homeroom_period_id='Red')
        self.assertNotEquals(tts, tts6)



class TestTimetableSchemaContainer(unittest.TestCase):

    def test_interface(self):
        service = TimetableSchemaContainer()
        verifyObject(ITimetableSchemaContainer, service)

    def test(self):
        service = TimetableSchemaContainer()
        self.assertEqual(list(service.keys()), [])

        tt = TimetableSchema(("A", "B"))
        tt["A"] = TimetableSchemaDay(("Green", "Blue"))
        tt["B"] = TimetableSchemaDay(("Red", "Yellow"))

        service["super"] = tt
        self.assertEqual(list(service.keys()), ["super"])
        self.assertEqual(service["super"].__name__, "super")
        self.assert_(service["super"].__parent__ is service)
        self.assertEqual(service.default_id, "super")

        del service["super"]
        self.assertRaises(KeyError, service.__getitem__, "super")
        self.assertEqual(list(service.keys()), [])
        self.assertEqual(service.default_id, None)

        self.assertRaises(ValueError, setattr, service, 'default_id', 'nosuch')


class TestGetPeriodsForDay(unittest.TestCase):

    def setUp(self):
        placefulSetUp()
        app = setup.setupSchoolToolSite()

        from schooltool.timetable.term import Term
        self.term1 = Term('Sample', date(2004, 9, 1), date(2004, 12, 20))
        self.term2 = Term('Sample', date(2005, 1, 1), date(2005, 6, 1))
        app["terms"]['2004-fall'] = self.term1
        app["terms"]['2005-spring'] = self.term2

        class TimetableModelStub:
            def periodsInDay(self, schooldays, ttschema, date):
                return 'periodsInDay', schooldays, ttschema, date

        tt = TimetableSchema([])
        tt.model = TimetableModelStub()
        self.tt = tt
        app["ttschemas"]['default'] = tt
        self.app = app

    def tearDown(self):
        placefulTearDown()

    def test_getPeriodsForDay(self):
        # A white-box test: we delegate to ITimetableModel.periodsInDay
        # with the correct arguments
        self.assertEquals(getPeriodsForDay(date(2004, 10, 14)),
                          ('periodsInDay', self.term1, self.tt,
                           date(2004, 10, 14)))

        # However, if there is no time period, we return []
        self.assertEquals(getPeriodsForDay(date(2005, 10, 14)),
                          [])

        # If there is no timetable schema, we return []
        self.app["ttschemas"].default_id = None
        self.assertEquals(getPeriodsForDay(date(2004, 10, 14)),
                          [])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableSchema))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaDay))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaContainer))
    suite.addTest(unittest.makeSuite(TestGetPeriodsForDay))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
