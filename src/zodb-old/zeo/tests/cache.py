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
"""Tests of the ZEO cache"""

from zodb.ztransaction import Transaction
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle
from zodb.storage.interfaces import IUndoStorage

class TransUndoStorageWithCache:

    def testUndoInvalidation(self):
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(23))
        revid = self._dostore(oid, revid=revid, data=MinPO(24))
        revid = self._dostore(oid, revid=revid, data=MinPO(25))

        info = self._storage.undoInfo()
        if not info:
            # XXX perhaps we have an old storage implementation that
            # does do the negative nonsense
            info = self._storage.undoInfo(0, 20)
        tid = info[0]['id']

        # We may need to bail at this point if the storage doesn't
        # support transactional undo
        if not IUndoStorage.isImplementedBy(self._storage):
            return

        # Now start an undo transaction
        t = Transaction()
        t.note('undo1')
        self._storage.tpcBegin(t)

        oids = self._storage.undo(tid, t)

        # Make sure this doesn't load invalid data into the cache
        self._storage.load(oid, '')

        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

        assert len(oids) == 1
        assert oids[0] == oid
        data, revid = self._storage.load(oid, '')
        obj = zodb_unpickle(data)
        assert obj == MinPO(24)

class StorageWithCache:

    def testAbortVersionInvalidation(self):
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(1))
        revid = self._dostore(oid, revid=revid, data=MinPO(2))
        revid = self._dostore(oid, revid=revid, data=MinPO(3), version="foo")
        revid = self._dostore(oid, revid=revid, data=MinPO(4), version="foo")
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.abortVersion("foo", t)
        self._storage.load(oid, "foo")
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        data, revid = self._storage.load(oid, "foo")
        obj = zodb_unpickle(data)
        assert obj == MinPO(2), obj

    def testCommitEmptyVersionInvalidation(self):
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(1))
        revid = self._dostore(oid, revid=revid, data=MinPO(2))
        revid = self._dostore(oid, revid=revid, data=MinPO(3), version="foo")
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.commitVersion("foo", "", t)
        self._storage.load(oid, "")
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        data, revid = self._storage.load(oid, "")
        obj = zodb_unpickle(data)
        assert obj == MinPO(3), obj

    def testCommitVersionInvalidation(self):
        oid = self._storage.newObjectId()
        revid = self._dostore(oid, data=MinPO(1))
        revid = self._dostore(oid, revid=revid, data=MinPO(2))
        revid = self._dostore(oid, revid=revid, data=MinPO(3), version="foo")
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.commitVersion("foo", "bar", t)
        self._storage.load(oid, "")
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        data, revid = self._storage.load(oid, "bar")
        obj = zodb_unpickle(data)
        assert obj == MinPO(3), obj
