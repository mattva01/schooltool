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
Unit tests for schooltool.absence

$Id$
"""

import unittest
from datetime import datetime
from zope.interface.verify import verifyObject
from schooltool.tests.utils import EventServiceTestMixin, EqualsSortedMixin
from schooltool.tests.utils import LocatableEventTargetMixin

__metaclass__ = type


class TestAbsencePersistence(EventServiceTestMixin, unittest.TestCase):

    def setUp(self):
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        import transaction
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()
        transaction.begin()
        self.setUpEventService()

    def tearDown(self):
        import transaction
        transaction.abort()
        self.datamgr.close()
        self.db.close()

    def test(self):
        from schooltool.absence import AbsenceComment, Absence
        import transaction

        person = LocatableEventTargetMixin(self.eventService)
        absence = Absence(person)
        self.datamgr.root()['a'] = absence
        transaction.commit()

        comment = AbsenceComment(object(), "text")
        absence.addComment(comment)
        transaction.commit()

        datamgr2 = self.db.open()
        absence2 = datamgr2.root()['a']
        self.assertEquals(len(absence2.comments), 1)


class TestAbsence(EventServiceTestMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.absence import Absence
        self.setUpEventService()
        self.person = LocatableEventTargetMixin(self.eventService)
        self.person.getCurrentAbsence = lambda: None
        self.absence = Absence(self.person)

    def test(self):
        from schooltool.interfaces import IAbsence
        verifyObject(IAbsence, self.absence)
        self.assertEquals(self.absence.person, self.person)
        self.assertEquals(self.absence.comments, [])
        self.assert_(not self.absence.ended)
        self.assert_(not self.absence.resolved)

    def test_addComment_raises(self):
        self.assertRaises(TypeError, self.absence.addComment, object())
        self.assertEquals(len(self.absence.comments), 0)
        self.assertEquals(len(self.eventService.events), 0)
        self.assertEquals(len(self.person.events), 0)

    def test_addComment_twice(self):
        from schooltool.absence import Absence, AbsenceComment
        comment = AbsenceComment()
        self.absence.addComment(comment)
        self.assertRaises(ValueError, self.absence.addComment, comment)

        comment = AbsenceComment()
        self.absence.addComment(comment)
        absence = Absence(self.person)
        self.assertRaises(ValueError, absence.addComment, comment)

    def test_addComment(self):
        from schooltool.absence import AbsenceComment
        from schooltool.interfaces import IAbsenceEvent
        from schooltool.interfaces import IAbsenceEndedEvent
        group1 = LocatableEventTargetMixin(self.eventService)
        comment1 = AbsenceComment(object(), "text", absent_from=group1,
                                  ended=False)
        self.absence.addComment(comment1)
        self.assertEquals(self.absence.comments, [comment1])
        e = self.checkOneEventReceived([self.person, group1])
        self.assert_(IAbsenceEvent.providedBy(e))
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
        self.assert_(IAbsenceEvent.providedBy(e))

        self.eventService.clearEvents()
        self.person.clearEvents()
        group1.clearEvents()
        group2.clearEvents()

        group3 = LocatableEventTargetMixin(self.eventService)
        # I'm not sure what absent_from might mean in a ended comment,
        # but I will still test it does what one might expect.
        comment3 = AbsenceComment(object(), "I'll be back",
                                  ended=True, absent_from=group3)
        self.absence.addComment(comment3)
        e = self.checkOneEventReceived([self.person, group1, group2, group3])
        self.assert_(IAbsenceEndedEvent.providedBy(e))

    def test_addComment_resolves(self):
        from schooltool.absence import AbsenceComment
        from schooltool.interfaces import Unchanged
        self.assert_(not self.absence.resolved)
        self.assert_(not self.absence.ended)
        # Cannot resolve unended absences
        self.assertRaises(ValueError, self.absence.addComment,
                          AbsenceComment(resolved=True))
        self.assert_(not self.absence.resolved)
        self.assert_(not self.absence.ended)
        self.absence.addComment(AbsenceComment(resolved=True, ended=True))
        self.assert_(self.absence.ended)
        self.assert_(self.absence.resolved)
        self.absence.addComment(AbsenceComment(resolved=Unchanged))
        self.assert_(self.absence.resolved)
        self.absence.addComment(AbsenceComment(resolved=False))
        self.assert_(not self.absence.resolved)
        self.absence.addComment(AbsenceComment(resolved=Unchanged))
        self.assert_(not self.absence.resolved)
        self.absence.addComment(AbsenceComment(resolved=True))
        self.assert_(self.absence.resolved)

    def test_addComment_reopening_clears_resolution(self):
        from schooltool.absence import AbsenceComment
        from schooltool.interfaces import Unchanged
        self.absence.addComment(AbsenceComment(resolved=True, ended=True))
        self.assert_(self.absence.resolved)
        self.absence.addComment(AbsenceComment(ended=False))
        self.assert_(not self.absence.resolved)

    def testAbsenceEvents(self):
        from schooltool.absence import AbsenceEvent, AttendanceEvent
        from schooltool.absence import AbsenceEndedEvent
        from schooltool.interfaces import IAttendanceEvent
        from schooltool.interfaces import IAbsenceEvent
        from schooltool.interfaces import IAbsenceEndedEvent
        comment = object()
        event = AttendanceEvent(self.absence, comment)
        verifyObject(IAttendanceEvent, event)
        self.assert_(event.absence is self.absence)
        self.assert_(event.comment is comment)

        event = AbsenceEvent(self.absence, comment)
        verifyObject(IAbsenceEvent, event)
        verifyObject(IAttendanceEvent, event)

        event = AbsenceEndedEvent(self.absence, comment)
        verifyObject(IAbsenceEndedEvent, event)
        verifyObject(IAttendanceEvent, event)

    def testAbsenceComment(self):
        from schooltool.absence import AbsenceComment
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
        self.assert_(comment1.ended is Unchanged)
        self.assert_(comment1.resolved is Unchanged)
        self.assert_(comment1.expected_presence is Unchanged)

        dt = datetime(2003, 10, 28)
        dt2 = datetime(2003, 10, 29, 9, 0)
        group = object()
        comment2 = AbsenceComment(reporter, text, dt=dt, absent_from=group,
                                  ended=True, resolved=False,
                                  expected_presence=dt2)
        self.assertEquals(comment2.reporter, reporter)
        self.assertEquals(comment2.text, text)
        self.assertEquals(comment2.absent_from, group)
        self.assertEquals(comment2.datetime, dt)
        self.assertEquals(comment2.ended, True)
        self.assertEquals(comment2.resolved, False)
        self.assertEquals(comment2.expected_presence, dt2)

        comment3 = AbsenceComment(ended=0, resolved=1)
        self.assert_(comment3.ended is False)
        self.assert_(comment3.resolved is True)


class TestAbsenceTrackerMixin(EventServiceTestMixin, EqualsSortedMixin,
                              unittest.TestCase):

    def setUp(self):
        self.setUpEventService()

    def test_interface(self):
        from schooltool.absence import AbsenceTrackerMixin
        from schooltool.interfaces import IAbsenceTracker

        tr = AbsenceTrackerMixin()
        verifyObject(IAbsenceTracker, tr)

    def test_notify(self):
        from schooltool.event import EventMixin
        from schooltool.absence import AbsenceTrackerMixin, AbsenceEndedEvent
        from schooltool.absence import Absence, AbsenceEvent

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

        absence1.ended = True
        event4 = AbsenceEndedEvent(absence1, "here again")
        tr.notify(event4)
        self.assertEquals(list(tr.absences), [absence2])


class TestAbsenceTrackerUtility(unittest.TestCase):

    def test_interface(self):
        from schooltool.absence import AbsenceTrackerUtility
        from schooltool.interfaces import IAbsenceTrackerUtility

        util = AbsenceTrackerUtility()
        verifyObject(IAbsenceTrackerUtility, util)


class TestAbsenceTrackerFacet(unittest.TestCase):

    def test_interface(self):
        from schooltool.absence import AbsenceTrackerFacet
        from schooltool.interfaces import IAbsenceTrackerFacet
        from schooltool.interfaces import IEvent, ICallAction

        facet = AbsenceTrackerFacet()
        verifyObject(IAbsenceTrackerFacet, facet)

        self.assertEquals(len(facet.eventTable), 1)
        ea = facet.eventTable[0]
        self.assert_(ICallAction.providedBy(ea))
        self.assertEquals(ea.eventType, IEvent)
        self.assertEquals(ea.callback, facet.notify)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAbsencePersistence))
    suite.addTest(unittest.makeSuite(TestAbsence))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerMixin))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerUtility))
    suite.addTest(unittest.makeSuite(TestAbsenceTrackerFacet))
    return suite

if __name__ == '__main__':
    unittest.main()
