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
Unit tests for the schooltool.calendar module.

$Id$
"""

import sets
import unittest
import calendar
from datetime import date, timedelta, datetime
from zope.interface.verify import verifyObject
from schooltool.tests.utils import EqualsSortedMixin, LinkStub
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.interfaces import ISchooldayModel


class PersonStub(object):
    pass


class ResourceStub(object):
    pass


class TestSchooldayModel(unittest.TestCase):

    def test_interface(self):
        from schooltool.cal import SchooldayModel
        from schooltool.interfaces import ISchooldayModel, ISchooldayModelWrite
        from schooltool.interfaces import ILocation

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 12, 24))
        verifyObject(ISchooldayModel, cal)
        verifyObject(ISchooldayModelWrite, cal)
        verifyObject(ILocation, cal)

    def testAddRemoveSchoolday(self):
        from schooltool.cal import SchooldayModel

        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 14))

        self.assert_(not cal.isSchoolday(date(2003, 9, 1)))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.isSchoolday, date(2003, 9, 15))

        cal.add(date(2003, 9, 2))
        self.assert_(cal.isSchoolday(date(2003, 9, 2)))
        cal.remove(date(2003, 9, 2))
        self.assert_(not cal.isSchoolday(date(2003, 9, 2)))
        self.assertRaises(ValueError, cal.add, date(2003, 9, 15))
        self.assertRaises(ValueError, cal.remove, date(2003, 9, 15))

    def testReset(self):
        from schooltool.cal import SchooldayModel
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 15))
        cal.addWeekdays(1, 3, 5)

        new_first, new_last = date(2003, 8, 1), date(2003, 9, 30)
        cal.reset(new_first, new_last)

        self.assertEqual(cal.first, new_first)
        self.assertEqual(cal.last, new_last)
        for d in cal:
            self.assert_(not cal.isSchoolday(d))

        self.assertRaises(ValueError, cal.reset, new_last, new_first)

    def testMarkWeekday(self):
        from schooltool.cal import SchooldayModel
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 17))
        for day in 1, 8, 15:
            self.assert_(not cal.isSchoolday(date(2003, 9, day)))

        cal.addWeekdays(calendar.MONDAY)
        for day in 1, 8, 15:
            self.assert_(cal.isSchoolday(date(2003, 9, day)))
            self.assert_(not cal.isSchoolday(date(2003, 9, day+1)))

        cal.removeWeekdays(calendar.MONDAY, calendar.TUESDAY)
        for day in 1, 8, 15:
            self.assert_(not cal.isSchoolday(date(2003, 9, day)))
            self.assert_(not cal.isSchoolday(date(2003, 9, day+1)))

        cal.addWeekdays(calendar.MONDAY, calendar.TUESDAY)
        for day in 1, 8, 15:
            self.assert_(cal.isSchoolday(date(2003, 9, day)))
            self.assert_(cal.isSchoolday(date(2003, 9, day+1)))

        cal.toggleWeekdays(calendar.TUESDAY, calendar.WEDNESDAY)
        for day in 1, 8, 15:
            self.assert_(cal.isSchoolday(date(2003, 9, day)))
            self.assert_(not cal.isSchoolday(date(2003, 9, day+1)))
            self.assert_(cal.isSchoolday(date(2003, 9, day+2)))

    def test_contains(self):
        from schooltool.cal import SchooldayModel
        cal = SchooldayModel(date(2003, 9, 1), date(2003, 9, 16))
        self.assert_(date(2003, 8, 31) not in cal)
        self.assert_(date(2003, 9, 17) not in cal)
        for day in range(1, 17):
            self.assert_(date(2003, 9, day) in cal)
        self.assertRaises(TypeError, cal.__contains__, 'some string')


class TestDateRange(unittest.TestCase):

    def test(self):
        from schooltool.cal import DateRange
        from schooltool.interfaces import IDateRange

        dr = DateRange(date(2003, 1, 1), date(2003, 1, 31))
        verifyObject(IDateRange, dr)

        # __contains__
        self.assert_(date(2002, 12, 31) not in dr)
        self.assert_(date(2003, 2, 1) not in dr)
        for day in range(1, 32):
            self.assert_(date(2003, 1, day) in dr)

        # __iter__
        days = list(dr)
        self.assertEqual(len(days), 31)
        self.assertEqual(len(dr), 31)

        days = DateRange(date(2003, 1, 1), date(2003, 1, 2))
        self.assertEqual(list(days), [date(2003, 1, 1), date(2003, 1, 2)])

        days = DateRange(date(2003, 1, 1), date(2003, 1, 1))
        self.assertEqual(list(days), [date(2003, 1, 1)])

        self.assertRaises(ValueError, DateRange,
                          date(2003, 1, 2), date(2003, 1, 1))


class TestImmutableCalendar(unittest.TestCase, EqualsSortedMixin):

    def makeCal(self, events):
        from schooltool.cal import ImmutableCalendar
        return ImmutableCalendar(events)

    def test(self):
        from schooltool.cal import ImmutableCalendar
        from schooltool.interfaces import ICalendar

        cal = ImmutableCalendar(())
        verifyObject(ICalendar, cal)

    def test_find(self):
        from schooltool.cal import CalendarEvent

        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")

        cal = self.makeCal([ev1])

        self.assert_(cal.find(ev1.unique_id) is ev1)
        self.assertRaises(KeyError, cal.find, ev1.unique_id + '-not')

    def test_byDate(self):
        from schooltool.cal import CalendarEvent

        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")
        ev2 = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                            timedelta(minutes=10),
                            "Latin")
        ev3 = CalendarEvent(datetime(2003, 11, 26, 10, 0),
                            timedelta(minutes=10),
                            "German")

        cal = self.makeCal([ev1, ev2, ev3])
        self.assertEqual(list(cal.byDate(date(2003, 11, 26))), [ev3])

        # event end date within the period
        ev4 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(1),
                            "Solar eclipse")
        cal = self.makeCal([ev1, ev2, ev3, ev4])
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3, ev4])

        # calendar daterange is within the event period
        ev4 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(2),
                            "Solar eclipse")
        cal = self.makeCal([ev1, ev2, ev3, ev4])
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3, ev4])

        # only the event start date falls within the period
        ev4 = CalendarEvent(datetime(2003, 11, 26, 10, 0),
                            timedelta(2),
                            "Solar eclipse")
        cal = self.makeCal([ev1, ev2, ev3, ev4])
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3, ev4])

        # the event is after the period
        ev4 = CalendarEvent(datetime(2003, 11, 27, 10, 0),
                            timedelta(2),
                            "Solar eclipse")
        cal = self.makeCal([ev1, ev2, ev3, ev4])
        self.assertEqualSorted(list(cal.byDate(date(2003, 11, 26))),
                               [ev3])

    def test_expand(self):
        from schooltool.cal import CalendarEvent
        from schooltool.cal import DailyRecurrenceRule
        from schooltool.interfaces import IExpandedCalendarEvent

        daily = DailyRecurrenceRule(until=date(2004, 12, 31))
        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English", recurrence=daily, unique_id="123")
        ev2 = CalendarEvent(datetime(2004, 10, 11, 11, 0),
                            timedelta(minutes=10),
                            "Coffee", unique_id="124",
                            privacy="private")
        ev3 = CalendarEvent(datetime(2004, 10, 13, 11, 0),
                            timedelta(minutes=10),
                            "Coffee 2", unique_id="125")
        cal = self.makeCal([ev1, ev2, ev3])
        result = list(cal.expand(date(2004, 10, 11), date(2004, 10, 12)))
        result.sort()

        # ev1 expands to [ev1_1, ev1_2]
        ev1_1 = ev1.replace(dtstart=datetime(2004, 10, 11, 10, 0))
        ev1_2 = ev1.replace(dtstart=datetime(2004, 10, 12, 10, 0))
        expected = [ev1_1, ev2, ev1_2]
        expected.sort()
        self.assertEqual(result, expected)

        for event in result:
            assert IExpandedCalendarEvent.providedBy(event)


class TestCalendar(TestImmutableCalendar):

    def test(self):
        from schooltool.cal import Calendar
        from schooltool.interfaces import ICalendar, ICalendarWrite, ILocation
        cal = Calendar()
        verifyObject(ICalendar, cal)
        verifyObject(ICalendarWrite, cal)
        verifyObject(ILocation, cal)

    def test_iter(self):
        from schooltool.cal import Calendar
        from schooltool.cal import CalendarEvent

        cal = Calendar()
        self.assertEqual(list(cal), [])

        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")

        cal.addEvent(ev1)
        self.assertEqual(list(cal), [ev1])

    def makeCal(self, events):
        from schooltool.cal import Calendar
        cal = Calendar()
        for event in events:
            cal.addEvent(event)
        return cal

    def test_clear(self):
        from schooltool.cal import CalendarEvent
        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")
        ev2 = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                            timedelta(minutes=10),
                            "Latin")
        cal = self.makeCal([ev1, ev2])
        cal.clear()
        self.assertEquals(list(cal), [])

    def test_removeEvent(self):
        from schooltool.cal import CalendarEvent
        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")
        ev2 = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                            timedelta(minutes=10),
                            "Latin")
        cal = self.makeCal([ev1, ev2])
        self.assertRaises(KeyError, cal.removeEvent,
                          CalendarEvent(datetime(2003, 11, 25, 10, 0),
                                        timedelta(minutes=10),
                                        "English")) # different unique ID
        cal.removeEvent(ev1)
        self.assertEquals(list(cal), [ev2])
        copy_of_ev2 = ev2.replace()
        assert copy_of_ev2 is not ev2
        cal.removeEvent(copy_of_ev2)
        self.assertEquals(list(cal), [])

    def test_removeEvent_magic(self):
        from schooltool.cal import CalendarEvent
        owner = PersonStub()
        context = ResourceStub()
        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English", owner=owner, context=context)

        owner.calendar = self.makeCal([ev1])
        context.calendar = self.makeCal([ev1])
        owner.calendar.removeEvent(ev1)
        self.assertEquals(list(owner.calendar), [])
        self.assertEquals(list(context.calendar), [])

        owner.calendar = self.makeCal([ev1])
        context.calendar = self.makeCal([ev1])
        context.calendar.removeEvent(ev1)
        self.assertEquals(list(owner.calendar), [])
        self.assertEquals(list(context.calendar), [])

    def test_update(self):
        from schooltool.cal import CalendarEvent
        ev1 = CalendarEvent(datetime(2003, 11, 25, 10, 0),
                            timedelta(minutes=10),
                            "English")
        ev2 = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                            timedelta(minutes=10),
                            "Latin")
        ev3 = CalendarEvent(datetime(2003, 11, 26, 10, 0),
                            timedelta(minutes=10),
                            "German")
        cal = self.makeCal([ev1, ev2])
        cal.update(self.makeCal([ev2, ev3]))
        self.assertEqualSorted(list(cal), [ev1, ev2, ev3])


class TestCalendarPersistence(unittest.TestCase):
    """A functional test for timetables persistence."""

    def setUp(self):
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def test_SchooldayModel(self):
        from schooltool.cal import SchooldayModel
        import transaction
        sm = SchooldayModel(date(2003, 9, 1), date(2003, 9, 30))
        self.datamgr.root()['sm'] = sm
        transaction.commit()

        d1 = date(2003, 9, 15)
        d2 = date(2003, 9, 16)
        sm.add(d1)
        sm.add(d2)
        transaction.commit()

        try:
            datamgr = self.db.open()
            sm2 = datamgr.root()['sm']
            self.assert_(sm2.isSchoolday(d1))
            self.assert_(sm2.isSchoolday(d2))
        finally:
            transaction.abort()
            datamgr.close()

        sm.remove(d1)
        transaction.commit()

        try:
            datamgr = self.db.open()
            sm2 = datamgr.root()['sm']
            self.assert_(not sm2.isSchoolday(d1))
            self.assert_(sm2.isSchoolday(d2))
        finally:
            transaction.abort()
            datamgr.close()

        sm.reset(date(2003, 9, 1), date(2003, 9, 30))
        transaction.commit()

        try:
            datamgr = self.db.open()
            sm2 = datamgr.root()['sm']
            self.assert_(not sm2.isSchoolday(d1))
            self.assert_(not sm2.isSchoolday(d2))
        finally:
            transaction.abort()
            datamgr.close()

    def test_Calendar(self):
        from schooltool.cal import Calendar, CalendarEvent
        import transaction
        cal = Calendar()
        self.datamgr.root()['cal'] = cal
        transaction.commit()

        e = CalendarEvent(datetime(2001, 2, 3, 4, 5, 6), timedelta(1), "xyzzy")
        cal.addEvent(e)
        transaction.commit()

        try:
            datamgr = self.db.open()
            cal2 = datamgr.root()['cal']
            self.assertEquals(list(cal2), [e])
        finally:
            transaction.abort()
            datamgr.close()

        cal.clear()
        transaction.commit()

        try:
            datamgr = self.db.open()
            cal2 = datamgr.root()['cal']
            self.assertEquals(list(cal2), [])
        finally:
            transaction.abort()
            datamgr.close()

        cal3 = Calendar()
        cal3.addEvent(e)
        cal.update(cal3)
        transaction.commit()

        try:
            datamgr = self.db.open()
            cal2 = datamgr.root()['cal']
            self.assertEquals(list(cal2), [e])
        finally:
            transaction.abort()
            datamgr.close()


class TestCalendarEvent(unittest.TestCase):

    def createEvent(self, *args, **kwargs):
        from schooltool.cal import CalendarEvent
        return CalendarEvent(*args, **kwargs)

    def test(self):
        from schooltool.interfaces import ICalendarEvent
        ce = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10), "something")
        verifyObject(ICalendarEvent, ce)
        self.assertEquals(ce.dtstart, datetime(2003, 11, 25, 12, 0))
        self.assertEquals(ce.duration, timedelta(minutes=10))
        self.assertEquals(ce.title, 'something')
        self.assert_(ce.owner is None)
        self.assert_(ce.context is None)
        self.assert_(ce.location is None)
        self.assert_(ce.unique_id is not None)
        # unique id is randomly generated in the style of rfc822, without angle
        # brackets
        self.assert_('@' in ce.unique_id)
        self.assert_('<' not in ce.unique_id)
        self.assert_('>' not in ce.unique_id)

    def test_all_arguments(self):
        from schooltool.interfaces import ICalendarEvent
        owner = object()
        context = object()
        ce = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10), "something", owner=owner,
                              context=context, location="The attic",
                              unique_id='uid')
        verifyObject(ICalendarEvent, ce)
        self.assertEquals(ce.dtstart, datetime(2003, 11, 25, 12, 0))
        self.assertEquals(ce.duration, timedelta(minutes=10))
        self.assertEquals(ce.title, 'something')
        self.assert_(ce.owner is owner)
        self.assert_(ce.context is context)
        self.assertEquals(ce.location, 'The attic')
        self.assertEquals(ce.unique_id, 'uid')

    def test_unique_ids(self):
        seen_ids = sets.Set([])
        count = 100
        for n in range(count):
            ev = self.createEvent(datetime(2003, 11, 25, 12, 0),
                                  timedelta(minutes=10), "something")
            if ev.unique_id in seen_ids:
                self.fail("ID is not unique enough")
            seen_ids.add(ev.unique_id)

    def test_immutability(self):
        ce = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10), "something")
        for attrname in ['dtstart', 'duration', 'title', 'owner', 'context',
                         'location', 'unique_id']:
            self.assertRaises(AttributeError, setattr, ce, attrname, 'not-ro')

    def test_replace(self):
        from schooltool.cal import DailyRecurrenceRule
        owner = object()
        owner2 = object()
        context = object()
        context2 = object()
        ce = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10), "something", owner=owner,
                              context=context, location="The attic",
                              unique_id='uid')
        self.assertEquals(ce.replace(), ce)
        fields_to_replace = {'dtstart': datetime(2004, 11, 12, 14, 30),
                             'duration': timedelta(minutes=30),
                             'title': 'news',
                             'owner': owner2,
                             'context': context2,
                             'location': 'basement',
                             'unique_id': 'uid2',
                             'recurrence': DailyRecurrenceRule(count=3)}
        all_fields = fields_to_replace.keys()
        for field, value in fields_to_replace.items():
            ce2 = ce.replace(**{field: value})
            self.assertNotEquals(ce2, ce)
            self.assertEquals(getattr(ce2, field), value)
            for check_field in all_fields:
                if check_field != field:
                    self.assertEquals(getattr(ce2, check_field),
                                      getattr(ce, check_field))
        all_at_once = ce.replace(**fields_to_replace)
        incremental = ce
        for field, value in fields_to_replace.items():
            incremental = incremental.replace(**{field: value})
        self.assertEquals(all_at_once, incremental)

    def test_comparisons(self):
        from schooltool.cal import DailyRecurrenceRule
        owner = object()
        context = object()
        ce = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10),
                              "reality check", unique_id='uid')
        ce1 = self.createEvent(datetime(2003, 11, 25, 12, 0),
                               timedelta(minutes=10),
                               "reality check", unique_id='uid')
        self.assert_(ce == ce1)
        self.assert_(ce <= ce1)
        self.assert_(ce >= ce1)
        self.assert_(not (ce != ce1))
        self.assert_(not (ce < ce1))
        self.assert_(not (ce > ce1))
        self.assertEquals(hash(ce), hash(ce1))

        fields_to_replace = {'dtstart': datetime(2004, 11, 12, 14, 30),
                             'duration': timedelta(minutes=30),
                             'title': 'news',
                             'owner': owner,
                             'context': context,
                             'location': 'basement',
                             'unique_id': 'uid2',
                             'recurrence': DailyRecurrenceRule(count=3)}
        for field, value in fields_to_replace.items():
            ce2 = ce.replace(**{field: value})
            self.assert_(ce != ce2)
            self.assert_(not (ce == ce2))
            self.assert_(ce < ce2 or ce > ce2)
            self.assertNotEquals(ce < ce2, ce > ce2)
            self.assertEquals(ce < ce2, ce <= ce2)
            self.assertEquals(ce > ce2, ce >= ce2)

        for not_event in [None, 42, 'a string']:
            self.assert_(ce != not_event)
            self.assert_(not (ce == not_event))
            self.assertRaises(TypeError, lambda: ce < not_event)
            self.assertRaises(TypeError, lambda: ce > not_event)
            self.assertRaises(TypeError, lambda: ce <= not_event)
            self.assertRaises(TypeError, lambda: ce >= not_event)

    def test_ordering(self):
        ce = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10),
                              "reality check", unique_id='uid')
        ce2 = ce.replace(dtstart=datetime(2003, 11, 25, 12, 1))
        self.assert_(ce < ce2)
        self.assert_(ce2 > ce)

        ce3 = ce.replace(title='zzz')
        self.assert_(ce < ce3)
        self.assert_(ce3 > ce)

        ce4 = ce2.replace(title='a')
        assert ce4.title < ce.title
        assert ce4.dtstart > ce.dtstart
        self.assert_(ce4 > ce) # dtstart is more important

    def testHasOccurrences(self):
        from schooltool.cal import DailyRecurrenceRule
        ce = self.createEvent(datetime(2004, 11, 25, 12, 0),
                              timedelta(minutes=10), "whatever")
        assert ce.hasOccurrences()

        ce = self.createEvent(datetime(2004, 11, 25, 12, 0),
                              timedelta(minutes=10), "whatever",
                              recurrence=DailyRecurrenceRule())
        assert ce.hasOccurrences()

        ce = self.createEvent(datetime(2004, 11, 25, 12, 0),
                              timedelta(minutes=10), "whatever",
                              recurrence=DailyRecurrenceRule(
                                    count=3,
                                    exceptions=[date(2004, 11, 25),
                                                date(2004, 11, 27)]))
        assert ce.hasOccurrences()

        ce = self.createEvent(datetime(2004, 11, 25, 12, 0),
                              timedelta(minutes=10), "whatever",
                              recurrence=DailyRecurrenceRule(
                                    count=3,
                                    exceptions=[date(2004, 11, 25),
                                                date(2004, 11, 26),
                                                date(2004, 11, 27)]))
        assert not ce.hasOccurrences()

    def test_privacy(self):
        ce1 = self.createEvent(datetime(2004, 11, 25, 12, 0),
                               timedelta(minutes=10), "whatever",
                               unique_id="123")
        ce2 = self.createEvent(datetime(2004, 11, 25, 12, 0),
                               timedelta(minutes=10), "whatever",
                               privacy="hidden", unique_id="123")
        self.assertNotEqual(ce1, ce2)
        self.assertNotEqual(hash(ce1), hash(ce2))

        self.assertRaises(ValueError, self.createEvent,
                          datetime(2004, 11, 25, 12, 0),
                          timedelta(minutes=10), "whatever",
                          privacy="other", unique_id="123")

        for p in ('private', 'public', 'hidden'):
            self.createEvent(datetime(2004, 11, 25, 12, 0),
                             timedelta(minutes=10), "whatever",
                             privacy=p, unique_id="123")
        self.assertEqual(ce1.replace(privacy="hidden"), ce2)
        self.assertEqual(ce2, ce2.replace())


class TestExpandedCalendarEvent(TestCalendarEvent):

    def createEvent(self, *args, **kwargs):
        from schooltool.cal import ExpandedCalendarEvent
        return ExpandedCalendarEvent(*args, **kwargs)

    def test_interface(self):
        from schooltool.interfaces import IExpandedCalendarEvent

        ev = self.createEvent(datetime(2003, 11, 25, 12, 0),
                              timedelta(minutes=10),
                              "reality check", unique_id='uid')
        verifyObject(IExpandedCalendarEvent, ev)

    def test_duplicate(self):
        from schooltool.cal import CalendarEvent, ExpandedCalendarEvent
        from schooltool.interfaces import IExpandedCalendarEvent
        ev = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid',
                           privacy="hidden")
        eev = ExpandedCalendarEvent.duplicate(ev)
        self.assertEqual(ev, eev)
        assert IExpandedCalendarEvent.providedBy(eev)


class TestInheritedCalendarEvent(unittest.TestCase):

    def test_inherit(self):
        from schooltool.cal import CalendarEvent, InheritedCalendarEvent
        from schooltool.interfaces import IInheritedCalendarEvent
        cal = object()
        ev = CalendarEvent(datetime(2003, 11, 25, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid',
                           privacy="hidden")
        iev = InheritedCalendarEvent(ev, cal)
        verifyObject(IInheritedCalendarEvent, iev)
        self.assertEquals(iev, ev)
        self.assertEquals(iev.dtstart, ev.dtstart)
        self.assert_(iev.calendar is cal)


class TestACLCalendar(unittest.TestCase):

    def test(self):
        from schooltool.cal import ACLCalendar
        from schooltool.interfaces import IACLCalendar, IACL
        calendar = ACLCalendar()
        verifyObject(IACLCalendar, calendar)
        verifyObject(IACL, calendar.acl)
        self.assertEquals(calendar.acl.__parent__, calendar)
        self.assertEquals(calendar.acl.__name__, 'acl')


class TestCalendarOwnerMixin(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpRegistries()
        from schooltool import relationship
        relationship.setUp()

    def test(self):
        from schooltool.cal import CalendarOwnerMixin
        from schooltool.interfaces import ICalendarOwner
        from schooltool.interfaces import IACLCalendar, IACL
        from schooltool.interfaces import ViewPermission, ModifyPermission
        from schooltool.interfaces import AddPermission

        com = CalendarOwnerMixin()
        verifyObject(ICalendarOwner, com)
        verifyObject(IACLCalendar, com.calendar)
        verifyObject(IACL, com.calendar.acl)
        self.assert_(com.calendar.__parent__ is com)
        self.assertEquals(com.calendar.__name__, 'calendar')
        assert not com.calendar.acl.allows(com, ViewPermission)
        assert not com.calendar.acl.allows(com, ModifyPermission)
        assert not com.calendar.acl.allows(com, AddPermission)
        com.addSelfToCalACL()
        assert com.calendar.acl.allows(com, ViewPermission)
        assert com.calendar.acl.allows(com, ModifyPermission)
        assert com.calendar.acl.allows(com, AddPermission)

    def test_makeCompositeCalendar(self):
        from schooltool.cal import CalendarOwnerMixin, CalendarEvent
        from schooltool.cal import DailyRecurrenceRule
        from schooltool.model import Group
        from schooltool.relationship import RelatableMixin
        from schooltool.uris import URICalendarProvider
        from schooltool.interfaces import IInheritedCalendarEvent

        ev1 = CalendarEvent(datetime(2003, 11, 26, 20, 00),
                            timedelta(minutes=30), "AG")
        gr1 = Group("Little")
        gr1.calendar.addEvent(ev1)

        rr = DailyRecurrenceRule()
        ev2 = CalendarEvent(datetime(2003, 11, 26, 13, 00),
                            timedelta(minutes=30), "AB", recurrence=rr)
        gr2 = Group("Big")
        gr2.calendar.addEvent(ev2)

        class AppObjectStub(CalendarOwnerMixin, RelatableMixin):

            def __init__(self):
                CalendarOwnerMixin.__init__(self)
                RelatableMixin.__init__(self)

            def listLinks(self, uri):
                if uri == URICalendarProvider:
                    return [LinkStub(gr1), LinkStub(gr2)]
                else:
                    return []

        com = AppObjectStub()

        result = com.makeCompositeCalendar(date(2003, 11, 26),
                                           date(2003, 11, 28))

        rec1 = CalendarEvent(datetime(2003, 11, 27, 13, 00),
                             timedelta(minutes=30), "AB", recurrence=rr,
                             unique_id=ev2.unique_id)
        rec2 = CalendarEvent(datetime(2003, 11, 28, 13, 00),
                             timedelta(minutes=30), "AB", recurrence=rr,
                             unique_id=ev2.unique_id)
        expected = {ev1.unique_id: ev1, ev2.unique_id: ev2,
                    rec1.unique_id: rec1, rec2.unique_id: rec2}

        self.assertEquals(result.events, expected)

        for event in result:
            verifyObject(IInheritedCalendarEvent, event)
            group = event.recurrence is None and gr1 or gr2
            self.assert_(event.calendar is group.calendar)

        self.assert_(result.__parent__ is com)
        self.assertEquals(result.__name__, 'composite-calendar')


class RecurrenceRuleTestBase:
    """Base tests for the recurrence rules"""

    def test_comparison(self):
        d = self.createRule()
        d2 = d.replace()
        d3 = d.replace(count=2)
        assert d is not d2
        self.assertEqual(d, d2)
        assert not d != d2
        self.assertEqual(hash(d), hash(d2))
        assert d != None
        assert d < None or d > None
        assert d3 < d or d < d3

    def test_replace(self):
        rule = self.createRule(interval=1, until=date(2005, 1, 1))
        assert rule == rule.replace()
        rule2 = rule.replace(until=None, count=20)
        assert rule != rule2
        self.assertRaises(ValueError, rule.replace, count=20)

    def test_validate(self):
        self.assertRaises(ValueError, self.createRule, count=3,
                          until=date.today())
        self.assertRaises(ValueError, self.createRule, exceptions=(1,))
        self.assertRaises(ValueError, self.createRule, interval=0)
        self.assertRaises(ValueError, self.createRule, interval=-1)
        self.createRule(exceptions=(date.today(),))
        self.createRule(until=date.today())
        self.createRule(count=42)

    def test_iCalRepresentation(self):
        # simple case
        rule = self.createRule(interval=2)
        freq = rule.ical_freq
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;INTERVAL=2' % freq])

        # count
        rule = self.createRule(interval=3, count=5)
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;COUNT=5;INTERVAL=3' % freq])

        # until
        rule = self.createRule(until=date(2004, 10, 20))
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;UNTIL=20041020T000000;INTERVAL=1'
                           % freq])

        # exceptions
        rule = self.createRule(exceptions=[date(2004, 10, 2*d)
                                           for d in range(3, 6)])
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;INTERVAL=1' % freq,
                           'EXDATE;VALUE=DATE:20041006,20041008,20041010'])

    def test_immutability(self):
        r = self.createRule()
        for attrname in ['interval', 'count', 'until', 'exceptions']:
            self.assertRaises(AttributeError, setattr, r, attrname, 'not-ro')


class TestDailyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schooltool.cal import DailyRecurrenceRule
        return DailyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schooltool.interfaces import IDailyRecurrenceRule
        rule = self.createRule()
        verifyObject(IDailyRecurrenceRule, rule)

    def test_apply(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule()
        ev = CalendarEvent(datetime(2004, 10, 13, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(2003, 10, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With an end date
        rule = self.createRule(until=date(2004, 10, 20))
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With a count
        rule = self.createRule(count=8)
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With an interval
        rule = self.createRule(interval=2)
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21, 2)])

        # With exceptions
        rule = self.createRule(exceptions=[date(2004, 10, d)
                                           for d in range(16, 21)])
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 16)])

        # With exceptions and count -- exceptions are excluded after
        # counting
        rule = self.createRule(exceptions=[date(2004, 10, d)
                                           for d in range(16, 21)],
                               count=6)
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, 13), date(2004, 10, 14),
                                  date(2004, 10, 15)])


class TestYearlyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schooltool.cal import YearlyRecurrenceRule
        return YearlyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schooltool.interfaces import IYearlyRecurrenceRule
        rule = self.createRule()
        verifyObject(IYearlyRecurrenceRule, rule)

    def test_apply(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule()
        ev = CalendarEvent(datetime(1978, 5, 17, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result, [date(y, 5, 17) for y in range(1978, 2005)])

        # With an end date
        rule = self.createRule(until=date(2004, 10, 20))
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(y, 5, 17) for y in range(1978, 2005)])

        # With a count
        rule = self.createRule(count=8)
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(y, 5, 17) for y in range(1978, 1986)])

        # With an interval
        rule = self.createRule(interval=4)
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result,
                         [date(y, 5, 17)
                          for y in [1978, 1982, 1986, 1990, 1994, 1998, 2002]])

        # With exceptions
        rule = self.createRule(exceptions=[date(1980, 5, 17)])
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result,
                         [date(y, 5, 17)
                          for y in [1978, 1979] + range(1981, 2005)])

        # With exceptions and count -- the total nr. of events is less
        # that count.
        rule = self.createRule(exceptions=[date(1980, 5, 17)], count=4)
        result = list(rule.apply(ev, date(2004, 10, 20)))
        self.assertEqual(result,
                         [date(1978, 5, 17), date(1979, 5, 17),
                          date(1981, 5, 17)])


class TestWeeklyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schooltool.cal import WeeklyRecurrenceRule
        return WeeklyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schooltool.interfaces import IWeeklyRecurrenceRule
        rule = self.createRule()
        verifyObject(IWeeklyRecurrenceRule, rule)

    def test_weeekday_validation(self):
        self.assertRaises(ValueError, self.createRule, weekdays=(1, 7))
        self.assertRaises(ValueError, self.createRule, weekdays=(1, "TH"))

    def test_replace_weekly(self):
        rule = self.createRule(weekdays=(1, 3))
        assert rule == rule.replace()
        assert rule != rule.replace(weekdays=(1,))

    def test_apply(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule()
        ev = CalendarEvent(datetime(1978, 5, 17, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, date(1978, 7, 17))) # Wednesday
        expected = [date(1978, 5, 17) + timedelta(w * 7) for w in range(9)]
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(until=date(1978, 7, 12))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(count=9)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(interval=2, weekdays=(3,))
        result = list(rule.apply(ev, date(1978, 7, 12)))
        expected = [date(1978, 5, 17), date(1978, 5, 18),
                    date(1978, 5, 31), date(1978, 6, 1),
                    date(1978, 6, 14), date(1978, 6, 15),
                    date(1978, 6, 28), date(1978, 6, 29),
                    date(1978, 7, 12)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(interval=2, weekdays=(3,),
                               exceptions=[date(1978, 6, 29)])
        result = list(rule.apply(ev, date(1978, 7, 12)))
        expected = [date(1978, 5, 17), date(1978, 5, 18),
                    date(1978, 5, 31), date(1978, 6, 1),
                    date(1978, 6, 14), date(1978, 6, 15),
                    date(1978, 6, 28), date(1978, 7, 12)]
        self.assertEqual(result, expected)

    def test_iCalRepresentation_weekly(self):
        rule = self.createRule(weekdays=(0, 3, 5, 6))
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=WEEKLY;BYDAY=MO,TH,SA,SU;INTERVAL=1'])


class TestMonthlyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schooltool.cal import MonthlyRecurrenceRule
        return MonthlyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schooltool.interfaces import IMonthlyRecurrenceRule
        rule = self.createRule()
        verifyObject(IMonthlyRecurrenceRule, rule)

    def test_monthly_validation(self):
        self.assertRaises(ValueError, self.createRule, monthly="whenever")
        self.assertRaises(ValueError, self.createRule, monthly=date.today())
        self.assertRaises(ValueError, self.createRule, monthly=None)
        self.createRule(monthly="lastweekday")
        self.createRule(monthly="monthday")
        self.createRule(monthly="weekday")

    def test_replace_(self):
        rule = self.createRule(monthly="lastweekday")
        assert rule == rule.replace()
        assert rule != rule.replace(monthly="monthday")

    def test_apply_monthday(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule(monthly="monthday")
        ev = CalendarEvent(datetime(1978, 5, 17, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, date(1978, 8, 17)))
        expected = [date(1978, m, 17) for m in range(5,9)]
        self.assertEqual(result, expected)

        # Over the end of the year
        result = list(rule.apply(ev, date(1979, 2, 17)))
        expected = ([date(1978, m, 17) for m in range(5, 13)] +
                    [date(1979, m, 17) for m in range(1, 3)])
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(monthly="monthday", until=date(1979, 2, 17))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(count=10)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(monthly="monthday", interval=2)
        result = list(rule.apply(ev, date(1979, 2, 17)))
        expected = [date(1978, 5, 17), date(1978, 7, 17),date(1978, 9, 17),
                    date(1978, 11, 17), date(1979, 1, 17)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(monthly="monthday", interval=2,
                               exceptions=[date(1978, 7, 17)])
        result = list(rule.apply(ev, date(1978, 9, 17)))
        expected = [date(1978, 5, 17), date(1978, 9, 17)]
        self.assertEqual(result, expected)

    def test_apply_endofmonth(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule(monthly="monthday")
        ev = CalendarEvent(datetime(2001, 1, 31, 0, 0),
                           timedelta(minutes=10),
                           "End of month", unique_id="uid")

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(2001, 12, 31)))
        self.assertEqual(len(result), 7)

        rule = self.createRule(monthly="monthday", count=7)
        result = list(rule.apply(ev, date(2001, 12, 31)))
        self.assertEqual(len(result), 7)
        self.assertEqual(result[-1], date(2001, 12, 31))

        rule = self.createRule(monthly="monthday", interval=2)
        result = list(rule.apply(ev, date(2002, 1, 31)))
        self.assertEqual(result, [date(2001, 1, 31),
                                  date(2001, 3, 31),
                                  date(2001, 5, 31),
                                  date(2001, 7, 31),
                                  date(2002, 1, 31),])

    def test_apply_weekday(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule(monthly="weekday")
        ev = CalendarEvent(datetime(1978, 5, 17, 12, 0),  # 3rd Wednesday
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, date(1978, 8, 17)))
        expected = [date(1978, 5, 17), date(1978, 6, 21),
                    date(1978, 7, 19), date(1978, 8, 16)]
        self.assertEqual(result, expected)

        # Over the end of the year
        result = list(rule.apply(ev, date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 6, 21),
                    date(1978, 7, 19), date(1978, 8, 16),
                    date(1978, 9, 20), date(1978, 10, 18),
                    date(1978, 11, 15), date(1978, 12, 20),
                    date(1979, 1, 17), date(1979, 2, 21)]
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(monthly="weekday", until=date(1979, 2, 21))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(monthly="weekday", count=10)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(monthly="weekday", interval=2)
        result = list(rule.apply(ev, date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 7, 19),
                    date(1978, 9, 20), date(1978, 11, 15),
                    date(1979, 1, 17)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(monthly="weekday", interval=2,
                               exceptions=[date(1978, 7, 19)])
        result = list(rule.apply(ev, date(1978, 9, 30)))
        expected = [date(1978, 5, 17), date(1978, 9, 20)]
        self.assertEqual(result, expected)

    def test_apply_lastweekday(self):
        from schooltool.cal import CalendarEvent
        rule = self.createRule(monthly="lastweekday")
        ev = CalendarEvent(datetime(1978, 5, 17, 12, 0),  # 3rd last Wednesday
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, date(1978, 8, 17)))
        expected = [date(1978, 5, 17), date(1978, 6, 14),
                    date(1978, 7, 12), date(1978, 8, 16)]
        self.assertEqual(result, expected)

        # Over the end of the year
        result = list(rule.apply(ev, date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 6, 14),
                    date(1978, 7, 12), date(1978, 8, 16),
                    date(1978, 9, 13), date(1978, 10, 11),
                    date(1978, 11, 15), date(1978, 12, 13),
                    date(1979, 1, 17), date(1979, 2, 14)]
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(monthly="lastweekday", until=date(1979, 2, 21))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(monthly="lastweekday", count=10)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(monthly="lastweekday", interval=2)
        result = list(rule.apply(ev, date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 7, 12),
                    date(1978, 9, 13), date(1978, 11, 15),
                    date(1979, 1, 17)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(monthly="lastweekday", interval=2,
                               exceptions=[date(1978, 7, 12)])
        result = list(rule.apply(ev, date(1978, 9, 30)))
        expected = [date(1978, 5, 17), date(1978, 9, 13)]
        self.assertEqual(result, expected)

    def test_iCalRepresentation(self):
        # This method deliberately overrides the test in the base class.

        # monthday
        rule = self.createRule(monthly="monthday")
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                          ['RRULE:FREQ=MONTHLY;BYMONTHDAY=26;INTERVAL=1'])

        # weekday
        rule = self.createRule(monthly="weekday")
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                          ['RRULE:FREQ=MONTHLY;BYDAY=4TU;INTERVAL=1'])

        # lastweekday
        rule = self.createRule(monthly="lastweekday")
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                          ['RRULE:FREQ=MONTHLY;BYDAY=-1TU;INTERVAL=1'])

        # some standard stuff
        rule = self.createRule(interval=3, count=7,
                               exceptions=[date(2004, 10, 2*d)
                                           for d in range(3, 6)])
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                      ['RRULE:FREQ=MONTHLY;COUNT=7;BYMONTHDAY=26;INTERVAL=3',
                       'EXDATE;VALUE=DATE:20041006,20041008,20041010'])


class TestWeekSpan(unittest.TestCase):

    def test_weekspan(self):
        from schooltool.cal import weekspan

        # The days are in the same week
        self.assertEqual(weekspan(date(2004, 10, 11), date(2004, 10, 17)), 0)
        #                              Monday, w42         Sunday, w42

        # The days are in the adjacent weeks
        self.assertEqual(weekspan(date(2004, 10, 17), date(2004, 10, 18)), 1)
        #                              Sunday, w42         Monday, w43

        # The days span the end of year
        self.assertEqual(weekspan(date(2004, 12, 30), date(2005, 01, 07)), 1)
        #                              Thursday, w53       Friday, w1

        # The days span the end of year, two weeks
        self.assertEqual(weekspan(date(2004, 12, 30), date(2005, 01, 14)), 2)
        #                              Thursday, w53       Friday, w2


class TestMonthIndex(unittest.TestCase):

    def test_monthindex(self):
        from schooltool.cal import monthindex
        # First Friday of October 2004
        self.assertEqual(monthindex(2004, 10, 1, 4), date(2004, 10, 1))
        self.assertEqual(monthindex(2004, 10, 1, 3), date(2004, 10, 7))
        self.assertEqual(monthindex(2004, 10, 1, 3), date(2004, 10, 7))

        # Users must check whether the month is correct themselves.
        self.assertEqual(monthindex(2004, 10, 5, 3), date(2004, 11, 4))

        self.assertEqual(monthindex(2004, 10, 4, 3), date(2004, 10, 28))
        self.assertEqual(monthindex(2004, 10, -1, 3), date(2004, 10, 28))

        self.assertEqual(monthindex(2004, 11, -1, 1), date(2004, 11, 30))
        self.assertEqual(monthindex(2004, 11, -1, 2), date(2004, 11, 24))

        self.assertEqual(monthindex(2004, 12, -1, 3), date(2004, 12, 30))
        self.assertEqual(monthindex(2004, 12, -1, 4), date(2004, 12, 31))
        self.assertEqual(monthindex(2004, 12, -1, 3), date(2004, 12, 30))
        self.assertEqual(monthindex(2004, 12, -2, 3), date(2004, 12, 23))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDateRange))
    suite.addTest(unittest.makeSuite(TestSchooldayModel))
    suite.addTest(unittest.makeSuite(TestCalendar))
    suite.addTest(unittest.makeSuite(TestImmutableCalendar))
    suite.addTest(unittest.makeSuite(TestCalendarPersistence))
    suite.addTest(unittest.makeSuite(TestCalendarEvent))
    suite.addTest(unittest.makeSuite(TestExpandedCalendarEvent))
    suite.addTest(unittest.makeSuite(TestInheritedCalendarEvent))
    suite.addTest(unittest.makeSuite(TestACLCalendar))
    suite.addTest(unittest.makeSuite(TestCalendarOwnerMixin))
    suite.addTest(unittest.makeSuite(TestDailyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestYearlyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestWeeklyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestMonthlyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestWeekSpan))
    suite.addTest(unittest.makeSuite(TestMonthIndex))
    return suite
