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
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

"""Run the basic tests for a storage as described in the official storage API

The most complete and most out-of-date description of the interface is:
http://www.zope.org/Documentation/Developer/Models/ZODB/ZODB_Architecture_Storage_Interface_Info.html

All storages should be able to pass these tests.

$Id: basic.py,v 1.11 2003/07/10 17:41:49 bwarsaw Exp $
"""

from zodb import interfaces
from zodb.storage.interfaces import StorageTransactionError, IStorage
from zodb.ztransaction import Transaction

from zodb.storage.base import ZERO
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle, zodb_pickle, handle_serials


class BasicStorage:

    def testIStorage(self):
        self.assert_(IStorage.isImplementedBy(self._storage))

    def testDatabaseVersion(self):
        version = "abcd"
        self._storage.setVersion(version)
        self.assertEqual(version, self._storage.getVersion())

    def testDatabaseVersionPersistent(self):
        version = "abcd"
        self._storage.setVersion(version)
        self._storage.close()
        self.open()
        self.assertEqual(version, self._storage.getVersion())

    def testBasics(self):
        t = Transaction()
        self._storage.tpcBegin(t)
        # This should simply return
        self._storage.tpcBegin(t)
        # Aborting is easy
        self._storage.tpcAbort(t)
        # Test a few expected exceptions when we're doing operations giving a
        # different Transaction object than the one we've begun on.
        self._storage.tpcBegin(t)
        self.assertRaises(StorageTransactionError, self._storage.store,
                          0, 0, 0, 0, 0, Transaction())

        try:
            self._storage.abortVersion('dummy', Transaction())
        except (StorageTransactionError, interfaces.VersionCommitError):
            pass # test passed ;)
        else:
            assert 0, "Should have failed, invalid transaction."

        try:
            self._storage.commitVersion('dummy', 'dummer', Transaction())
        except (StorageTransactionError, interfaces.VersionCommitError):
            pass # test passed ;)
        else:
            assert 0, "Should have failed, invalid transaction."

        self.assertRaises(StorageTransactionError, self._storage.store,
                          0, 1, 2, 3, 4, Transaction())
        self._storage.tpcAbort(t)

    def testSerialIsNoneForInitialRevision(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        txn = Transaction()
        self._storage.tpcBegin(txn)
        # Use None for serial.  Don't use _dostore() here because that coerces
        # serial=None to serial=ZERO.
        data, refs = zodb_pickle(MinPO(11))
        r1 = self._storage.store(oid, None, data, refs, '', txn)
        r2 = self._storage.tpcVote(txn)
        self._storage.tpcFinish(txn)
        newrevid = handle_serials(oid, r1, r2)
        data, revid = self._storage.load(oid, '')
        value = zodb_unpickle(data)
        eq(value, MinPO(11))
        eq(revid, newrevid)

    def testNonVersionStore(self, oid=None, revid=None, version=None):
        revid = ZERO
        newrevid = self._dostore(revid=revid)
        # Finish the transaction.
        self.assertNotEqual(newrevid, revid)

    def testNonVersionStoreAndLoad(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        self._dostore(oid=oid, data=MinPO(7))
        data, revid = self._storage.load(oid, '')
        value = zodb_unpickle(data)
        eq(value, MinPO(7))
        # Now do a bunch of updates to an object
        for i in range(13, 22):
            revid = self._dostore(oid, revid=revid, data=MinPO(i))
        # Now get the latest revision of the object
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(21))

    def testNonVersionModifiedInVersion(self):
        oid = self._storage.newObjectId()
        self._dostore(oid=oid)
        self.assertEqual(self._storage.modifiedInVersion(oid), '')

    def testConflicts(self):
        oid = self._storage.newObjectId()
        revid1 = self._dostore(oid, data=MinPO(11))
        revid2 = self._dostore(oid, revid=revid1, data=MinPO(12))
        self.assertRaises(interfaces.ConflictError,
                          self._dostore,
                          oid, revid=revid1, data=MinPO(13))

    def testWriteAfterAbort(self):
        oid = self._storage.newObjectId()
        t = Transaction()
        self._storage.tpcBegin(t)
        data, refs = zodb_pickle(MinPO(5))
        self._storage.store(oid, ZERO, data, refs, '', t)
        # Now abort this transaction
        self._storage.tpcAbort(t)
        # Now start all over again
        oid = self._storage.newObjectId()
        self._dostore(oid=oid, data=MinPO(6))

    def testAbortAfterVote(self):
        oid1 = self._storage.newObjectId()
        revid1 = self._dostore(oid=oid1, data=MinPO(-2))
        oid = self._storage.newObjectId()
        t = Transaction()
        self._storage.tpcBegin(t)
        data, refs = zodb_pickle(MinPO(5))
        self._storage.store(oid, ZERO, data, refs, '', t)
        # Now abort this transaction
        self._storage.tpcVote(t)
        self._storage.tpcAbort(t)
        # Now start all over again
        oid = self._storage.newObjectId()
        revid = self._dostore(oid=oid, data=MinPO(6))

        for oid, revid in [(oid1, revid1), (oid, revid)]:
            data, _revid = self._storage.load(oid, '')
            self.assertEqual(revid, _revid)

    def testStoreTwoObjects(self):
        noteq = self.assertNotEqual
        p31, p32, p51, p52 = map(MinPO, (31, 32, 51, 52))
        oid1 = self._storage.newObjectId()
        oid2 = self._storage.newObjectId()
        noteq(oid1, oid2)
        revid1 = self._dostore(oid1, data=p31)
        revid2 = self._dostore(oid2, data=p51)
        noteq(revid1, revid2)
        revid3 = self._dostore(oid1, revid=revid1, data=p32)
        revid4 = self._dostore(oid2, revid=revid2, data=p52)
        noteq(revid3, revid4)

    def testGetSerial(self):
        if not hasattr(self._storage, 'getSerial'):
            return
        eq = self.assertEqual
        p41, p42 = map(MinPO, (41, 42))
        oid = self._storage.newObjectId()
        self.assertRaises(KeyError, self._storage.getSerial, oid)
        # Now store a revision
        revid1 = self._dostore(oid, data=p41)
        eq(revid1, self._storage.getSerial(oid))
        # And another one
        revid2 = self._dostore(oid, revid=revid1, data=p42)
        eq(revid2, self._storage.getSerial(oid))

    def testTwoArgBegin(self):
        # XXX how standard is three-argument tpc_begin()?
        t = Transaction()
        tid = chr(42) * 8
        self._storage.tpcBegin(t, tid)
        oid = self._storage.newObjectId()
        data, refs = zodb_pickle(MinPO(8))
        self._storage.store(oid, None, data, refs, '', t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

    def testNote(self):
        oid = self._storage.newObjectId()
        t = Transaction()
        self._storage.tpcBegin(t)
        t.note('this is a test')
        data, refs = zodb_pickle(MinPO(5))
        self._storage.store(oid, ZERO, data, refs, '', t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

    def testGetExtensionMethods(self):
        m = self._storage.getExtensionMethods()
        self.assertEqual(type(m),type({}))
        for k,v in m.items():
            self.assertEqual(v,None)
            self.assert_(callable(getattr(self._storage,k)))

    def testLastTransactionBeforeFirstTransaction(self):
        self.assertEqual(self._storage.lastTransaction(), ZERO)

    def testLastTransaction(self):
        eq = self.assertEqual
        unless = self.failUnless
        revid = self._dostore()
        last = self._storage.lastTransaction()
        eq(revid, last)
        revid = self._dostore()
        nextlast = self._storage.lastTransaction()
        eq(revid, nextlast)
        unless(nextlast > last)
        # Start a transaction, abort it, and make sure the last committed
        # transaction id doesn't change.
        t = Transaction()
        oid = self._storage.newObjectId()
        self._storage.tpcBegin(t)
        data, refs = zodb_pickle(MinPO(5))
        self._storage.store(oid, ZERO, data, refs, '', t)
        # Now abort this transaction
        self._storage.tpcAbort(t)
        eq(nextlast, self._storage.lastTransaction())
