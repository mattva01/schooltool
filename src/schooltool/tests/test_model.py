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
from schooltool.tests.utils import EventServiceTestMixin
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


class TestPerson(EventServiceTestMixin, unittest.TestCase):

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
        absence = person.addAbsence(AbsenceComment(None, None))
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

    def test_absenteeism(self):
        from schooltool.interfaces import IAbsence
        from schooltool.model import Person, AbsenceComment
        person = Person('John Smith')
        person.__parent__ = self.eventService

        self.assert_(person.getCurrentAbsence() is None)
        self.assertEquals(list(person.iterAbsences()), [])

        self.assertRaises(TypeError, person.addAbsence, object())
        self.assert_(person.getCurrentAbsence() is None)
        self.assertEquals(list(person.iterAbsences()), [])

        comment1 = AbsenceComment(object(), "some text")
        absence = person.addAbsence(comment1)
        self.assert_(IAbsence.isImplementedBy(absence))
        self.assert_(comment1 in absence.comments)
        self.assert_(absence.person is person)
        self.assert_(absence.__parent__ is person)
        self.assert_(not absence.resolved)
        self.assert_(person.getAbsence(absence.__name__) is absence)
        self.assertRaises(KeyError, person.getAbsence, absence.__name__ + "X")
        self.assert_(absence in person.iterAbsences())
        self.assert_(person.getCurrentAbsence() is absence)

        dt = datetime(2003, 10, 28)
        comment2 = AbsenceComment(object(), "some text",
                                  expected_presence_change=dt)
        absence2 = person.addAbsence(comment2)
        self.assert_(absence2 is absence)
        self.assertEquals(absence.comments, [comment1, comment2])
        self.assertEquals(absence.expected_presence, dt)
        self.assert_(person.getCurrentAbsence() is absence)

        comment3 = AbsenceComment(None, "resolved", resolution_change=True)
        absence3 = person.addAbsence(comment3)
        self.assert_(absence3 is absence)
        self.assert_(absence.resolved)
        self.assert_(person.getCurrentAbsence() is None)

        comment4 = AbsenceComment(object(), "some text")
        absence4 = person.addAbsence(comment4)
        self.assert_(absence4 is not absence)
        self.assertEquals(absence4.comments, [comment4])
        self.assert_(person.getCurrentAbsence() is absence4)

        absence4.addComment(AbsenceComment(None, "", resolution_change=True))
        self.assert_(person.getCurrentAbsence() is None)
        absence4.addComment(AbsenceComment(None, "", resolution_change=True))
        self.assert_(person.getCurrentAbsence() is None)
        absence.addComment(AbsenceComment(None, "", resolution_change=False))
        self.assert_(person.getCurrentAbsence() is absence)
        absence.addComment(AbsenceComment(None, "", resolution_change=False))
        self.assert_(person.getCurrentAbsence() is absence)
        absence4.addComment(AbsenceComment(None, "", resolution_change=True))
        self.assert_(person.getCurrentAbsence() is absence)
        old_len = len(absence4.comments)
        self.assertRaises(ValueError, absence4.addComment,
                          AbsenceComment(None, "", resolution_change=False,
                                         expected_presence_change=dt))
        self.assertEquals(len(absence4.comments), old_len)
        self.assert_(absence4.resolved)
        self.assert_(absence4.expected_presence is None)


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


class TestAbsenteeism(EventServiceTestMixin, unittest.TestCase):

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
        from schooltool.interfaces import IAbsence, IAbsenceComment
        from schooltool.interfaces import IAbsenteeismEvent
        from schooltool.model import Absence, AbsenceComment, AbsenteeismEvent

        person = LocatableEventTargetMixin(self.eventService)
        absence = Absence(person)
        verifyObject(IAbsence, absence)
        self.assertEquals(absence.person, person)
        self.assertEquals(absence.comments, [])
        self.assert_(not absence.resolved)

        reporter = object()
        text = "some text"
        lower_limit = datetime.utcnow()
        comment1 = AbsenceComment(reporter, text)
        upper_limit = datetime.utcnow()
        verifyObject(IAbsenceComment, comment1)
        self.assertEquals(comment1.reporter, reporter)
        self.assertEquals(comment1.text, text)
        self.assertEquals(comment1.absent_from, None)
        self.assert_(lower_limit <= comment1.datetime <= upper_limit)
        self.assert_(comment1.resolution_change is None)
        self.assert_(comment1.expected_presence_change is None)

        dt = datetime(2003, 10, 28)
        dt2 = datetime(2003, 10, 29, 9, 0)
        group = object()
        comment2 = AbsenceComment(reporter, text, dt=dt, absent_from=group,
                                  resolution_change=True,
                                  expected_presence_change=dt2)
        self.assertEquals(comment2.reporter, reporter)
        self.assertEquals(comment2.text, text)
        self.assertEquals(comment2.absent_from, group)
        self.assertEquals(comment2.datetime, dt)
        self.assertEquals(comment2.resolution_change, True)
        self.assertEquals(comment2.expected_presence_change, dt2)

        absence.addComment(comment1)
        self.assertEquals(absence.comments, [comment1])
        e = self.check_one_event_received([person])
        self.assert_(IAbsenteeismEvent.isImplementedBy(e))
        self.assert_(e.absence, absence)
        self.assert_(e.comment, comment1)

        self.assertRaises(TypeError, absence.addComment, object())
        e2 = self.check_one_event_received([person])
        self.assert_(e is e2)

        self.datamgr.add(absence)
        absence._p_changed = False
        self.assert_(not absence._p_changed)
        absence.addComment(comment2)
        self.assertEquals(absence.comments, [comment1, comment2])
        self.assert_(absence._p_changed)

        event = AbsenteeismEvent(absence, comment1)
        verifyObject(IAbsenteeismEvent, event)
        self.assert_(event.absence is absence)
        self.assert_(event.comment is comment1)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestAbsenteeism))
    return suite

if __name__ == '__main__':
    unittest.main()
