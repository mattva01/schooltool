##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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

import tempfile
import unittest

import zodb.storage.file
from zodb.storage.memory import MemoryFullStorage, MemoryMinimalStorage
from zodb.storage.base import BerkeleyConfig

# The memory storages can't possibly pass persistent or readonly tests because
# both close and then re-open the database.  The minimal storage has other
# tests it can't pass -- see below.
from zodb.storage.tests import base, basic, conflict, corruption, history, \
     iterator, mt, packable, recovery, revision, \
     synchronization, undo, undoversion, version


class FullMemoryTests(base.StorageTestBase,
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
                       
    def open(self, read_only=False):
        config = BerkeleyConfig()
        config.read_only = read_only
        self._storage = MemoryFullStorage('memory', config=config)

    def setUp(self):
        self.open()

    def tearDown(self):
        self._storage.close()

    # Individual tests that can't possibly pass
    
    def testDatabaseVersionPersistent(self): pass



class MinimalMemoryTests(base.StorageTestBase,
                         basic.BasicStorage,
                         packable.PackableStorage,
                         synchronization.SynchronizedStorage,
                         conflict.ConflictResolvingStorage,
                         mt.MTStorage,
                         ):
                       
    def open(self, read_only=False):
        config = BerkeleyConfig()
        config.read_only = read_only
        self._storage = MemoryMinimalStorage('memory', config=config)

    def setUp(self):
        self.open()

    def tearDown(self):
        self._storage.close()

    # Individual tests that can't possibly pass

    def testDatabaseVersionPersistent(self): pass
    def testPackUnlinkedFromRoot(self): pass # requires undo

    # XXX These fail because conflict resolution requires implementation of
    # loadSerial() in the IUndoStorage interface.  This is probably a design
    # flaw of the interface.

    def testBuggyResolve1(self): pass
    def testBuggyResolve2(self): pass
    def testUnresolvable2(self): pass
    def testResolve(self): pass

    # XXX More tests that require loadSerial()
    def testPackOnlyOneObject(self): pass
    def testPackAllRevisions(self): pass
    def testPackJustOldRevisions(self): pass
    def testPackOnlyOneObject(self): pass
        


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FullMemoryTests))
    suite.addTest(unittest.makeSuite(MinimalMemoryTests))
    return suite
