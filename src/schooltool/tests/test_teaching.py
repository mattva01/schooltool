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
Unit tests for schooltool.teaching

$Id$
"""

import unittest
from sets import Set
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import EventServiceTestMixin
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.interfaces import IRelatable
from schooltool.relationship import RelatableMixin

__metaclass__ = type


class Relatable(LocatableEventTargetMixin, RelatableMixin):
    implements(IRelatable)

    def __init__(self, parent=None, name='does not matter'):
        LocatableEventTargetMixin.__init__(self, parent, name)
        self.__links__ = Set()


class TestTeaching(RegistriesSetupMixin, EventServiceTestMixin,
                   unittest.TestCase):

    def setUp(self):
        self.setUpEventService()
        self.setUpRegistries()

        from schooltool import relationship
        relationship.setUp()

    def tearDown(self):
        self.tearDownRegistries()

    def testURIs(self):
        from schooltool.uris import URITeaching, URITeacher, URITaught
        from schooltool.uris import verifyURI

        verifyURI(URITeaching)
        verifyURI(URITeacher)
        verifyURI(URITaught)

    def testRelationshipSchema(self):
        from schooltool.teaching import Teaching
        from schooltool.uris import URITeaching, URITeacher, URITaught

        teacher = Relatable(self.serviceManager)
        student = Relatable(self.serviceManager)

        Teaching(teacher=teacher, taught=student)

        self.assert_(teacher.listLinks(URITaught)[0].traverse() is student)
        self.assert_(student.listLinks(URITeacher)[0].traverse() is teacher)

    def testModuleSetup(self):
        from schooltool import teaching
        from schooltool.interfaces import IModuleSetup
        from schooltool.component import getFacetFactory
        verifyObject(IModuleSetup, teaching)
        teaching.setUp()
        getFacetFactory('subject_group')
        getFacetFactory('teacher_group')

    def testTeacherFacet(self):
        from schooltool.teaching import TeacherFacet
        from schooltool.uris import URITeaching, URITeacher, URITaught
        from schooltool.interfaces import IFacet, IRelationshipValencies
        from schooltool.interfaces import ICompositeTimetableProvider

        facet = TeacherFacet()

        verifyObject(IFacet, facet)
        verifyObject(IRelationshipValencies, facet)
        self.assertEquals(facet.getValencies().keys(),
                          [(URITeaching, URITeacher)])
        verifyObject(ICompositeTimetableProvider, facet)
        self.assert_((URITaught, False) in facet.timetableSource)

    def testSubjectGroupFacet(self):
        from schooltool.teaching import SubjectGroupFacet
        from schooltool.uris import URITeaching, URITaught
        from schooltool.interfaces import IFacet, IRelationshipValencies

        facet = SubjectGroupFacet()

        verifyObject(IFacet, facet)
        verifyObject(IRelationshipValencies, facet)
        self.assertEquals(facet.getValencies().keys(),
                          [(URITeaching, URITaught)])

    def testTeacherGroupFacet(self):
        from schooltool.interfaces import IFacet
        from schooltool.teaching import TeacherGroupFacet, TeacherFacet
        facet = TeacherGroupFacet()
        verifyObject(IFacet, facet)
        self.assertMembersGetFacet(facet, TeacherFacet, facet_name='teacher')

    def assertMembersGetFacet(self, valencies, facet_class, facet_name):
        from schooltool.uris import URIMembership, URIGroup
        from schooltool.facet import FacetedRelationshipSchema, FacetFactory
        valency = valencies.getValencies()[URIMembership, URIGroup]
        self.assert_(isinstance(valency.schema, FacetedRelationshipSchema))
        factory = valency.schema._factories['member']
        self.assert_(isinstance(factory, FacetFactory))
        self.assert_(factory.factory is facet_class)
        self.assertEquals(factory.facet_name, facet_name)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTeaching))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
