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


class TestPersistentListSet(unittest.TestCase):

    def test(self):
        from schooltool.db import PersistentListSet
        p = PersistentListSet()
        a, b = object(), object()
        p.add(a)
        self.assertEquals(list(p), [a])
        p.add(a)
        self.assertEquals(list(p), [a])
        p.add(b)
        self.assertEquals(list(p), [a, b])
        p.remove(a)
        self.assertEquals(list(p), [b])
        p.add(a)
        self.assertEquals(list(p), [b, a])


class P(Persistent):
    pass

class TestPersistentKeysDict(unittest.TestCase):

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
        self.assertEqual(d.keys(), [p, p2])
        self.assertEqual(list(d), [p, p2])
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

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersistentListSet))
    suite.addTest(unittest.makeSuite(TestPersistentKeysDict))
    return suite
