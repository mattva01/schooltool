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


class ApplicationObjectsTestMixin(unittest.TestCase):
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


class TestPerson(EventServiceTestMixin, ApplicationObjectsTestMixin,
                 EqualsSortedMixin):

    def newObject(self):
        from schooltool.model import Person
        return Person('John Smith')

    def test(self):
        from schooltool.interfaces import IPerson
        verifyObject(IPerson, self.newObject())

    def test_getRelativePath(self):
        from schooltool.model import Person
        from schooltool.absence import AbsenceComment
        from schooltool.component import FacetManager
        person = Person('John Smith')
        person.__parent__ = self.eventService
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

        comment = AbsenceComment(object(), "some text", ended=True,
                                 resolved=True)
        absence = person.reportAbsence(comment)
        self.assert_(absence.ended)
        self.assert_(absence.resolved)
        self.assert_(absence in person.iterAbsences())
        self.assert_(person.getCurrentAbsence() is None)


class TestGroup(ApplicationObjectsTestMixin):

    def newObject(self):
        from schooltool.model import Group
        return Group("root")

    def test(self):
        from schooltool.interfaces import IGroup
        verifyObject(IGroup, self.newObject())


class TestResource(ApplicationObjectsTestMixin):

    def newObject(self):
        from schooltool.model import Resource
        return Resource("Room 3")

    def test(self):
        from schooltool.interfaces import IResource
        resource = self.newObject()
        verifyObject(IResource, resource)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestResource))
    return suite

if __name__ == '__main__':
    unittest.main()
