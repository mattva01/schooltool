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
"""Database objects

$Id: db.py,v 1.19 2003/06/20 20:46:09 jeremy Exp $
"""

__metaclass__ = type

import sys
from threading import Lock
from time import time
import logging

from zope.interface import implements

from zodb.storage.interfaces import *
from zodb.connection import Connection
from zodb.serialize import getDBRoot
from zodb.ztransaction import Transaction
from zodb.interfaces import ZERO
from zodb.utils import Set

from transaction import get_transaction
from transaction.interfaces import IDataManager

class DB:
    """The Object Database

    The Object database coordinates access to and interaction of one
    or more connections, which manage object spaces.  Most of the actual work
    of managing objects is done by the connections.
    """

    # the database version number, a 4-byte string
    version = "DB01"

    def __init__(self, storage, pool_size=7, cache_size=400):
        """Create an object database.

        The storage for the object database must be passed in.
        Optional arguments are:

        pool_size -- The size of the pool of object spaces.
        """

        self.log = logging.getLogger("zodb")

        # The lock protects access to the pool data structures.
        # Store the lock acquire and release methods as methods
        # of the instance.
        l = Lock()
        self._a = l.acquire
        self._r = l.release

        # Setup connection pools and cache info
        # _pool is currently available (closed) connections
        # _allocated is all connections, open and closed
        # _temps is temporary connections
        self._pool = []
        self._allocated = []
        self._temps = []
        self._pool_lock = Lock()
        self._pool_lock.acquire()
        self._pool_size = pool_size

        self._cache_size = cache_size

        # Setup storage
        self._storage = storage
        self._checkVersion()
        storage.registerDB(self)
        try:
            storage.load(ZERO, "")
        except KeyError:
            # Create the database's root in the storage if it doesn't exist
            t = Transaction(description="initial database creation")
            storage.tpcBegin(t)
            # Because this is the initial root object, we know it can't have
            # any references, so include a longer comment then it would take
            # to unpack getDBRoot()'s return value.
            storage.store(ZERO, None, getDBRoot()[0], [], '', t)
            storage.tpcVote(t)
            storage.tpcFinish(t)

        # Pass through methods:
        if IUndoStorage.isImplementedBy(storage):
            self.undoInfo = storage.undoInfo
        if IVersionStorage.isImplementedBy(storage):
            for m in ['versionEmpty', 'versions', 'modifiedInVersion',
                      'versionEmpty']:
                setattr(self, m, getattr(storage, m))

    def _checkVersion(self):
        # Make sure the database version that created the storage is
        # compatible with this version of the database.  If the storage
        # doesn't have a database version, it's brand-new so set it.
        ver = self._storage.getVersion()
        if ver is None:
            self._storage.setVersion(self.version)
        elif ver != self.version:
            raise StorageVersionError(self.version, ver)

    def _closeConnection(self, connection):
        """Return a connection to the pool"""
        self._a()
        try:
            self._pool.append(connection)
            if len(self._pool) == 1:
                # Pool now usable again, unlock it.
                self._pool_lock.release()
        finally:
            self._r()

    def _connectionMap(self, f):
        self._a()
        try:
            map(f, self._allocated)

            # XXX I don't understand what this code is trying to do
            if self._temps:
                for cc in self._temps:
                    if sys.getrefcount(cc) > 3:
                        f(cc)
                self._temps = []
        finally:
            self._r()

    def abortVersion(self, version):
        AbortVersion(self, version)

    def close(self):
        # XXX Jim observes that database close typically occurs when
        # the app server is shutting down.  If an errant thread is
        # still running, it may not be possible to stop it.  Thus,
        # the error on connection.close() may be counter-productive.
        for c in self._allocated:
            c.close()
        del self._allocated[:]
        del self._pool[:]
        self._storage.close()

    def commitVersion(self, source, destination=''):
        CommitVersion(self, source, destination)

    def getCacheSize(self):
        return self._cache_size

    def getName(self):
        return self._storage.getName()

    def getPoolSize(self):
        return self._pool_size

    def invalidate(self, oids, connection=None, version=''):
        """Invalidate references to a given oid.

        This is used to indicate that one of the connections has committed a
        change to the object.  The connection commiting the change should be
        passed in to prevent useless (but harmless) messages to the
        connection.
        """
        if connection is not None:
            assert version == connection._version
            version = connection._version

        self.log.debug("invalidate %s" % oids)

        # Notify connections
        for cc in self._allocated:
            if cc is not connection:
                self.invalidateConnection(cc, oids, version)

        if self._temps:
            # t accumulates all the connections that aren't closed.
            t = []
            for cc in self._temps:
                if cc is not connection:
                    self.invalidateConnection(cc, oids, version,
                                              t.append)
            self._temps = t

    def invalidateConnection(self, conn, oids, version, alive=None):
        """Send invalidation message to conn for oid on version.

        If the modification occurred on a version, an invalidation is
        sent only if the version of the mod matches the version of the
        connection.

        This function also handles garbage collection of connection's
        that aren't used anymore.  If the optional argument alive is
        defined, it is a function that is called for all connections
        that aren't garbage collected.
        """

        # XXX use weakrefs instead of refcounts?
        if sys.getrefcount(conn) <= 3:
            conn.close()
        else:
            if alive is not None:
                alive(conn)
        if not version or conn.getVersion() == version:
            conn.invalidate(oids)

    def open(self, version='', transaction=None, temporary=0, force=None,
             waitflag=1):
        """Return a object space (AKA connection) to work in

        The optional version argument can be used to specify that a
        version connection is desired.

        The optional transaction argument can be provided to cause the
        connection to be automatically closed when a transaction is
        terminated.  In addition, connections per transaction are
        reused, if possible.

        Note that the connection pool is managed as a stack, to increate the
        likelihood that the connection's stack will include useful objects.
        """
        self._a()
        try:

            if transaction is not None:
                connections=transaction._connections
                if connections:
                    v = connections.get(version)
                    if not (v is None or temporary):
                        return v
                else:
                    transaction._connections = connections = {}
                transaction = transaction._connections

            if temporary:
                # This is a temporary connection.
                # We won't bother with the pools.  This will be
                # a one-use connection.
                c = Connection(self, self._storage, version,
                               cache_size=self._cache_size)
                self._temps.append(c)
                if transaction is not None:
                    transaction[id(c)] = c
                return c

            # Pool locks are tricky.  Basically, the lock needs to be
            # set whenever the pool becomes empty so that threads are
            # forced to wait until the pool gets a connection in it.
            # The lock is acquired when the (empty) pool is
            # created. The The lock is acquired just prior to removing
            # the last connection from the pool and just after adding
            # a connection to an empty pool.

            if not self._pool:
                if self._pool_size > len(self._allocated) or force:
                    # If the number allocated is less than the pool
                    # size, then we've never reached the limit.
                    # Allocate a connection and return without
                    # touching the lock.
                    c = Connection(self, self._storage, version,
                                   cache_size=self._cache_size)
                    self._allocated.append(c)
                    return c
                else:
                    # If the number allocated is larger than the pool
                    # size, then we have to wait for another thread to
                    # close its connection.
                    if waitflag:
                        self.log.debug("waiting for pool lock")
                        self._r()
                        self._pool_lock.acquire()
                        self._a()
                        self.log.debug("acquired pool lock")
                        if len(self._pool) > 1:
                            # Note that the pool size will normally be 1 here,
                            # but it could be higher due to a race condition.
                            self._pool_lock.release()
                    else:
                        self.log.debug("open failed because pool is empty")
                        return
            elif len(self._pool) == 1:
                # Taking last one, lock the pool

                # Note that another thread might grab the lock before
                # us, so we might actually block, however, when we get
                # the lock back, there *will* be a connection in the
                # pool.

                self._r()
                self._pool_lock.acquire()
                self._a()
                if len(self._pool) > 1:
                    # Note that the pool size will normally be 1 here,
                    # but it could be higher due to a race condition.
                    self._pool_lock.release()

            # XXX Could look for a connection with the right version
            c = self._pool.pop()
            c.reset(version)
            for other_conn in self._pool:
                other_conn.cacheGC()

            if transaction is not None:
                transaction[version] = c
            return c

        finally: self._r()

    def pack(self, t=None, days=0):
        if t is None:
            t = time()
        t -= days * 86400
        try:
            self._storage.pack(t)
        except:
            self.log.exception("packing")
            raise

    def setCacheSize(self, v):
        self._cache_size = v
        for c in self._pool:
            c._cache.cache_size = v

    def setPoolSize(self, v):
        self._pool_size = v

    def undo(self, id):
        TransactionalUndo(self, id)

class SimpleDataManager:

    implements(IDataManager)

    def __init__(self, db):
        self._db = db
        self._storage = db._storage
        get_transaction().join(self)

    def prepare(self, txn):
        self._storage.tpcBegin(txn)
        try:
            self._prepare(txn)
            self._storage.tpcVote(txn)
        except StorageError, err:
            logging.getLogger("zodb").info("Error during prepare: %s", err)
            return False
        else:
            return True

    def abort(self, txn):
        self._storage.tpcAbort(txn)

    def commit(self, txn):
        self._storage.tpcFinish(txn)

    def _prepare(self, txn):
        # Hook for clients to perform action during 2PC
        pass

class CommitVersion(SimpleDataManager):
    """An object that will see to version commit."""

    def __init__(self, db, version, dest=''):
        super(CommitVersion, self).__init__(db)
        self._version = version
        self._dest = dest

    def _prepare(self, txn):
        self._oids = Set(self._storage.commitVersion(self._version, self._dest,
                                                     txn))

    def commit(self, txn):
        super(CommitVersion, self).commit(txn)
        self._db.invalidate(self._oids, version=self._dest)
        if self._dest:
            # the code above just invalidated the dest version.
            # now we need to invalidate the source!
            self._db.invalidate(self._oids, version=self._version)

class AbortVersion(SimpleDataManager):
    """An object that will see to version abortion."""

    def __init__(self, db, version):
        super(AbortVersion, self).__init__(db)
        self._version = version

    def _prepare(self, txn):
        self._oids = Set(self._storage.abortVersion(self._version, txn))

    def commit(self, txn):
        super(AbortVersion, self).commit(txn)
        self._db.invalidate(self._oids, version=self._version)

class TransactionalUndo(SimpleDataManager):
    """An object that will see to transactional undo."""

    def __init__(self, db, tid):
        super(TransactionalUndo, self).__init__(db)
        self._tid = tid

    def _prepare(self, txn):
        self._oids = Set(self._storage.undo(self._tid, txn))

    def commit(self, txn):
        super(TransactionalUndo, self).commit(txn)
        self._db.invalidate(self._oids)
