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
"""The StorageServer class and the exception that it may raise.

This server acts as a front-end for one or more real storages, like
file storage or Berkeley storage.

XXX Need some basic access control-- a declaration of the methods
exported for invocation by the server.
"""

from __future__ import nested_scopes

import asyncore
import cPickle
import logging
import os
import sys
import threading
import time

from zodb.zeo.stubs import ClientStorageStub
from zodb.zeo.commitlog import CommitLog
from zodb.zeo.monitor import StorageStats, StatsServer
from zodb.zeo.zrpc.server import Dispatcher
from zodb.zeo.zrpc.connection import ManagedServerConnection, Delay, MTDelay
from zodb.zeo.zrpc.trigger import trigger

from zodb.serialize import findrefs
from zodb.interfaces import *
from zodb.storage.interfaces import *
from zodb.conflict import ResolvedSerial
from zodb.utils import u64
from zodb.ztransaction import Transaction

from zope.interface import providedBy

from transaction.interfaces import TransactionError

class StorageServerError(StorageError):
    """Error reported when an unpickleable exception is raised."""

class ZEOStorage:
    """Proxy to underlying storage for a single remote client."""

    # Classes we instantiate.  A subclass might override.

    ClientStorageStubClass = ClientStorageStub

    # A list of extension methods.  A subclass with extra methods
    # should override.
    extensions = []

    def __init__(self, server, read_only=0, auth_realm=None):
        self.server = server
        # timeout and stats will be initialized in register()
        self.timeout = None
        self.stats = None
        self.connection = None
        self.client = None
        self.storage = None
        self.storage_id = "uninitialized"
        self.transaction = None
        self.read_only = read_only
        self.locked = 0
        self.verifying = 0
        self.logger = logging.getLogger("ZSS.%d.ZEO" % os.getpid())
        self.log_label = ""
        self.authenticated = 0
        self.auth_realm = auth_realm
        # The authentication protocol may define extra methods.
        self._extensions = {}
        for func in self.extensions:
            self._extensions[func.func_name] = None

    def finish_auth(self, authenticated):
        if not self.auth_realm:
            return 1
        self.authenticated = authenticated
        return authenticated

    def set_database(self, database):
        self.database = database
        
    def notifyConnected(self, conn):
        self.connection = conn # For restart_other() below
        self.client = self.ClientStorageStubClass(conn)
        addr = conn.addr
        if isinstance(addr, str):
            self.log_label = addr
        else:
            host, port = addr
            self.log_label = str(host) + ":" + str(port)

    def notifyDisconnected(self):
        # When this storage closes, we must ensure that it aborts
        # any pending transaction.
        if self.transaction is not None:
            self.logger.warn("%s: disconnected during transaction %s",
                             self.log_label, self.transaction)
            self._abort()
        else:
            self.logger.warn("%s: disconnected", self.log_label)
        if self.stats is not None:
            self.stats.clients -= 1

    def __repr__(self):
        tid = self.transaction and repr(self.transaction.id)
        if self.storage:
            stid = (self.storage._transaction and
                    repr(self.storage._transaction.id))
        else:
            stid = None
        name = self.__class__.__name__
        return "<%s %X trans=%s s_trans=%s>" % (name, id(self), tid, stid)

    def setup_delegation(self):
        """Delegate several methods to the storage"""
        self.versionEmpty = self.storage.versionEmpty
        self.versions = self.storage.versions
        self.getSerial = self.storage.getSerial
        self.load = self.storage.load
        self.modifiedInVersion = self.storage.modifiedInVersion
        self.getVersion = self.storage.getVersion
        self.setVersion = self.storage.setVersion
        if IUndoStorage.isImplementedBy(self.storage):
            self.loadSerial = self.storage.loadSerial
        try:
            fn = self.storage.getExtensionMethods
        except AttributeError:
            # We must be running with a ZODB which
            # predates adding getExtensionMethods to
            # BaseStorage. Eventually this try/except
            # can be removed
            pass
        else:
            d = fn()
            self._extensions.update(d)
            for name in d.keys():
                assert not hasattr(self, name)
                setattr(self, name, getattr(self.storage, name))
        self.lastTransaction = self.storage.lastTransaction

    def _check_tid(self, tid, exc=None):
        if self.read_only:
            raise ReadOnlyError()
        caller = sys._getframe().f_back.f_code.co_name
        if self.transaction is None:
            self.logger.warn("no current transaction: %s()", caller)
            if exc is not None:
                raise exc(None, tid)
            else:
                return 0
        if self.transaction.id != tid:
            self.logger.warn("%s(%s) invalid; current transaction = %s",
                             caller, repr(tid), repr(self.transaction.id))
            if exc is not None:
                raise exc(self.transaction.id, tid)
            else:
                return 0
        return 1

    def getAuthProtocol(self):
        """Return string specifying name of authentication module to use.

        The module name should be auth_%s where %s is auth_protocol."""
        protocol = self.server.auth_protocol
        if not protocol or protocol == 'none':
            return None
        return protocol
    
    def register(self, storage_id, read_only):
        """Select the storage that this client will use

        This method must be the first one called by the client.
        """
        if self.storage is not None:
            self.logger.warn("duplicate register() call")
            raise ValueError, "duplicate register() call"
        storage = self.server.storages.get(storage_id)
        if storage is None:
            self.logger.warn("unknown storage_id: %s", storage_id)
            raise ValueError, "unknown storage: %s" % storage_id

        if not read_only and (self.read_only or storage.isReadOnly()):
            raise ReadOnlyError()

        self.read_only = self.read_only or read_only
        self.storage_id = storage_id
        self.storage = storage
        self.setup_delegation()
        self.timeout, self.stats = self.server.register_connection(storage_id,
                                                                   self)

    def get_info(self):
        return {"name": self.storage.getName(),
                "extensionMethods": self.getExtensionMethods(),
                 "implements": [iface.__name__
                                for iface in providedBy(self.storage)],
                }

    def getExtensionMethods(self):
        return self._extensions

    def zeoLoad(self, oid):
        self.stats.loads += 1
        v = self.storage.modifiedInVersion(oid)
        if v:
            pv, sv = self.storage.load(oid, v)
        else:
            pv = sv = None
        try:
            p, s = self.storage.load(oid, '')
        except KeyError:
            if sv:
                # Created in version, no non-version data
                p = s = None
            else:
                raise
        return p, s, v, pv, sv

    def getSerial(self, oid):
        return self.storage.getSerial(oid)

    def getInvalidations(self, tid):
        invtid, invlist = self.server.get_invalidations(tid)
        if invtid is None:
            return None
        self.logger.debug("Return %d invalidations up to tid %s",
                          len(invlist), u64(invtid))
        return invtid, invlist

    def zeoVerify(self, oid, s, sv):
        if not self.verifying:
            self.verifying = 1
            self.stats.verifying_clients += 1
        try:
            os = self.storage.getSerial(oid)
        except KeyError:
            self.client.invalidateVerify((oid, ''))
            # XXX It's not clear what we should do now.  The KeyError
            # could be caused by an object uncreation, in which case
            # invalidation is right.  It could be an application bug
            # that left a dangling reference, in which case it's bad.
        else:
            # If the client has version data, the logic is a bit more
            # complicated.  If the current serial number matches the
            # client serial number, then the non-version data must
            # also be valid.  If the current serialno is for a
            # version, then the non-version data can't change.

            # If the version serialno isn't valid, then the
            # non-version serialno may or may not be valid.  Rather
            # than trying to figure it whether it is valid, we just
            # invalidate it.  Sending an invalidation for the
            # non-version data implies invalidating the version data
            # too, since an update to non-version data can only occur
            # after the version is aborted or committed.
            if sv:
                if sv != os:
                    self.client.invalidateVerify((oid, ''))
            else:
                if s != os:
                    self.client.invalidateVerify((oid, ''))

    def endZeoVerify(self):
        if self.verifying:
            self.stats.verifying_clients -= 1
        self.verifying = 0
        self.client.endVerify()

    def pack(self, time, wait=1):
        # Yes, you can pack a read-only server or storage!
        if wait:
            return run_in_thread(self._pack_impl, time)
        else:
            # If the client isn't waiting for a reply, start a thread
            # and forget about it.
            t = threading.Thread(target=self._pack_impl, args=(time,))
            t.start()
            return None

    def _pack_impl(self, time):
        self.logger.warn("%s: pack(time=%r) started...", self.log_label, time)
        self.storage.pack(time)
        self.logger.warn("%s: pack(time=%r) complete", self.log_label, time)

    def newObjectIds(self, n=100):
        """Return a sequence of n new oids, where n defaults to 100"""
        if self.read_only:
            raise ReadOnlyError()
        if n <= 0:
            n = 1
        return [self.storage.newObjectId() for i in range(n)]

    def undo(self, transaction_id):
        if self.read_only:
            raise ReadOnlyError()
        oids = self.storage.undo(transaction_id)
        if oids:
            self.server.invalidate(self, self.storage_id, None,
                                   map(lambda oid: (oid, ''), oids))
            return oids
        return ()

    # undoLog and undoInfo are potentially slow methods

    def undoInfo(self, first, last, spec):
        return run_in_thread(self.storage.undoInfo, first, last, spec)

    def undoLog(self, first, last):
        return run_in_thread(self.storage.undoLog, first, last)

    def tpcBegin(self, id, user, description, ext, tid, status):
        if self.read_only:
            raise ReadOnlyError()
        if self.transaction is not None:
            if self.transaction.id == id:
                self.logger.warn("duplicate tpcBegin(%r)", id)
                return
            else:
                raise StorageTransactionError("Multiple simultaneous tpc_begin"
                                              " requests from one client.")

        self.transaction = t = Transaction()
        t.id = id
        t.user = user
        t.description = description
        t._extension = ext

        self.serials = []
        self.invalidated = []
        self.txnlog = CommitLog()
        self.tid = tid
        self.status = status
        self.stats.active_txns += 1

    def tpcFinish(self, id):
        if not self._check_tid(id):
            return
        assert self.locked
        self.stats.active_txns -= 1
        self.stats.commits += 1
        self.storage.tpcFinish(self.transaction)
        tid = self.storage.lastTransaction()
        if self.invalidated:
            self.server.invalidate(self, self.storage_id, tid,
                                   self.invalidated)
        self._clear_transaction()
        # Return the tid, for cache invalidation optimization
        return tid

    def tpcAbort(self, id):
        if not self._check_tid(id):
            return
        self.stats.active_txns -= 1
        self.stats.aborts += 1
        if self.locked:
            self.storage.tpcAbort(self.transaction)
        self._clear_transaction()

    def _clear_transaction(self):
        # Common code at end of tpcFinish() and tpcAbort()
        self.transaction = None
        if self.locked:
            self.locked = 0
            self.timeout.end(self)
            self.stats.lock_time = None
        # _handle_waiting() can start another transaction (by
        # restarting a waiting one) so must be done last
        self._handle_waiting()

    def _abort(self):
        # called when a connection is closed unexpectedly
        if not self.locked:
            # Delete (d, zeo_storage) from the _waiting list, if found.
            waiting = self.storage._waiting
            for i in range(len(waiting)):
                d, z = waiting[i]
                if z is self:
                    del waiting[i]
                    self.logger.warn("Closed connection removed from waiting "
                                     "list. Clients waiting: %d.",
                                     len(waiting))
                    break

        if self.transaction:
            self.stats.active_txns -= 1
            self.stats.aborts += 1
            self.tpcAbort(self.transaction.id)

    # The public methods of the ZEO client API do not do the real work.
    # They defer work until after the storage lock has been acquired.
    # Most of the real implementations are in methods beginning with
    # an _.

    def storea(self, oid, serial, data, refs, version, id):
        self._check_tid(id, exc=StorageTransactionError)
        self.stats.stores += 1
        self.txnlog.store(oid, serial, data, refs, version)

    # The following four methods return values, so they must acquire
    # the storage lock and begin the transaction before returning.

    def tpcVote(self, id):
        self._check_tid(id, exc=StorageTransactionError)
        if self.locked:
            return self._tpcVote()
        else:
            return self._wait(lambda: self._tpcVote())

    def abortVersion(self, src, id):
        self._check_tid(id, exc=StorageTransactionError)
        if self.locked:
            return self._abortVersion(src)
        else:
            return self._wait(lambda: self._abortVersion(src))

    def commitVersion(self, src, dest, id):
        self._check_tid(id, exc=StorageTransactionError)
        if self.locked:
            return self._commitVersion(src, dest)
        else:
            return self._wait(lambda: self._commitVersion(src, dest))

    def undo(self, trans_id, id):
        self._check_tid(id, exc=StorageTransactionError)
        if self.locked:
            return self._transactionalUndo(trans_id)
        else:
            return self._wait(lambda: self._transactionalUndo(trans_id))

    def _tpc_begin(self, txn, tid, status):
        self.locked = 1
        self.timeout.begin(self)
        self.stats.lock_time = time.time()
        self.storage.tpcBegin(txn, tid, status)

    def _store(self, oid, serial, data, refs, version):
        try:
            newserial = self.storage.store(oid, serial, data, refs,
                                           version, self.transaction)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, err:
            if isinstance(err, ConflictError):
                self.stats.conflicts += 1
            if not isinstance(err, TransactionError):
                # Unexpected errors are logged and passed to the client
                t, v = sys.exc_info()[:2]
                self.logger.error("%s: store error: %s, %s",
                                  self.log_label, t, v, exc_info=True)
            # Try to pickle the exception.  If it can't be pickled,
            # the RPC response would fail, so use something else.
            pickler = cPickle.Pickler()
            pickler.fast = 1
            try:
                pickler.dump(err, 1)
            except:
                msg = "Couldn't pickle storage exception: %s" % repr(err)
                self.logger.error("%s: %s", self.log_label, msg)
                err = StorageServerError(msg)
            # The exception is reported back as newserial for this oid
            newserial = err
        else:
            if serial != "\0\0\0\0\0\0\0\0":
                self.invalidated.append((oid, version))
        if newserial == ResolvedSerial:
            self.stats.conflicts_resolved += 1
        self.serials.append((oid, newserial))

    def _tpcVote(self):
        self.client.serialnos(self.serials)
        return self.storage.tpcVote(self.transaction)

    def _abortVersion(self, src):
        oids = self.storage.abortVersion(src, self.transaction)
        inv = [(oid, src) for oid in oids]
        self.invalidated.extend(inv)
        return oids

    def _commitVersion(self, src, dest):
        oids = self.storage.commitVersion(src, dest, self.transaction)
        inv = [(oid, dest) for oid in oids]
        self.invalidated.extend(inv)
        if dest:
            inv = [(oid, src) for oid in oids]
            self.invalidated.extend(inv)
        return oids

    def _transactionalUndo(self, trans_id):
        oids = self.storage.undo(trans_id, self.transaction)
        inv = [(oid, None) for oid in oids]
        self.invalidated.extend(inv)
        return oids

    # When a delayed transaction is restarted, the dance is
    # complicated.  The restart occurs when one ZEOStorage instance
    # finishes as a transaction and finds another instance is in the
    # _waiting list.

    # XXX It might be better to have a mechanism to explicitly send
    # the finishing transaction's reply before restarting the waiting
    # transaction.  If the restart takes a long time, the previous
    # client will be blocked until it finishes.

    def _wait(self, thunk):
        # Wait for the storage lock to be acquired.
        self._thunk = thunk
        if self.storage._transaction:
            d = Delay()
            self.storage._waiting.append((d, self))
            self.logger.warn("%s: Transaction blocked waiting for storage. "
                             "Clients waiting: %d.",
                             self.log_label, len(self.storage._waiting))
            return d
        else:
            self.logger.debug("%s: Transaction acquired storage lock.",
                              self.log_label)
            return self._restart()

    def _restart(self, delay=None):
        # Restart when the storage lock is available.
        self._tpc_begin(self.transaction, self.tid, self.status)
        loads, loader = self.txnlog.get_loader()
        for i in range(loads):
            # load oid, serial, data, version
            self._store(*loader.load())
        resp = self._thunk()
        if delay is not None:
            delay.reply(resp)
        else:
            return resp

    def _handle_waiting(self):
        # Restart any client waiting for the storage lock.
        while self.storage._waiting:
            delay, zeo_storage = self.storage._waiting.pop(0)
            if self._restart_other(zeo_storage, delay):
                if self.storage._waiting:
                    n = len(self.storage._waiting)
                    self.logger.warn("%s: Blocked transaction restarted.  "
                                     "Clients waiting: %d", self.log_label, n)
                else:
                    self.logger.warn("%s: Blocked transaction restarted.",
                                     self.log_label)
                return

    def _restart_other(self, zeo_storage, delay):
        # Return True if the server restarted.
        # call the restart() method on the appropriate server.
        try:
            zeo_storage._restart(delay)
        except:
            self.logger.error("%s: Unexpected error "
                              "handling waiting transaction",
                              self.log_label, exc_info=True)
            zeo_storage.connection.close()
            return 0
        else:
            return 1

class StorageServer:

    """The server side implementation of ZEO.

    The StorageServer is the 'manager' for incoming connections.  Each
    connection is associated with its own ZEOStorage instance (defined
    below).  The StorageServer may handle multiple storages; each
    ZEOStorage instance only handles a single storage.
    """

    # Classes we instantiate.  A subclass might override.

    DispatcherClass = Dispatcher
    ZEOStorageClass = ZEOStorage
    ManagedServerConnectionClass = ManagedServerConnection

    def __init__(self, addr, storages, read_only=0,
                 invalidation_queue_size=100,
                 transaction_timeout=None,
                 monitor_address=None,
                 auth_protocol=None,
                 auth_filename=None,
                 auth_realm=None):
        """StorageServer constructor.

        This is typically invoked from the start.py script.

        Arguments (the first two are required and positional):

        addr -- the address at which the server should listen.  This
            can be a tuple (host, port) to signify a TCP/IP connection
            or a pathname string to signify a Unix domain socket
            connection.  A hostname may be a DNS name or a dotted IP
            address.

        storages -- a dictionary giving the storage(s) to handle.  The
            keys are the storage names, the values are the storage
            instances, typically FileStorage or Berkeley storage
            instances.  By convention, storage names are typically
            strings representing small integers starting at '1'.

        read_only -- an optional flag saying whether the server should
            operate in read-only mode.  Defaults to false.  Note that
            even if the server is operating in writable mode,
            individual storages may still be read-only.  But if the
            server is in read-only mode, no write operations are
            allowed, even if the storages are writable.  Note that
            pack() is considered a read-only operation.

        invalidation_queue_size -- The storage server keeps a queue
            of the objects modified by the last N transactions, where
            N == invalidation_queue_size.  This queue is used to
            speed client cache verification when a client disconnects
            for a short period of time.

        transaction_timeout -- The maximum amount of time to wait for
            a transaction to commit after acquiring the storage lock.
            If the transaction takes too long, the client connection
            will be closed and the transaction aborted.

        monitor_address -- The address at which the monitor server
            should listen.  If specified, a monitor server is started.
            The monitor server provides server statistics in a simple
            text format.

        auth_protocol -- The name of the authentication protocol to use.
            Examples are "digest" and "srp".
            
        auth_filename -- The name of the password database filename.
            It should be in a format compatible with the authentication
            protocol used; for instance, "sha" and "srp" require different
            formats.
            
            Note that to implement an authentication protocol, a server
            and client authentication mechanism must be implemented in a
            auth_* module, which should be stored inside the "auth"
            subdirectory. This module may also define a DatabaseClass
            variable that should indicate what database should be used
            by the authenticator.
        """

        self.addr = addr
        self.storages = storages
        self.logger = logging.getLogger("ZSS.%s" % os.getpid())
        msg = ", ".join(
            ["%s:%s:%s" % (name, storage.isReadOnly() and "RO" or "RW",
                           storage.getName())
             for name, storage in storages.items()])
        self.logger.warn("%s created %s with storages: %s",
                         self.__class__.__name__,
                          read_only and "RO" or "RW", msg)
        for s in storages.values():
            s._waiting = []
        self.read_only = read_only
        self.auth_protocol = auth_protocol
        self.auth_filename = auth_filename
        self.auth_realm = auth_realm
        self.database = None
        if auth_protocol:
            self._setup_auth(auth_protocol)
        # A list of at most invalidation_queue_size invalidations
        self.invq = []
        self.invq_bound = invalidation_queue_size
        self.connections = {}
        self.dispatcher = self.DispatcherClass(addr,
                                               factory=self.new_connection)
        self.stats = {}
        self.timeouts = {}
        for name in self.storages.keys():
            self.stats[name] = StorageStats()
            if transaction_timeout is None:
                # An object with no-op methods
                timeout = StubTimeoutThread()
            else:
                timeout = TimeoutThread(transaction_timeout)
                timeout.start()
            self.timeouts[name] = timeout
        if monitor_address:
            self.monitor = StatsServer(monitor_address, self.stats)
        else:
            self.monitor = None

    def _setup_auth(self, protocol):
        # Can't be done in global scope, because of cyclic references
        from zodb.zeo.auth import get_module

        name = self.__class__.__name__

        module = get_module(protocol)
        if not module:
            self.logger.info("%s: no such an auth protocol: %s",
                             name, protocol)
            return
        
        storage_class, client, db_class = module
        
        if not storage_class or not issubclass(storage_class, ZEOStorage):
            self.logger.info("%s: %s isn't a valid protocol, "
                             "must have a StorageClass", name, protocol)
            self.auth_protocol = None
            return
        self.ZEOStorageClass = storage_class

        self.logger.info("%s: using auth protocol: %s", name, protocol)
        
        # We create a Database instance here for use with the authenticator
        # modules. Having one instance allows it to be shared between multiple
        # storages, avoiding the need to bloat each with a new authenticator
        # Database that would contain the same info, and also avoiding any
        # possibly synchronization issues between them.
        self.database = db_class(self.auth_filename)
        if self.database.realm != self.auth_realm:
            raise ValueError("password database realm %r "
                             "does not match storage realm %r"
                             % (self.database.realm, self.auth_realm))

    def new_connection(self, sock, addr):
        """Internal: factory to create a new connection.

        This is called by the Dispatcher class in ZEO.zrpc.server
        whenever accept() returns a socket for a new incoming
        connection.
        """
        if self.auth_protocol and self.database:
            zstorage = self.ZEOStorageClass(self, self.read_only,
                                            auth_realm=self.auth_realm)
            zstorage.set_database(self.database)
        else:
            zstorage = self.ZEOStorageClass(self, self.read_only)
        c = self.ManagedServerConnectionClass(sock, addr, zstorage, self)
        self.logger.warn("new connection %s: %s", addr, `c`)
        return c

    def register_connection(self, storage_id, conn):
        """Internal: register a connection with a particular storage.

        This is called by ZEOStorage.register().

        The dictionary self.connections maps each storage name to a
        list of current connections for that storage; this information
        is needed to handle invalidation.  This function updates this
        dictionary.

        Returns the timeout and stats objects for the appropriate storage.
        """
        l = self.connections.get(storage_id)
        if l is None:
            l = self.connections[storage_id] = []
        l.append(conn)
        stats = self.stats[storage_id]
        stats.clients += 1
        return self.timeouts[storage_id], stats

    def invalidate(self, conn, storage_id, tid, invalidated=()):
        """Internal: broadcast info and invalidations to clients.

        This is called from several ZEOStorage methods.

        This can do three different things:

        - If the invalidated argument is non-empty, it broadcasts
          invalidateTransaction() messages to all clients of the given
          storage except the current client (the conn argument).

        - If the invalidated argument is empty and the info argument
          is a non-empty dictionary, it broadcasts info() messages to
          all clients of the given storage, including the current
          client.

        - If both the invalidated argument and the info argument are
          non-empty, it broadcasts invalidateTransaction() messages to all
          clients except the current, and sends an info() message to
          the current client.

        """
        if invalidated:
            if len(self.invq) >= self.invq_bound:
                del self.invq[0]
            self.invq.append((tid, invalidated))
        for p in self.connections.get(storage_id, ()):
            if invalidated and p is not conn:
                p.client.invalidateTransaction(tid, invalidated)

    def get_invalidations(self, tid):
        """Return a tid and list of all objects invalidation since tid.

        The tid is the most recent transaction id committed by the server.

        Returns None if it is unable to provide a complete list
        of invalidations for tid.  In this case, client should
        do full cache verification.
        """

        if not self.invq:
            self.logger.warn("invq empty")
            return None, []

        earliest_tid = self.invq[0][0]
        if earliest_tid > tid:
            self.logger.warn("tid to old for invq %s < %s",
                             u64(tid), u64(earliest_tid))
            return None, []

        oids = {}
        for tid, L in self.invq:
            for key in L:
                oids[key] = 1
        latest_tid = self.invq[-1][0]
        return latest_tid, oids.keys()

    def close_server(self):
        """Close the dispatcher so that there are no new connections.

        This is only called from the test suite, AFAICT.
        """
        self.dispatcher.close()
        if self.monitor is not None:
            self.monitor.close()
        for storage in self.storages.values():
            storage.close()
        # Force the asyncore mainloop to exit by hackery, i.e. close
        # every socket in the map.  loop() will return when the map is
        # empty.
        for s in asyncore.socket_map.values():
            try:
                s.close()
            except:
                self.logger.exception(
                    "Unexpected error shutting down mainloop")

    def close_conn(self, conn):
        """Internal: remove the given connection from self.connections.

        This is the inverse of register_connection().
        """
        for cl in self.connections.values():
            if conn.obj in cl:
                cl.remove(conn.obj)

class StubTimeoutThread:

    def begin(self, client):
        pass

    def end(self, client):
        pass

class TimeoutThread(threading.Thread):
    """Monitors transaction progress and generates timeouts."""

    # There is one TimeoutThread per storage, because there's one
    # transaction lock per storage.

    def __init__(self, timeout):
        threading.Thread.__init__(self)
        self.setDaemon(1)
        self._timeout = timeout
        self._client = None
        self._deadline = None
        self._cond = threading.Condition() # Protects _client and _deadline
        self._trigger = trigger()

    def begin(self, client):
        # Called from the restart code the "main" thread, whenever the
        # storage lock is being acquired.  (Serialized by asyncore.)
        self._cond.acquire()
        try:
            assert self._client is None
            self._client = client
            self._deadline = time.time() + self._timeout
            self._cond.notify()
        finally:
            self._cond.release()

    def end(self, client):
        # Called from the "main" thread whenever the storage lock is
        # being released.  (Serialized by asyncore.)
        self._cond.acquire()
        try:
            assert self._client is not None
            self._client = None
            self._deadline = None
        finally:
            self._cond.release()

    def run(self):
        # Code running in the thread.
        while 1:
            self._cond.acquire()
            try:
                while self._deadline is None:
                    self._cond.wait()
                howlong = self._deadline - time.time()
                if howlong <= 0:
                    # Prevent reporting timeout more than once
                    self._deadline = None
                client = self._client # For the howlong <= 0 branch below
            finally:
                self._cond.release()
            if howlong <= 0:
                client.logger.error("Transaction timeout after %s seconds",
                                    self._timeout)
                self._trigger.pull_trigger(lambda: client.connection.close())
            else:
                time.sleep(howlong)
        self.trigger.close()

def run_in_thread(method, *args):
    t = SlowMethodThread(method, args)
    t.start()
    return t.delay

class SlowMethodThread(threading.Thread):
    """Thread to run potentially slow storage methods.

    Clients can use the delay attribute to access the MTDelay object
    used to send a zrpc response at the right time.
    """

    # Some storage methods can take a long time to complete.  If we
    # run these methods via a standard asyncore read handler, they
    # will block all other server activity until they complete.  To
    # avoid blocking, we spawn a separate thread, return an MTDelay()
    # object, and have the thread reply() when it finishes.

    def __init__(self, method, args):
        threading.Thread.__init__(self)
        self._method = method
        self._args = args
        self.delay = MTDelay()

    def run(self):
        try:
            result = self._method(*self._args)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception:
            self.delay.error(sys.exc_info())
        else:
            self.delay.reply(result)
