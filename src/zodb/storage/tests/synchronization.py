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

"""Test the storage's implemenetation of the storage synchronization spec.

The Synchronization spec
    http://www.zope.org/Documentation/Developer/Models/ZODB/
    ZODB_Architecture_Storage_Interface_State_Synchronization_Diag.html

It specifies two states committing and non-committing.  A storage
starts in the non-committing state.  tpc_begin() transfers to the
committting state; tpc_abort() and tpc_finish() transfer back to
non-committing.

Several other methods are only allowed in one state or another.  Many
methods allowed only in the committing state require that they apply
to the currently committing transaction.

The spec is silent on a variety of methods that don't appear to modify
the state, e.g. load(), undoLog(), pack().  It's unclear whether there
is a separate set of synchronization rules that apply to these methods
or if the synchronization is implementation dependent, i.e. only what
is need to guarantee a corrected implementation.

The synchronization spec is also silent on whether there is any
contract implied with the caller.  If the storage can assume that a
single client is single-threaded and that it will not call, e.g., store()
until after it calls tpc_begin(), the implementation can be
substantially simplified.

New and/or unspecified methods:

tpc_vote(): handled like tpc_abort
transactionalUndo(): handled like undo()  (which is how?)

Methods that have nothing to do with committing/non-committing:
load(), loadSerial(), getName(), getSize(), __len__(), history(),
undoLog(), modifiedInVersion(), versionEmpty(), versions(), pack().

Specific questions:

The spec & docs say that undo() takes three arguments, the second
being a transaction.  If the specified arg isn't the current
transaction, the undo() should raise StorageTransactionError.  This
isn't implemented anywhere.  It looks like undo can be called at
anytime.

FileStorage does not allow undo() during a pack.  How should this be
tested?  Is it a general restriction?
"""

from zodb.storage.base import ZERO
from zodb.ztransaction import Transaction
from zodb.storage.interfaces import StorageTransactionError

VERSION = "testversion"
OID = ZERO
SERIALNO = ZERO
TID = ZERO

class SynchronizedStorage:

##    def verifyCommitting(self, callable, *args):
##        self.assertRaises(StorageTransactionError, callable *args)

    def verifyNotCommitting(self, callable, *args):
        args = (StorageTransactionError, callable) + args
        self.assertRaises(*args)

    def verifyWrongTrans(self, callable, *args):
        t = Transaction()
        self._storage.tpcBegin(t)
        self.assertRaises(StorageTransactionError, callable, *args)
        self._storage.tpcAbort(t)

    def testAbortVersionNotCommitting(self):
        self.verifyNotCommitting(self._storage.abortVersion,
                                 VERSION, Transaction())

    def testAbortVersionWrongTrans(self):
        self.verifyWrongTrans(self._storage.abortVersion,
                              VERSION, Transaction())

    def testCommitVersionNotCommitting(self):
        self.verifyNotCommitting(self._storage.commitVersion,
                                 VERSION, "", Transaction())

    def testCommitVersionWrongTrans(self):
        self.verifyWrongTrans(self._storage.commitVersion,
                              VERSION, "", Transaction())


    def testStoreNotCommitting(self):
        self.verifyNotCommitting(self._storage.store,
                                 OID, SERIALNO, "", "", "", Transaction())

    def testStoreWrongTrans(self):
        self.verifyWrongTrans(self._storage.store,
                              OID, SERIALNO, "", "", "", Transaction())

##    def testNewOidNotCommitting(self):
##        self.verifyNotCommitting(self._storage.new_oid)

##    def testNewOidWrongTrans(self):
##        self.verifyWrongTrans(self._storage.new_oid)


    def testAbortNotCommitting(self):
        self._storage.tpcAbort(Transaction())

    def testAbortWrongTrans(self):
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.tpcAbort(Transaction())
        self._storage.tpcAbort(t)

    def testFinishNotCommitting(self):
        t = Transaction()
        self._storage.tpcFinish(t)
        self._storage.tpcAbort(t)

    def testFinishWrongTrans(self):
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.tpcFinish(Transaction())
        self._storage.tpcAbort(t)

    def testBeginCommitting(self):
        t = Transaction()
        self._storage.tpcBegin(t)
        self._storage.tpcBegin(t)
        self._storage.tpcAbort(t)

    # XXX how to check undo?
