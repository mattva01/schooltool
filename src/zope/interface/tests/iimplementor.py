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
$Id: iimplementor.py,v 1.4 2004/03/30 22:01:34 jim Exp $
"""

import unittest
from zope.interface import Interface

class R1(Interface): pass
class R12(Interface): pass
class R2(R1): pass
class R3(R2): pass
class R4(R3): pass

class P1(Interface): pass
class P2(P1): pass
class P3(P2): pass
class P4(P3): pass

class TestIImplementorRegistry(unittest.TestCase):

    def _new(self):
        # subclass must define method to return registry
        raise NotImplementedError

    def testImplementsIImplementorRegistry(self):
        from zope.interface.verify import verifyObject
        from zope.interface.implementor import IImplementorRegistry

        registry = self._new()
        verifyObject(IImplementorRegistry, registry)

    def __registry(self):
        registry = self._new()
        registry.register(P3, 'C3')
        return registry

    def test_get(self):
        registry = self.__registry()

        for P in [P1, P2, P3]:
            self.assertEqual(registry.get(P), 'C3')

        self.assertEqual(registry.get(P4), None)

        registry.register(P1, 'C1')
        registry.register(P2, 'C3')

    def testBadProvide(self):
        registry = self.__registry()
        self.assertRaises(TypeError, registry.register, None, '')

    def test_getRegisteredMatching(self):
        registry = self.__registry()
        self.assertEqual(list(registry.getRegisteredMatching()),
                         [(P3, 'C3')])
