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
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Test suite for ZEO based on zodb.tests."""

# System imports
import os
import sys
import time
import errno
import socket
import random
import logging
import asyncore
import tempfile
import unittest

# ZODB test support
import zodb
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle
from transaction import get_transaction


# ZODB test mixin classes
from zodb.storage.tests import base, basic, version, undo, undoversion, \
     packable, synchronization, conflict, revision, mt, readonly

from zodb.zeo.client import ClientStorage
from zodb.zeo.tests import forker, cache
from zodb.zeo.tests import commitlock, threadtests
from zodb.zeo.tests.common import TestClientStorage, DummyDB

def get_port():
    """Return a port that is not in use.

    Checks if a port is in use by trying to connect to it.  Assumes it
    is not in use if connect raises an exception.

    Raises RuntimeError after 10 tries.
    """
    for i in range(10):
        port = random.randrange(20000, 30000)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                s.connect(('localhost', port))
            except socket.error:
                # XXX check value of error?
                return port
        finally:
            s.close()
    raise RuntimeError, "Can't find port"

class DummyDB:
    def invalidate(self, *args):
        pass

class MiscZEOTests:
    """ZEO tests that don't fit in elsewhere."""

    def testLargeUpdate(self):
        obj = MinPO("X" * (10 * 128 * 1024))
        self._dostore(data=obj)

    def testZEOInvalidation(self):
        addr = self._storage._addr
        storage2 = TestClientStorage(addr, wait=True, min_disconnect_poll=0.1)
        try:
            oid = self._storage.newObjectId()
            ob = MinPO('first')
            revid1 = self._dostore(oid, data=ob)
            data, serial = storage2.load(oid, '')
            self.assertEqual(zodb_unpickle(data), MinPO('first'))
            self.assertEqual(serial, revid1)
            revid2 = self._dostore(oid, data=MinPO('second'), revid=revid1)
            for n in range(3):
                # Let the server and client talk for a moment.
                # Is there a better way to do this?
                asyncore.poll(0.1)
            data, serial = storage2.load(oid, '')
            self.assertEqual(zodb_unpickle(data), MinPO('second'),
                             'Invalidation message was not sent!')
            self.assertEqual(serial, revid2)
        finally:
            storage2.close()

class ZEOConflictTests(
    conflict.ConflictResolvingStorage,
    conflict.ConflictResolvingTransUndoStorage):

    def unresolvable(self, klass):
        # This helper method is used to test the implementation of
        # conflict resolution.  That code runs in the server, and there
        # is no way for the test suite (a client) to inquire about it.
        return False

class StorageTests(
    # Base class for all ZODB tests
    base.StorageTestBase,
    # ZODB test mixin classes
    basic.BasicStorage,
    readonly.ReadOnlyStorage,
    synchronization.SynchronizedStorage,
    # ZEO test mixin classes
    commitlock.CommitLockTests,
    threadtests.ThreadTests,
    # Locally defined (see above)
    MiscZEOTests
    ):
    """Tests for storage that supports IStorage."""

    def setUp(self):
        logging.info("testZEO: setUp() %s", self.id())
        config = self.getConfig()
        for i in range(10):
            port = get_port()
            zconf = forker.ZEOConfig(('', port))
            try:
                zport, adminaddr, pid, path = \
                       forker.start_zeo_server(config, zconf, port)
            except socket.error, e:
                if e[0] not in (errno.ECONNREFUSED, errno.ECONNRESET):
                    raise
            else:
                break
        else:
            raise
        self._pids = [pid]
        self._servers = [adminaddr]
        self._conf_path = path
        self._storage = ClientStorage(zport, '1', cache_size=20000000,
                                      min_disconnect_poll=0.5, wait=1)
        self._storage.registerDB(DummyDB())

    def tearDown(self):
        # Clean up any transaction that might be left hanging around
        get_transaction().abort()
        self._storage.close()
        os.remove(self._conf_path)
        for server in self._servers:
            forker.shutdown_zeo_server(server)
        if hasattr(os, 'waitpid'):
            # Not in Windows Python until 2.3
            for pid in self._pids:
                os.waitpid(pid, 0)

    def open(self, read_only=False):
        # XXX Needed to support ReadOnlyStorage tests.  Ought to be a
        # cleaner way.
        addr = self._storage._addr
        self._storage.close()
        self._storage = TestClientStorage(addr, read_only=read_only, wait=True)

class UndoVersionStorageTests(
    StorageTests,
    ZEOConflictTests,
    cache.StorageWithCache,
    cache.TransUndoStorageWithCache,
    commitlock.CommitLockUndoTests,
    mt.MTStorage,
    packable.PackableStorage,
    revision.RevisionStorage,
    undo.TransactionalUndoStorage,
    undoversion.TransactionalUndoVersionStorage,
    version.VersionStorage,
    ):
    """Tests for storage that supports IUndoStorage and IVersionStorage."""

    # XXX Some of the pack tests should really be run for the mapping
    # storage, but the pack tests assume that the storage also supports
    # multiple revisions.

    # ZEO doesn't provide iterators, so some tests will be incomplete
    # or skipped.

    def testUnicodeTransactionAttributes(self):
        pass

    def testTransactionalUndoIterator(self):
        pass

    def _iterate(self):
        pass

class FileStorageTests(UndoVersionStorageTests):
    """Test ZEO backed by a FileStorage."""

    level = 2

    def getConfig(self):
        filename = self.__fs_base = tempfile.mktemp()
        return """\
        <filestorage 1>
        path %s
        </filestorage>
        """ % filename

class BDBTests(UndoVersionStorageTests):
    """ZEO backed by a Berkeley Full storage."""

    level = 2

    def getConfig(self):
        self._envdir = tempfile.mktemp()
        return """\
        <fullstorage 1>
        name %s
        </fullstorage>
        """ % self._envdir

    # XXX These test seems to have massive failures when I run them.
    # I don't think they should fail, but need Barry's help to debug.

    def testCommitLockUndoClose(self):
        pass

    def testCommitLockUndoAbort(self):
        pass

class MappingStorageTests(StorageTests):

    def getConfig(self):
        return """<mappingstorage 1/>"""

test_classes = [FileStorageTests, MappingStorageTests]

from zodb.storage.base import berkeley_is_available
if berkeley_is_available:
    test_classes.append(BDBTests)

def test_suite():
    suite = unittest.TestSuite()
    for klass in test_classes:
        sub = unittest.makeSuite(klass)
        suite.addTest(sub)
    return suite
