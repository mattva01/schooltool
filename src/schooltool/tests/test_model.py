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
Unit tests for schooltool.model

$Id$
"""

import unittest
from datetime import datetime, time, date, timedelta
from persistent import Persistent
from zope.testing.doctestunit import DocTestSuite
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.utils import EqualsSortedMixin, NiceDiffsMixin
from schooltool.interfaces import ILink, IFacet

__metaclass__ = type


class LinkStub:
    implements(ILink)
    __name__ = None
    __parent__ = None
    reltype = None
    role = None
    target = Persistent()

    def traverse(self):
        return self.target


class FacetStub(Persistent):
    implements(IFacet)
    active = False
    owner = None
    __name__ = None
    __parent__ = None


class ApplicationObjectsTestMixin(NiceDiffsMixin, unittest.TestCase):
    """A base class for the tests of application objects.

    Subclasses must provide a newObject() method.
    """

    def testAppObjectInterfaces(self):
        from schooltool.interfaces import IFaceted, IRelatable
        from schooltool.interfaces import IEventConfigurable, IEventTarget
        from schooltool.interfaces import IMultiContainer
        from schooltool.interfaces import ITimetabled
        obj = self.newObject()
        verifyObject(IFaceted, obj)
        verifyObject(IEventTarget, obj)
        verifyObject(IEventConfigurable, obj)
        verifyObject(IRelatable, obj)
        verifyObject(ITimetabled, obj)
        verifyObject(IMultiContainer, obj)

    def test_getFreeIntervals(self):
        from schooltool.cal import Calendar, CalendarEvent
        obj = self.newObject()
        cal = Calendar()
        obj.makeTimetableCalendar = lambda: cal
        one_hour = timedelta(hours=1)
        three_hours = timedelta(hours=3)
        four_hours = timedelta(hours=4)
        five_hours = timedelta(hours=5)
        eight_hours = timedelta(hours=8)
        one_day = timedelta(days=1)
        first = date(2004, 1, 1)
        last = date(2004, 1, 3)
        whole_day = [(time(0), one_day)]
        working_hours = [(time(9), eight_hours)]
        working_hours_with_lunch = [(time(9), three_hours),
                                    (time(14), five_hours)]
        self.assertEqual(obj.getFreeIntervals(first, last, whole_day,
                                              one_hour),
                         [(first, last - first + one_day)])
        self.assertEqual(obj.getFreeIntervals(first, last, working_hours,
                                             one_hour),
                         [(datetime(2004, 1, 1, 9), eight_hours),
                          (datetime(2004, 1, 2, 9), eight_hours),
                          (datetime(2004, 1, 3, 9), eight_hours),
                         ])
        self.assertEqual(obj.getFreeIntervals(first, last,
                                             working_hours_with_lunch,
                                             one_hour),
                         [(datetime(2004, 1, 1, 9), three_hours),
                          (datetime(2004, 1, 1, 14), five_hours),
                          (datetime(2004, 1, 2, 9), three_hours),
                          (datetime(2004, 1, 2, 14), five_hours),
                          (datetime(2004, 1, 3, 9), three_hours),
                          (datetime(2004, 1, 3, 14), five_hours),
                         ])
        self.assertEqual(obj.getFreeIntervals(first, last,
                                             working_hours_with_lunch,
                                             four_hours),
                         [(datetime(2004, 1, 1, 14), five_hours),
                          (datetime(2004, 1, 2, 14), five_hours),
                          (datetime(2004, 1, 3, 14), five_hours),
                         ])
        self.assertEqual(obj.getFreeIntervals(first, last,
                                             working_hours_with_lunch,
                                             five_hours),
                         [(datetime(2004, 1, 1, 14), five_hours),
                          (datetime(2004, 1, 2, 14), five_hours),
                          (datetime(2004, 1, 3, 14), five_hours),
                         ])
        obj.calendar.addEvent(CalendarEvent(datetime(2004, 1, 2, 15),
                                           one_hour, "Busy"))
        self.assertEqual(obj.getFreeIntervals(first, last,
                                             working_hours_with_lunch,
                                             five_hours),
                         [(datetime(2004, 1, 1, 14), five_hours),
                          (datetime(2004, 1, 3, 14), five_hours),
                         ])
        cal.addEvent(CalendarEvent(datetime(2004, 1, 3, 15),
                                   one_hour, "Busy"))
        self.assertEqual(obj.getFreeIntervals(first, last,
                                             working_hours_with_lunch,
                                             five_hours),
                         [(datetime(2004, 1, 1, 14), five_hours),
                         ])

    def test_getFreeIntervals_recurring_events(self):
        from schooltool.cal import Calendar, CalendarEvent, RecurrenceRule
        obj = self.newObject()
        cal = Calendar()
        obj.makeTimetableCalendar = lambda: []

        # some convenience definitions
        day = timedelta(days=1)
        half_day = timedelta(hours=12)
        whole_day = [(time(0), day)]
        first = date(2004, 1, 1)
        last = date(2004, 1, 5)

        recurrence = RecurrenceRule(interval=2)
        obj.calendar.addEvent(CalendarEvent(datetime(2004, 1, 2, 12, 0),
                                            half_day, "Busy",
                                            recurrence=recurrence))

        self.assertEqual(obj.getFreeIntervals(first, last, whole_day,
                                              half_day),
                         [(first, day + half_day),
                          (first + day*2 + half_day, day + half_day),
                          (first + day*4 + half_day, day)])

    # _availabilityMap was factored out of getFreeIntervals and is therefore
    # tested (albeit indirectly)

    def createServiceManager(self):
        """Return a service manager stub for getPeriodsForDay.

        Our timetable stubs define these periods for the the following days:
          2004-09-01
            A:  9:00- 9:45
            B: 10:00-10:45
          2004-09-02
            (holiday)
          2004-09-03
            C:  9:00- 9:45
            D: 10:00-10:45
        """
        from schooltool.interfaces import IServiceManager

        class SchooldayPeriodStub:
            def __init__(self, hour, title):
                self.title = title
                self.tstart = time(hour)
                self.duration = timedelta(minutes=45)

        class TimetableModelStub:
            def periodsInDay(self, schooldays, schema, day):
                if day == date(2004, 9, 1):
                    return [SchooldayPeriodStub(9, 'A'),
                            SchooldayPeriodStub(10, 'B')]
                if day == date(2004, 9, 3):
                    return [SchooldayPeriodStub(9, 'C'),
                            SchooldayPeriodStub(10, 'D')]
                return []

        class TimetableStub:
            model = TimetableModelStub()

        class TimetableSchemaServiceStub:
            default_id = 'default'
            _default_tt = TimetableStub()
            def getDefault(self):
                return self._default_tt

        class TimePeriodServiceStub:
            """"""
            def keys(self):
                return ('whenever', )
            def __getitem__(self, key):
                assert key == 'whenever'
                return [date(2004, 9, 1), date(2004, 9, 2), date(2004, 9, 3)]

        class ServiceManagerStub:
            implements(IServiceManager)
            timetableSchemaService = TimetableSchemaServiceStub()
            timePeriodService = TimePeriodServiceStub()

        return ServiceManagerStub()

    def test_getFreePeriods_no_events(self):
        obj = self.newObject()
        obj.__parent__ = self.createServiceManager()
        periods = obj.getFreePeriods(date(2004, 9, 1), date(2004, 9, 3),
                                     ['A', 'B', 'C'])
        self.assertEquals(periods, [(datetime(2004, 9, 1, 9, 0),
                                     timedelta(minutes=45), 'A'),
                                    (datetime(2004, 9, 1, 10, 0),
                                     timedelta(minutes=45), 'B'),
                                    (datetime(2004, 9, 3, 9, 0),
                                     timedelta(minutes=45), 'C')])

    def test_getFreePeriods_with_events(self):
        from schooltool.cal import CalendarEvent
        obj = self.newObject()
        obj.__parent__ = self.createServiceManager()
        obj.calendar.addEvent(CalendarEvent(datetime(2004, 9, 1, 9, 55),
                                            timedelta(minutes=10), "Busy"))
        periods = obj.getFreePeriods(date(2004, 9, 1), date(2004, 9, 3),
                                     ['A', 'B', 'C'])
        self.assertEquals(periods, [(datetime(2004, 9, 1, 9, 0),
                                     timedelta(minutes=45), 'A'),
                                    (datetime(2004, 9, 3, 9, 0),
                                     timedelta(minutes=45), 'C')])

    def test_getRelativePath(self):
        from schooltool.component import FacetManager
        obj = self.newObject()
        link = LinkStub()
        obj.__links__.add(link)
        facet = FacetStub()
        FacetManager(obj).setFacet(facet)

        self.assertEquals(obj.getRelativePath(link),
                          'relationships/%s' % link.__name__)
        self.assertEquals(obj.getRelativePath(facet),
                          'facets/%s' % facet.__name__)

    def test_hash(self):
        from schooltool.interfaces import IContainmentRoot
        class C:
            implements(IContainmentRoot)
        parent = C()
        ob = self.newObject()
        ob.__name__ = 'foo'
        ob.__parent__ = parent
        self.assertEquals(hash(ob), hash((ob.__class__.__name__, 'foo')))
        ob2 = self.newObject()
        ob2.__name__ = 'foo'
        ob2.__parent__ = parent
        self.assertEquals(hash(ob), hash(ob2))


class TestPerson(EventServiceTestMixin, ApplicationObjectsTestMixin,
                 EqualsSortedMixin):

    def newObject(self):
        from schooltool.model import Person
        return Person('John Smith')

    def setUp(self):
        self.setUpEventService()

    def test(self):
        from schooltool.interfaces import IPerson, IPersonInfoFacet
        from schooltool.component import FacetManager
        p = self.newObject()
        verifyObject(IPerson, p)
        facet = FacetManager(p).facetByName("person_info")
        verifyObject(IPersonInfoFacet, facet)

    def test_getRelativePath(self):
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
        from schooltool.component import FacetManager
        person = Person('John Smith')
        person.__parent__ = self.eventService
        person.__name__ = 'foo'
        absence = person.reportAbsence(AbsenceComment())
        link = LinkStub()
        person.__links__.add(link)
        facet = FacetStub()
        FacetManager(person).setFacet(facet)

        self.assertEquals(person.getRelativePath(absence),
                          'absences/%s' % absence.__name__)
        self.assertEquals(person.getRelativePath(link),
                          'relationships/%s' % link.__name__)
        self.assertEquals(person.getRelativePath(facet),
                          'facets/%s' % facet.__name__)

    def test_absence(self):
        from schooltool.interfaces import IAbsence
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
        person = Person('John Smith')
        person.__parent__ = self.eventService
        person.__name__ = 'foo'

        # A new person has no absences
        self.assert_(person.getCurrentAbsence() is None)
        self.assertEquals(list(person.iterAbsences()), [])

        # Adding a non-IAbsenceComment does not affect anything
        self.assertRaises(TypeError, person.reportAbsence, object())
        self.assert_(person.getCurrentAbsence() is None)
        self.assertEquals(list(person.iterAbsences()), [])

        # Adding an IAbsenceComment to a person creates an IAbsence
        comment1 = AbsenceComment(object(), "some text")
        absence = person.reportAbsence(comment1)
        self.assert_(IAbsence.providedBy(absence))
        self.assert_(comment1 in absence.comments)
        self.assert_(absence.person is person)
        self.assert_(absence.__parent__ is person)
        self.assert_(not absence.ended)
        self.assert_(not absence.resolved)
        self.assert_(person.getAbsence(absence.__name__) is absence)
        self.assertRaises(KeyError, person.getAbsence, absence.__name__ + "X")
        self.assertEquals([absence], list(person.iterAbsences()))
        self.assert_(person.getCurrentAbsence() is absence)

        # Check that adding a second comment changes the current absence
        dt = datetime(2003, 10, 28)
        comment2 = AbsenceComment(object(), "some text",
                                  expected_presence=dt)
        absence2 = person.reportAbsence(comment2)
        self.assertEquals([absence], list(person.iterAbsences()))
        self.assert_(absence2 is absence)
        self.assertEquals(absence.comments, [comment1, comment2])
        self.assertEquals(absence.expected_presence, dt)
        self.assert_(person.getCurrentAbsence() is absence)

        # Check that a comment can end the absence
        comment3 = AbsenceComment(None, "ended", ended=True)
        absence3 = person.reportAbsence(comment3)
        self.assert_(absence3 is absence)
        self.assert_(absence.ended)
        self.assert_(person.getCurrentAbsence() is None)

        # Check that reporting an absence when there is no current absence
        # creates a new absence.
        comment4 = AbsenceComment(object(), "some text")
        absence4 = person.reportAbsence(comment4)
        self.assert_(absence4 is not absence)
        self.assertEquals(absence4.comments, [comment4])
        self.assert_(person.getCurrentAbsence() is absence4)
        self.assertEqualsSorted([absence, absence4],
                                list(person.iterAbsences()))

        # Add comments to absences directly, rather than via Person.
        # Check that ending an absence multiple times is ok.
        absence4.addComment(AbsenceComment(ended=True))
        self.assert_(person.getCurrentAbsence() is None)
        absence4.addComment(AbsenceComment(ended=True))
        self.assert_(person.getCurrentAbsence() is None)
        # Unending a previously ended absence makes it into the current
        # absence.
        absence.addComment(AbsenceComment(ended=False))
        self.assert_(person.getCurrentAbsence() is absence)
        absence.addComment(AbsenceComment(ended=False))
        self.assert_(person.getCurrentAbsence() is absence)
        absence4.addComment(AbsenceComment(ended=True))
        self.assert_(person.getCurrentAbsence() is absence)
        # Check that you cannot re-open an absence while another absence is
        # unended.
        old_len = len(absence4.comments)
        self.assertRaises(ValueError, absence4.addComment,
                          AbsenceComment(ended=False, expected_presence=dt))
        self.assertEquals(len(absence4.comments), old_len)
        self.assert_(absence4.ended)
        self.assert_(absence4.expected_presence is None)

    def test_absence_ended_initially(self):
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
        person = Person('John Smith')
        person.__parent__ = self.eventService
        person.__name__ = 'foo'

        comment = AbsenceComment(object(), "some text", ended=True,
                                 resolved=True)
        absence = person.reportAbsence(comment)
        self.assert_(absence.ended)
        self.assert_(absence.resolved)
        self.assert_(absence in person.iterAbsences())
        self.assert_(person.getCurrentAbsence() is None)

    def test_setPassword_checkPassword_hasPassword(self):
        p = self.newObject()
        self.assert_(not p.hasPassword())
        self.assert_(not p.checkPassword(""))
        p.setPassword("xyzzy")
        self.assert_(p.hasPassword())
        self.assert_(p.checkPassword("xyzzy"))
        self.assert_(not p.checkPassword("XYZZY"))
        p.setPassword(None)
        self.assert_(not p.hasPassword())
        self.assert_(not p.checkPassword(None))
        self.assert_(not p.checkPassword("xyzzy"))
        p.setPassword("")
        self.assert_(p.hasPassword())
        self.assert_(p.checkPassword(""))
        self.assert_(not p.checkPassword(None))


class TestGroup(ApplicationObjectsTestMixin):

    def newObject(self):
        from schooltool.model import Group
        return Group("root")

    def test(self):
        from schooltool.interfaces import IGroup
        from schooltool.interfaces import Everybody, ViewPermission
        group = self.newObject()
        verifyObject(IGroup, group)
        self.assertEquals(list(group.acl), [(Everybody, ViewPermission)])


class TestResource(ApplicationObjectsTestMixin):

    def newObject(self):
        from schooltool.model import Resource
        return Resource("Room 3")

    def test(self):
        from schooltool.interfaces import IResource
        resource = self.newObject()
        verifyObject(IResource, resource)


class TestNote(unittest.TestCase):

    def newObject(self):
        from schooltool.model import Note
        return Note("Test Note", "Test Body", "/start")

    def test(self):
        from schooltool.interfaces import INote, ILocation, IRelatable
        note = self.newObject()
        verifyObject(INote, note)
        verifyObject(ILocation, note)
        verifyObject(IRelatable, note)


class TestResidence(unittest.TestCase):

    def newObject(self):
        from schooltool.model import Residence
        return Residence("Home Residence")

    def test(self):
        from schooltool.interfaces import IResidence, IAddressFacet
        from schooltool.component import FacetManager
        residence = self.newObject()
        verifyObject(IResidence, residence)
        facet = FacetManager(residence).facetByName("address_info")
        verifyObject(IAddressFacet, facet)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.model'))
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestResource))
    suite.addTest(unittest.makeSuite(TestNote))
    suite.addTest(unittest.makeSuite(TestResidence))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
