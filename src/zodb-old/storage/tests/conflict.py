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
"""Tests for application-level conflict resolution."""

from persistence import Persistent

from zodb.ztransaction import Transaction
from zodb.interfaces import ConflictError, UndoError
from zodb.conflict import ResolveObjectReader
from zodb.storage.tests.base import zodb_unpickle, zodb_pickle


class PCounter(Persistent):
    _value = 0

    def __repr__(self):
        return "<PCounter %d>" % self._value

    def inc(self):
        self._value += 1


class RPCounter(PCounter):
    """Version of PCounter that supports conflict resolution."""

    def _p_resolveConflict(self, oldState, savedState, newState):
        savedDiff = savedState['_value'] - oldState['_value']
        newDiff = newState['_value'] - oldState['_value']

        oldState['_value'] = oldState['_value'] + savedDiff + newDiff

        return oldState

    # XXX What if _p_resolveConflict _thinks_ it resolved the
    # conflict, but did something wrong?

class PCounter2(PCounter):
    def _p_resolveConflict(self, oldState, savedState, newState):
        raise ConflictError

class PCounter3(PCounter):
    def _p_resolveConflict(self, oldState, savedState, newState):
        raise AttributeError, "no attribute (testing conflict resolution)"

class PCounter4(PCounter):
    def _p_resolveConflict(self, oldState, savedState):
        raise RuntimeError, "Can't get here; not enough args"


class ConflictResolvingStorage:
    def testResolve(self):
        obj = RPCounter()
        obj.inc()

        oid = self._storage.newObjectId()

        revid1 = self._dostoreNP(oid, data=zodb_pickle(obj))

        obj.inc()
        obj.inc()
        # The effect of committing two transactions with the same
        # pickle is to commit two different transactions relative to
        # revid1 that add two to _value.
        revid2 = self._dostoreNP(oid, revid=revid1, data=zodb_pickle(obj))
        revid3 = self._dostoreNP(oid, revid=revid1, data=zodb_pickle(obj))

        data, serialno = self._storage.load(oid, '')
        inst = zodb_unpickle(data)
        self.assertEqual(inst._value, 5)

    def unresolvable(self, klass):
        self.assert_(ResolveObjectReader.unresolvable(PCounter))

    def testUnresolvable1(self):
        obj = PCounter()
        obj.inc()

        oid = self._storage.newObjectId()

        revid1 = self._dostoreNP(oid, data=zodb_pickle(obj))

        obj.inc()
        obj.inc()
        # The effect of committing two transactions with the same
        # pickle is to commit two different transactions relative to
        # revid1 that add two to _value.
        revid2 = self._dostoreNP(oid, revid=revid1, data=zodb_pickle(obj))
        self.assertRaises(ConflictError,
                          self._dostoreNP,
                          oid, revid=revid1, data=zodb_pickle(obj))
        self.unresolvable(PCounter)

    def testUnresolvable2(self):
        obj = PCounter2()
        obj.inc()

        oid = self._storage.newObjectId()

        revid1 = self._dostoreNP(oid, data=zodb_pickle(obj))

        obj.inc()
        obj.inc()
        # The effect of committing two transactions with the same
        # pickle is to commit two different transactions relative to
        # revid1 that add two to _value.
        revid2 = self._dostoreNP(oid, revid=revid1, data=zodb_pickle(obj))
        self.assertRaises(ConflictError,
                          self._dostoreNP,
                          oid, revid=revid1, data=zodb_pickle(obj))

    def testBuggyResolve1(self):
        obj = PCounter3()
        obj.inc()

        oid = self._storage.newObjectId()

        revid1 = self._dostoreNP(oid, data=zodb_pickle(obj))

        obj.inc()
        obj.inc()
        # The effect of committing two transactions with the same
        # pickle is to commit two different transactions relative to
        # revid1 that add two to _value.
        revid2 = self._dostoreNP(oid, revid=revid1, data=zodb_pickle(obj))
        self.assertRaises(AttributeError,
                          self._dostoreNP,
                          oid, revid=revid1, data=zodb_pickle(obj))

    def testBuggyResolve2(self):
        obj = PCounter4()
        obj.inc()

        oid = self._storage.newObjectId()

        revid1 = self._dostoreNP(oid, data=zodb_pickle(obj))

        obj.inc()
        obj.inc()
        # The effect of committing two transactions with the same
        # pickle is to commit two different transactions relative to
        # revid1 that add two to _value.
        revid2 = self._dostoreNP(oid, revid=revid1, data=zodb_pickle(obj))
        self.assertRaises(TypeError,
                          self._dostoreNP,
                          oid, revid=revid1, data=zodb_pickle(obj))

class ConflictResolvingTransUndoStorage:

    def testUndoConflictResolution(self):
        # This test is based on checkNotUndoable in the
        # TransactionalUndoStorage test suite.  Except here, conflict
        # resolution should allow us to undo the transaction anyway.

        obj = RPCounter()
        obj.inc()
        oid = self._storage.newObjectId()
        revid_a = self._dostore(oid, data=obj)
        obj.inc()
        revid_b = self._dostore(oid, revid=revid_a, data=obj)
        obj.inc()
        revid_c = self._dostore(oid, revid=revid_b, data=obj)
        # Start the undo
        info = self._storage.undoInfo()
        tid = info[1]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.undo(tid, t)
        self._storage.tpcFinish(t)

    def testUndoUnresolvable(self):
        # This test is based on checkNotUndoable in the
        # TransactionalUndoStorage test suite.  Except here, conflict
        # resolution should allow us to undo the transaction anyway.
        obj = PCounter2()
        obj.inc()
        oid = self._storage.newObjectId()
        revid_a = self._dostore(oid, data=obj)
        obj.inc()
        revid_b = self._dostore(oid, revid=revid_a, data=obj)
        obj.inc()
        revid_c = self._dostore(oid, revid=revid_b, data=obj)
        # Start the undo
        info = self._storage.undoInfo()
        tid = info[1]['id']
        t = Transaction()
        self._storage.tpcBegin(t)
        self.assertRaises(UndoError, self._storage.undo, tid, t)
        self._storage.tpcAbort(t)
