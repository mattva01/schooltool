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

import os
import tempfile
import unittest

from zodb.interfaces import ConflictError, VersionLockError
from zodb.storage.base import ZERO
from zodb.storage.file import FileStorage
from zodb.storage.demo import DemoStorage

from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle

# Demo storage can't possible pass the readonly or persistent tests
from zodb.storage.tests import base, basic, conflict, corruption, history, \
     iterator, mt, packable, recovery, revision, \
     synchronization, undo, undoversion, version

class BasicDemoStorageTests(base.StorageTestBase,
                            basic.BasicStorage,
                            undo.TransactionalUndoStorage,
                            revision.RevisionStorage,
                            version.VersionStorage,
                            undoversion.TransactionalUndoVersionStorage,
                            packable.PackableStorage,
                            synchronization.SynchronizedStorage,
                            conflict.ConflictResolvingStorage,
                            conflict.ConflictResolvingTransUndoStorage,
                            iterator.IteratorStorage,
                            iterator.ExtendedIteratorStorage,
                            mt.MTStorage,
                            ):

    def setUp(self):
        self._back = FileStorage(tempfile.mktemp())
        self._storage = DemoStorage('demo', self._back)

    def tearDown(self):
        self._storage.close()
        self._back.close()
        self._back.cleanup()

    # Individual tests that can't possible succeed
    def testDatabaseVersionPersistent(self): pass


class InterestingDemoStorageTests(base.StorageTestBase):
    def setUp(self):
        self._backfile = tempfile.mktemp()
        self._storage = FileStorage(self._backfile, create=True)

    def flip(self):
        self._storage.close()
        self._back = FileStorage(self._backfile, read_only=True)
        self._storage = DemoStorage('demo', self._back)

    def tearDown(self):
        self._storage.close()
        self._back.close()
        self._back.cleanup()

    def testFindRootInBack(self):
        eq = self.assertEqual
        self._initroot()
        data0, revid0 = self._storage.load(ZERO)
        self.flip()
        data1, revid1 = self._storage.load(ZERO)
        eq(data0, data1)
        eq(revid0, revid1)

    def testFindObjectInBack(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        obj = MinPO(11)
        self._dostore(oid=oid, data=obj)
        self.flip()
        data, revid = self._storage.load(oid)
        eq(obj, zodb_unpickle(data))

    def testStoreInBackStoreInFront(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        revid1 = self._dostore(oid=oid, data=MinPO(7))
        self.flip()
        revid2 = self._dostore(oid=oid, data=MinPO(8), revid=revid1)
        data, serial = self._storage.load(oid, '')
        eq(serial, revid2)
        eq(zodb_unpickle(data), MinPO(8))

    def testStoreInBackConflictInFront(self):
        raises = self.assertRaises
        oid = self._storage.newObjectId()
        revid1 = self._dostore(oid=oid, data=MinPO(7))
        self.flip()
        # Calculate a bogus revid
        bogus = '\ff' + revid1[1:]
        raises(ConflictError, self._dostore,
               oid=oid, data=MinPO(8), revid=bogus)

    def testStoreInBackVersionLockInFront(self):
        raises = self.assertRaises
        oid = self._storage.newObjectId()
        revid1 = self._dostore(oid=oid, data=MinPO(7), version='backversion')
        self.flip()
        raises(VersionLockError, self._dostore,
               oid=oid, data=MinPO(8), revid=revid1, version='frontversion')

    def testNoDuplicateObjectIds(self):
        oids = {}
        for i in range(10):
            oids[self._storage.newObjectId()] = True
        self.flip()
        for i in range(10):
            self.failIf(self._storage.newObjectId() in oids)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BasicDemoStorageTests))
    suite.addTest(unittest.makeSuite(InterestingDemoStorageTests))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
