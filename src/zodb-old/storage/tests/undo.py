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
"""Check transactionalUndo().

Any storage that supports transactionalUndo() must pass these tests.
"""

import time

from zodb import interfaces
from zodb.interfaces import ZERO
from zodb.ztransaction import Transaction
from zodb.utils import u64, p64
from zodb.db import DB

from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_pickle, zodb_unpickle, snooze
from zodb.storage.tests.base import handle_serials
from zodb.storage.interfaces import IUndoStorage

from persistence import Persistent
from transaction import get_transaction

class C(Persistent):
    pass

def listeq(L1, L2):
    """Return True if L1.sort() == L2.sort()"""
    c1 = L1[:]
    c2 = L2[:]
    c1.sort()
    c2.sort()
    return c1 == c2

class TransactionalUndoStorage:

    def _transaction_begin(self):
        self.__serials = {}

    def _transaction_store(self, oid, rev, (data, refs), vers, trans):
        r = self._storage.store(oid, rev, data, refs, vers, trans)
        if r:
            if isinstance(r, str):
                self.__serials[oid] = r
            else:
                for oid, serial in r:
                    self.__serials[oid] = serial

    def _transaction_vote(self, trans):
        r = self._storage.tpcVote(trans)
        if r:
            for oid, serial in r:
                self.__serials[oid] = serial

    def _transaction_newserial(self, oid):
        return self.__serials[oid]

    def _multi_obj_transaction(self, objs, note=None):
        newrevs = {}
        t = Transaction()
        if note:
            t.note(note)
        self._storage.tpcBegin(t)
        self._transaction_begin()
        # datarefs is a tuple of (data, refs)
        for oid, rev, datarefs in objs:
            self._transaction_store(oid, rev, datarefs, '', t)
            newrevs[oid] = None
        self._transaction_vote(t)
        self._storage.tpcFinish(t)
        for oid in newrevs.keys():
            newrevs[oid] = self._transaction_newserial(oid)
        return newrevs

    def _iterate(self):
        """Iterate over the storage in its final state."""
        # This is testing that the iterator() code works correctly, but not
        # all storages support iteration.
        if not IUndoStorage.isImplementedBy(self._storage):
            return
        iter = self._storage.iterator()
        for txn in iter:
            for rec in txn:
                pass

    def testSimpleTransactionalUndo(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(23))
        revid = self._dostore(oid, revid=revid, data=MinPO(24))
        revid = self._dostore(oid, revid=revid, data=MinPO(25))

        info = self._storage.undoInfo()
        tid = info[0]['id']
        # Now start an undo transaction
        t = Transaction()
        t.note('undo1')
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(24))
        # Do another one
        info = self._storage.undoInfo()
        tid = info[2]['id']
        t = Transaction()
        t.note('undo2')
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(23))
        # Try to undo the first record
        info = self._storage.undoInfo()
        tid = info[4]['id']
        t = Transaction()
        t.note('undo3')
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

        eq(len(oids), 1)
        eq(oids[0], oid)
        # This should fail since we've undone the object's creation
        self.assertRaises(KeyError,
                          self._storage.load, oid, '')
        # And now let's try to redo the object's creation
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(23))
        self._iterate()

##    def testCreationUndoneGetSerial(self):
##        # XXX Do we really want to change FileStorage to make this test
##        # pass?  getSerial() is nice and fast right now.
        
##        # create an object
##        oid = self._storage.newObjectId()
##        revid = self._dostore(oid, data=MinPO(23))
##        print repr(revid)
##        # undo its creation
##        info = self._storage.undoInfo()
##        tid = info[0]['id']
##        t = Transaction()
##        t.note('undo1')
##        self._storage.tpcBegin(t)
##        oids = self._storage.undo(tid, t)
##        self._storage.tpcVote(t)
##        self._storage.tpcFinish(t)
##        # Check that calling getSerial on an uncreated object raises a KeyError
##        # The current version of FileStorage fails this test
##        self.assertRaises(KeyError, self._storage.getSerial, oid)

    def testUndoCreationBranch1(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(11))
        revid = self._dostore(oid, revid=revid, data=MinPO(12))
        # Undo the last transaction
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(11))
        # Now from here, we can either redo the last undo, or undo the object
        # creation.  Let's undo the object creation.
        info = self._storage.undoInfo()
        tid = info[2]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        self.assertRaises(KeyError, self._storage.load, oid, '')
        self._iterate()

    def testUndoCreationBranch2(self):
        eq = self.assertEqual
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(11))
        revid = self._dostore(oid, revid=revid, data=MinPO(12))
        # Undo the last transaction
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(11))
        # Now from here, we can either redo the last undo, or undo the object
        # creation.  Let's redo the last undo
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        eq(zodb_unpickle(data), MinPO(12))
        self._iterate()

    def testTwoObjectUndo(self):
        eq = self.assertEqual
        # Convenience
        p31, p32, p51, p52 = [zodb_pickle(MinPO(i)) for i in (31, 32, 51, 52)]
        oid1 = self._storage.newObjectId()
        oid2 = self._storage.newObjectId()
        revid1 = revid2 = ZERO
        # Store two objects in the same transaction
        t = Transaction()
        self._storage.tpcBegin(t)
        self._transaction_begin()
        self._transaction_store(oid1, revid1, p31, '', t)
        self._transaction_store(oid2, revid2, p51, '', t)
        # Finish the transaction
        self._transaction_vote(t)
        revid1 = self._transaction_newserial(oid1)
        revid2 = self._transaction_newserial(oid2)
        self._storage.tpcFinish(t)
        eq(revid1, revid2)
        # Update those same two objects
        t = Transaction()
        self._storage.tpcBegin(t)
        self._transaction_begin()
        self._transaction_store(oid1, revid1, p32, '', t)
        self._transaction_store(oid2, revid2, p52, '', t)
        # Finish the transaction
        self._transaction_vote(t)
        revid1 = self._transaction_newserial(oid1)
        revid2 = self._transaction_newserial(oid2)
        self._storage.tpcFinish(t)
        eq(revid1, revid2)
        # Make sure the objects have the current value
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(32))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(52))
        # Now attempt to undo the transaction containing two objects
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 2)
        self.failUnless(oid1 in oids)
        self.failUnless(oid2 in oids)
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(31))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(51))
        self._iterate()

    def testTwoObjectUndoAtOnce(self):
        # Convenience
        eq = self.assertEqual
        unless = self.failUnless
        p30, p31, p32, p50, p51, p52 = [zodb_pickle(MinPO(i))
                                        for i in (30, 31, 32, 50, 51, 52)]
        oid1 = self._storage.newObjectId()
        oid2 = self._storage.newObjectId()
        revid1 = revid2 = ZERO
        # Store two objects in the same transaction
        d = self._multi_obj_transaction([(oid1, revid1, p30),
                                         (oid2, revid2, p50),
                                         ], "first update")
        eq(d[oid1], d[oid2])
        # Update those same two objects
        d = self._multi_obj_transaction([(oid1, d[oid1], p31),
                                         (oid2, d[oid2], p51),
                                         ], "second update")
        eq(d[oid1], d[oid2])
        # Update those same two objects
        d = self._multi_obj_transaction([(oid1, d[oid1], p32),
                                         (oid2, d[oid2], p52),
                                         ], "third update")
        eq(d[oid1], d[oid2])
        revid1 = self._transaction_newserial(oid1)
        revid2 = self._transaction_newserial(oid2)
        eq(revid1, revid2)
        # Make sure the objects have the current value
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(32))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(52))
        # Now attempt to undo the transaction containing two objects
        info = self._storage.undoInfo()
        tid = info[0]['id']
        tid1 = info[1]['id']
        t = Transaction()
        t.note("undo transaction containing two objects")
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        oids1 = self._storage.undo(tid1, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 2)
        eq(len(oids1), 2)
        unless(oid1 in oids)
        unless(oid2 in oids)
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(30))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(50))
        # Now try to undo the one we just did to undo, whew
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        t.note("undo the undo")
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 2)
        unless(oid1 in oids)
        unless(oid2 in oids)
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(32))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(52))
        self._iterate()

    def testTwoObjectUndoAgain(self):
        eq = self.assertEqual
        p31, p32, p33, p51, p52, p53 = [zodb_pickle(MinPO(i))
                                        for i in (31, 32, 33, 51, 52, 53)]
        # Like the above, but the first revision of the objects are stored in
        # different transactions.
        oid1 = self._storage.newObjectId()
        oid2 = self._storage.newObjectId()
        revid1 = self._dostore(oid1, data=p31, already_pickled=True)
        revid2 = self._dostore(oid2, data=p51, already_pickled=True)
        # Update those same two objects
        t = Transaction()
        self._storage.tpcBegin(t)
        self._transaction_begin()
        self._transaction_store(oid1, revid1, p32, '', t)
        self._transaction_store(oid2, revid2, p52, '', t)
        # Finish the transaction
        self._transaction_vote(t)
        self._storage.tpcFinish(t)
        revid1 = self._transaction_newserial(oid1)
        revid2 = self._transaction_newserial(oid2)
        eq(revid1, revid2)
        # Now attempt to undo the transaction containing two objects
        info = self._storage.undoInfo()
        tid = info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 2)
        self.failUnless(oid1 in oids)
        self.failUnless(oid2 in oids)
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(31))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(51))
        # Like the above, but this time, the second transaction contains only
        # one object.
        t = Transaction()
        self._storage.tpcBegin(t)
        self._transaction_begin()
        self._transaction_store(oid1, revid1, p33, '', t)
        self._transaction_store(oid2, revid2, p53, '', t)
        # Finish the transaction
        self._transaction_vote(t)
        self._storage.tpcFinish(t)
        revid1 = self._transaction_newserial(oid1)
        revid2 = self._transaction_newserial(oid2)
        eq(revid1, revid2)
        # Update in different transactions
        revid1 = self._dostore(oid1, revid=revid1, data=MinPO(34))
        revid2 = self._dostore(oid2, revid=revid2, data=MinPO(54))
        # Now attempt to undo the transaction containing two objects
        info = self._storage.undoInfo()
        tid = info[1]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        self.failUnless(oid1 in oids)
        self.failUnless(not oid2 in oids)
        data, revid1 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(33))
        data, revid2 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(54))
        self._iterate()

    def testNotUndoable(self):
        eq = self.assertEqual
        # Set things up so we've got a transaction that can't be undone
        oid = self._storage.newObjectId()
        revid_a = self._dostore(oid, data=MinPO(51))
        revid_b = self._dostore(oid, revid=revid_a, data=MinPO(52))
        revid_c = self._dostore(oid, revid=revid_b, data=MinPO(53))
        # Start the undo
        info = self._storage.undoInfo()
        tid = info[1]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        self.assertRaises(interfaces.UndoError,
                          self._storage.undo,
                          tid, t)
        self._storage.tpcAbort(t)
        # Now have more fun: object1 and object2 are in the same transaction,
        # which we'll try to undo to, but one of them has since modified in
        # different transaction, so the undo should fail.
        oid1 = oid
        revid1 = revid_c
        oid2 = self._storage.newObjectId()
        revid2 = ZERO
        p81, p82, p91, p92 = [zodb_pickle(MinPO(i)) for i in (81, 82, 91, 92)]
        t = Transaction()
        self._storage.tpcBegin(t)
        self._transaction_begin()
        self._transaction_store(oid1, revid1, p81, '', t)
        self._transaction_store(oid2, revid2, p91, '', t)
        self._transaction_vote(t)
        self._storage.tpcFinish(t)
        revid1 = self._transaction_newserial(oid1)
        revid2 = self._transaction_newserial(oid2)
        eq(revid1, revid2)
        # Make sure the objects have the expected values
        data, revid_11 = self._storage.load(oid1, '')
        eq(zodb_unpickle(data), MinPO(81))
        data, revid_22 = self._storage.load(oid2, '')
        eq(zodb_unpickle(data), MinPO(91))
        eq(revid_11, revid1)
        eq(revid_22, revid2)
        # Now modify oid2
        revid2 = self._dostore(oid2, revid=revid2, data=MinPO(92))
        self.assertNotEqual(revid1, revid2)
        self.assertNotEqual(revid2, revid_22)
        info = self._storage.undoInfo()
        tid = info[1]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        self.assertRaises(interfaces.UndoError,
                          self._storage.undo,
                          tid, t)
        self._storage.tpcAbort(t)
        self._iterate()

    def testTransactionalUndoAfterPack(self):
        eq = self.assertEqual
        # Add a few object revisions
        self._initroot()
        obj, root, revid0 = self._linked_newobj()
        oid = obj._p_oid
        revid1 = self._dostore(oid, data=MinPO(51))
        # Get a packtime greater than revid1's timestamp
        snooze()
        packtime = time.time()
        # Now be sure that revid2 has a timestamp after packtime
        snooze()
        revid2 = self._dostore(oid, revid=revid1, data=MinPO(52))
        revid3 = self._dostore(oid, revid=revid2, data=MinPO(53))
        # Now get the undo log
        info = self._storage.undoInfo()
        eq(len(info), 5)
        tid = info[0]['id']

        # Now pack just the initial revision of the object.  We need the
        # second revision otherwise we won't be able to undo the third
        # revision!
        self._storage.pack(packtime)

        # Make some basic assertions about the undo information now
        info2 = self._storage.undoInfo()
        eq(len(info2), 2)
        # And now attempt to undo the last transaction
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        eq(len(oids), 1)
        eq(oids[0], oid)
        data, revid = self._storage.load(oid, '')
        # The object must now be at the second state
        eq(zodb_unpickle(data), MinPO(52))
        self._iterate()

    def testTransactionalUndoAfterPackWithObjectUnlinkFromRoot(self):
        eq = self.assertEqual
        db = DB(self._storage)
        conn = db.open()
        root = conn.root()

        o1 = C()
        o2 = C()
        root['obj'] = o1
        o1.obj = o2
        txn = get_transaction()
        txn.note('o1 -> o2')
        txn.commit()
        now = packtime = time.time()
        while packtime <= now:
            packtime = time.time()

        o3 = C()
        o2.obj = o3
        txn = get_transaction()
        txn.note('o1 -> o2 -> o3')
        txn.commit()

        o1.obj = o3
        txn = get_transaction()
        txn.note('o1 -> o3')
        txn.commit()

        log = self._storage.undoLog()
        eq(len(log), 4)
        for entry in zip(log, ('o1 -> o3', 'o1 -> o2 -> o3',
                               'o1 -> o2', 'initial database creation')):
            eq(entry[0]['description'], entry[1])

        self._storage.pack(packtime)

        log = self._storage.undoLog()
        for entry in zip(log, ('o1 -> o3', 'o1 -> o2 -> o3')):
            eq(entry[0]['description'], entry[1])

        tid = log[0]['id']
        db.undo(tid)
        txn = get_transaction()
        txn.note('undo')
        txn.commit()
        # undo does a txn-undo, but doesn't invalidate
        conn.sync()

        log = self._storage.undoLog()
        for entry in zip(log, ('undo', 'o1 -> o3', 'o1 -> o2 -> o3')):
            eq(entry[0]['description'], entry[1])

        eq(o1.obj, o2)
        eq(o1.obj.obj, o3)
        self._iterate()

    def testPackAfterUndoDeletion(self):
        db = DB(self._storage)
        cn = db.open()
        root = cn.root()

        pack_times = []
        def set_pack_time():
            snooze()
            pack_times.append(time.time())

        root["key0"] = MinPO(0)
        root["key1"] = MinPO(1)
        root["key2"] = MinPO(2)
        txn = get_transaction()
        txn.note("create 3 keys")
        txn.commit()

        set_pack_time()

        del root["key1"]
        txn = get_transaction()
        txn.note("delete 1 key")
        txn.commit()

        set_pack_time()

        root._p_deactivate()
        cn.sync()
        self.assert_(listeq(root.keys(), ["key0", "key2"]))

        L = db.undoInfo()
        db.undo(L[0]["id"])
        txn = get_transaction()
        txn.note("undo deletion")
        txn.commit()

        set_pack_time()

        root._p_deactivate()
        cn.sync()
        self.assert_(listeq(root.keys(), ["key0", "key1", "key2"]))

        for t in pack_times:
            self._storage.pack(t)

            root._p_deactivate()
            cn.sync()
            self.assert_(listeq(root.keys(), ["key0", "key1", "key2"]))
            for i in range(3):
                obj = root["key%d" % i]
                self.assertEqual(obj.value, i)
            root.items()

    def testPackAfterUndoManyTimes(self):
        db = DB(self._storage)
        cn = db.open()
        rt = cn.root()

        rt["test"] = MinPO(1)
        get_transaction().commit()
        rt["test2"] = MinPO(2)
        get_transaction().commit()
        rt["test"] = MinPO(3)
        txn = get_transaction()
        txn.note("root of undo")
        txn.commit()

        packtimes = []
        for i in range(10):
            L = db.undoInfo()
            db.undo(L[0]["id"])
            txn = get_transaction()
            txn.note("undo %d" % i)
            txn.commit()
            rt._p_deactivate()
            cn.sync()

            self.assertEqual(rt["test"].value, i % 2 and 3 or 1)
            self.assertEqual(rt["test2"].value, 2)

            # Ensure that the pack time is distinguishable from any
            # timestamps on both sides of it.
            snooze()
            packtimes.append(time.time())
            snooze()

        for t in packtimes:
            self._storage.pack(t)
            cn.sync()
            cn._cache.clear()
            # The last undo set the value to 3 and pack should
            # never change that.
            self.assertEqual(rt["test"].value, 3)
            self.assertEqual(rt["test2"].value, 2)

    def testTransactionalUndoIterator(self):
        # check that data_txn set in iterator makes sense
        if not IUndoStorage.isImplementedBy(self._storage):
            return

        s = self._storage

        BATCHES = 4
        OBJECTS = 4

        orig = []
        for i in range(BATCHES):
            t = Transaction()
            tid = p64(i + 1)
            s.tpcBegin(t, tid)
            for j in range(OBJECTS):
                oid = s.newObjectId()
                obj = MinPO(i * OBJECTS + j)
                data, refs = zodb_pickle(obj)
                revid = s.store(oid, None, data, refs, '', t)
                orig.append((tid, oid, revid))
            s.tpcVote(t)
            s.tpcFinish(t)

        i = 0
        for tid, oid, revid in orig:
            self._dostore(oid, revid=revid, data=MinPO(revid),
                          description="update %s" % i)

        # Undo the OBJECTS transactions that modified objects created
        # in the ith original transaction.

        def undo(i):
            info = s.undoInfo()
            t = Transaction()
            s.tpcBegin(t)
            base = i * OBJECTS + i
            for j in range(OBJECTS):
                tid = info[base + j]['id']
                s.undo(tid, t)
            s.tpcVote(t)
            s.tpcFinish(t)

        for i in range(BATCHES):
            undo(i)

        # There are now (2 + OBJECTS) * BATCHES transactions:
        #     BATCHES original transactions, followed by
        #     OBJECTS * BATCHES modifications, followed by
        #     BATCHES undos

        fsiter = iter(s.iterator())
        offset = 0

        eq = self.assertEqual

        for i in range(BATCHES):
            txn = fsiter.next()
            offset += 1

            tid = p64(i + 1)
            eq(txn.tid, tid)

            L1 = [(rec.oid, rec.serial, rec.data_txn) for rec in txn]
            L2 = [(oid, revid, None) for _tid, oid, revid in orig
                  if _tid == tid]

            eq(L1, L2)

        for i in range(BATCHES * OBJECTS):
            txn = fsiter.next()
            offset += 1
            eq(len([rec for rec in txn if rec.data_txn is None]), 1)

        for i in range(BATCHES):
            txn = fsiter.next()
            offset += 1

            # The undos are performed in reverse order.
            otid = p64(BATCHES - i)
            L1 = [(rec.oid, rec.data_txn) for rec in txn]
            L2 = [(oid, otid) for _tid, oid, revid in orig
                  if _tid == otid]
            L1.sort()
            L2.sort()
            eq(L1, L2)

        self.assertRaises(StopIteration, fsiter.next)

    def testUnicodeTransactionAttributes(self):
        eq = self.assertEqual
        user = u'\xc2nne P\xebrson'
        descrip = u'What this is about'
        txn = Transaction(user=user, description=descrip)
        self._storage.tpcBegin(txn)
        oid = self._storage.newObjectId()
        data, refs = zodb_pickle(MinPO(9))
        r1 = self._storage.store(oid, None, data, refs, '', txn)
        r2 = self._storage.tpcVote(txn)
        self._storage.tpcFinish(txn)
        revid = handle_serials(oid, r1, r2)
        # Now use the iterator to find the transaction's user and descr
        for txn in self._storage.iterator():
            if txn.tid == revid:
                eq(txn.user, user)
                eq(txn.description, descrip)
                break
        else:
            self.fail('transaction not found')

    def testPackUndoLog(self):
        self._initroot()
        eq = self.assertEqual
        raises = self.assertRaises
        # Create a `persistent' object
        obj = self._newobj()
        obj.value = 1
        oid = obj._p_oid
        # Commit two different revisions
        revid1 = self._dostore(oid, data=obj)
        obj.value = 2
        snooze()
        packtime = time.time()
        snooze()
        revid2 = self._dostore(oid, revid=revid1, data=obj)
        # Now pack the first transaction
        self.assertEqual(3, len(self._storage.undoLog()))
        self._storage.pack(packtime)
        # The undo log contains only the most resent transaction
        self.assertEqual(1, len(self._storage.undoLog()))

    def dont_testPackUndoLogUndoable(self):
        # XXX This test was copied from ZODB3, but no effort was made
        # to convert the code to make it work in ZODB4.
        
        # A disabled test. I wanted to test that the content of the
        # undo log was consistent, but every storage appears to
        # include something slightly different. If the result of this
        # method is only used to fill a GUI then this difference
        # doesnt matter.  Perhaps re-enable this test once we agree
        # what should be asserted.

        self._initroot()
        # Create two `persistent' object
        obj1 = self._newobj()
        oid1 = obj1.getoid()
        obj1.value = 1
        obj2 = self._newobj()
        oid2 = obj2.getoid()
        obj2.value = 2
        
        # Commit the first revision of each of them
        revid11 = self._dostoreNP(oid1, data=pickle.dumps(obj1),
                                  description="1-1")
        revid22 = self._dostoreNP(oid2, data=pickle.dumps(obj2),
                                  description="2-2")
        
        # remember the time. everything above here will be packed away
        snooze()
        packtime = time.time()
        snooze()
        # Commit two revisions of the first object
        obj1.value = 3
        revid13 = self._dostoreNP(oid1, revid=revid11,
                                  data=pickle.dumps(obj1), description="1-3")
        obj1.value = 4
        revid14 = self._dostoreNP(oid1, revid=revid13,
                                  data=pickle.dumps(obj1), description="1-4")
        # Commit one revision of the second object
        obj2.value = 5
        revid25 = self._dostoreNP(oid2, revid=revid22,
                                  data=pickle.dumps(obj2), description="2-5")
        # Now pack
        self.assertEqual(6,len(self._storage.undoLog()))
        print '\ninitial undoLog was'
        for r in self._storage.undoLog(): print r
        self._storage.pack(packtime, referencesf)
        # The undo log contains only two undoable transaction.
        print '\nafter packing undoLog was'
        for r in self._storage.undoLog(): print r
        # what can we assert about that?

