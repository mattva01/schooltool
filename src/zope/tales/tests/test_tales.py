##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
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
"""TALES Tests

$Id$
"""
import unittest

from zope.tales import tales
from zope.tales.tests.simpleexpr import SimpleExpr
from zope.testing.doctestunit import DocTestSuite


class TALESTests(unittest.TestCase):

    def testIterator0(self):
        # Test sample Iterator class
        context = Harness(self)
        it = tales.Iterator('name', (), context)
        self.assert_( not it.next(), "Empty iterator")
        context._complete_()

    def testIterator1(self):
        # Test sample Iterator class
        context = Harness(self)
        it = tales.Iterator('name', (1,), context)
        context._assert_('setLocal', 'name', 1)
        self.assert_( it.next() and not it.next(), "Single-element iterator")
        context._complete_()

    def testIterator2(self):
        # Test sample Iterator class
        context = Harness(self)
        it = tales.Iterator('text', 'text', context)
        for c in 'text':
            context._assert_('setLocal', 'text', c)
        for c in 'text':
            self.assert_(it.next(), "Multi-element iterator")
        self.assert_( not it.next(), "Multi-element iterator")
        context._complete_()

    def testRegisterType(self):
        # Test expression type registration
        e = tales.ExpressionEngine()
        e.registerType('simple', SimpleExpr)
        self.assert_( e.getTypes()['simple'] == SimpleExpr)

    def testRegisterTypeUnique(self):
        # Test expression type registration uniqueness
        e = tales.ExpressionEngine()
        e.registerType('simple', SimpleExpr)
        try:
            e.registerType('simple', SimpleExpr)
        except tales.RegistrationError:
            pass
        else:
            self.assert_( 0, "Duplicate registration accepted.")

    def testRegisterTypeNameConstraints(self):
        # Test constraints on expression type names
        e = tales.ExpressionEngine()
        for name in '1A', 'A!', 'AB ':
            try:
                e.registerType(name, SimpleExpr)
            except tales.RegistrationError:
                pass
            else:
                self.assert_( 0, 'Invalid type name "%s" accepted.' % name)

    def testCompile(self):
        # Test expression compilation
        e = tales.ExpressionEngine()
        e.registerType('simple', SimpleExpr)
        ce = e.compile('simple:x')
        self.assert_( ce(None) == ('simple', 'x'), (
            'Improperly compiled expression %s.' % `ce`))

    def testGetContext(self):
        # Test Context creation
        tales.ExpressionEngine().getContext()
        tales.ExpressionEngine().getContext(v=1)
        tales.ExpressionEngine().getContext(x=1, y=2)

    def getContext(self, **kws):
        e = tales.ExpressionEngine()
        e.registerType('simple', SimpleExpr)
        return apply(e.getContext, (), kws)

    def testContext0(self):
        # Test use of Context
        se = self.getContext().evaluate('simple:x')
        self.assert_( se == ('simple', 'x'), (
            'Improperly evaluated expression %s.' % `se`))

    def testVariables(self):
        # Test variables
        ctxt = self.getContext()
        ctxt.beginScope()
        ctxt.setLocal('v1', 1)
        ctxt.setLocal('v2', 2)

        c = ctxt.vars
        self.assert_( c['v1'] == 1, 'Variable "v1"')

        ctxt.beginScope()
        ctxt.setLocal('v1', 3)
        ctxt.setGlobal('g', 1)

        c = ctxt.vars
        self.assert_( c['v1'] == 3, 'Inner scope')
        self.assert_( c['v2'] == 2, 'Outer scope')
        self.assert_( c['g'] == 1, 'Global')

        ctxt.endScope()

        c = ctxt.vars
        self.assert_( c['v1'] == 1, "Uncovered local")
        self.assert_( c['g'] == 1, "Global from inner scope")

        ctxt.endScope()


class Harness(object):
    def __init__(self, testcase):
        self._callstack = []
        self._testcase = testcase

    def _assert_(self, name, *args, **kwargs):
        self._callstack.append((name, args, kwargs))

    def _complete_(self):
        self._testcase.assert_(len(self._callstack) == 0,
                               "Harness methods called")

    def __getattr__(self, name):
        return HarnessMethod(self, name)

class HarnessMethod(object):

    def __init__(self, harness, name):
        self._harness = harness
        self._name = name

    def __call__(self, *args, **kwargs):
        name = self._name
        self = self._harness

        cs = self._callstack
        self._testcase.assert_(
            len(cs),
            'Unexpected harness method call "%s".' % name
            )
        self._testcase.assert_(
            cs[0][0] == name, 
            'Harness method name "%s" called, "%s" expected.' %
            (name, cs[0][0])
            )
        
        name, aargs, akwargs = self._callstack.pop(0)
        self._testcase.assert_(aargs == args, "Harness method arguments")
        self._testcase.assert_(akwargs == kwargs,
                                "Harness method keyword args")


def test_suite():
    suite = unittest.makeSuite(TALESTests)
    suite.addTest(DocTestSuite("zope.tales.tales"))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
