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
Unit tests for schooltool.facet

$Id$
"""

import unittest
from sets import Set
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember, IFacet, IFaceted
from schooltool.interfaces import IEventConfigurable

__metaclass__ = type

class FacetStub:
    implements(IFacet)

    def __init__(self, context=None, active=False):
        self.context = context
        self.active = active

class FacetWithEventsStub(FacetStub):
    implements(IEventConfigurable)

    def __init__(self, context=None, active=False, eventTable=None):
        FacetStub.__init__(self, context, active)
        if eventTable is None:
            eventTable = []
        self.eventTable = eventTable


class TestFacetedMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedMixin
        from schooltool.interfaces import IFaceted
        m = FacetedMixin()
        verifyObject(IFaceted, m)


class TestFacetedEventTargetMixin(unittest.TestCase):

    def test(self):
        from schooltool.facet import FacetedEventTargetMixin
        from schooltool.interfaces import IFaceted, IEventTarget
        from schooltool.interfaces import IEventConfigurable
        et = FacetedEventTargetMixin()
        verifyObject(IFaceted, et)
        verifyObject(IEventTarget, et)
        verifyObject(IEventConfigurable, et)

    def test_getEventTable(self):
        from schooltool.facet import FacetedEventTargetMixin
        from schooltool.component import setFacet
        et = FacetedEventTargetMixin()
        et.__facets__ = Set()
        et.eventTable.append(0)
        setFacet(et, FacetStub())
        setFacet(et, FacetStub(active=True))
        setFacet(et, FacetWithEventsStub(eventTable=[1]))
        setFacet(et, FacetWithEventsStub(active=True, eventTable=[2]))
        self.assertEquals(et.getEventTable(), [0, 2])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFacetedMixin))
    suite.addTest(unittest.makeSuite(TestFacetedEventTargetMixin))
    return suite

if __name__ == '__main__':
    unittest.main()
