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
"""Test that invalidations propagate across connections."""

import unittest

from zodb.db import DB
from zodb.connection import Connection
from zodb.storage.mapping import MappingStorage
from zodb.storage.tests.minpo import MinPO

from transaction import get_transaction

class InvalidationTests(unittest.TestCase):

    num_conn = 4

    def setUp(self):
        self.storage = MappingStorage()
        self.db = DB(self.storage)
        self.connections = [self.db.open() for i in range(self.num_conn)]

    def tearDown(self):
        self.db.close()

    def testSimpleInvalidation(self):
        root = self.connections[0].root()
        obj = root[1] = MinPO(1)
        get_transaction().commit()
        for cn in self.connections[1:]:
            cn.sync()
            root = cn.root()
            self.assertEqual(root[1].value, 1)
        obj.value = 2
        get_transaction().commit()
        for cn in self.connections[1:]:
            cn.sync()
            root = cn.root()
            self.assertEqual(root[1].value, 2)

    def testSimpleInvalidationClosedConnection(self):
        # Test that invalidations are still sent to closed connections.
        root = self.connections[0].root()
        obj = root[1] = MinPO(1)
        get_transaction().commit()
        for cn in self.connections[1:]:
            cn.sync()
            root = cn.root()
            self.assertEqual(root[1].value, 1)
            cn.close()
        obj.value = 2
        get_transaction().commit()
        for cn in self.connections[1:]:
            self.assert_(obj._p_oid in cn._invalidated)
            # Call reset() which is equivalent to re-opening it via
            # the db connection pool.
            cn.reset()
            root = cn.root()
            self.assertEqual(root[1].value, 2)

    def testReadConflict(self):
        # If an object is modified after a transaction begins and the
        # transaction reads the object, it should get a read conflict.
        pass

    def testReadConflictIgnored(self):
        # If an application gets a read conflict and ignores it, the
        # data manager for the object should refuse to commit the
        # transaction.
        pass

    def testAtomicInvalidations(self):
        # Invalidations must be delivered atomically.  If several
        # objects are modified by a transaction, other transactions
        # should apply all the invalidations at once.  Otherwise, a
        # mix of out-of-date and current object revisions could be
        # read.
        pass

def test_suite():
    return unittest.makeSuite(InvalidationTests)
