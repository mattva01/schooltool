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
        from schooltool.teaching import URITeaching, URITeacher, URITaught
        from schooltool.component import inspectSpecificURI

        inspectSpecificURI(URITeaching)
        inspectSpecificURI(URITeacher)
        inspectSpecificURI(URITaught)

    def testRelationshipSchema(self):
        from schooltool.teaching import Teaching
        from schooltool.teaching import URITeaching, URITeacher, URITaught

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
        getFacetFactory('Subject Group')

    def testSubjectGroupFacet(self):
        from schooltool.teaching import SubjectGroupFacet
        from schooltool.teaching import URITeaching, URITaught
        from schooltool.interfaces import IRelationshipValencies

        facet = SubjectGroupFacet()

        verifyObject(IRelationshipValencies, facet)
        self.assertEquals(facet.getValencies().keys(),
                          [(URITeaching, URITaught)])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTeaching))
    return suite

if __name__ == '__main__':
    unittest.main()
