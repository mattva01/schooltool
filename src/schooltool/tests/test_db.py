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


class TestPersistentListSet(unittest.TestCase):

    def test(self):
        from schooltool.db import PersistentListSet
        p = PersistentListSet()
        self.assertEqual(len(p), 0)
        a, b = object(), object()
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        p.add(a)
        self.assertEquals(list(p), [a])
        self.assertEqual(len(p), 1)
        p.add(b)
        self.assertEquals(list(p), [a, b])
        self.assertEqual(len(p), 2)
        p.remove(a)
        self.assertEquals(list(p), [b])
        self.assertEqual(len(p), 1)
        p.add(a)
        self.assertEquals(list(p), [b, a])
        self.assertEqual(len(p), 2)



class P(Persistent):
    pass

class FalseP(Persistent):

    def __nonzero__(self):
        return False

class TestPersistentKeysDict(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def test_setitem(self):
        from schooltool.db import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.assertRaises(TypeError, d.__setitem__, p, 1)
        self.datamgr.add(d)
        d[p] = 2
        self.assert_(p._p_oid)
        self.assertRaises(TypeError, d.__setitem__, ob, 1)

    def test_getitem(self):
        from schooltool.db import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.datamgr.add(d)
        d[p] = 2
        self.assertEqual(d[p], 2)
        self.assertRaises(TypeError, d.__getitem__, object())
        self.assertRaises(KeyError, d.__getitem__, P())

    def test_delitem(self):
        from schooltool.db import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.datamgr.add(d)
        d[p] = 2
        self.assertEqual(d[p], 2)
        del d[p]
        self.assertRaises(KeyError, d.__getitem__, p)
        self.assertRaises(KeyError, d.__delitem__, p)
        self.assertRaises(KeyError, d.__delitem__, P())
        self.assertRaises(TypeError, d.__delitem__, object())

    def test_keys_iter_len(self):
        from schooltool.db import PersistentKeysDict
        ob = object()
        p = P()
        p2 = P()
        d = PersistentKeysDict()
        self.assertRaises(TypeError, d.keys)
        self.assertRaises(TypeError, list, d)
        self.datamgr.add(d)
        d[p] = 2
        d[p2] = 3
        self.assertEqualsSorted(d.keys(), [p, p2])
        self.assertEqualsSorted(list(d), [p, p2])
        self.assertEqual(len(d), 2)

    def test_contains(self):
        from schooltool.db import PersistentKeysDict
        ob = object()
        p = P()
        d = PersistentKeysDict()
        self.datamgr.add(d)
        d[p] = 2
        self.assert_(p in d)
        self.assertRaises(TypeError, d.__contains__, object())
        self.assert_(P() not in d)


class TestPersistentTuplesDict(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def test___init__(self):
        from schooltool.db import PersistentTuplesDict
        self.assertRaises(TypeError, PersistentTuplesDict)
        self.assertRaises(ValueError, PersistentTuplesDict, 'x')
        self.assertRaises(ValueError, PersistentTuplesDict, ('x',))
        self.assertRaises(TypeError, PersistentTuplesDict, ((),))

        # The rest of this test is a white-box
        d = PersistentTuplesDict('')
        self.assertEquals(d._patternlen, 0)
        self.assertEquals(d._pindexes, [])
        d = PersistentTuplesDict(())
        self.assertEquals(d._patternlen, 0)
        self.assertEquals(d._pindexes, [])

        d = PersistentTuplesDict('p')
        self.assertEquals(d._patternlen, 1)
        self.assertEquals(d._pindexes, [0])
        d = PersistentTuplesDict(('p',))
        self.assertEquals(d._patternlen, 1)
        self.assertEquals(d._pindexes, [0])

        d = PersistentTuplesDict('pop')
        self.assertEquals(d._patternlen, 3)
        self.assertEquals(d._pindexes, [0, 2])
        d = PersistentTuplesDict(('p','o', 'p'))
        self.assertEquals(d._patternlen, 3)
        self.assertEquals(d._pindexes, [0, 2])

        d = PersistentTuplesDict(u'pop')
        self.assertEquals(d._patternlen, 3)
        self.assertEquals(d._pindexes, [0, 2])
        d = PersistentTuplesDict((u'p', u'o', u'p'))
        self.assertEquals(d._patternlen, 3)
        self.assertEquals(d._pindexes, [0, 2])

    def test_setitem(self):
        from schooltool.db import PersistentTuplesDict
        ob = object()
        p = P()
        p2 = P()
        d = PersistentTuplesDict('pop')
        key = (p, ob, p2)
        self.assertRaises(TypeError, d.__setitem__, key, 1)
        self.datamgr.add(d)
        d[key] = 2
        self.assertEquals(d[key], 2)
        self.assert_(p._p_oid)
        self.assertRaises(TypeError, d.__setitem__, ob, 1)
        d[(p, p, p2)] = 23
        self.assertRaises(TypeError, d.__setitem__, (ob, p, p), 1)
        self.assertRaises(ValueError, d.__setitem__, (p, ob, p, ob), 1)

    def testFalsePersistentObject(self):
        from schooltool.db import PersistentTuplesDict
        ob = object()
        p = FalseP()
        d = PersistentTuplesDict('po')
        self.datamgr.add(d)
        key = (p, ob)
        d[key] = 23
        self.assertEquals(d.keys(), [key])

    def test_getitem(self):
        from schooltool.db import PersistentTuplesDict
        ob = object()
        p = P()
        p2 = P()
        key = (p, ob, p2)
        d = PersistentTuplesDict('pop')
        self.datamgr.add(d)
        d[key] = 2
        self.assertEqual(d[key], 2)
        self.assertRaises(TypeError, d.__getitem__, object())
        self.assertRaises(TypeError, d.__getitem__, P())
        self.assertRaises(ValueError, d.__getitem__, (p, p, p, p))
        self.assertRaises(TypeError, d.__getitem__, (ob, p, ob))
        self.assertRaises(KeyError, d.__getitem__, (p, p, p))

    def test_delitem(self):
        from schooltool.db import PersistentTuplesDict
        ob = object()
        ob2 = object()
        p = P()
        d = PersistentTuplesDict('poo')
        key = (p, ob, ob2)
        self.datamgr.add(d)
        d[key] = 2
        self.assertEqual(d[key], 2)
        del d[key]
        self.assertRaises(KeyError, d.__getitem__, key)
        self.assertRaises(KeyError, d.__delitem__, key)
        self.assertRaises(KeyError, d.__delitem__, (p, ob, ob2))
        self.assertRaises(TypeError, d.__delitem__, ob)
        self.assertRaises(TypeError, d.__delitem__, P())
        self.assertRaises(ValueError, d.__delitem__, (p, p, p, p))
        self.assertRaises(TypeError, d.__delitem__, (ob, p, ob))
        self.assertRaises(KeyError, d.__delitem__, (p, p, p))

    def test_keys_iter_len(self):
        from schooltool.db import PersistentTuplesDict
        ob = object()
        p = P()
        p2 = P()
        key1 = (p, p2, ob)
        key2 = (p2, p, ob)
        d = PersistentTuplesDict('ppo')
        self.assertRaises(TypeError, d.keys)
        self.assertRaises(TypeError, list, d)
        self.datamgr.add(d)
        d[key1] = 2
        d[key2] = 3
        self.assertEqualsSorted(d.keys(), [key1, key2])
        self.assertEqualsSorted(list(d), [key1, key2])
        self.assertEqual(len(d), 2)

    def test_contains(self):
        from schooltool.db import PersistentTuplesDict
        ob = object()
        ob2 = object()
        p = P()
        key = (ob, ob2, p)
        d = PersistentTuplesDict('oop')
        self.datamgr.add(d)
        d[key] = 2
        self.assert_(key in d)
        self.assertRaises(TypeError, d.__contains__, ob)
        self.assertRaises(TypeError, d.__contains__, p)
        self.assertRaises(TypeError, d.__contains__, (ob, p, ob))
        self.assertRaises(ValueError, d.__contains__, (ob, ob, p, p))
        self.assert_((object(), ob2, p) not in d)


class TestPersistentKeysSet(unittest.TestCase, EqualsSortedMixin):

    def setUp(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()

    def test(self):
        from schooltool.db import PersistentKeysSet
        p = PersistentKeysSet()
        self.datamgr.add(p)
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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersistentListSet))
    suite.addTest(unittest.makeSuite(TestPersistentKeysSet))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDict))
    suite.addTest(unittest.makeSuite(TestPersistentTuplesDict))
    return suite
