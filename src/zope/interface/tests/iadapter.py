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
$Id: iadapter.py,v 1.4 2003/05/03 16:37:26 jim Exp $
"""

import unittest

from zope.interface import Interface, directlyProvides

class R1(Interface): pass
class R12(Interface): pass
class R2(R1): pass
class R3(R2): pass
class R4(R3): pass

class P1(Interface): pass
class P2(P1): pass
class P3(P2): pass
class P4(P3): pass

class TestIAdapterRegistry(unittest.TestCase):

    def _new(self):
        # subclass should override to return registry to test
        pass

    def testImplementsIAdapterRegistry(self):
        from zope.interface.verify import verifyObject
        from zope.interface.interfaces import IAdapterRegistry

        registry = self._new()

        verifyObject(IAdapterRegistry, registry)

    def __registery(self):
        registry = self._new()

        registry.register(None, P3, 'default P3')
        registry.register(Interface, P3, 'any P3')
        registry.register(R2, P3, 'R2 P3')

        return registry

    def testBadRequire(self):
        registry = self._new()
        self.assertRaises(TypeError, registry.register, 42, P3, '')

    def testBadProvide(self):
        registry = self._new()
        self.assertRaises(TypeError, registry.register, R2, None, '')


    def test_get(self):
        registry = self.__registery()

        for R in [R2, R3, R4, (R12, R2), (R12, R4)]:
            for P in [P1, P2, P3]:
                self.assertEqual(registry.get((R, P)), 'R2 P3')

        for R in [None, R1, R2, R3, R4, (R12, R2), (R12, R4)]:
            self.assertEqual(registry.get((R, P4)), None)

        for P in [P1, P2, P3]:
            self.assertEqual(registry.get((R1, P)), 'any P3')

        for P in [P1, P2, P3]:
            self.assertEqual(registry.get((None, P)), 'default P3')

    def test_getForObject(self):
        registry = self.__registery()

        class C: pass
        c = C()

        for R in [R2, R3, R4, (R12, R2), (R12, R4)]:
            directlyProvides(c, R)
            for P in [P1, P2, P3]:
                self.assertEqual(registry.getForObject(c, P), 'R2 P3')

        directlyProvides(c, R1)
        for P in [P1, P2, P3]:
            self.assertEqual(registry.getForObject(c, P), 'any P3')

        c = C()
        for P in [P1, P2, P3]:
            self.assertEqual(registry.getForObject(c, P), 'default P3')

    def test_get_w_filter(self):
        registry = self.__registery()

        for R in [R2, R3, R4, (R12, R2), (R12, R4)]:
            for P in [P1, P2, P3]:
                self.assertEqual(
                    registry.get((R, P), filter=lambda o: o.startswith('a')),
                    'any P3')
                self.assertEqual(
                    registry.get((R, P), filter=lambda o: o.startswith('d')),
                    'default P3')
                self.assertEqual(
                    registry.get((R, P), filter=lambda o: o.startswith('z')),
                    None)

    def test_getForObject_w_filter(self):
        registry = self.__registery()

        class C: pass
        c = C()

        for R in [R2, R3, R4, (R12, R2), (R12, R4)]:
            directlyProvides(c, R)
            for P in [P1, P2, P3]:
                self.assertEqual(
                    registry.getForObject(c, P,
                                          filter=lambda o: o.startswith('a')),
                    'any P3')
                self.assertEqual(
                    registry.getForObject(c, P,
                                          filter=lambda o: o.startswith('d')),
                    'default P3')
                self.assertEqual(
                    registry.getForObject(c, P,
                                          filter=lambda o: o.startswith('z')),
                    None)

    def test_getRegistered(self):
        registry = self.__registery()

        # Get something that was registered directly
        self.assertEqual(registry.getRegistered(R2, P3), 'R2 P3')
        self.assertEqual(registry.getRegistered(Interface, P3), 'any P3')
        self.assertEqual(registry.getRegistered(None, P3), 'default P3')

        # this mustn't return anything that was not registered directly
        self.assertEqual(registry.getRegistered(R3, P3), None)
        self.assertEqual(registry.getRegistered(R2, P2), None)

    def test_getRegisteredMatching_all(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching())
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)

    def test_getRegisteredMatching_required_R1(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            required_interfaces = (R1, )
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)

    def test_getRegisteredMatching_required_multiple(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            required_interfaces = (R12, R2)
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)

    def test_getRegisteredMatching_provided_P1(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            provided_interfaces = (P1, )
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)

    def test_getRegisteredMatching_provided_P2(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            provided_interfaces = (P3, )
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)

    def test_getRegisteredMatching_required_and_provided_1(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            required_interfaces = (R4, R12),
            provided_interfaces = (P1, ),
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)

    def test_getRegisteredMatching_required_and_provided_2(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            required_interfaces = (R4, R12),
            provided_interfaces = (P3, ),
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)


    def test_getRegisteredMatching_required_and_provided_exact(self):
        registry = self.__registery()

        got = list(registry.getRegisteredMatching(
            required_interfaces = (R2, ),
            provided_interfaces = (P3, ),
            ))
        got.sort()
        expect = [
            (None, P3, 'default P3'),
            (Interface, P3, 'any P3'),
            (R2, P3, 'R2 P3'),
            ]
        expect.sort()
        self.assertEqual(got, expect)
