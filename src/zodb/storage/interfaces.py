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
"""ZODB storage interface

$Id: interfaces.py,v 1.18 2003/07/10 17:37:35 bwarsaw Exp $
"""

from zope.interface import Interface, Attribute
from zodb.interfaces import POSError

__all__ = ["IStorage",
           "IUndoStorage",
           "IVersionStorage",
           "IStorageIterator",
           "ITransactionRecordIterator",
           "IDataRecord",
           # the rest are exceptions
           "StorageError",
           "StorageVersionError",
           "StorageTransactionError",
           "StorageSystemError",
           "MountedStorageError",
           "ReadOnlyError",
           "TransactionTooLargeError",
           ]

class IStorage(Interface):
    """Storage layer for ZODB.

    This part of the interface should document important concepts like
    what methods must execute in a transaction context.

    Synchronization

    A storage implementation must be thread-safe.  Multiple threads
    call call storage methods at any time.

    A storage must implement a two-phase commit protocol for updates.
    Only one transaction can commit at a time.  The storage must
    guarantee that after a tpcVote() call returns, no other
    transaction can advance beyond the tpcVote() until the first
    transaction commits or aborts.  Some storages do not allow more
    than one storage to advance beyond tpcBegin().

    The load() method must always return the most recently committed
    data.  A load() method can not run at the same time as tpcFinish()
    if it would be possible to read inconsistent data.  XXX Need to
    flesh out the details here.

    """

    def close():
        """Close the storage.

        The storage should be in a stable persistent state and any
        external resources should be freed.  After this method is called,
        the storage should not be used.

        It should be possible to call close() more than once.
        """

    def cleanup():
        """Remove all files created by the storage.

        This method primarily exists to support the test suite.
        """

    def sortKey():
        """Return a string representing the transaction sort key.

        Every storage instance must have a sort key that uniquely
        identifies the storage.  The key must be unique across all
        storages participating in a transaction.  It should never
        change.

        If a storage can be used in a distributed setting, then the
        sort key should be unique across all storages available on the
        network.
        """

    def getVersion():
        """Return the database version string for the data in the storage."""

    def setVersion():
        """Set the database version string for the data in the storage."""

    def load(oid, version=""):
        """Return data record and serial number for object `oid`.

        Raises KeyError if the object does not exist.  Note that a
        storage supporting multiple revisions will raise KeyError when
        an object does not currently exist, even though historical
        revisions of the object are still in the database.

        Takes an optional argument that specifies the version to read from.
        """

    def getSerial(oid):
        """Return the current serial number for oid.

        If the object is modified in the version, return that serial number.
        """

    def store(oid, serial, data, refs, version, txn):
        """Store an object and returns a new serial number.

        Arguments:
        oid -- the object id, a string
        serial -- the serial number of the revision read by txn, a string
        data -- a 2-tuple of the data record (string), and the oids of the
                objects referenced by the this object, as a list
        refs -- the list of object ids of objects referenced by the data
        version -- the version, a string, typically the empty string
        txn -- the current transaction

        Raises ConflictError if `serial` does not match the serial number
        of the most recent revision of the object.

        Raises VersionLockError if `oid` is locked in a version other
        than `version`.

        Raises StorageTransactionError when `txn` is not the current
        transaction.

        XXX Should the funny return serial number from conflict resolution
        be documented.

        XXX ZEO client storage has a really gross extension to this
        protocol that complicates the return value.  Maybe we can fix that.
        """

    def restore(oid, serial, data, refs, version, prev_txn, txn):
        """Store an object with performing consistency checks.

        The arguments are the same as store() except for prev_txn.
        If prev_txn is not None, then prev_txn is the XXX ...?
        """

    def newObjectId():
        pass

    def registerDB(db):
        pass

    def isReadOnly():
        pass

    def getExtensionMethods():
        pass

    def copyTransactionsFrom(other, verbose=False):
        pass

    def lastObjectId():
        """Return the last assigned object id.

        Unlike newObjectId() this works even if the storage was opened in
        read-only mode.
        """

    def lastTransaction():
        """Return transaction id for last committed transaction.

        If no transactions have yet been committed, return ZERO.
        """

    def lastSerial(oid):
        """Return last serialno committed for object oid.

        If there is no serialno for this oid -- which can only occur
        if it is a new object -- return None.
        """

    def pack(t, gc=True):
        """Perform a pack on the storage.

        There are two forms of packing: incremental and full gc.  In an
        incremental pack, only old object revisions are removed.  In a full gc
        pack, cyclic garbage detection and removal is also performed.

        t is the pack time.  All non-current object revisions older than
        or the same age as t will be removed in an incremental pack.

        pack() always performs an incremental pack.  If the gc flag is True,
        then pack() will also perform a garbage collection.  Some storages
        (e.g. FileStorage) always do both phases in a pack() call.  Such
        storages should simply ignore the gc flag.
        """

    # two-phase commit

    def tpcBegin(txn):
        pass

    def tpcVote(txn):
        pass

    def tpcFinish(txn):
        pass

    def tpcAbort(txn):
        pass

class IUndoStorage(Interface):

    def loadSerial(oid, serial):
        """Return data record for revision `serial` of `oid.`

        Raises POSKeyError if the revisions is not available.
        """

    def undo(txnid, txn):
        pass

    def undoInfo(first=0, last=-20, specification=None):
        pass

    def undoLog(first, last, filter=None):
        """deprecated, using undoInfo instead"""

    def iterator(start=None, stop=None):
        pass

class IVersionStorage(Interface):
    # XXX should be renamed
    def abortVersion(version):
        pass

    def commitVersion(version):
        pass

    def modifiedInVersion(oid):
        pass

    def versionEmpty(version):
        pass

    def versions():
        pass

class IStorageIterator(Interface):

    def close():
        """Close the iterator and free any external resources."""

    def next():
        """Return the next transaction record iterator.

        Raises IndexError if there are no more.
        """

class ITransactionRecordIterator(Interface):

    tid = Attribute("tid", "transaction id, a string")
    status = Attribute("status", "transaction status, a character")
    user = Attribute("user", "username, if set")
    description = Attribute("description", "description of the transaction")

    # XXX what about this one?
    _extension = Attribute("_extension", "the pickled extensions dictionary")

    def next():
        """Return the next data record.

        Raises IndexError if there are no more.
        """

class IDataRecord(Interface):

    oid = Attribute("oid", "object id")
    serial = Attribute("serial", "revision serial number")
    version = Attribute("version", "version string")
    data = Attribute("data", "data record")
    refs = Attribute("refs",
                     """list of object ids referred to by this object""")
    data_txn = Attribute("data_txn",
                         """id of previous transaction or None

                         If previous transaction is not None, then it
                         is the id of the transaction that originally
                         wrote the data.  The current transaction contains
                         a logical copy of that data.
                         """)

class StorageError(POSError):
    """Base class for storage based exceptions."""

class StorageVersionError(StorageError):
    """The storage version doesn't match the database version."""

    def __init__(self, db_ver, storage_ver):
        self.db_ver = db_ver
        self.storage_ver = storage_ver

    def __str__(self):
        db = ".".join(self.db_ver)
        storage = ".".join(self.storage_ver)
        return ("Storage version %s passed to database version %s"
                % (storage, db))

class StorageTransactionError(StorageError):
    """An operation was invoked for an invalid transaction or state."""

class StorageSystemError(StorageError):
    """Panic! Internal storage error!"""

class MountedStorageError(StorageError):
    """Unable to access mounted storage."""

class ReadOnlyError(StorageError):
    """Unable to modify objects in a read-only storage."""

class TransactionTooLargeError(StorageTransactionError):
    """The transaction exhausted some finite storage resource."""
