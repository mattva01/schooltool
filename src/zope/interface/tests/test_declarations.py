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
"""Test the new API for making and checking interface declarations


$Id: test_declarations.py,v 1.9 2003/09/23 19:12:36 jim Exp $
"""

import unittest
from zope.interface import *
from zope.testing.doctestunit import DocTestSuite
from zope.interface import Interface

class I1(Interface): pass
class I2(Interface): pass
class I3(Interface): pass
class I4(Interface): pass
class I5(Interface): pass

class A:
    implements(I1)
class B:
    implements(I2)
class C(A, B):
    implements(I3)

class COnly(A, B):
    implementsOnly(I3)

class COnly_old(A, B):
    __implements__ = I3
    
class D(COnly):
    implements(I5)
    

class Test(unittest.TestCase):

    # Note that most of the tests are in the doc strings of the
    # declarations module.

    def test_ObjectSpecification_Simple(self):
        c = C()
        directlyProvides(c, I4)
        spec = providedBy(c)
        sig = spec.__signature__
        expect = ('zope.interface.tests.test_declarations.I4\t'
                  'zope.interface.Interface',
                  'zope.interface.tests.test_declarations.I3\t'
                  'zope.interface.tests.test_declarations.I1\t'
                  'zope.interface.tests.test_declarations.I2\t'
                  'zope.interface.Interface')
        self.assertEqual(sig, expect)

    def test_ObjectSpecification_Simple_w_only(self):
        c = COnly()
        directlyProvides(c, I4)
        spec = providedBy(c)
        sig = spec.__signature__
        expect = ('zope.interface.tests.test_declarations.I4\t'
                  'zope.interface.Interface',
                  'zope.interface.tests.test_declarations.I3\t'
                  'zope.interface.Interface')
        self.assertEqual(sig, expect)

    def test_ObjectSpecification_Simple_old_style(self):
        c = COnly_old()
        directlyProvides(c, I4)
        spec = providedBy(c)
        sig = spec.__signature__
        expect = ('zope.interface.tests.test_declarations.I4\t'
                  'zope.interface.Interface',
                  'zope.interface.tests.test_declarations.I3\t'
                  'zope.interface.Interface')
        self.assertEqual(sig, expect)

    def test_backward_compat(self):

        class C1: __implements__ = I1
        class C2(C1): __implements__ = I2, I5
        class C3(C2): __implements__ = I3, C2.__implements__

        self.assert_(C3.__implements__.__class__ is tuple)

        self.assertEqual(
            [i.getName() for i in providedBy(C3())],
            ['I3', 'I2', 'I5'],
            )

        class C4(C3):
            implements(I4)

        self.assertEqual(
            [i.getName() for i in providedBy(C4())],
            ['I4', 'I3', 'I2', 'I5'],
            )

        self.assertEqual(
            [i.getName() for i in C4.__implements__],
            ['I4', 'I3', 'I2', 'I5'],
            )

        # Note that C3.__implements__ should now be a sequence of interfaces
        self.assertEqual(
            [i.getName() for i in C3.__implements__],
            ['I3', 'I2', 'I5'],
            )
        self.failIf(C3.__implements__.__class__ is tuple)

    def test_module(self):
        import zope.interface.tests.m1
        import zope.interface.tests.m2
        directlyProvides(zope.interface.tests.m2,
                         zope.interface.tests.m1.I1,
                         zope.interface.tests.m1.I2,
                         )
        self.assertEqual(list(providedBy(zope.interface.tests.m1)),
                         list(providedBy(zope.interface.tests.m2)),
                         )

    def test_builtins(self):
        # Setup
        from zope.interface.declarations import _implements_reg
        oldint = _implements_reg.get(int)
        if oldint:
            del _implements_reg[int]
        
        
        classImplements(int, I1)
        class myint(int):
            implements(I2)

        x = 42
        self.assertEqual([i.getName() for i in providedBy(x)],
                         ['I1'])

        x = myint(42)
        directlyProvides(x, I3)
        self.assertEqual([i.getName() for i in providedBy(x)],
                         ['I3', 'I2', 'I1'])

        # cleanup
        del _implements_reg[int]

        x = 42
        self.assertEqual([i.getName() for i in providedBy(x)],
                         [])

        # cleanup
        if oldint is not None:
            _implements_reg[int] = oldint
        

def test_signature_w_no_class_interfaces():
    """
    >>> from zope.interface import *
    >>> class C:
    ...     pass
    >>> c = C()
    >>> providedBy(c).__signature__
    ''
    
    >>> class I(Interface):
    ...    pass
    >>> directlyProvides(c, I)
    >>> int(providedBy(c).__signature__
    ...     == directlyProvidedBy(c).__signature__)
    1
    """

def test_classImplement_on_deeply_nested_classes():
    """This test is in response to a bug found, which is why it's a bit
    contrived

    >>> from zope.interface import *
    >>> class B1:
    ...     pass
    >>> class B2(B1):
    ...     pass
    >>> class B3(B2):
    ...     pass
    >>> class D:
    ...     implements()
    >>> class S(B3, D):
    ...     implements()

    This failed due to a bug in the code for finding __providedBy__
    descriptors for old-style classes.

    """

def test_computeSignature():
    """Compute a specification signature

    For example::

      >>> from zope.interface import Interface
      >>> class I1(Interface): pass
      ...
      >>> class I2(I1): pass
      ...
      >>> spec = InterfaceSpecification(I2)
      >>> int(spec.__signature__ == "%s\\t%s\\t%s" % (
      ...    I2.__identifier__, I1.__identifier__,
      ...    Interface.__identifier__))
      1

    """

def test_cant_pickle_plain_specs():
    """
    >>> from pickle import dumps
    >>> dumps(InterfaceSpecification())
    Traceback (most recent call last):
    ...
    TypeError: can't pickle InterfaceSpecification objects
    >>> dumps(InterfaceSpecification(), 2)
    Traceback (most recent call last):
    ...
    TypeError: can't pickle InterfaceSpecification objects
    
    """

def test_pickle_provides_specs():
    """
    >>> from pickle import dumps, loads
    >>> a = A()
    >>> int(I2.isImplementedBy(a))
    0
    >>> directlyProvides(a, I2)
    >>> int(I2.isImplementedBy(a))
    1
    >>> a2 = loads(dumps(a))
    >>> int(I2.isImplementedBy(a2))
    1
    
    """

def test_pickle_implements_specs():
    """
    >>> from pickle import dumps, loads
    >>> class A:
    ...   implements(I1)
    >>> class B(A):
    ...   implements(I2)
    >>> names =  [i.getName() for i in implementedBy(B)]
    >>> names
    ['I2', 'I1']
    >>> old = B.__dict__['__implements__']
    >>> new = loads(dumps(old))
    >>> names =  [i.getName() for i in new]
    >>> names
    ['I2']
    >>> classImplements(A, I3)
    >>> B.__implements__ = new
    >>> names =  [i.getName() for i in implementedBy(B)]
    >>> names
    ['I2', 'I1', 'I3']
    
    """

def test_pickle_only_specs():
    """
    >>> from pickle import dumps, loads
    >>> class A:
    ...   implements(I1)
    >>> class B(A):
    ...   implementsOnly(I2)
    >>> names =  [i.getName() for i in implementedBy(B)]
    >>> names
    ['I2']
    >>> old = B.__dict__['__implements__']
    >>> new = loads(dumps(old))
    >>> names =  [i.getName() for i in new]
    >>> names
    ['I2']
    >>> classImplements(A, I3)
    >>> B.__implements__ = new
    >>> names =  [i.getName() for i in implementedBy(B)]
    >>> names
    ['I2']
    
    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Test))
    suite.addTest(DocTestSuite("zope.interface.declarations"))
    suite.addTest(DocTestSuite())
    
    return suite


if __name__ == '__main__':
    unittest.main()
