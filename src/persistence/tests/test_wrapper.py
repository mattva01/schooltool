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

from persistence import Persistent, PersistentMetaClass
from persistence.wrapper import Struct
from persistence.tests.test_persistence import DM as BaseDM, BrokenDM

class Dummy(object):

    def __init__(self, x=0):
        self.x = x

DUMMY = Dummy(42)

class DM(BaseDM):
    def setstate(self, ob):
        ob.__setstate__({'__proxied__': DUMMY})

def makeInstance(self):
    d = Dummy()
    p = Struct(d)
    return p

class Test(unittest.TestCase):

    klass = None # override in subclass

    def testSaved(self):
        p = self.klass()
        p._p_oid = '\0\0\0\0\0\0hi'
        dm = DM()
        p._p_jar = dm
        self.assertEqual(p._p_changed, 0)
        self.assertEqual(dm.called, 0)
        p.x += 1
        self.assertEqual(p._p_changed, 1)
        self.assertEqual(dm.called, 1)
        p.x += 1
        self.assertEqual(p._p_changed, 1)
        self.assertEqual(dm.called, 1)
        p._p_deactivate()
        self.assertEqual(p._p_changed, 1)
        self.assertEqual(dm.called, 1)
        p._p_deactivate()
        self.assertEqual(p._p_changed, 1)
        self.assertEqual(dm.called, 1)
        p._p_deactivate(force=True)
        # XXX deal with current cPersistence implementation
        if p._p_changed != 3:
            self.assertEqual(p._p_changed, None)
        self.assertEqual(dm.called, 1)
        p.x += 1
        self.assertEqual(p.x, 43)
        self.assertEqual(p._p_changed, 1)
        self.assertEqual(dm.called, 2)
        p._p_changed = 0
        self.assertEqual(p._p_changed, 0)
        self.assertEqual(dm.called, 2)
        self.assertEqual(p.x, 43)
        p.x += 1
        self.assertEqual(p._p_changed, 1)
        self.assertEqual(dm.called, 3)

    def testUnsaved(self):
        p = self.klass()

        self.assertEqual(p.x, 0)
        self.assertEqual(p._p_changed, 0)
        self.assertEqual(p._p_jar, None)
        self.assertEqual(p._p_oid, None)
        p.x += 1
        p.x += 1
        self.assertEqual(p.x, 2)
        self.assertEqual(p._p_changed, 0)

        p._p_deactivate()
        self.assertEqual(p._p_changed, 0)
        p._p_changed = 1
        self.assertEqual(p._p_changed, 0)
        p._p_deactivate()
        self.assertEqual(p._p_changed, 0)
        p._p_deactivate(force=True)
        self.assertEqual(p._p_changed, 0)
        if self.has_dict:
            self.failUnless(p.__dict__)
        self.assertEqual(p.x, 2)

    def testState(self):
        p = self.klass()
        d = Dummy()
        self.failUnless(p.__getstate__().has_key('__proxied__'))
        self.assertEqual(p._p_changed, 0)
        p.__setstate__({'__proxied__':d})
        self.assertEqual(p._p_changed, 0)
        if self.has_dict:
            p._v_foo = 2
        self.failUnless(p.__getstate__(), {'__proxied__': d})
        self.assertEqual(p._p_changed, 0)

    def testSetStateSerial(self):
        p = self.klass()
        p._p_serial = 12
        p.__setstate__(p.__getstate__())
        self.assertEqual(p._p_serial, 12)

    def testDirectChanged(self):
        p = self.klass()
        p._p_oid = 1
        dm = DM()
        p._p_jar = dm
        self.assertEqual(p._p_changed, 0)
        self.assertEqual(dm.called, 0)
        p._p_changed = 1
        self.assertEqual(dm.called, 1)

    def testGhostChanged(self):
        # An object is a ghost, and it's _p_changed it set to True.
        # This assignment should have no effect.
        p = self.klass()
        p._p_oid = 1
        dm = DM()
        p._p_jar = dm
        p._p_deactivate()
        self.assertEqual(p._p_state, 3)
        p._p_changed = True
        self.assertEqual(p._p_state, 3)

    def testRegistrationFailure(self):
        p = self.klass()
        p._p_oid = 1
        dm = BrokenDM()
        p._p_jar = dm
        self.assertEqual(p._p_changed, 0)
        self.assertEqual(dm.called, 0)
        try:
            p._p_changed = 1
        except NotImplementedError:
            pass
        else:
            raise AssertionError("Exception not propagated")
        self.assertEqual(dm.called, 1)
        self.assertEqual(p._p_changed, 0)

    def testLoadFailure(self):
        p = self.klass()
        p._p_oid = 1
        dm = BrokenDM()
        p._p_jar = dm
        p._p_deactivate()  # make it a ghost

        try:
            p._p_activate()
        except NotImplementedError:
            pass
        else:
            raise AssertionError("Exception not propagated")
        self.assertEqual(p._p_changed, None)

    def testActivate(self):
        p = self.klass()
        dm = DM()
        p._p_oid = 1
        p._p_jar = dm
        p._p_changed = 0
        p._p_deactivate()
        # XXX does this really test the activate method?
        p._p_activate()
        self.assertEqual(p._p_state, 0)
        self.assertEqual(p.x, 42)

    def testDeactivate(self):
        p = self.klass()
        dm = DM()
        p._p_oid = 1
        p._p_deactivate() # this deactive has no effect
        self.assertEqual(p._p_state, 0)
        p._p_jar = dm
        p._p_changed = 0
        p._p_deactivate()
        self.assertEqual(p._p_state, 3)
        p._p_activate()
        self.assertEqual(p._p_state, 0)
        self.assertEqual(p.x, 42)


# XXX to do this right and expose both IPersistent and the
# underlying object's interfaces, we'd need to use a specialized
# descriptor.  This would create to great a dependency on
# zope.interface.
#
##     def testInterface(self):
##         from persistence.interfaces import IPersistent
##         self.assert_(IPersistent.isImplementedByInstancesOf(Persistent),
##                      "%s does not implement IPersistent" % Persistent)
##         p = Persistent()
##         self.assert_(IPersistent.isImplementedBy(p),
##                      "%s does not implement IPersistent" % p)

##         self.assert_(IPersistent.isImplementedByInstancesOf(Struct),
##                      "%s does not implement IPersistent" % Struct)
##         p = self.klass()
##         self.assert_(IPersistent.isImplementedBy(p),
##                      "%s does not implement IPersistent" % p)

    def testDataManagerAndAttributes(self):
        # Test to cover an odd bug where the instance __dict__ was
        # set at the same location as the data manager in the C type.
        p = self.klass()
        p.x += 1
        p.x += 1
        self.assert_('__proxied__' in p.__dict__)
        self.assert_(p._p_jar is None)

    def testMultipleInheritance(self):
        # make sure it is possible to inherit from two different
        # subclasses of persistent.
        class A(Persistent):
            pass
        class B(Persistent):
            pass
        class C(A, B):
            pass
        class D(object):
            pass
        class E(D, B):
            pass

    def testMultipleMeta(self):
        # make sure it's possible to define persistent classes
        # with a base whose metaclass is different
        class alternateMeta(type):
            pass
        class alternate(object):
            __metaclass__ = alternateMeta
        class mixedMeta(alternateMeta, PersistentMetaClass):
            pass
        class mixed(alternate,Persistent):
            __metaclass__ = mixedMeta

    def testSlots(self):
        # Verify that Persistent classes behave the same way
        # as pure Python objects where '__slots__' and '__dict__'
        # are concerned.

        class noDict(object):
            __slots__ = ['foo']

        class shouldHaveDict(noDict):
            pass

        class p_noDict(Persistent):
            __slots__ = ['foo']

        class p_shouldHaveDict(p_noDict):
            pass

        self.assertEqual(noDict.__dictoffset__, 0)
        self.assertEqual(p_noDict.__dictoffset__, 0)

        self.assert_(shouldHaveDict.__dictoffset__ <> 0)
        self.assert_(p_shouldHaveDict.__dictoffset__ <> 0)

    def testBasicTypeStructure(self):
        # test that a persistent class has a sane C type structure
        # use P (defined below) as simplest example
        self.assertEqual(Persistent.__dictoffset__, 0)
        self.assertEqual(Persistent.__weakrefoffset__, 0)
        self.assert_(Persistent.__basicsize__ > object.__basicsize__)
        self.assert_(Struct.__dictoffset__)
        self.assert_(Struct.__weakrefoffset__)
        self.assert_(Struct.__dictoffset__ < Struct.__weakrefoffset__)
        self.assert_(Struct.__basicsize__ > Persistent.__basicsize__)

    def testDeactivateErrors(self):
        p = self.klass()
        p._p_oid = '\0\0\0\0\0\0hi'
        dm = DM()
        p._p_jar = dm

        def typeerr(*args, **kwargs):
            self.assertRaises(TypeError, p, *args, **kwargs)

        typeerr(1)
        typeerr(1, 2)
        typeerr(spam=1)
        typeerr(spam=1, force=1)

        p._p_changed = True
        class Err(object):
            def __nonzero__(self):
                raise RuntimeError

        typeerr(force=Err())

class PersistentTest(Test):

    klass = makeInstance
    has_dict = 1

    def testPicklable(self):
        import pickle

        p = self.klass()
        p.x += 1
        p2 = pickle.loads(pickle.dumps(p))
        self.assertEqual(p2.__class__, p.__class__);
        self.assertEqual(p2.__dict__['__proxied__'].__dict__,
                         p.__dict__['__proxied__'].__dict__)

def test_suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(PersistentTest))
    return s
