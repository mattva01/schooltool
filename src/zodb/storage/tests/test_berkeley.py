##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors.
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

# Unit tests for basic storage functionality

import unittest
from zodb import interfaces

from zodb.storage.base import berkeley_is_available
from zodb.storage.tests import bdbmixin
from zodb.storage.tests.basic import BasicStorage
from zodb.storage.tests.revision import RevisionStorage
from zodb.storage.tests.synchronization import SynchronizedStorage
from zodb.storage.tests.version import VersionStorage
from zodb.storage.tests.undo import TransactionalUndoStorage
from zodb.storage.tests.undoversion import \
     TransactionalUndoVersionStorage
from zodb.storage.tests.packable import PackableStorage
from zodb.storage.tests.iterator import \
     IteratorStorage, ExtendedIteratorStorage
from zodb.storage.tests.recovery import RecoveryStorage
from zodb.storage.tests import conflict
from zodb.storage.tests.mt import MTStorage



class MinimalTest(bdbmixin.MinimalTestBase, BasicStorage,
                  PackableStorage, SynchronizedStorage, MTStorage):
    def testVersionedStoreAndLoad(self):
        # This storage doesn't support versions, so we should get an exception
        oid = self._storage.newObjectId()
        self.assertRaises(NotImplementedError,
                          self._dostore,
                          oid, data=11, version='a version')

    # requires undo
    def testPackUnlinkedFromRoot(self): pass
    # XXX More tests that require loadSerial()
    def testPackOnlyOneObject(self): pass
    def testPackAllRevisions(self): pass
    def testPackJustOldRevisions(self): pass
    def testPackOnlyOneObject(self): pass


class FullTest(bdbmixin.FullTestBase, BasicStorage,
               RevisionStorage, VersionStorage,
               SynchronizedStorage,
               TransactionalUndoStorage,
               TransactionalUndoVersionStorage,
               PackableStorage,
               IteratorStorage, ExtendedIteratorStorage,
               conflict.ConflictResolvingStorage,
               conflict.ConflictResolvingTransUndoStorage):
    pass



DST_DBHOME = 'test-dst'

class FullRecoveryTest(bdbmixin.FullTestBase, RecoveryStorage):
    def setUp(self):
        bdbmixin.FullTestBase.setUp(self)
        self._zap_dbhome(DST_DBHOME)
        self._dst = self._mk_dbhome(DST_DBHOME)

    def tearDown(self):
        bdbmixin.FullTestBase.tearDown(self)
        self._dst.close()
        self._zap_dbhome(DST_DBHOME)

    def new_dest(self):
        self._zap_dbhome(DST_DBHOME)
        return self._mk_dbhome(DST_DBHOME)



def test_suite():
    suite = unittest.TestSuite()
    if berkeley_is_available:
        suite.addTest(unittest.makeSuite(FullTest))
        suite.addTest(unittest.makeSuite(FullRecoveryTest))
        suite.addTest(unittest.makeSuite(MinimalTest))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
