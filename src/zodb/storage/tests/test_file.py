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
import sys
import errno
import unittest

import zodb.storage.file
from zodb.ztransaction import Transaction
from zodb.storage.interfaces import *

from zodb.storage.tests import base, basic, conflict, corruption, history, \
     iterator, mt, packable, persistent, readonly, recovery, revision, \
     synchronization, undo, undoversion, version

from zodb.storage.tests.base import MinPO, zodb_unpickle

from transaction import get_transaction

class FileStorageTests(
    base.StorageTestBase,
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
    persistent.PersistentStorage,
    mt.MTStorage,
    readonly.ReadOnlyStorage
    ):

    def open(self, **kwargs):
        self._storage = zodb.storage.file.FileStorage('FileStorageTests.fs',
                                                      **kwargs)

    def setUp(self):
        self.open(create=1)

    def tearDown(self):
        get_transaction().abort()
        self._test_read_index()
        self._storage.close()
        self._storage.cleanup()

    def _test_read_index(self):
        # For each test, open a read-only copy and make sure that
        # reading the index file results in the same storage-internal
        # state.
        try:
            copy = zodb.storage.file.FileStorage('FileStorageTests.fs',
                                                 read_only=True)
        except:
            from zodb.storage.file.dump import dump
            dump("FileStorageTests.fs")
            raise

        L1 = copy._index.items()
        L2 = self._storage._index.items()
        copy.close()
        L1.sort(); L2.sort()
        self.assertEqual(L1, L2)

    def testLongMetadata(self):
        s = "X" * 75000
        try:
            self._dostore(user=s)
        except StorageError:
            pass
        else:
            self.fail("expect long user field to raise error")
        try:
            self._dostore(description=s)
        except StorageError:
            pass
        else:
            self.fail("expect long user field to raise error")

class FileStorageRecoveryTest(base.StorageTestBase, recovery.RecoveryStorage):

    def setUp(self):
        self._storage = zodb.storage.file.FileStorage('Source.fs')
        self._dst = zodb.storage.file.FileStorage('Dest.fs')

    def tearDown(self):
        self._storage.close()
        self._dst.close()
        self._storage.cleanup()
        self._dst.cleanup()

    def new_dest(self):
        return zodb.storage.file.FileStorage('Dest.fs')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileStorageTests))
    suite.addTest(unittest.makeSuite(corruption.FileStorageCorruptTests))
    suite.addTest(unittest.makeSuite(FileStorageRecoveryTest))
    return suite
