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
Unit tests for schooltool.occupies

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


class TestOccupies(RegistriesSetupMixin, EventServiceTestMixin,
                   unittest.TestCase):

    def setUp(self):
        self.setUpEventService()
        self.setUpRegistries()

        from schooltool import relationship
        relationship.setUp()

    def tearDown(self):
        self.tearDownRegistries()

    def testURIs(self):
        from schooltool.uris import URIOccupies, URICurrentlyResides
        from schooltool.uris import URICurrentResidence
        from schooltool.uris import verifyURI

        verifyURI(URIOccupies)
        verifyURI(URICurrentlyResides)
        verifyURI(URICurrentResidence)

    def testRelationshipSchema(self):
        from schooltool.occupies import Occupies
        from schooltool.uris import URIOccupies, URICurrentlyResides, URICurrentResidence

        address = Relatable(self.serviceManager)
        student = Relatable(self.serviceManager)

        Occupies(resides=address, residence=student)

        self.assert_(address.listLinks(URICurrentResidence)[0].traverse() is student)
        self.assert_(student.listLinks(URICurrentlyResides)[0].traverse() is address)

    def testResidenceFacet(self):
        from schooltool.occupies import ResidenceFacet
        from schooltool.uris import URIOccupies, URICurrentlyResides, URICurrentResidence
        from schooltool.interfaces import IFacet, IRelationshipValencies

        facet = ResidenceFacet()

        verifyObject(IFacet, facet)
        verifyObject(IRelationshipValencies, facet)
        self.assertEquals(facet.getValencies().keys(),
                          [(URIOccupies, URICurrentResidence)])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestOccupies))
    return suite

if __name__ == '__main__':
    unittest.main()
