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
"""Run some tests relevant for storages that support pack()."""

import threading
import time

from transaction import get_transaction

from zodb.db import DB
from zodb.interfaces import ZERO, ConflictError
from zodb.serialize import getDBRoot, ConnectionObjectReader
from zodb.ztransaction import Transaction
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle, snooze
from zodb.storage.interfaces import IUndoStorage



class PackableStorage:
    def testPackEmptyStorage(self):
        self._storage.pack(time.time())

    def testPackTomorrow(self):
        self._initroot()
        self._storage.pack(time.time() + 100000)

    def testPackYesterday(self):
        self._initroot()
        self._storage.pack(time.time() - 100000)

    def testPackAllRevisions(self):
        self._initroot()
        eq = self.assertEqual
        raises = self.assertRaises
        # Create a `persistent' object
        obj = self._newobj()
        obj.value = 1
        oid = obj._p_oid
        # Commit three different revisions
        revid1 = self._dostore(oid, data=obj)
        obj.value = 2
        revid2 = self._dostore(oid, revid=revid1, data=obj)
        obj.value = 3
        revid3 = self._dostore(oid, revid=revid2, data=obj)
        # Now make sure all three revisions can be extracted
        data = self._storage.loadSerial(oid, revid1)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 1)
        data = self._storage.loadSerial(oid, revid2)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 2)
        data = self._storage.loadSerial(oid, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)
        # Now pack all transactions
        snooze()
        self._storage.pack(time.time())
        # All revisions of the object should be gone, since there is no
        # reference from the root object to this object.
        raises(KeyError, self._storage.loadSerial, oid, revid1)
        raises(KeyError, self._storage.loadSerial, oid, revid2)
        raises(KeyError, self._storage.loadSerial, oid, revid3)

    def testPackJustOldRevisions(self):
        eq = self.assertEqual
        raises = self.assertRaises
        # Create a root object
        self._initroot()
        obj, root, revid0 = self._linked_newobj()
        # Make sure the root can be retrieved
        data, revid = self._storage.load(ZERO, '')
        eq(revid, revid0)
        eq(zodb_unpickle(data).value, 0)
        # Commit three different revisions of the other object
        obj.value = 1
        oid = obj._p_oid
        revid1 = self._dostore(oid, data=obj)
        obj.value = 2
        revid2 = self._dostore(oid, revid=revid1, data=obj)
        obj.value = 3
        revid3 = self._dostore(oid, revid=revid2, data=obj)
        # Now make sure all three revisions can be extracted
        data = self._storage.loadSerial(oid, revid1)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 1)
        data = self._storage.loadSerial(oid, revid2)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 2)
        data = self._storage.loadSerial(oid, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)
        # Now pack just revisions 1 and 2.  The object's current revision
        # should stay alive because it's pointed to by the root.
        snooze()
        self._storage.pack(time.time())
        # Make sure the revisions are gone, but that the root object and
        # revision 3 are still there and correct
        data, revid = self._storage.load(ZERO, '')
        eq(revid, revid0)
        eq(zodb_unpickle(data).value, 0)
        raises(KeyError, self._storage.loadSerial, oid, revid1)
        raises(KeyError, self._storage.loadSerial, oid, revid2)
        data = self._storage.loadSerial(oid, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)
        data, revid = self._storage.load(oid, '')
        eq(revid, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)

    def testPackOnlyOneObject(self):
        eq = self.assertEqual
        raises = self.assertRaises
        # Create a root object.
        self._initroot()
        data, revid0 = self._storage.load(ZERO, '')
        root = self._reader.getObject(data)
        root.value = -1
        root._p_jar = self._jar
        # Create a persistent object, with some initial state
        obj1 = self._newobj()
        obj1.value = -1
        oid1 = obj1._p_oid
        # Create another persistent object, with some initial state.  Make
        # sure its oid is greater than the first object's oid.
        obj2 = self._newobj()
        obj2.value = -1
        oid2 = obj2._p_oid
        self.failUnless(oid2 > oid1)
        # Link the root object to the persistent objects, in order to keep
        # them alive.  Store the root object.
        root.obj1 = obj1
        root.obj2 = obj2
        root.value = 0
        revid0 = self._dostore(ZERO, data=root, revid=revid0)
        # Make sure the root can be retrieved
        data, revid = self._storage.load(ZERO, '')
        eq(revid, revid0)
        eq(zodb_unpickle(data).value, 0)
        # Commit three different revisions of the first object
        obj1.value = 1
        revid1 = self._dostore(oid1, data=obj1)
        obj1.value = 2
        revid2 = self._dostore(oid1, revid=revid1, data=obj1)
        obj1.value = 3
        revid3 = self._dostore(oid1, revid=revid2, data=obj1)
        # Now make sure all three revisions can be extracted
        data = self._storage.loadSerial(oid1, revid1)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 1)
        data = self._storage.loadSerial(oid1, revid2)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 2)
        data = self._storage.loadSerial(oid1, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)
        # Now commit a revision of the second object
        obj2.value = 11
        revid4 = self._dostore(oid2, data=obj2)
        # And make sure the revision can be extracted
        data = self._storage.loadSerial(oid2, revid4)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 11)
        # Now pack just revisions 1 and 2 of object1.  Object1's current
        # revision should stay alive because it's pointed to by the root, as
        # should Object2's current revision.
        snooze()
        self._storage.pack(time.time())
        # Make sure the revisions are gone, but that object zero, object2, and
        # revision 3 of object1 are still there and correct.
        data, revid = self._storage.load(ZERO, '')
        eq(revid, revid0)
        eq(zodb_unpickle(data).value, 0)
        raises(KeyError, self._storage.loadSerial, oid1, revid1)
        raises(KeyError, self._storage.loadSerial, oid1, revid2)
        data = self._storage.loadSerial(oid1, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)
        data, revid = self._storage.load(oid1, '')
        eq(revid, revid3)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 3)
        data, revid = self._storage.load(oid2, '')
        eq(revid, revid4)
        eq(zodb_unpickle(data).value, 11)
        data = self._storage.loadSerial(oid2, revid4)
        pobj = zodb_unpickle(data)
        eq(pobj.value, 11)

    def testPackUnlinkedFromRoot(self):
        eq = self.assertEqual
        db = DB(self._storage)
        conn = db.open()
        root = conn.root()

        txn = get_transaction()
        txn.note('root')
        txn.commit()

        now = packtime = time.time()
        while packtime <= now:
            packtime = time.time()

        obj = MinPO(7)

        root['obj'] = obj
        txn = get_transaction()
        txn.note('root -> o1')
        txn.commit()

        del root['obj']
        txn = get_transaction()
        txn.note('root -x-> o1')
        txn.commit()

        self._storage.pack(packtime)

        log = self._storage.undoLog()
        tid = log[0]['id']
        db.undo(tid)
        txn = get_transaction()
        txn.note('undo root -x-> o1')
        txn.commit()

        conn.sync()

        eq(root['obj'].value, 7)

    def _PackWhileWriting(self, pack_now=False):
        # A storage should allow some reading and writing during
        # a pack.  This test attempts to exercise locking code
        # in the storage to test that it is safe.  It generates
        # a lot of revisions, so that pack takes a long time.

        db = DB(self._storage)
        conn = db.open()
        root = conn.root()

        for i in range(10):
            root[i] = MinPO(i)
        get_transaction().commit()

        snooze()
        packt = time.time()

        for j in range(10):
            for i in range(10):
                root[i].value = MinPO(i)
                get_transaction().commit()

        threads = [ClientThread(db) for i in range(4)]
        for t in threads:
            t.start()

        if pack_now:
            db.pack(time.time())
        else:
            db.pack(packt)

        for t in threads:
            t.join(30)
        for t in threads:
            t.join(1)
            self.assert_(not t.isAlive())

        # Iterate over the storage to make sure it's sane, but not every
        # storage supports iterators.
        if not hasattr(self._storage, "iterator"):
            return

        iter = self._storage.iterator()
        for txn in iter:
            for data in txn:
                pass
        iter.close()

    def testPackWhileWriting(self):
        self._PackWhileWriting(pack_now=False)

    def testPackNowWhileWriting(self):
        self._PackWhileWriting(pack_now=True)


class ClientThread(threading.Thread):

    def __init__(self, db):
        threading.Thread.__init__(self)
        self.root = db.open().root()

    def run(self):
        for j in range(50):
            try:
                self.root[j % 10].value = MinPO(j)
                get_transaction().commit()
            except ConflictError:
                get_transaction().abort()
