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
# Check interactions between transactionalUndo() and versions.  Any storage
# that supports both transactionalUndo() and versions must pass these tests.

from zodb.ztransaction import Transaction
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_unpickle


class TransactionalUndoVersionStorage:
    def testUndoInVersion(self):
        oid = self._storage.newObjectId()
        version = 'one'
        revid_a = self._dostore(oid, data=MinPO(91))
        revid_b = self._dostore(oid, revid=revid_a, data=MinPO(92),
                                version=version)
        revid_c = self._dostore(oid, revid=revid_b, data=MinPO(93),
                                version=version)

        info=self._storage.undoInfo()
        tid=info[0]['id']
        t = Transaction()
        t.note("undo last revision (93)")
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

        assert len(oids) == 1
        assert oids[0] == oid
        data, revid = self._storage.load(oid, '')
        assert revid == revid_a
        assert zodb_unpickle(data) == MinPO(91)
        data, revid = self._storage.load(oid, version)
        assert revid > revid_b and revid > revid_c
        assert zodb_unpickle(data) == MinPO(92)
        # Now commit the version...
        t = Transaction()
        t.note("commit version")
        self._storage.tpcBegin(t)
        oids = self._storage.commitVersion(version, '', t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

        assert len(oids) == 1
        assert oids[0] == oid

        data, revid = self._storage.load(oid, version)
        assert zodb_unpickle(data) == MinPO(92)
        data, revid = self._storage.load(oid, '')
        assert zodb_unpickle(data) == MinPO(92)
        # ...and undo the commit
        info=self._storage.undoInfo()
        tid=info[0]['id']
        t = Transaction()
        t.note("undo commit version")
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)

        assert len(oids) == 1
        assert oids[0] == oid
        data, revid = self._storage.load(oid, version)
        self.assertEqual(zodb_unpickle(data), MinPO(92))
        data, revid = self._storage.load(oid, '')
        self.assertEqual(zodb_unpickle(data), MinPO(91))
        # Now abort the version
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.abortVersion(version, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        assert len(oids) == 1
        assert oids[0] == oid

        data, revid = self._storage.load(oid, version)
        assert zodb_unpickle(data) == MinPO(91)
        data, revid = self._storage.load(oid, '')
        assert zodb_unpickle(data) == MinPO(91)
        # Now undo the abort
        info=self._storage.undoInfo()
        tid=info[0]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        assert len(oids) == 1
        assert oids[0] == oid
        # And the object should be back in versions 'one' and ''
        data, revid = self._storage.load(oid, version)
        assert zodb_unpickle(data) == MinPO(92)
        data, revid = self._storage.load(oid, '')
        assert zodb_unpickle(data) == MinPO(91)
