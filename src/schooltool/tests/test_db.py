#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for the persistent helper objects.

$Id$
"""

import unittest
from persistent import Persistent
from schooltool.tests.utils import EqualsSortedMixin
from zope.interface import Interface, directlyProvides


class P(Persistent):
    pass


class N(Persistent):
    __name__ = None


class FalseP(Persistent):

    def __nonzero__(self):
        return False


class BaseTestPersistentKeysDict(unittest.TestCase, EqualsSortedMixin):

    def tearDown(self):
        import transaction
        transaction.abort()

    def maybeAdd(self, obj):
        if self.datamgr is not None:
            self.datamgr.add(obj)

    def doSet(self):
        from schooltool.db import PersistentKeysDict
        ob = object()
        p1 = P()
        p2 = P()
        d = PersistentKeysDict()
        self.maybeAdd(p1)
        self.maybeAdd(d)
        d[p1] = 1
        d[p2] = 2
        return d, p1, p2

    def test_setitem(self):
        d, p1, p2 = self.doSet()
        self.assertRaises(TypeError, d.__setitem__, object(), 1)

        import transaction
        transaction.commit()

    def test_getitem(self):
        d, p1, p2 = self.doSet()
        self.assertEqual(d[p1], 1)
        self.assertEqual(d[p2], 2)
        self.assertRaises(TypeError, d.__getitem__, object())
        self.assertRaises(KeyError, d.__getitem__, P())

        import transaction
        transaction.commit()

    def test_delitem(self):
        d, p1, p2 = self.doSet()
        del d[p1]
        del d[p2]
        self.assertRaises(KeyError, d.__getitem__, p1)
        self.assertRaises(KeyError, d.__delitem__, p1)
        self.assertRaises(KeyError, d.__getitem__, p1)
        self.assertRaises(KeyError, d.__delitem__, p2)
        self.assertRaises(KeyError, d.__delitem__, P())
        self.assertRaises(TypeError, d.__delitem__, object())

        import transaction
        transaction.commit()

    def test_keys_iter_len(self):
        d, p1, p2 = self.doSet()
        self.assertEqualsSorted(d.keys(), [p1, p2])
        self.assertEqualsSorted(list(d), [p1, p2])
        self.assertEqual(len(d), 2)

        import transaction
        transaction.commit()

    def test_contains(self):
        d, p1, p2 = self.doSet()
        self.assert_(p1 in d)
        self.assert_(p2 in d)
        self.assertRaises(TypeError, d.__contains__, object())
        self.assert_(P() not in d)

        import transaction
        transaction.commit()


class TestPersistentKeysDictWithDataManager(BaseTestPersistentKeysDict):

    def setUp(self):
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def testDifferentConnection(self):
        import transaction
        d, p1, p2 = self.doSet()
        self.datamgr.root()['p'] = d
        transaction.commit()
        p3 = P()
        d[p3] = 3
        self.datamgr.root()['p3'] = p3
        self.assertEqual(d[p3], 3)
        transaction.commit()
        try:
            datamgr = self.db.open()
            p = datamgr.root()['p']
            p3 = datamgr.root()['p3']
            self.assert_(p3 in d, 'p3 not in d')
            self.assertEqual(d[p3], 3)
        finally:
            transaction.abort()
            datamgr.close()


class TestPersistentKeysDictBare(BaseTestPersistentKeysDict):

    def setUp(self):
        self.datamgr = None


class TestPersistentKeysSet(unittest.TestCase, EqualsSortedMixin):

    def newInstance(self):
        from schooltool.db import PersistentKeysSet
        return PersistentKeysSet()

    def setUp(self):
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def tearDown(self):
        import transaction
        transaction.abort()
        self.datamgr.close()

    def testPersistentKeys(self):
        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a, b = P(), P()
        self.assertEqual(len(p), 0)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        p.add(b)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        p.remove(a)
        self.assertEquals(list(p), [b])
        self.assertEqual(len(p), 1)
        p.add(a)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)

        import transaction
        transaction.commit()

    def testValueNotPersistent(self):
        p = self.newInstance()
        self.assertRaises(TypeError, p.add, object())

    def test_clear(self):
        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a, b = P(), P()
        p.add(a)
        p.add(b)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        p.clear()
        self.assertEqual(list(p), [])
        self.assertEqual(len(p), 0)


class TestMaybePersistentKeysSet(TestPersistentKeysSet):

    def newInstance(self):
        from schooltool.db import MaybePersistentKeysSet
        return MaybePersistentKeysSet()

    def testValueNotPersistent(self):
        # We like non-persistent values
        pass

    def testNonPersistentAndPersistentValues(self):
        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a = P()
        b = object
        self.assertEqual(len(p), 0)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        p.add(b)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        p.remove(a)
        self.assertEquals(list(p), [b])
        self.assertEqual(len(p), 1)
        p.add(a)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)

        import transaction
        transaction.commit()

    def test_clear(self):
        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a, b = P(), object
        p.add(a)
        p.add(b)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        p.clear()
        self.assertEqual(list(p), [])
        self.assertEqual(len(p), 0)


class TestPersistentPairKeysDict(unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.db import PersistentPairKeysDict

        d = PersistentPairKeysDict()

        value = object()
        p = P()
        d[(p, 1)] = value
        self.assertEqual(d[(p, 1)], value)
        value2 = object()
        d[(p, 2)] = value2
        self.assertEqual(d[(p, 1)], value)
        self.assertEqual(d[(p, 2)], value2)
        self.assert_((p, 2) in d)
        self.assert_((p, 3) not in d)
        del d[(p, 2)]
        self.assertRaises(KeyError, d.__getitem__, (p, 2))

    def testPersistentSetitem(self):
        from schooltool.db import PersistentPairKeysDict
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        import transaction
        db = DB(MappingStorage())

        datamgr = db.open()
        d = PersistentPairKeysDict()
        p = P()
        value = 23
        d[(p, 1)] = value
        datamgr.root()['D'] = d
        datamgr.root()['P'] = p
        transaction.commit()
        datamgr.close()

        datamgr = db.open()
        d = datamgr.root()['D']
        p = datamgr.root()['P']
        self.assertEqual(d[(p, 1)], value)
        d[(p, 2)] = value
        transaction.commit()

        # Opening a second datamanager while this one is still open to
        # ensure that the second datamanager is not the first one
        # recycled.
        datamgr2 = db.open()
        d2_d = datamgr2.root()['D']
        d2_p = datamgr2.root()['P']
        self.assertEqual(d2_d[(d2_p, 1)], value)
        # The next assert will fail if the item with key (p, 2) is not
        # persisted properly on __setitem__.
        self.assertEqual(d2_d[(d2_p, 2)], value)
        transaction.commit()
        datamgr2.close()
        datamgr.close()

    def testPersistentDelitem(self):
        from schooltool.db import PersistentPairKeysDict
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        import transaction
        db = DB(MappingStorage())

        datamgr = db.open()
        d = PersistentPairKeysDict()
        p = P()
        value = 23
        d[(p, 1)] = value
        d[(p, 2)] = value
        datamgr.root()['D'] = d
        datamgr.root()['P'] = p
        transaction.commit()
        datamgr.close()

        datamgr = db.open()
        d = datamgr.root()['D']
        p = datamgr.root()['P']
        del d[(p, 2)]
        transaction.commit()

        # Opening a second datamanager while this one is still open to
        # ensure that the second datamanager is not the first one
        # recycled.
        datamgr2 = db.open()
        d2_d = datamgr2.root()['D']
        d2_p = datamgr2.root()['P']
        self.assertEqual(d2_d[(d2_p, 1)], value)
        # The next assert will fail if the item with key (p, 2) is not
        # persisted properly on __delitem__.
        self.assertRaises(KeyError, d2_d.__getitem__, (d2_p, 2))
        transaction.commit()
        datamgr2.close()
        datamgr.close()

    def testNoEmptyDicts(self):
        from schooltool.db import PersistentPairKeysDict

        d = PersistentPairKeysDict()

        value = object()
        p = P()
        d[(p, 1)] = value
        self.assertEqual(len(d._data), 1)
        del d[(p, 1)]
        self.assertEqual(len(d._data), 0)

    def test_keys_len_iter_iteritems(self):
        from schooltool.db import PersistentPairKeysDict

        d = PersistentPairKeysDict()

        p = P()
        self.assertEqual(d.keys(), [])
        self.assertEqual(len(d), 0)
        self.assertEqualsSorted(list(iter(d)), [])
        self.assertEqualsSorted(list(d.iteritems()), [])
        d[(p, 1)] = 1
        self.assertEqual(d.keys(), [(p, 1)])
        self.assertEqual(len(d), 1)
        self.assertEqualsSorted(list(iter(d)), [(p, 1)])
        self.assertEqualsSorted(list(d.iteritems()),
                                [((p, 1), 1)])
        p2 = P()
        d[(p2, 2)] = 2
        self.assertEqualsSorted(d.keys(), [(p, 1), (p2, 2)])
        self.assertEqual(len(d), 2)
        self.assertEqualsSorted(list(iter(d)), [(p, 1), (p2, 2)])
        self.assertEqualsSorted(list(d.iteritems()),
                                [((p, 1), 1), ((p2, 2), 2)])


class NamedObject:

    __name__ = None


class TestUniqueNamesMixin(unittest.TestCase, EqualsSortedMixin):

    def test(self):
        from schooltool.db import UniqueNamesMixin
        u = UniqueNamesMixin(name_length=5)
        self.assertEqual(u.getNames(), [])
        named_object = NamedObject()
        u.newName(named_object)
        self.assertNotEqual(named_object.__name__, None)
        self.assertEqual(len(named_object.__name__), 5)
        self.assertEqual(named_object.__name__, '00001')
        self.assertRaises(ValueError, u.newName, named_object)
        named_object2 = NamedObject()
        value = object()
        u.newName(named_object2, value)
        self.assertNotEqual(named_object2.__name__, None)
        self.assertNotEqual(named_object2.__name__, named_object.__name__)
        self.assertEqual(len(named_object2.__name__), 5)
        self.assertEqual(named_object2.__name__, '00002')
        self.assert_(u.valueForName(named_object2.__name__) is value)

        self.assertEqualSorted(list(u.getNames()), ['00001', '00002'])

        u.removeName('00001')
        self.assertRaises(KeyError, u.removeName, '00001')
        self.assertEqual(list(u.getNames()), ['00002'])
        u.clearNames()
        self.assertEqual(list(u.getNames()), [])
        named_object3 = NamedObject()
        u.newName(named_object3)
        self.assertEqual(named_object3.__name__, '00003')

    def test_fixed_names(self):
        from schooltool.db import UniqueNamesMixin
        u = UniqueNamesMixin(name_length=3)
        named_object1 = NamedObject()
        u.newName(named_object1, name='name')
        self.assertEqual(named_object1.__name__, 'name')

        named_object2 = NamedObject()
        self.assertRaises(ValueError, u.newName, named_object2, name='name')
        self.assert_(named_object2.__name__ is None)

        named_object3 = NamedObject()
        named_object4 = NamedObject()
        named_object5 = NamedObject()
        u.newName(named_object3, name='002')
        u.newName(named_object4)
        u.newName(named_object5)
        self.assertEqual(named_object3.__name__, '002')
        self.assertEqual(named_object4.__name__, '001')
        self.assertEqual(named_object5.__name__, '003')


class TestPersistentKeysSetWithNames(unittest.TestCase, EqualsSortedMixin):

    def newInstance(self):
        from schooltool.db import PersistentKeysSetWithNames
        return PersistentKeysSetWithNames()

    def setUp(self):
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def tearDown(self):
        import transaction
        transaction.abort()
        self.datamgr.close()

    def testPersistentKeys(self):
        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a, b = N(), N()
        self.assertEqual(len(p), 0)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        self.assertEquals(a.__name__, '001')
        self.assertEquals(list(p.getNames()), ['001'])
        self.assertEquals(p.valueForName('001'), a)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        self.assertEquals(a.__name__, '001')
        self.assertEquals(list(p.getNames()), ['001'])
        p.add(b)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        self.assertEquals(b.__name__, '002')
        self.assertEqualSorted(list(p.getNames()), ['001', '002'])
        self.assertEquals(p.valueForName('002'), b)
        p.remove(a)
        self.assertEquals(list(p), [b])
        self.assertEqual(len(p), 1)
        self.assertEquals(a.__name__, '001')  # a.__name__ not cleared
        self.assertEquals(list(p.getNames()), ['002'])
        self.assertRaises(KeyError, p.valueForName, '001')

        self.assertRaises(ValueError, p.add, a)  # a.__name__ is not None
        a.__name__ = None
        p.add(a)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        self.assertEquals(a.__name__, '003')  # a.__name__ not cleared
        self.assertEqualSorted(list(p.getNames()), ['002', '003'])

        import transaction
        transaction.commit()

    def testValueNotPersistent(self):
        p = self.newInstance()
        self.assertRaises(TypeError, p.add, object())

    def test_clear(self):
        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a, b = N(), N()
        p.add(a)
        p.add(b)
        self.assertEqualsSorted(list(p), [a, b])
        self.assertEqual(len(p), 2)
        self.assertEqualSorted(list(p.getNames()), ['001', '002'])
        p.clear()
        self.assertEqual(list(p), [])
        self.assertEqual(len(p), 0)
        self.assertEqual(list(p.getNames()), [])
        c = N()
        p.add(c)
        self.assertEqual(c.__name__, '003')
        self.assertEquals(list(p.getNames()), ['003'])

    def testDifferentConnection(self):
        import transaction

        p = self.newInstance()
        self.datamgr.root()['p'] = p
        a, b = N(), N()
        self.assertEqual(len(p), 0)
        transaction.commit()
        #import pdb; pdb.set_trace()
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        self.assertEquals(a.__name__, '001')
        self.assertEquals(list(p.getNames()), ['001'])
        self.assertEquals(p.valueForName('001'), a)
        transaction.commit()
        try:
            datamgr = self.db.open()
            p = datamgr.root()['p']
            len(p._data._data)
            self.assertEqual(len(p), 1)
            self.assertEquals(a.__name__, '001')
            self.assertEquals(list(p)[0].__name__, a.__name__)
            self.assertEquals(list(p.getNames()), ['001'])
            self.assertEquals(p.valueForName('001').__name__, a.__name__)
        finally:
            transaction.abort()
            datamgr.close()

    def test_add_with_name(self):
        p = self.newInstance()
        a = N()
        p.add(a, name='foo')
        self.assertEquals(a.__name__, 'foo')

        b = N()
        self.assertRaises(ValueError, p.add, b, 'foo')
        self.assert_(b.__name__ is None)
        self.assert_(b not in p)


class TestPersistentPairKeysDictWithNames(unittest.TestCase,
                                          EqualsSortedMixin):

    def test(self):
        from schooltool.db import PersistentPairKeysDictWithNames
        s = PersistentPairKeysDictWithNames()
        p = P()
        s[p, 1] = x = N()
        self.assert_(x.__name__ is not None)
        self.assert_(s.valueForName(x.__name__) is x)
        del s[p, 1]
        self.assertRaises(KeyError, s.valueForName, x.__name__)
        s[p, 1] = x = N()
        s[p, 2] = y = N()
        s.clear()
        self.assertRaises(KeyError, s.valueForName, x.__name__)
        self.assertRaises(KeyError, s.valueForName, y.__name__)


class TestPersistentKeysSetContainer(unittest.TestCase):

    def test(self):
        from schooltool.db import PersistentKeysSetContainer
        parent = object()
        c = PersistentKeysSetContainer('box', parent)
        self.assertEquals(c.__name__, 'box')
        self.assert_(c.__parent__ is parent)
        p = P()
        p2 = P()
        p.__name__ = p.__parent__ = None
        p2.__name__ = p2.__parent__ = None

        c.add(p)
        c.add(p2, name='another_one')

        self.assert_(c.valueForName('001') is p)
        self.assertEquals(p.__name__, '001')
        self.assert_(p.__parent__ is c)

        self.assert_(c.valueForName('another_one') is p2)
        self.assertEquals(p2.__name__, 'another_one')
        self.assert_(p2.__parent__ is c)

    def test_check_interface(self):
        from schooltool.db import PersistentKeysSetContainer
        class IRoundThing(Interface): pass
        c = PersistentKeysSetContainer('round_box', None, IRoundThing)
        self.assertEquals(c.__name__, 'round_box')
        p = P()
        p.__name__ = p.__parent__ = None
        directlyProvides(p, IRoundThing)
        p2 = P()
        p2.__name__ = p2.__parent__ = None
        c.add(p)
        self.assert_(c.valueForName('001') is p)
        self.assertRaises(ValueError, c.add, p2)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersistentKeysSet))
    suite.addTest(unittest.makeSuite(TestMaybePersistentKeysSet))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDictBare))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDictWithDataManager))
    suite.addTest(unittest.makeSuite(TestPersistentPairKeysDict))
    suite.addTest(unittest.makeSuite(TestUniqueNamesMixin))
    suite.addTest(unittest.makeSuite(TestPersistentKeysSetWithNames))
    suite.addTest(unittest.makeSuite(TestPersistentPairKeysDictWithNames))
    suite.addTest(unittest.makeSuite(TestPersistentKeysSetContainer))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
