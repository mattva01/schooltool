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
import os
import pickle
import unittest

from persistence.dict import PersistentDict
from persistence._persistence import UPTODATE
from transaction import get_transaction

import zodb.db
from zodb.storage.mapping import MappingStorage
from zodb.code import tests # import this package, to get at __file__ reliably
from zodb.code.module \
     import ManagedRegistry, PersistentModuleImporter, PersistentPackage

# snippets of source code used by testModules
foo_src = """\
import string
x = 1
def f(y):
    return x + y
"""
quux_src = """\
from foo import x
def f(y):
    return x + y
"""
side_effect_src = """\
x = 1
def inc():
    global x
    x += 1
    return x
"""
builtin_src = """\
x = 1, 2, 3
def f():
    return len(x)
"""
nested_src = """\
def f(x):
    def g(y):
        def z(z):
            return x + y + z
        return x + y
    return g
"""

nested_err_src = nested_src + """\
g = f(3)
"""

closure_src = """\
def f(x):
    def g(y):
        return x + y
    return g

inc = f(1)
"""

class TestPersistentModuleImporter(PersistentModuleImporter):

    def __init__(self, registry):
        self._registry = registry
        self._registry._p_activate()

    def __import__(self, name, globals={}, locals={}, fromlist=[]):
        mod = self._import(self._registry, name, self._get_parent(globals),
                           fromlist)
        if mod is not None:
            return mod
        return self._saved_import(name, globals, locals, fromlist)

class TestBase(unittest.TestCase):

    def setUp(self):
        self.db = zodb.db.DB(MappingStorage())
        self.root = self.db.open().root()
        self.registry = ManagedRegistry()
        self.importer = TestPersistentModuleImporter(self.registry)
        self.importer.install()
        self.root["registry"] = self.registry
        get_transaction().commit()
        _dir, _file = os.path.split(tests.__file__)
        self._pmtest = os.path.join(_dir, "_pmtest.py")

    def tearDown(self):
        self.importer.uninstall()
        # just in case
        get_transaction().abort()

    def sameModules(self, registry):
        m1 = self.registry.modules()
        m1.sort()
        m2 = registry.modules()
        m2.sort()
        self.assertEqual(m1, m2)

    def useNewConnection(self):
        # load modules using a separate connection to test that
        # modules can be recreated from the database
        cn = self.db.open()
        reg = cn.root()["registry"]
        self.sameModules(reg)
        for name in reg.modules():
            mod = reg.findModule(name)
            mod._p_activate()
            self.assertEqual(mod._p_state, UPTODATE)
            for obj in mod.__dict__.values():
                if hasattr(obj, "_p_activate"):
                    obj._p_activate()
        # XXX somehow objects are getting registered here, but not
        # modified.  need to figure out what is going wrong, but for
        # now just abort the transaction.
        ##assert not cn._registered
        get_transaction().abort()
        cn.close()

class TestModule(TestBase):

    def testModule(self):
        self.registry.newModule("pmtest", open(self._pmtest).read())
        get_transaction().commit()
        self.assert_(self.registry.findModule("pmtest"))
        import pmtest
        pmtest._p_deactivate()
        self.assertEqual(pmtest.a, 1)
        pmtest.f(4)
        self.useNewConnection()

    def testUpdateFunction(self):
        self.registry.newModule("pmtest", "def f(x): return x")
        get_transaction().commit()
        import pmtest
        self.assertEqual(pmtest.f(3), 3)
        copy = pmtest.f
        self.registry.updateModule("pmtest", "def f(x): return x + 1")
        get_transaction().commit()
        pmtest._p_deactivate()
        self.assertEqual(pmtest.f(3), 4)
        self.assertEqual(copy(3), 4)
        self.useNewConnection()

    def testUpdateClass(self):
        self.registry.newModule("pmtest", src)
        get_transaction().commit()
        import pmtest
        inst = pmtest.Foo()
        v0 = inst.x
        v1 = inst.m()
        v2 = inst.n()
        self.assertEqual(v1 - 1, v2)
        self.assertEqual(v0 + 1, v1)
        self.registry.updateModule("pmtest", src2)
        get_transaction().commit()
        self.assertRaises(AttributeError, getattr, inst, "n")
        self.useNewConnection()

    def testModules(self):
        self.registry.newModule("foo", foo_src)
        # quux has a copy of foo.x
        self.registry.newModule("quux", quux_src)
        # bar has a reference to foo
        self.registry.newModule("bar", "import foo")
        # baz has reference to f and copy of x,
        # remember the the global x in f is looked up in foo
        self.registry.newModule("baz", "from foo import *")
        import foo, bar, baz, quux
        self.assert_(foo._p_oid is None)
        get_transaction().commit()
        self.assert_(foo._p_oid)
        self.assert_(bar._p_oid)
        self.assert_(baz._p_oid)
        self.assert_(quux._p_oid)
        self.assertEqual(foo.f(4), 5)
        self.assertEqual(bar.foo.f(4), 5)
        self.assertEqual(baz.f(4), 5)
        self.assertEqual(quux.f(4), 5)
        self.assert_(foo.f is bar.foo.f)
        self.assert_(foo.f is baz.f)
        foo.x = 42
        self.assertEqual(quux.f(4), 5)
        get_transaction().commit()
        self.assertEqual(quux.f(4), 5)
        foo._p_deactivate()
        # foo is deactivated, which means its dict is empty when f()
        # is activated, how do we guarantee that foo is also
        # activated?
        self.assertEqual(baz.f(4), 46)
        self.assertEqual(bar.foo.f(4), 46)
        self.assertEqual(foo.f(4), 46)
        self.useNewConnection()

    def testFunctionAttrs(self):
        self.registry.newModule("foo", foo_src)
        import foo
        A = foo.f.attr = "attr"
        self.assertEqual(foo.f.attr, A)
        get_transaction().commit()
        self.assertEqual(foo.f.attr, A)
        foo.f._p_deactivate()
        self.assertEqual(foo.f.attr, A)
        del foo.f.attr
        self.assertRaises(AttributeError, getattr, foo.f, "attr")
        foo.f.func_code
        self.useNewConnection()

    def testFunctionSideEffects(self):
        self.registry.newModule("effect", side_effect_src)
        import effect
        effect.inc()
        get_transaction().commit()
        effect.inc()
        self.assert_(effect._p_changed)
        self.useNewConnection()

    def testBuiltins(self):
        self.registry.newModule("test", builtin_src)
        get_transaction().commit()
        import test
        self.assertEqual(test.f(), len(test.x))
        test._p_deactivate()
        self.assertEqual(test.f(), len(test.x))
        self.useNewConnection()

    def testNested(self):
        self.assertRaises(TypeError,
                          self.registry.newModule, "nested", nested_err_src)
        self.registry.newModule("nested", nested_src)
        get_transaction().commit()
        import nested
        g = nested.f(3)
        self.assertEqual(g(4), 7)

    def testLambda(self):
        # test a lambda that contains another lambda as a default
        self.registry.newModule("test",
                                "f = lambda x, y = lambda: 1: x + y()")
        get_transaction().commit()
        import test
        self.assertEqual(test.f(1), 2)
        self.useNewConnection()

    def testClass(self):
        self.registry.newModule("foo", src)
        get_transaction().commit()
        import foo
        obj = foo.Foo()
        obj.m()
        self.root["m"] = obj
        get_transaction().commit()
        foo._p_deactivate()
        o = foo.Foo()
        i = o.m()
        j = o.m()
        self.assertEqual(i + 1, j)
        self.useNewConnection()

    def testPackage(self):
        self.registry.newModule("A.B.C", "def f(x): return x")
        get_transaction().commit()

        import A.B.C
        self.assert_(isinstance(A, PersistentPackage))
        self.assertEqual(A.B.C.f("A"), "A")

        self.assertRaises(ValueError, self.registry.newModule,
                          "A.B", "def f(x): return x + 1")

        self.registry.newModule("A.B.D", "def f(x): return x")
        get_transaction().commit()

        from A.B import D
        self.assert_(hasattr(A.B.D, "f"))
        self.useNewConnection()

    def testPackageInit(self):
        self.registry.newModule("A.B.C", "def f(x): return x")
        get_transaction().commit()

        import A.B.C

        self.registry.newModule("A.B.__init__", "x = 2")
        get_transaction().commit()

        import A.B
        self.assert_(hasattr(A.B, "C"))
        self.assertEqual(A.B.x, 2)

        self.assertRaises(ValueError, self.registry.newModule,
                          "A.__init__.D", "x = 2")
        self.useNewConnection()

    def testPackageRelativeImport(self):
        self.registry.newModule("A.B.C", "def f(x): return x")
        get_transaction().commit()

        self.registry.newModule("A.Q", "from B.C import f")
        get_transaction().commit()

        import A.Q
        self.assertEqual(A.B.C.f, A.Q.f)

        self.registry.updateModule("A.Q", "import B.C")
        get_transaction().commit()

        self.assertEqual(A.B.C.f, A.Q.B.C.f)

        try:
            import A.B.Q
        except ImportError:
            pass
        self.useNewConnection()

    def testImportAll(self):
        self.registry.newModule("A.B.C",
                                """__all__ = ["a", "b"]; a, b, c = 1, 2, 3""")
        get_transaction().commit()

        d = {}
        exec "from A.B.C import *" in d
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2)
        self.assertRaises(KeyError, d.__getitem__, "c")

        self.registry.newModule("A.B.D", "from C import *")
        get_transaction().commit()

        import A.B.D
        self.assert_(hasattr(A.B.D, "a"))
        self.assert_(hasattr(A.B.D, "b"))
        self.assert_(not hasattr(A.B.D, "c"))

        self.registry.newModule("A.__init__", """__all__ = ["B", "F"]""")
        get_transaction().commit()

        self.registry.newModule("A.F", "spam = 1")
        get_transaction().commit()

        import A
        self.assertEqual(A.F.spam, 1)
        self.useNewConnection()

class TestModuleReload(unittest.TestCase):
    """Test reloading of modules"""

    def setUp(self):
        self.storage = MappingStorage()
        self.open()
        _dir, _file = os.path.split(tests.__file__)
        self._pmtest = os.path.join(_dir, "_pmtest.py")

    def tearDown(self):
        get_transaction().abort()

    def open(self):
        # open a new db and importer from the storage
        self.db = zodb.db.DB(self.storage)
        self.root = self.db.open().root()
        self.registry = self.root.get("registry")
        if self.registry is None:
            self.root["registry"] = self.registry = ManagedRegistry()
        self.importer = TestPersistentModuleImporter(self.registry)
        self.importer.install()
        get_transaction().commit()

    def close(self):
        self.importer.uninstall()
        self.db.close()

    def testModuleReload(self):
        self.registry.newModule("pmtest", open(self._pmtest).read())
        get_transaction().commit()
        import pmtest
        pmtest._p_deactivate()
        self.assertEqual(pmtest.a, 1)
        pmtest.f(4)
        self.close()
        pmtest._p_deactivate()
        self.importer.uninstall()
        self.open()
        del pmtest
        import pmtest

    def testClassReload(self):
        self.registry.newModule("foo", src)
        get_transaction().commit()
        import foo
        obj = foo.Foo()
        obj.m()
        self.root["d"] = d = PersistentDict()
        d["m"] = obj
        get_transaction().commit()
        self.close()
        foo._p_deactivate()
        self.importer.uninstall()
        self.open()
        del foo
        import foo

    def testModulePicklability(self):
        from zodb.code.tests import test_module
        s = pickle.dumps(test_module)
        m = pickle.loads(s)
        self.assertEqual(m, test_module)

def test_suite():
    s = unittest.TestSuite()
    for klass in TestModule, TestModuleReload:
        s.addTest(unittest.makeSuite(klass))
    return s

src = """\
class Foo(object):
    def __init__(self):
        self.x = id(self)
    def m(self):
        self.x += 1
        return self.x
    def n(self):
        self.x -= 1
        return self.x
"""

src2 = """\
class Foo(object):
    def __init__(self):
        self.x = 0
    def m(self):
        self.x += 10
        return self.x
"""
