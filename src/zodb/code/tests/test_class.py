##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
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

from zodb.code.tests.test_module import TestBase

from transaction import get_transaction
from persistent.cPersistence import CHANGED, UPTODATE

class TestClass(TestBase):

    # TODO
    # test classes with getstate and setstate
    # make sure class invalidation works correctly

    class_with_init = """class Foo:
    def __init__(self, arg):
        self.var = arg""" "\n"

    def _load_path(self, path):
        # Load an object from a new connection given a database path.
        root = self.db.open().root()
        obj = root
        for part in path.split("."):
            try:
                obj = obj[part]
            except TypeError:
                obj = getattr(obj, part)
        return obj

    def _load_name(self, name):
        # Load a class from a new connection given a dotted name
        i = name.rfind(".")
        module = name[:i]
        klass = name[i+1:]
        # The following depends entirely on the internals of the
        # implementation.
        return self._load_path("registry._mgrs.%s._module.%s"
                               % (module, klass))

    def testClassWithInit(self):
        self.registry.newModule("testclass", self.class_with_init)
        get_transaction().commit()
        import testclass
        x = testclass.Foo(12)
        self.assertEqual(x.var, 12)

        Foo2 = self._load_name("testclass.Foo")
        y = Foo2(12)
        self.assertEqual(y.var, 12)

    class_and_instance = """class Foo:
    def __init__(self, arg):
        self.var = arg

    # The class must have a getinitargs because the instance
    # will be pickled during module conversion.

    def __getinitargs__(self):
        return self.var,

y = Foo(11)
x = Foo(12)""" "\n"

    def testClassAndInstance(self):
        self.registry.newModule("testclass", self.class_and_instance)
        get_transaction().commit()
        import testclass
        self.assertEqual(testclass.x.var, 12)

        Foo2 = self._load_name("testclass.Foo")
        self.assertEqual(Foo2(12).var, 12)
        x = self._load_name("testclass.x")
        self.assertEqual(x.var, 12)
        y = self._load_name("testclass.y")
        self.assertEqual(y.var, 11)

        self.assert_(not hasattr(x, "_p_oid"))
        self.assert_(not hasattr(y, "_p_oid"))
        x._p_oid = 1234
        y._p_oid = 4321

    class_interface = """class Foo:
    __implements__ = 1""" + "\n"

    def testClassInterface(self):
        # this doesn't do a proper zope interface, but we're really
        # only concerned about handling of the __implements__ attribute.
        self.registry.newModule("testclass", self.class_interface)
        get_transaction().commit()
        import testclass
        obj = testclass.Foo()
        self.assertEqual(obj.__implements__, 1)

    cross_module_import = "from testclass import Foo"

    def testCrossModuleImport(self):
        self.registry.newModule("testclass", self.class_with_init)
        get_transaction().commit()
        self.registry.newModule("another", self.cross_module_import)
        get_transaction().commit()

    update_in_place1 = """class Foo:
    def meth(self, arg):
        return arg * 3""" "\n"

    update_in_place2 = """class Foo:
    def meth(self, arg):
        return arg + 3""" "\n"

    def testUpdateInPlace(self):
        self.registry.newModule("testclass", self.update_in_place1)
        get_transaction().commit()
        import testclass
        inst = testclass.Foo()
        self.assertEqual(inst.meth(4), 12)

        Foo2 = self._load_name("testclass.Foo")
        inst2 = Foo2()
        self.assertEqual(inst2.meth(4), 12)

        self.registry.updateModule("testclass", self.update_in_place2)
        get_transaction().commit()
        self.assertEqual(inst.meth(4), 7)

        # The old instance's connection hasn't processed the
        # invalidation yet.
        self.assertEqual(inst2.meth(4), 12)
        self.assertEqual(Foo2().meth(4), 12)
        inst2.__class__._p_jar.sync()
        self.assertEqual(inst2.meth(4), 7)
        self.assertEqual(Foo2().meth(4), 7)

    parent1 = """class Foo(object):
    def meth(self, arg):
        return arg * 2""" "\n"

    parent2 = """class Foo(object):
    def meth(self, arg):
        return arg // 2""" "\n"

    child = """import parent

class Bar(parent.Foo):
    def meth(self, arg):
        return super(Bar, self).meth(arg) + 5""" "\n"

    def testInheritanceAcrossModules(self):
        self.registry.newModule("parent", self.parent1)
        self.registry.newModule("child", self.child)
        get_transaction().commit()
        import child
        self.assertEqual(child.Bar().meth(3), 3*2+5)
        self.registry.updateModule("parent", self.parent2)
        get_transaction().commit()
        self.assertEqual(child.Bar().meth(3), 3//2+5)

        Bar = self._load_name("child.Bar")
        self.assertEqual(Bar().meth(3), 3//2+5)

    persist = """from persistence import Persistent
class Foo(Persistent):
    pass""" "\n"

    def testPersistentSubclass(self):
        self.registry.newModule("persist", self.persist)
        get_transaction().commit()
        import persist
        # Verify that the instances are persistent and that the
        # _p_ namespace is separate.
        obj = persist.Foo()
        foo_oid = persist.Foo._p_oid
        self.assertEqual(obj._p_oid, None)
        obj._p_oid = 1
        self.assertEqual(obj._p_oid, 1)
        self.assertEqual(persist.Foo._p_oid, foo_oid)

    save_persist = """from persist import Foo
x = Foo()
"""

    def testSavePersistentSubclass(self):
        self.registry.newModule("persist", self.persist)
        get_transaction().commit()
        import persist
        self.registry.newModule("save_persist", self.save_persist)
        get_transaction().commit()
        import save_persist

    def XXXtestUpdateClassAttribute(self):
        self.registry.newModule("parent", self.parent1)
        get_transaction().commit()
        import parent
        parent.Foo.attr = 2
        self.assertEqual(parent.Foo._p_state, CHANGED)
        get_transaction().commit()
        self.assertEqual(parent.Foo._p_state, UPTODATE)

        Foo = self._load_name("parent.Foo")
        self.assertEqual(Foo.attr, 2)

def test_suite():
    return unittest.makeSuite(TestClass)
