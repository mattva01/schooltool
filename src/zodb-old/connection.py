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
"""Database connection support

The Connection object serves as a data manager.  ZODB is organized so
that each thread should have its own Connection.  A thread acquires a
Connection by calling the open() method on a database object.

A Connection can be associated with a single version when it is
created.  By default, a Connection is not associated with a version.
It uses non-version data.

The root() method on a Connection returns the root object for the
database.  This object and all objects reachable from it are
associated with the Connection that loaded them.  When the objects are
modified, the Connection is registered with the current transaction.

Synchronization

A Connection instance is not thread-safe.  It is designed to support a
thread model where each thread has its own transaction.  If an
application has more than one thread that uses the connection or the
transaction the connection is registered with, the application should
provide locking.

$Id: connection.py,v 1.39 2003/10/15 12:00:19 mgedmin Exp $
"""

import logging
import struct
import tempfile
import threading
from types import StringType

from zope.interface import implements

from zodb import interfaces
from zodb.conflict import ResolvedSerial
from zodb.export import ExportImport
from zodb.interfaces import *
from zodb.interfaces import _fmt_oid
from zodb.serialize import ConnectionObjectReader, ObjectWriter
from zodb.storage.base import splitrefs
from zodb.utils import u64, Set

from transaction import get_transaction
from transaction.interfaces import IDataManager, IRollback, TransactionError
from persistence.cache import Cache
from persistence.interfaces import IPersistentDataManager


class RegisteredMapping(dict):
    """Mapping used for Connection._registered.

    This mapping must support additions and clears during iteration over
    values.
    """

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self._added_keys = []

    def __setitem__(self, key, value):
        if key not in self:
             self._added_keys.append(key)
        dict.__setitem__(self, key, value)

    def setdefault(self, key, value=None):
        if key not in self:
             self._added_keys.append(key)
        dict.setdefault(self, key, value)

    def update(self, other):
        self._added_keys.extend([key for key in other if key not in self])
        dict.update(self, other)

    def iterAddedKeys(self):
        return iter(self._added_keys)

    def clearAddedKeys(self):
        del self._added_keys[:]


class Connection(ExportImport, object):
    """Object managers for individual object space.

    An object space is a version of collection of objects.  In a
    multi-threaded application, each thread gets its own object
    space.

    The Connection manages movement of objects in and out of object
    storage.
    """

    implements(IAppConnection, IConnection, IPersistentDataManager,
               IDataManager)

    def __init__(self, db, storage, version='', cache_size=400):
        self._db = db
        self._storage = storage
        self._version = version
        self._cache = Cache(cache_size)
        self._reader = ConnectionObjectReader(self, self._cache)
        self._log = logging.getLogger("zodb")
        # a TmpStore object used by sub-transactions
        self._tmp = None
        # whether the connection is open or closed
        self._open = True
        # the connection's current txn
        self._txn = None

        # _invalidated queues invalidate messages delivered from the DB
        # _inv_lock prevents one thread from modifying the set while
        # another is processing invalidations.  All the invalidations
        # from a single transaction should be applied atomically, so
        # the lock must be held when reading _invalidated.

        # XXX It sucks that we have to hold the lock to read
        # _invalidated.  Normally, _invalidated is written by call
        # dict.update, which will execute atomically by virtue of the
        # GIL.  But some storage might generate oids where hash or
        # compare invokes Python code.  In that case, the GIL can't
        # save us.
        self._inv_lock = threading.Lock()
        self._invalidated = Set()
        self._committed = []

        # Bookkeeping for objects affected by the current transaction.
        # These sets are clear()ed at transaction boundaries.

        # XXX Is a Set safe?  What if the objects are not hashable?
        self._registered = RegisteredMapping()
        self._modified = Set() # XXX is this the same as registered?
        self._created = Set()
        # _conflicts: set of objects that failed to load because
        # of read conflicts.  We must track these explicitly
        # because they occur outside the two-phase commit and
        # we must not allow the transaction they occur in to commit.
        self._conflicts = Set()

        # new_oid is used by serialize
        self.newObjectId = self._storage.newObjectId

    def _get_transaction(self):
        # Return the transaction currently active.
        # If no transaction is active, call get_transaction().
        if self._txn is None:
            self._txn = get_transaction()
        return self._txn

    ######################################################################
    # IAppConnection defines the next three methods
    # root(), sync(), get()

    def root(self):
        return self.get(ZERO)

    def sync(self):
        if self._txn:
            self._txn.abort()
        sync = getattr(self._storage, 'sync', None)
        if sync is not None:
            sync()
        self._flush_invalidations()

    def get(self, oid):
        # assume that a cache cannot store None as a valid object
        object = self._cache.get(oid)
        if object is not None:
            return object

        p, serial = self._storage.load(oid, self._version)
        obj = self._reader.getGhost(p)

        obj._p_oid = oid
        obj._p_jar = self
        # When an object is created, it is put in the UPTODATE state.
        # We must explicitly deactivate it to turn it into a ghost.
        obj._p_deactivate()
        obj._p_serial = serial

        self._cache.set(oid, obj)
        if oid == ZERO:
            # Keep a reference to the root so that the pickle cache
            # won't evict it.  XXX Not sure if this is necessary.  If
            # the cache is LRU, it should know best if the root is needed.
            self._root = obj
        return obj

    ######################################################################
    # IPersistentDataManager requires the next three methods:
    # setstate(), register(), mtime()

    def setstate(self, obj):
        oid = obj._p_oid

        if not self._open:
            msg = "Attempt to load object on closed connection: %r" % oid
            self._log.warn(msg)
            raise POSError(msg)

        try:
            # Avoid reading data from a transaction that committed
            # after the current transaction started, as that might
            # lead to mixing of cached data from earlier transactions
            # and new inconsistent data.
            #
            # Wait for check until after data is loaded from storage
            # to avoid time-of-check to time-of-use race.
            p, serial = self._storage.load(oid, self._version)
            invalid = self._is_invalidated(obj)
            self._reader.setGhostState(obj, p)
            obj._p_serial = serial
            if invalid:
                self._handle_independent(obj)
        except ConflictError:
            raise
        except:
            self._log.exception("Couldn't load state for %r", oid)
            raise
        else:
            # Add the object to the cache active list
            self._cache.activate(oid)

    def _is_invalidated(self, obj):
        # Helper method for setstate() covers three cases:
        # returns false if obj is valid
        # returns true if obj was invalidation, but is independent
        # otherwise, raises ConflictError for invalidated objects
        self._inv_lock.acquire()
        try:
            if obj._p_oid in self._invalidated:
                ind = getattr(obj, "_p_independent", None)
                if ind is not None:
                    # Defer _p_independent() call until state is loaded.
                    return True
                else:
                    self._get_transaction().join(self)
                    self._conflicts.add(obj._p_oid)
                    raise ReadConflictError(object=obj)
            else:
                return False
        finally:
            self._inv_lock.release()

    def _handle_independent(self, obj):
        # Helper method for setstate() handles possibly independent objects
        # Call _p_independent(), if it returns True, setstate() wins.
        # Otherwise, raise a ConflictError.

        if obj._p_independent():
            self._inv_lock.acquire()
            try:
                try:
                    self._invalidated.remove(obj._p_oid)
                except KeyError:
                    pass
            finally:
                self._inv_lock.release()
        else:
            self._get_transaction().join(self)
            raise ReadConflictError(object=obj)

    def register(self, obj):
        assert obj._p_jar is self and obj._p_oid is not None
        self._log.debug("register oid=%s" % _fmt_oid(obj._p_oid))
        if not self._registered:
            self._get_transaction().join(self)
        self._registered[obj._p_oid] = obj

    def mtime(self, obj):
        # required by the IPersistentDataManager interface, but unimplemented
        return None

    ######################################################################
    # IConnection requires the next six methods:
    # getVersion(), reset(), cacheGC(), invalidate(), close(), add()

    def getVersion(self):
        return self._version

    def reset(self, version=""):
        self._log.debug("connection reset")
        if version != self._version:
            # XXX I think it's necessary to clear the cache here, because
            # the objects in the cache don't know that they were in a
            # version.
            self._cache.clear()
            self._version = version
        self._inv_lock.acquire()
        try:
            self._cache.invalidate(self._invalidated)
            self._invalidated.clear()
        finally:
            self._inv_lock.release()
        self._open = True

    def cacheGC(self):
        self._cache.shrink()

    def invalidate(self, oids):
        self._inv_lock.acquire()
        try:
            self._invalidated.update(oids)
        finally:
            self._inv_lock.release()

    def close(self):
        if self._txn is not None:
            msg = "connection closed while transaction active"
            self._log.warn(msg)
            raise TransactionError(msg)
        self._log.debug("connection closed")
        self._open = False
        self._cache.shrink()
        # Return the connection to the pool.
        self._db._closeConnection(self)

    def add(self, obj):
        marker = object()
        oid = getattr(obj, "_p_oid", marker)
        if oid is marker:
            raise TypeError("cannot add a non-persistent object %r "
                            "to a connection" % (obj, ))
        if obj._p_jar is not None and obj._p_jar is not self:
            raise InvalidObjectReference(obj, obj._p_jar)
        if obj._p_jar is None:
            # Setting _p_changed has a side-effect of adding obj to
            # _p_jar._registered, so it must be set after _p_jar.
            obj._p_oid = self.newObjectId()
            obj._p_jar = self
            obj._p_changed = True
            self._created.add(obj._p_oid)

            # There is an 'invariant' that objects in the cache can be
            # made into ghosts because they have _p_jar and _p_oid.
            # We are breaking this invariant, but that's OK because
            # it's not used anywhere.  The right solution is to have a
            # separate cache of objects outside that invariant.
            self._cache.set(obj._p_oid, obj)


    ######################################################################
    # transaction.interfaces.IDataManager requires the next four methods
    # prepare(), abort(), commit(), savepoint()

    def prepare(self, txn):
        if self._conflicts:
            # XXX should raise all of the conflicting oids, but
            # haven't gotten around to changing the exception
            # to store them.
            oid = list(self._conflicts)[0]
            raise ReadConflictError(oid)
        self._modified.clear()
        self._created.clear()
        if self._tmp is not None:
            # commit_sub() will call tpc_begin() on the real storage
            self._commit_sub(txn)
        else:
            self._storage.tpcBegin(txn)

        self._registered.clearAddedKeys()
        for obj in self._registered.values():
            self._objcommit(obj, txn)
        for oid in self._registered.iterAddedKeys():
            # _registered can have new items added to it during _objcommit,
            # but it cannot have any existing ones removed
            obj = self._registered[oid]
            self._objcommit(obj, txn)

        s = self._storage.tpcVote(txn)
        self._handle_serial(s)
        return True

    def abort(self, txn):
        if self._tmp is not None:
            self._abort_sub()
        self._storage.tpcAbort(txn)

        if self._registered:
            self._cache.invalidate(list(self._registered))
            self._registered.clear()
        self._invalidate_created(self._created)
        self._cache.invalidate(self._modified)
        self._txn = None
        self._flush_invalidations()
        self._created.clear()
        self._modified.clear()
        self._conflicts.clear()

    def commit(self, txn):
        # It's important that the storage call the function we pass
        # (self._invalidate_modified) while it still has its lock.
        # We don't want another thread to be able to read any
        # updated data until we've had a chance to send an
        # invalidation message to all of the other connections!

        # If another thread could read the newly committed data
        # before the invalidation is delivered, the connection would
        # not be able to detect a read conflict.
        self._storage.tpcFinish(txn, self._invalidate_modified)
        self._txn = None
        self._conflicts.clear()
        self._flush_invalidations()
        self._registered.clear()
        self._created.clear()
        self._modified.clear()

    def savepoint(self, txn):
        if self._tmp is None:
            tmp = TmpStore(self._db, self._storage, self._version)
            self._tmp = self._storage
            self._storage = tmp
        self._modified = Set()
        self._created = Set()
        self._storage.tpcBegin(txn)

        self._registered.clearAddedKeys()
        for obj in self._registered.values():
            self._objcommit(obj, txn)
        for oid in self._registered.iterAddedKeys():
            # _registered can have new items added to it during _objcommit,
            # but it cannot have any existing ones removed
            obj = self._registered[oid]
            self._objcommit(obj, txn)
        self.importHook(txn) # hook for ExportImport

        # The tpcFinish() of TmpStore returns an UndoInfo object.
        undo = self._storage.tpcFinish(txn)
        self._cache.shrink()
        self._storage._created = self._created
        self._created = Set()
        return Rollback(self, undo)

    def _invalidate_created(self, created):
        # Dis-own new objects from uncommitted transaction.
        for oid in created:
            o = self._cache.get(oid)
            if o is not None:
                del o._p_jar
                del o._p_oid
                self._cache.remove(oid)

    def _invalidate_modified(self):
        self._db.invalidate(self._modified, self, self._version)

    def _flush_invalidations(self):
        self._inv_lock.acquire()
        try:
            self._cache.invalidate(self._invalidated)
            self._invalidated.clear()
        finally:
            self._inv_lock.release()
        # Now is a good time to collect some garbage
        self._cache.shrink()

    def _handle_serial(self, store_return, oid=None, change=1):
        """Handle the returns from store() and tpc_vote() calls."""

        # These calls can return different types depending on whether
        # ZEO is used.  ZEO uses asynchronous returns that may be
        # returned in batches by the ClientStorage.  ZEO1 can also
        # return an exception object and expect that the Connection
        # will raise the exception.

        # When commit_sub() exceutes a store, there is no need to
        # update the _p_changed flag, because the subtransaction
        # tpc_vote() calls already did this.  The change=1 argument
        # exists to allow commit_sub() to avoid setting the flag
        # again.

        # When conflict resolution occurs, the object state held by
        # the connection does not match what is written to the
        # database.  Invalidate the object here to guarantee that
        # the new state is read the next time the object is used.
        
        if not store_return:
            return
        if isinstance(store_return, StringType):
            assert oid is not None
            self._handle_one_serial(oid, store_return, change)
        else:
            for oid, serial in store_return:
                self._handle_one_serial(oid, serial, change)

    def _handle_one_serial(self, oid, serial, change=1):
        if not isinstance(serial, StringType):
            raise serial
        obj = self._cache.get(oid, None)
        if obj is None:
            return
        if serial == ResolvedSerial:
            obj._p_deactivate(force=True)
        else:
            if change:
                obj._p_changed = False
            obj._p_serial = serial

    def _objcommit(self, obj, transaction):
        oid = obj._p_oid
        self._log.debug("commit object %s", _fmt_oid(oid))

        if obj._p_changed:
            self._modified.add(oid)
        else:
            # The object reverted to the up-to-date state after
            # registering.
            self._log.info("object not modified %s", _fmt_oid(oid))
            return

        writer = ObjectWriter(self)
        try:
            for o in writer.newObjects(obj):
                self._commit_store(writer, o, transaction)
        finally:
            writer.close()

    def _commit_store(self, writer, obj, transaction):
        oid = obj._p_oid
        serial = getattr(obj, '_p_serial', None)
        if serial is None:
            self._created.add(oid)
        else:
            # Make a quick check against the invalidated set, because
            # pickling is expensive.  Catching a conflict here will
            # be much faster than catching it in the store call.
            self._inv_lock.acquire()
            try:
                if (oid in self._invalidated and
                    getattr(obj, '_p_resolveConflict', None) is None):
                    raise ConflictError(oid=oid)
            finally:
                self._inv_lock.release()
            # XXX persistent classes don't register themselves
            # when they are modified, so we call add again here
            # to be sure they are invalidated.
            self._modified.add(oid)

        data, refs = writer.getState(obj)
        s = self._storage.store(oid, serial, data, refs, self._version,
                                transaction)
        # Put the object in the cache before handling the
        # response, just in case the response contains the
        # serial number for a newly created object
        self._cache.set(oid, obj)
        self._handle_serial(s, oid)

    def _commit_sub(self, txn):
        # Commit all work done in subtransactions.
        assert self._tmp is not None

        tmp = self._storage
        self._storage = self._tmp
        self._tmp = None

        self._storage.tpcBegin(txn)

        # Copy invalidating and creating info from temporary storage:
        self._modified |= Set(tmp._index)
        self._created |= tmp._created

        for oid in tmp._index:
            data, refs, serial = tmp.loadrefs(oid, tmp._bver)
            s = self._storage.store(oid, serial, data, refs,
                                    self._version, txn)
            self._handle_serial(s, oid, change=False)
        tmp.close()

    def _abort_sub(self):
        # Abort work done in subtransactions.
        assert self._tmp is not None

        tmp = self._storage
        self._storage = self._tmp
        self._tmp = None

        self._cache.invalidate(tmp._index)
        self._invalidate_created(tmp._created)
        tmp.close()

class Rollback:
    """Rollback changes associated with savepoint"""

    # In order to rollback changes for a savepoint(), we must remove
    # the logged changes from the TmpStore and invalidate any object
    # that has been changed since the rolledback transaction started.

    # XXX Should it be possible to rollback() to the same savepoint
    # more than once?  (Yes.)

    implements(IRollback)

    def __init__(self, conn, tmp_undo):
        self._conn = conn
        self._tmp_undo = tmp_undo # undo info from the storage

    def rollback(self):
        if not self._tmp_undo.current(self._conn._storage):
            msg = "savepoint has already been committed"
            raise interfaces.RollbackError(msg)
        self._tmp_undo.rollback()
        self._conn._cache.invalidate(self._conn._modified)

class UndoInfo:
    """A helper class for rollback.

    The class stores the state necessary for rolling back to a
    particular time.
    """

    def __init__(self, store, pos, index):
        self._store = store
        self._pos = pos
        self._index = index

    def current(self, cur_store):
        """Return true if the UndoInfo is for cur_store."""
        return self._store is cur_store

    def rollback(self):
        self._store.rollback(self._pos, self._index)


class TmpStore:
    """A storage to support savepoints."""

    _bver = ''

    # The header format is oid, serial, nrefs, len(data).  Following
    # the header are the refs and the data, where the size of refs is
    # nrefs * 8.

    _fmt = ">8s8sQI"
    _header_size = 28

    def __init__(self, db, storage, base_version):
        self._db = db
        self._storage = storage
        self._transaction = None
        if base_version:
            self._bver = base_version
        self._file = tempfile.TemporaryFile()
        # _pos: current file position
        # _tpos: file position at last commit point
        self._pos = self._tpos = 0
        # _index: map oid to pos of last committed version
        self._index = {}
        # _tindex: map oid to pos for new updates
        self._tindex = {}
        self._created = Set()
        self._db = None

    def close(self):
        self._file.close()

    def load(self, oid, version):
        # XXX I don't think the version handling is correct here.
        pos = self._index.get(oid, None)
        if pos is None:
            return self._storage.load(oid, self._bver)
        data, refs, serial = self.loadrefs(oid, version)
        return data, serial

    def loadrefs(self, oid, version):
        # A version of load the returns data, refs, and serial.
        pos = self._index.get(oid)
        # We only call loadrefs() for objects in the TmpStore.
        assert pos is not None
        self._file.seek(pos)
        buf = self._file.read(self._header_size)
        oid, serial, nrefs, size = struct.unpack(self._fmt, buf)
        refs = self._file.read(nrefs * 8)
        data = self._file.read(size)
        return data, splitrefs(refs), serial

    def newObjectId(self):
        return self._storage.newObjectId()

    def store(self, oid, serial, data, refs, version, transaction):
        if transaction is not self._transaction:
            raise interfaces.StorageTransactionError(self, transaction)
        self._file.seek(self._pos)
        if serial is None:
            serial = ZERO
        buf = struct.pack(self._fmt, oid, serial, len(refs), len(data))
        self._file.write(buf)
        self._file.write("".join(refs))
        self._file.write(data)
        self._tindex[oid] = self._pos
        self._pos += len(refs) * 8 + len(data) + self._header_size
        return serial

    def tpcAbort(self, transaction):
        if transaction is not self._transaction:
            return
        self._tindex.clear()
        self._transaction = None
        self._pos = self._tpos

    def tpcBegin(self, transaction):
        if self._transaction is transaction:
            return
        self._transaction = transaction
        self._tindex.clear() # Just to be sure!
        self._pos = self._tpos

    def tpcVote(self, transaction):
        pass

    def tpcFinish(self, transaction, f=None):
        if transaction is not self._transaction:
            return
        if f is not None:
            f()
        undo = UndoInfo(self, self._tpos, self._index.copy())
        self._index.update(self._tindex)
        self._tindex.clear()
        self._tpos = self._pos
        return undo

    def undoLog(self, first, last, filter=None):
        return ()

    def versionEmpty(self, version):
        # XXX what is this supposed to do?
        if version == self._bver:
            return len(self._index)

    def rollback(self, pos, index):
        if not (pos <= self._tpos <= self._pos):
            msg = "transaction rolled back to early point"
            raise interfaces.RollbackError(msg)
        self._tpos = self._pos = pos
        self._index = index
        self._tindex.clear()
