##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
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
"""Tests of the distributed commit lock."""

import threading
import time

from zodb.ztransaction import Transaction
from zodb.timestamp import TimeStamp
from zodb.storage.tests.base import zodb_pickle, MinPO
from zodb.interfaces import ZERO

from zodb.zeo.client import ClientStorage
from zodb.zeo.interfaces import ClientDisconnected
from zodb.zeo.tests.basethread import TestThread
from zodb.zeo.tests.common import DummyDB


class WorkerThread(TestThread):

    # run the entire test in a thread so that the blocking call for
    # tpc_vote() doesn't hang the test suite.

    def __init__(self, testcase, storage, trans, method="tpcFinish"):
        self.storage = storage
        self.trans = trans
        self.method = method
        self.ready = threading.Event()
        TestThread.__init__(self, testcase)

    def testrun(self):
        try:
            self.storage.tpcBegin(self.trans)
            oid = self.storage.newObjectId()
            data, refs = zodb_pickle(MinPO("c"))
            self.storage.store(oid, ZERO, data, refs, '', self.trans)
            oid = self.storage.newObjectId()
            data, refs = zodb_pickle(MinPO("c"))
            self.storage.store(oid, ZERO, data, refs, '', self.trans)
            self.myvote()
            if self.method == "tpcFinish":
                self.storage.tpcFinish(self.trans)
            else:
                self.storage.tpcAbort(self.trans)
        except ClientDisconnected:
            pass

    def myvote(self):
        # The vote() call is synchronous, which makes it difficult to
        # coordinate the action of multiple threads that all call
        # vote().  This method sends the vote call, then sets the
        # event saying vote was called, then waits for the vote
        # response.  It digs deep into the implementation of the client.

        # This method is a replacement for:
        #     self.ready.set()
        #     self.storage.tpc_vote(self.trans)

        rpc = self.storage._server.rpc
        msgid = rpc._deferred_call("tpcVote", self.storage._serial)
        self.ready.set()
        rpc._deferred_wait(msgid)
        self.storage._check_serials()

class CommitLockTests:

    NUM_CLIENTS = 5

    # The commit lock tests verify that the storage successfully
    # blocks and restarts transactions when there is contention for a
    # single storage.  There are a lot of cases to cover.  transaction
    # has finished.

    # The general flow of these tests is to start a transaction by
    # getting far enough into 2PC to acquire the commit lock.  Then
    # begin one or more other connections that also want to commit.
    # This causes the commit lock code to be exercised.  Once the
    # other connections are started, the first transaction completes.

    def _cleanup(self):
        for store, trans in self._storages:
            store.tpcAbort(trans)
            store.close()
        self._storages = []

    def _start_txn(self):
        txn = Transaction()
        self._storage.tpcBegin(txn)
        oid = self._storage.newObjectId()
        data, refs = zodb_pickle(MinPO(1))
        self._storage.store(oid, ZERO, data, refs, '', txn)
        return oid, txn

    def testCommitLockVoteFinish(self):
        oid, txn = self._start_txn()
        self._storage.tpcVote(txn)

        self._begin_threads()

        self._storage.tpcFinish(txn)
        self._storage.load(oid, '')

        self._finish_threads()

        self._dostore()
        self._cleanup()

    def testCommitLockVoteAbort(self):
        oid, txn = self._start_txn()
        self._storage.tpcVote(txn)

        self._begin_threads()

        self._storage.tpcAbort(txn)

        self._finish_threads()

        self._dostore()
        self._cleanup()

    def testCommitLockVoteClose(self):
        oid, txn = self._start_txn()
        self._storage.tpcVote(txn)

        self._begin_threads()

        self._storage.close()

        self._finish_threads()
        self._cleanup()

    def _begin_threads(self):
        # Start a second transaction on a different connection without
        # blocking the test thread.
        self._storages = []
        self._threads = []

        for i in range(self.NUM_CLIENTS):
            storage = self._duplicate_client()
            txn = Transaction()
            tid = self._get_timestamp()

            t = WorkerThread(self, storage, txn)
            self._threads.append(t)
            t.start()
            t.ready.wait()

            # Close on the connections abnormally to test server response
            if i == 0:
                storage.close()
            else:
                self._storages.append((storage, txn))

    def _finish_threads(self):
        for t in self._threads:
            t.cleanup()

    def _duplicate_client(self):
        "Open another ClientStorage to the same server."
        # XXX argh it's hard to find the actual address
        # The rpc mgr addr attribute is a list.  Each element in the
        # list is a socket domain (AF_INET, AF_UNIX, etc.) and an
        # address.
        addr = self._storage._addr
        new = ClientStorage(addr, wait=1)
        new.registerDB(DummyDB())
        return new

    def _get_timestamp(self):
        t = time.time()
        t = TimeStamp(*time.gmtime(t)[:5]+(t%60,))
        return `t`

class CommitLockUndoTests(CommitLockTests):

    def _get_trans_id(self):
        self._dostore()
        L = self._storage.undoInfo()
        return L[0]['id']

    def _begin_undo(self, trans_id):
        rpc = self._storage._server.rpc
        return rpc._deferred_call("undo", trans_id, self._storage._serial)

    def _finish_undo(self, msgid):
        return self._storage._server.rpc._deferred_wait(msgid)

    def testCommitLockUndoFinish(self):
        trans_id = self._get_trans_id()
        oid, txn = self._start_txn()
        msgid = self._begin_undo(trans_id)

        self._begin_threads()

        self._finish_undo(msgid)
        self._storage.tpcVote(txn)
        self._storage.tpcFinish(txn)
        self._storage.load(oid, '')

        self._finish_threads()

        self._dostore()
        self._cleanup()

    def testCommitLockUndoAbort(self):
        trans_id = self._get_trans_id()
        oid, txn = self._start_txn()
        msgid = self._begin_undo(trans_id)

        self._begin_threads()

        self._finish_undo(msgid)
        self._storage.tpcVote(txn)
        self._storage.tpcAbort(txn)

        self._finish_threads()

        self._dostore()
        self._cleanup()

    def testCommitLockUndoClose(self):
        trans_id = self._get_trans_id()
        oid, txn = self._start_txn()
        msgid = self._begin_undo(trans_id)

        self._begin_threads()

        self._finish_undo(msgid)
        self._storage.tpcVote(txn)
        self._storage.close()

        self._finish_threads()

        self._cleanup()
