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
from persistence import Persistent


class EqualsSortedMixin:

    def assertEqualsSorted(self, a, b):
        x = a[:]
        y = b[:]
        x.sort()
        y.sort()
        self.assertEquals(x, y)


class P(Persistent):
    pass


class FalseP(Persistent):

    def __nonzero__(self):
        return False


class BaseTestPersistentKeysDict(unittest.TestCase, EqualsSortedMixin):

    def tearDown(self):
        from transaction import get_transaction
        get_transaction().abort()

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

        from transaction import get_transaction
        get_transaction().commit()

    def test_getitem(self):
        d, p1, p2 = self.doSet()
        self.assertEqual(d[p1], 1)
        self.assertEqual(d[p2], 2)
        self.assertRaises(TypeError, d.__getitem__, object())
        self.assertRaises(KeyError, d.__getitem__, P())

        from transaction import get_transaction
        get_transaction().commit()

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

        from transaction import get_transaction
        get_transaction().commit()

    def test_keys_iter_len(self):
        d, p1, p2 = self.doSet()
        self.assertEqualsSorted(d.keys(), [p1, p2])
        self.assertEqualsSorted(list(d), [p1, p2])
        self.assertEqual(len(d), 2)

        from transaction import get_transaction
        get_transaction().commit()

    def test_contains(self):
        d, p1, p2 = self.doSet()
        self.assert_(p1 in d)
        self.assert_(p2 in d)
        self.assertRaises(TypeError, d.__contains__, object())
        self.assert_(P() not in d)

        from transaction import get_transaction
        get_transaction().commit()

class TestPersistentKeysDictWithDataManager(BaseTestPersistentKeysDict):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

class TestPersistentKeysDictBare(BaseTestPersistentKeysDict):

    def setUp(self):
        self.datamgr = None

class TestPersistentKeysSet(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def tearDown(self):
        from transaction import get_transaction
        get_transaction().abort()

    def test(self):
        from schooltool.db import PersistentKeysSet
        p = PersistentKeysSet()
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

        from transaction import get_transaction
        get_transaction().commit()


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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersistentKeysSet))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDictBare))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDictWithDataManager))
    suite.addTest(unittest.makeSuite(TestPersistentPairKeysDict))
    return suite
