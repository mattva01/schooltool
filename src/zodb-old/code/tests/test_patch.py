##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
from zodb.code.patch import NameFinder, convert
from zodb.code.tests import atestmodule

import unittest
from types import FunctionType as function

class TestNameFinder(unittest.TestCase):

    def testNameFinder(self):
        nf = NameFinder(atestmodule)
        names = nf.names()
        for name in ("Foo", "Bar", "aFunc", "anotherFunc",
                     "Foo.meth", "Foo.Nested", "Bar.bar",
                     "Foo.Nested.bar"):
            self.assert_(name in names)
        for name in ("aFunc.nestedFunc", "anotherFunc.NotFound"):
            self.assert_(name not in names)

class TestPatch(unittest.TestCase):

    def testPatch(self):
        # verify obvious facts of object identity
        self.assert_(atestmodule.Bar is atestmodule.Sub.__bases__[0])
        self.assert_(atestmodule.aFunc is atestmodule.foo[0])

        moddict = atestmodule.__dict__
        convert(atestmodule, {})
        newdict = atestmodule.__dict__

        L1 = moddict.keys()
        L2 = newdict.keys()
        L1.sort()
        L2.sort()
        self.assertEqual(L1, L2)

        self.assertEqual(atestmodule.__dict__, atestmodule.aFunc.func_globals)

        # make sure object identity is maintained by patch
        Bar = newdict["Bar"]
        Bar_as_base = newdict["Sub"].__bases__[0]
        self.assert_(Bar is Bar_as_base)

        self.assert_(newdict["aFunc"] is newdict["foo"][0])

        # The patch should not touch modules, functions, etc. that
        # are imported from other modules.
        import zodb.utils
        for name in dir(zodb.utils):
            obj = getattr(zodb.utils, name)
            if isinstance(obj, type) or isinstance(obj, function):
                self.assert_(obj is newdict[name])

def test_suite():
    s = unittest.TestSuite()
    for c in TestNameFinder, TestPatch:
        s.addTest(unittest.makeSuite(c))
    return s
