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
"""

Revision information:
$Id: test_type.py,v 1.7 2003/06/07 06:37:30 stevea Exp $
"""

import unittest
from zope.interface.type import TypeRegistry
from zope.interface import Interface, implements

def getAllForObject(reg, ob):
    all = list(reg.getAllForObject(ob))
    all.sort()
    return all

def getTypesMatching(reg, interface):
    all = list(reg.getTypesMatching(interface))
    all.sort()
    return all

class TestTypeRegistry(unittest.TestCase):

    def new_instance(self):
        return TypeRegistry()

    def test(self):
        class I1(Interface): pass
        class I2(I1): pass
        class I3(I2): pass

        reg = self.new_instance()
        self.assertEqual(len(reg), 0)

        reg.register(I2, 2)
        self.assertEqual(len(reg), 1)
        self.assertEqual(getTypesMatching(reg, None), [I2])
        self.assertEqual(getTypesMatching(reg, Interface), [I2])
        self.assertEqual(getTypesMatching(reg, I1), [I2])
        self.assertEqual(getTypesMatching(reg, I2), [I2])
        self.assertEqual(getTypesMatching(reg, I3), [])

        class C1: implements(I1)
        class C2: implements(I2)
        class C3: implements(I3)
        class C: pass

        self.assertEqual(getAllForObject(reg, C1()), [])
        self.assertEqual(getAllForObject(reg, C2()), [2])
        self.assertEqual(getAllForObject(reg, C3()), [2])
        self.assertEqual(getAllForObject(reg,  C()), [])

        self.assertEqual(reg.get(I1), None)
        self.assertEqual(reg.get(I2), 2)
        self.assertEqual(reg.get(I3), None)

        reg.register(I1, 1)
        self.assertEqual(len(reg), 2)
        self.assertEqual(getTypesMatching(reg, None), [I1, I2])
        self.assertEqual(getTypesMatching(reg, Interface), [I1, I2])
        self.assertEqual(getTypesMatching(reg, I1), [I1, I2])
        self.assertEqual(getTypesMatching(reg, I2), [I2])
        self.assertEqual(getTypesMatching(reg, I3), [])

        self.assertEqual(getAllForObject(reg, C1()), [1])
        self.assertEqual(getAllForObject(reg, C2()), [1, 2])
        self.assertEqual(getAllForObject(reg, C3()), [1, 2])
        self.assertEqual(getAllForObject(reg,  C()), [])

        self.assertEqual(reg.get(I1), 1)
        self.assertEqual(reg.get(I2), 2)
        self.assertEqual(reg.get(I3), None)

        reg.register(I3, 3)
        self.assertEqual(len(reg), 3)
        self.assertEqual(getTypesMatching(reg, None), [I1, I2, I3])
        self.assertEqual(getTypesMatching(reg, Interface), [I1, I2, I3])
        self.assertEqual(getTypesMatching(reg, I1), [I1, I2, I3])
        self.assertEqual(getTypesMatching(reg, I2), [I2, I3])
        self.assertEqual(getTypesMatching(reg, I3), [I3])

        self.assertEqual(getAllForObject(reg, C1()), [1])
        self.assertEqual(getAllForObject(reg, C2()), [1, 2])
        self.assertEqual(getAllForObject(reg, C3()), [1, 2, 3])
        self.assertEqual(getAllForObject(reg,  C()), [])

        self.assertEqual(reg.get(I1), 1)
        self.assertEqual(reg.get(I2), 2)
        self.assertEqual(reg.get(I3), 3)

        reg.unregister(I3)
        self.assertEqual(len(reg), 2)
        self.assertEqual(getTypesMatching(reg, None), [I1, I2])
        self.assertEqual(getTypesMatching(reg, Interface), [I1, I2])
        self.assertEqual(getTypesMatching(reg, I1), [I1, I2])
        self.assertEqual(getTypesMatching(reg, I2), [I2])
        self.assertEqual(getTypesMatching(reg, I3), [])

        self.assertEqual(getAllForObject(reg, C1()), [1])
        self.assertEqual(getAllForObject(reg, C2()), [1, 2])
        self.assertEqual(getAllForObject(reg, C3()), [1, 2])
        self.assertEqual(getAllForObject(reg,  C()), [])

        self.assertEqual(reg.get(I1), 1)
        self.assertEqual(reg.get(I2), 2)
        self.assertEqual(reg.get(I3), None)

    def testSetdefault(self):
        class I(Interface):
            pass
        reg = TypeRegistry()
        x = reg.setdefault(I, 1)
        y = reg.setdefault(I, 2)
        self.assertEqual(x, y)
        self.assertEqual(x, 1)

    def testDup(self):
        class I1(Interface): pass
        class I2(I1): pass
        class I3(I1): pass
        class I4(I2, I3): pass
        class C1: implements(I1)
        class C2: implements(I2)
        class C3: implements(I3)
        class C4: implements(I4)
        class C5: implements(I1, I2, I3, I4)
        class C: pass

        reg = TypeRegistry()
        reg.register(I1, 1)
        reg.register(I2, 2)
        reg.register(I3, 3)

        self.assertEqual(getAllForObject(reg, C1()), [1])
        self.assertEqual(getAllForObject(reg, C2()), [1, 2])
        self.assertEqual(getAllForObject(reg, C3()), [1, 3])
        self.assertEqual(getAllForObject(reg, C4()), [1, 2, 3])
        self.assertEqual(getAllForObject(reg, C5()), [1, 2, 3])
        self.assertEqual(getAllForObject(reg,  C()), [])

    def testBadRequire(self):
        registry = TypeRegistry()
        self.assertRaises(TypeError, registry.register, 42, '')

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(TestTypeRegistry)

if __name__=='__main__':
    unittest.TextTestRunner().run(test_suite())
