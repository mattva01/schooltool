##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import unittest
from zope.interface.tests.unitfixtures import *  # hehehe
from zope.interface.exceptions import BrokenImplementation
from zope.interface import implementedBy
from zope.interface import providedBy
from zope.interface import Interface
from zope.interface.interface import Attribute

class InterfaceTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testClassImplements(self):
        assert IC.isImplementedByInstancesOf(C)

        assert I1.isImplementedByInstancesOf(A)
        assert I1.isImplementedByInstancesOf(B)
        assert not I1.isImplementedByInstancesOf(C)
        assert I1.isImplementedByInstancesOf(D)
        assert I1.isImplementedByInstancesOf(E)

        assert not I2.isImplementedByInstancesOf(A)
        assert I2.isImplementedByInstancesOf(B)
        assert not I2.isImplementedByInstancesOf(C)

        # No longer after interfacegeddon
        # assert not I2.isImplementedByInstancesOf(D)

        assert not I2.isImplementedByInstancesOf(E)

    def testUtil(self):
        f = implementedBy
        assert IC in f(C)
        assert I1 in f(A)
        assert not I1 in f(C)
        assert I2 in f(B)
        assert not I2 in f(C)

        f = providedBy
        assert IC in f(C())
        assert I1 in f(A())
        assert not I1 in f(C())
        assert I2 in f(B())
        assert not I2 in f(C())


    def testObjectImplements(self):
        assert IC.isImplementedBy(C())

        assert I1.isImplementedBy(A())
        assert I1.isImplementedBy(B())
        assert not I1.isImplementedBy(C())
        assert I1.isImplementedBy(D())
        assert I1.isImplementedBy(E())

        assert not I2.isImplementedBy(A())
        assert I2.isImplementedBy(B())
        assert not I2.isImplementedBy(C())

        # Not after interface geddon
        # assert not I2.isImplementedBy(D())

        assert not I2.isImplementedBy(E())

    def testDeferredClass(self):
        a = A()
        self.assertRaises(BrokenImplementation, a.ma)


    def testInterfaceExtendsInterface(self):
        assert BazInterface.extends(BobInterface)
        assert BazInterface.extends(BarInterface)
        assert BazInterface.extends(FunInterface)
        assert not BobInterface.extends(FunInterface)
        assert not BobInterface.extends(BarInterface)
        assert BarInterface.extends(FunInterface)
        assert not BarInterface.extends(BazInterface)

    def testVerifyImplementation(self):
        from zope.interface.verify import verifyClass
        assert verifyClass(FooInterface, Foo)
        assert Interface.isImplementedBy(I1)

    def test_names(self):
        names = list(_I2.names()); names.sort()
        self.assertEqual(names, ['f21', 'f22', 'f23'])
        names = list(_I2.names(all=True)); names.sort()
        self.assertEqual(names, ['a1', 'f11', 'f12', 'f21', 'f22', 'f23'])

    def test_namesAndDescriptions(self):
        names = [nd[0] for nd in _I2.namesAndDescriptions()]; names.sort()
        self.assertEqual(names, ['f21', 'f22', 'f23'])
        names = [nd[0] for nd in _I2.namesAndDescriptions(1)]; names.sort()
        self.assertEqual(names, ['a1', 'f11', 'f12', 'f21', 'f22', 'f23'])

        for name, d in _I2.namesAndDescriptions(1):
            self.assertEqual(name, d.__name__)

    def test_getDescriptionFor(self):
        self.assertEqual(_I2.getDescriptionFor('f11').__name__, 'f11')
        self.assertEqual(_I2.getDescriptionFor('f22').__name__, 'f22')
        self.assertEqual(_I2.queryDescriptionFor('f33', self), self)
        self.assertRaises(KeyError, _I2.getDescriptionFor, 'f33')

    def test___getitem__(self):
        self.assertEqual(_I2['f11'].__name__, 'f11')
        self.assertEqual(_I2['f22'].__name__, 'f22')
        self.assertEqual(_I2.get('f33', self), self)
        self.assertRaises(KeyError, _I2.__getitem__, 'f33')

    def test___contains__(self):
        self.failUnless('f11' in _I2)
        self.failIf('f33' in _I2)

    def test___iter__(self):
        names = list(iter(_I2))
        names.sort()
        self.assertEqual(names, ['a1', 'f11', 'f12', 'f21', 'f22', 'f23'])

    def testAttr(self):
        description = _I2.getDescriptionFor('a1')
        self.assertEqual(description.__name__, 'a1')
        self.assertEqual(description.__doc__, 'This is an attribute')


    def testFunctionAttributes(self):
        # Make sure function attributes become tagged values.
        meth = _I1['f12']
        self.assertEqual(meth.getTaggedValue('optional'), 1)

    def test___doc___element(self):
        class I(Interface):
            "xxx"

        self.assertEqual(I.__doc__, "xxx")
        self.assertEqual(list(I), [])

        class I(Interface):
            "xxx"

            __doc__ = Attribute('the doc')

        self.assertEqual(I.__doc__, "")
        self.assertEqual(list(I), ['__doc__'])



class _I1(Interface):

    a1 = Attribute("This is an attribute")

    def f11(): pass
    def f12(): pass
    f12.optional = 1

class _I1_(_I1): pass
class _I1__(_I1_): pass

class _I2(_I1__):
    def f21(): pass
    def f22(): pass
    f23 = f22


def test_suite():
    return unittest.makeSuite(InterfaceTests)

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    main()
