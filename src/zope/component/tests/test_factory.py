##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Factory-related Tests

$Id$
"""
import unittest
from zope.interface import Interface, implements
from zope.interface.interfaces import IDeclaration

from zope.component import createObject, getFactoryInterfaces, getFactoriesFor
from zope.component import getService, servicenames
from zope.component.interfaces import IFactory
from zope.component.factory import Factory
from placelesssetup import PlacelessSetup

class IFunction(Interface):
    pass

class IKlass(Interface):
    pass

class Klass(object):
    implements(IKlass)

    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw


class TestFactory(unittest.TestCase):

    def setUp(self):
        self._factory = Factory(Klass, 'Klass', 'Klassier')
        self._factory2 = Factory(lambda x: x, 'Func', 'Function')
        self._factory3 = Factory(lambda x: x, 'Func', 'Function', (IFunction,))

    def testCall(self):
        kl = self._factory(3, foo=4)
        self.assert_(isinstance(kl, Klass))
        self.assertEqual(kl.args, (3, ))
        self.assertEqual(kl.kw, {'foo': 4})
        self.assertEqual(self._factory2(3), 3)
        self.assertEqual(self._factory3(3), 3)

    def testTitleDescription(self):
        self.assertEqual(self._factory.title, 'Klass')
        self.assertEqual(self._factory.description, 'Klassier')
        self.assertEqual(self._factory2.title, 'Func')
        self.assertEqual(self._factory2.description, 'Function')
        self.assertEqual(self._factory3.title, 'Func')
        self.assertEqual(self._factory3.description, 'Function')

    def testGetInterfaces(self):
        implemented = self._factory.getInterfaces()
        self.assert_(implemented.isOrExtends(IKlass))
        self.assertEqual(list(implemented), [IKlass])
        self.assertEqual(implemented.__name__,
                         'zope.component.tests.test_factory.Klass')

        implemented2 = self._factory2.getInterfaces()
        self.assertEqual(list(implemented2), [])
        self.assertEqual(implemented2.__name__, '<lambda>')

        implemented3 = self._factory3.getInterfaces()
        self.assertEqual(list(implemented3), [IFunction])
        self.assertEqual(implemented3.__name__, '<lambda>')


class TestFactoryZAPIFunctions(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        super(TestFactoryZAPIFunctions, self).setUp()
        self.factory = Factory(Klass, 'Klass', 'Klassier')
        utilityService = getService(servicenames.Utilities)
        utilityService.provideUtility(IFactory, self.factory, 'klass')

    def testCreateObject(self):
        kl = createObject(None, 'klass', 3, foo=4)
        self.assert_(isinstance(kl, Klass))
        self.assertEqual(kl.args, (3, ))
        self.assertEqual(kl.kw, {'foo': 4})

    def testGetFactoryInterfaces(self):
        implemented = getFactoryInterfaces('klass')
        self.assert_(implemented.isOrExtends(IKlass))
        self.assertEqual([iface for iface in implemented], [IKlass])

    def testGetFactoriesFor(self):
        self.assertEqual(list(getFactoriesFor(IKlass)),
                         [('klass', self.factory)])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TestFactory),
        unittest.makeSuite(TestFactoryZAPIFunctions)
        ))

if __name__=='__main__':
    unittest.main(defaultTest='test_suite')

