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
Unit tests for schooltool.app

$Id$
"""

import unittest
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import ILocation
from schooltool.tests.utils import EqualsSortedMixin


class P(Persistent):
    pass


class Location(Persistent):

    __slots__ = '__parent__', '__name__', 'optional'
    implements(ILocation)

    def __init__(self, optional=None):
        self.__parent__ = None
        self.__name__ = None
        self.optional = optional


class TestApplication(unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.app import Application
        from schooltool.interfaces import IApplication
        from schooltool.interfaces import IEventService, IUtilityService
        from schooltool.interfaces import ITimetableSchemaService
        from schooltool.interfaces import ITimePeriodService

        a = Application()
        verifyObject(IApplication, a)

        verifyObject(IEventService, a.eventService)

        verifyObject(IUtilityService, a.utilityService)
        self.assert_(a.utilityService.__parent__ is a,
                     "__parent__ of utility service should be the application")
        self.assertEqual(a.utilityService.__name__, 'utils')

        verifyObject(ITimetableSchemaService, a.timetableSchemaService)
        self.assert_(a.timetableSchemaService.__parent__ is a)
        self.assertEqual(a.timetableSchemaService.__name__, 'ttschemas')

        verifyObject(ITimePeriodService, a.timePeriodService)
        self.assert_(a.timePeriodService.__parent__ is a)
        self.assertEqual(a.timePeriodService.__name__, 'time-periods')

    def testTraversal(self):
        from schooltool.app import Application
        a = Application()
        self.assertEqual(a.traverse('utils'), a.utilityService)
        marker = Location()
        a['foo'] = marker
        self.assertEqual(a.traverse('foo'), marker)
        a['utils'] = marker
        self.assertEqual(a.traverse('utils'), a.utilityService)
        a['ttschemas'] = marker
        self.assertEqual(a.traverse('ttschemas'), a.timetableSchemaService)
        a['time-periods'] = marker
        self.assertEqual(a.traverse('time-periods'), a.timePeriodService)

    def testRoots(self):
        from schooltool.app import Application
        a = Application()
        self.assertEqual(list(a.getRoots()), [])
        root1 = P()
        a.addRoot(root1)
        self.assertEqual(list(a.getRoots()), [root1])
        root2 = P()
        a.addRoot(root2)
        self.assertEqualsSorted(list(a.getRoots()), [root1, root2])

    def testAppObjectContainers(self):
        from schooltool.app import Application
        a = Application()
        self.assertEqual(a.keys(), [])
        self.assertRaises(KeyError, a.__getitem__, 'people')
        self.assertRaises(TypeError, a.__setitem__, 'people', P())
        location = Location()
        a['people'] = location
        self.assertEqual(a.keys(), ['people'])
        self.assertEqual(a['people'], location)
        self.assertEqual(location.__name__, 'people')
        self.assert_(location.__parent__ is a, 'location.__parent__ is a')


class TestApplicationObjectContainer(unittest.TestCase):

    def test(self):
        from schooltool.app import ApplicationObjectContainer
        from schooltool.interfaces import IApplicationObjectContainer
        factory = Location
        a = ApplicationObjectContainer(factory)
        verifyObject(IApplicationObjectContainer, a)

    def testDoingStuffToContents(self):
        from schooltool.app import ApplicationObjectContainer
        factory = Location
        a = ApplicationObjectContainer(factory)

        def case1():
            return None, a.new(), None

        def case2():
            name = 'whatever something'
            return name, a.new(name), None

        def case3():
            name = 'whatever something 2'
            return name, a.new(name, optional='yes'), 'yes'

        for case in case1, case2, case3:
            desiredname, obj, optional = case()
            name = obj.__name__
            if desiredname:
                self.assertEqual(name, desiredname)
            self.assertEqual(obj.optional, optional)
            self.assert_(obj.__parent__ is a, 'obj.__parent__ is a')
            self.assert_(a[name] is obj, 'a[name] is obj')
            self.assertEqual(a.keys(), [name])
            self.assertEqual(list(a.itervalues()), [obj])
            del a[name]
            self.assertRaises(KeyError, a.__getitem__, name)
            self.assertEqual(obj.__name__, None)
            self.assertEqual(obj.__parent__, None)

    def testNameCollision(self):
        from schooltool.app import ApplicationObjectContainer
        factory = Location
        a = ApplicationObjectContainer(factory)
        a.new('foo')
        self.assertRaises(KeyError, a.new, 'foo')

        a.new('%06i' % 4)
        for count in 1, 2, 3, 4, 5, 6, 7, 8:
            a.new()

    def testAnotherContainerTakesResponsibility(self):
        from schooltool.app import ApplicationObjectContainer
        factory = Location
        a = ApplicationObjectContainer(factory)
        obj = a.new()
        name = obj.__name__
        self.assert_(obj.__parent__ is a)
        parent = P()
        obj.__parent__ = parent
        del a[name]
        self.assert_(obj.__parent__ is parent)
        self.assertEqual(obj.__name__, name)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplication))
    suite.addTest(unittest.makeSuite(TestApplicationObjectContainer))
    return suite

if __name__ == '__main__':
    unittest.main()
