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
from datetime import datetime
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.tests.utils import EventServiceTestMixin, EqualsSortedMixin
from schooltool.tests.utils import LocatableEventTargetMixin
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


class TestPerson(EventServiceTestMixin, unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.interfaces import IPerson, IEventTarget, IRelatable
        from schooltool.interfaces import IEventConfigurable
        from schooltool.interfaces import IMultiContainer
        from schooltool.model import Person
        person = Person('John Smith')
        verifyObject(IPerson, person)
        verifyObject(IEventTarget, person)
        verifyObject(IEventConfigurable, person)
        verifyObject(IRelatable, person)
        verifyObject(IMultiContainer, person)

    def test_getRelativePath(self):
        from schooltool.model import Person, AbsenceComment
        from schooltool.component import FacetManager
        person = Person('John Smith')
        person.__parent__ = self.eventService
        absence = person.reportAbsence(AbsenceComment(None, None))
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
        from schooltool.model import Person, AbsenceComment
        person = Person('John Smith')
        person.__parent__ = self.eventService

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
        self.assert_(IAbsence.isImplementedBy(absence))
        self.assert_(comment1 in absence.comments)
        self.assert_(absence.person is person)
        self.assert_(absence.__parent__ is person)
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

        # Check that a comment can resolve the absence
        comment3 = AbsenceComment(None, "resolved", resolution=True)
        absence3 = person.reportAbsence(comment3)
        self.assert_(absence3 is absence)
        self.assert_(absence.resolved)
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
        # Check that resolving an absence multiple times is ok.
        absence4.addComment(AbsenceComment(None, "", resolution=True))
        self.assert_(person.getCurrentAbsence() is None)
        absence4.addComment(AbsenceComment(None, "", resolution=True))
        self.assert_(person.getCurrentAbsence() is None)
        # Unresolving a previously resolved absence makes it into the current
        # absence.
        absence.addComment(AbsenceComment(None, "", resolution=False))
        self.assert_(person.getCurrentAbsence() is absence)
        absence.addComment(AbsenceComment(None, "", resolution=False))
        self.assert_(person.getCurrentAbsence() is absence)
        absence4.addComment(AbsenceComment(None, "", resolution=True))
        self.assert_(person.getCurrentAbsence() is absence)
        # Check that you cannot re-open an absence while another absence is
        # unresolved.
        old_len = len(absence4.comments)
        self.assertRaises(ValueError, absence4.addComment,
                          AbsenceComment(None, "", resolution=False,
                                         expected_presence=dt))
        self.assertEquals(len(absence4.comments), old_len)
        self.assert_(absence4.resolved)
        self.assert_(absence4.expected_presence is None)

    def test_absence_resolved_initially(self):
        from schooltool.interfaces import IAbsence
        from schooltool.model import Person, AbsenceComment
        person = Person('John Smith')
        person.__parent__ = self.eventService

        comment = AbsenceComment(object(), "some text", resolution=True)
        absence = person.reportAbsence(comment)
        self.assert_(absence.resolved)
        self.assert_(absence in person.iterAbsences())
        self.assert_(person.getCurrentAbsence() is None)


class TestUnchanged(unittest.TestCase):

    def test(self):
        from StringIO import StringIO
        from cPickle import Pickler, Unpickler
        from schooltool.interfaces import UnchangedClass, Unchanged
        unchanged1 = UnchangedClass()
        self.assert_(unchanged1 is Unchanged)
        self.assert_(Unchanged is not UnchangedClass)

        self.assertRaises(TypeError, lambda: Unchanged < Unchanged)
        self.assertRaises(TypeError, lambda: Unchanged <= Unchanged)
        self.assertRaises(TypeError, lambda: Unchanged > Unchanged)
        self.assertRaises(TypeError, lambda: Unchanged >= Unchanged)
        self.assert_(Unchanged == Unchanged)
        self.assert_(not (Unchanged != Unchanged))
        self.assert_(Unchanged != object())
        self.assert_(not (Unchanged == object()))

        s = StringIO()
        p = Pickler(s)
        p.dump(unchanged1)
        s.seek(0)
        u = Unpickler(s)
        unchanged2 = u.load()

        self.assert_(unchanged2 is Unchanged)


class TestGroup(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup, IFaceted, IRelatable
        from schooltool.interfaces import IEventConfigurable, IEventTarget
        from schooltool.model import Group
        group = Group("root")
        verifyObject(IGroup, group)
        verifyObject(IFaceted, group)
        verifyObject(IEventTarget, group)
        verifyObject(IEventConfigurable, group)
        verifyObject(IRelatable, group)

    def test_getRelativePath(self):
        from schooltool.model import Group
        from schooltool.component import FacetManager
        group = Group('MI5')
        link = LinkStub()
        group.__links__.add(link)
        facet = FacetStub()
        FacetManager(group).setFacet(facet)

        self.assertEquals(group.getRelativePath(link),
                          'relationships/%s' % link.__name__)
        self.assertEquals(group.getRelativePath(facet),
                          'facets/%s' % facet.__name__)


class TestAbsencePersistence(EventServiceTestMixin, unittest.TestCase):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        from transaction import get_transaction
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()
        get_transaction().begin()
        self.setUpEventService()

    def tearDown(self):
        from transaction import get_transaction
        get_transaction().abort()
        self.datamgr.close()
        self.db.close()

    def test(self):
        from schooltool.model import AbsenceComment, Absence
        from transaction import get_transaction

        person = LocatableEventTargetMixin(self.eventService)
        absence = Absence(person)
        self.datamgr.root()['a'] = absence
        get_transaction().commit()

        comment = AbsenceComment(object(), "text")
        absence.addComment(comment)
        get_transaction().commit()

        datamgr2 = self.db.open()
        absence2 = datamgr2.root()['a']
        self.assertEquals(len(absence2.comments), 1)


class TestAbsence(EventServiceTestMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.model import Absence
        self.setUpEventService()
        self.person = LocatableEventTargetMixin(self.eventService)
        self.absence = Absence(self.person)

    def test(self):
        from schooltool.interfaces import IAbsence
        verifyObject(IAbsence, self.absence)
        self.assertEquals(self.absence.person, self.person)
        self.assertEquals(self.absence.comments, [])
        self.assert_(not self.absence.resolved)

    def test_addComment_raises(self):
        self.assertRaises(TypeError, self.absence.addComment, object())
        self.assertEquals(len(self.absence.comments), 0)
        self.assertEquals(len(self.eventService.events), 0)
        self.assertEquals(len(self.person.events), 0)

    def test_addComment(self):
        from schooltool.model import AbsenceComment
        from schooltool.interfaces import IAbsenceEvent
        from schooltool.interfaces import IResolvedAbsenceEvent
        group1 = LocatableEventTargetMixin(self.eventService)
        comment1 = AbsenceComment(object(), "text", absent_from=group1,
                                  resolution=False)
        self.absence.addComment(comment1)
        self.assertEquals(self.absence.comments, [comment1])
        e = self.checkOneEventReceived([self.person, group1])
        self.assert_(IAbsenceEvent.isImplementedBy(e))
        self.assert_(e.absence, self.absence)
        self.assert_(e.comment, comment1)

        self.eventService.clearEvents()
        self.person.clearEvents()
        group1.clearEvents()

        group2 = LocatableEventTargetMixin(self.eventService)
        comment2 = AbsenceComment(object(), "still absent", absent_from=group2)
        self.absence.addComment(comment2)
        e = self.checkOneEventReceived([self.person, group2])
        self.assertEquals(len(group1.events), 0)
        self.assert_(IAbsenceEvent.isImplementedBy(e))

        self.eventService.clearEvents()
        self.person.clearEvents()
        group1.clearEvents()
        group2.clearEvents()

        group3 = LocatableEventTargetMixin(self.eventService)
        # I'm not sure what absent_from might mean in a resolution comment,
        # but I will still test it does what one might expect.
        comment3 = AbsenceComment(object(), "I'll be back",
                                  resolution=True, absent_from=group3)
        self.absence.addComment(comment3)
        e = self.checkOneEventReceived([self.person, group1, group2, group3])
        self.assert_(IResolvedAbsenceEvent.isImplementedBy(e))


    def testAbsenceEvents(self):
        from schooltool.model import AbsenceEvent, AttendanceEvent
        from schooltool.model import ResolvedAbsenceEvent
        from schooltool.interfaces import IAttendanceEvent
        from schooltool.interfaces import IAbsenceEvent
        from schooltool.interfaces import IResolvedAbsenceEvent
        comment = object()
        event = AttendanceEvent(self.absence, comment)
        verifyObject(IAttendanceEvent, event)
        self.assert_(event.absence is self.absence)
        self.assert_(event.comment is comment)

        event = AbsenceEvent(self.absence, comment)
        verifyObject(IAbsenceEvent, event)
        verifyObject(IAttendanceEvent, event)

        event = ResolvedAbsenceEvent(self.absence, comment)
        verifyObject(IResolvedAbsenceEvent, event)
        verifyObject(IAttendanceEvent, event)


    def testAbsenceComment(self):
        from schooltool.model import AbsenceComment
        from schooltool.interfaces import IAbsenceComment, Unchanged
        reporter = object()
        text = "this person is late AGAIN"
        lower_limit = datetime.utcnow()
        comment1 = AbsenceComment(reporter, text)
        upper_limit = datetime.utcnow()
        verifyObject(IAbsenceComment, comment1)
        self.assertEquals(comment1.reporter, reporter)
        self.assertEquals(comment1.text, text)
        self.assertEquals(comment1.absent_from, None)
        self.assert_(lower_limit <= comment1.datetime <= upper_limit)
        self.assert_(comment1.resolution is Unchanged)
        self.assert_(comment1.expected_presence is Unchanged)

        dt = datetime(2003, 10, 28)
        dt2 = datetime(2003, 10, 29, 9, 0)
        group = object()
        comment2 = AbsenceComment(reporter, text, dt=dt, absent_from=group,
                                  resolution=True,
                                  expected_presence=dt2)
        self.assertEquals(comment2.reporter, reporter)
        self.assertEquals(comment2.text, text)
        self.assertEquals(comment2.absent_from, group)
        self.assertEquals(comment2.datetime, dt)
        self.assertEquals(comment2.resolution, True)
        self.assertEquals(comment2.expected_presence, dt2)


class TestAbsenceTrackerMixin(EventServiceTestMixin, EqualsSortedMixin,
                              unittest.TestCase):

    def setUp(self):
        self.setUpEventService()

    def test_interface(self):
        from schooltool.model import AbsenceTrackerMixin
        from schooltool.interfaces import IAbsenceTracker

        tr = AbsenceTrackerMixin()
        verifyObject(IAbsenceTracker, tr)

    def test_notify(self):
        from schooltool.event import EventMixin
        from schooltool.model import AbsenceTrackerMixin, ResolvedAbsenceEvent
        from schooltool.model import Absence, AbsenceEvent

        tr = AbsenceTrackerMixin()

        person1 = LocatableEventTargetMixin(self.eventService)
        absence1 = Absence(person1)
        event1 = AbsenceEvent(absence1, "wasn't me")

        self.assertEquals(list(tr.absences), [])

        tr.notify(event1)

        self.assertEquals(list(tr.absences), [absence1])

        person2 = LocatableEventTargetMixin(self.eventService)
        absence2 = Absence(person1)
        event2 = AbsenceEvent(absence2, "wasn't me")

        tr.notify(event2)
        self.assertEqualsSorted(list(tr.absences), [absence1, absence2])

        event3 = EventMixin()
        tr.notify(event3)
        self.assertEqualsSorted(list(tr.absences), [absence1, absence2])

        absence1.resolved = True
        event4 = ResolvedAbsenceEvent(absence1, "here again")
        tr.notify(event4)
        self.assertEquals(list(tr.absences), [absence2])


class TestAbsenceTrackerUtility(unittest.TestCase):

    def test_interface(self):
        from schooltool.model import AbsenceTrackerUtility
        from schooltool.interfaces import IAbsenceTrackerUtility

        util = AbsenceTrackerUtility()
        verifyObject(IAbsenceTrackerUtility, util)


class TestAbsenceTrackerFacet(unittest.TestCase):

    def test_interface(self):
        from schooltool.model import AbsenceTrackerFacet
        from schooltool.interfaces import IAbsenceTrackerFacet
        from schooltool.interfaces import IEvent, ICallAction

        facet = AbsenceTrackerFacet()
        verifyObject(IAbsenceTrackerFacet, facet)

        self.assertEquals(len(facet.eventTable), 1)
        ea = facet.eventTable[0]
        self.assert_(ICallAction.isImplementedBy(ea))
        self.assertEquals(ea.eventType, IEvent)
        self.assertEquals(ea.callback, facet.notify)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestUnchanged))
    suite.addTest(unittest.makeSuite(TestAbsencePersistence))
    suite.addTest(unittest.makeSuite(TestAbsence))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerMixin))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerUtility))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerFacet))
    return suite

if __name__ == '__main__':
    unittest.main()
