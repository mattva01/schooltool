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
# FOR A PARTICULAR PURPOSE
#
##############################################################################

import os
import sys
import time
import random
import select
import socket
import asyncore
import tempfile
import threading
import logging

from zodb.zeo.client import ClientStorage
from zodb.zeo.interfaces import ClientDisconnected
from zodb.zeo.zrpc.marshal import Marshaller
from zodb.zeo.tests import forker
from zodb.zeo.tests.common import TestClientStorage, DummyDB

from transaction import get_transaction
from zodb.db import DB
from zodb.ztransaction import Transaction
from zodb.storage.interfaces import ReadOnlyError
from zodb.storage.tests.base import StorageTestBase
from zodb.storage.tests.minpo import MinPO
from zodb.storage.tests.base import zodb_pickle, zodb_unpickle
from zodb.storage.tests.base import handle_all_serials, ZERO

class TestClientStorage(ClientStorage):

    test_connection = 0

    def verify_cache(self, stub):
        self.end_verify = threading.Event()
        self.verify_result = ClientStorage.verify_cache(self, stub)

    def endVerify(self):
        ClientStorage.endVerify(self)
        self.end_verify.set()

    def testConnection(self, conn):
        try:
            return ClientStorage.testConnection(self, conn)
        finally:
            self.test_connection = 1

class DummyDB:
    def invalidate(self, *args, **kwargs):
        pass

class CommonSetupTearDown(StorageTestBase):
    """Common boilerplate"""

    keep = 0
    invq = None
    timeout = None
    monitor = 0
    db_class = DummyDB

    def setUp(self):
        """Test setup for connection tests.

        This starts only one server; a test may start more servers by
        calling self._newAddr() and then self.startServer(index=i)
        for i in 1, 2, ...
        """
        super(CommonSetupTearDown, self).setUp()
        self.logger = logging.getLogger("testZEO")
        self.logger.warn("setUp() %s", self.id())
        self.file = tempfile.mktemp()
        self.addr = []
        self._pids = []
        self._servers = []
        self._conf_paths = []
        self._caches = []
        self._newAddr()
        self.startServer()

    def tearDown(self):
        """Try to cause the tests to halt"""
        get_transaction().abort()
        self.logger.warn("tearDown() %s", self.id())
        for p in self._conf_paths:
            os.remove(p)
        if getattr(self, '_storage', None) is not None:
            self._storage.close()
            if hasattr(self._storage, 'cleanup'):
                self._storage.cleanup()
        for adminaddr in self._servers:
            if adminaddr is not None:
                forker.shutdown_zeo_server(adminaddr)
        if hasattr(os, 'waitpid'):
            # Not in Windows Python until 2.3
            for pid in self._pids:
                os.waitpid(pid, 0)
        for c in self._caches:
            for i in 0, 1:
                path = "c1-%s-%d.zec" % (c, i)
                # On Windows before 2.3, we don't have a way to wait for
                # the spawned server(s) to close, and they inherited
                # file descriptors for our open files.  So long as those
                # processes are alive, we can't delete the files.  Try
                # a few times then give up.
                need_to_delete = 0
                if os.path.exists(path):
                    need_to_delete = 1
                    for dummy in range(5):
                        try:
                            os.unlink(path)
                        except:
                            time.sleep(0.5)
                        else:
                            need_to_delete = 0
                            break
                if need_to_delete:
                    os.unlink(path)  # sometimes this is just gonna fail
        super(CommonSetupTearDown, self).tearDown()

    def _newAddr(self):
        self.addr.append(self._getAddr())

    def _getAddr(self):
        # port+1 is also used, so only draw even port numbers
        return 'localhost', random.randrange(25000, 30000, 2)

    def getConfig(self, path, create, read_only):
        raise NotImplementedError

    def openClientStorage(self, cache='', cache_size=200000, wait=True,
                          read_only=False, read_only_fallback=False,
                          username=None, password=None, realm=None):
        self._caches.append(cache)
        storage = TestClientStorage(self.addr,
                                    client=cache,
                                    cache_size=cache_size,
                                    wait=wait,
                                    min_disconnect_poll=0.1,
                                    read_only=read_only,
                                    read_only_fallback=read_only_fallback,
                                    username=username,
                                    password=password,
                                    realm=realm)
        storage.registerDB(DummyDB())
        return storage

    def getServerConfig(self, addr, ro_svr):
        zconf = forker.ZEOConfig(addr)
        if ro_svr:
            zconf.read_only = 1
        if self.monitor:
             zconf.monitor_address = ("", 42000)
        if self.invq:
            zconf.invalidation_queue_size = self.invq
        if self.timeout:
            zconf.transaction_timeout = self.timeout
        return zconf

    def startServer(self, create=True, index=0, read_only=False, ro_svr=False,
                    keep=None):
        addr = self.addr[index]
        self.logger.warn("startServer(create=%d, index=%d, read_only=%d) @ %s",
                         create, index, read_only, addr)
        path = "%s.%d" % (self.file, index)
        sconf = self.getConfig(path, create, read_only)
        zconf = self.getServerConfig(addr, ro_svr)
        if keep is None:
            keep = self.keep
        zeoport, adminaddr, pid, path = forker.start_zeo_server(
            sconf, zconf, addr[1], keep)
        self._conf_paths.append(path)
        self._pids.append(pid)
        self._servers.append(adminaddr)

    def shutdownServer(self, index=0):
        self.logger.warn("shutdownServer(index=%d) @ %s", index,
                         self._servers[index])
        adminaddr = self._servers[index]
        if adminaddr is not None:
            forker.shutdown_zeo_server(adminaddr)
            self._servers[index] = None

    def pollUp(self, timeout=30.0, storage=None):
        # Poll until we're connected
        if storage is None:
            storage = self._storage
        now = time.time()
        giveup = now + timeout
        while not storage.is_connected():
            asyncore.poll(0.1)
            now = time.time()
            if now > giveup:
                self.fail("timed out waiting for storage to connect")

    def pollDown(self, timeout=30.0):
        # Poll until we're disconnected
        now = time.time()
        giveup = now + timeout
        while self._storage.is_connected():
            asyncore.poll(0.1)
            now = time.time()
            if now > giveup:
                self.fail("timed out waiting for storage to disconnect")


class ConnectionTests(CommonSetupTearDown):
    """Tests that explicitly manage the server process.

    To test the cache or re-connection, these test cases explicit
    start and stop a ZEO storage server.
    """

    def testMultipleAddresses(self):
        for i in range(4):
            self._newAddr()
        self._storage = self.openClientStorage('test', 100000)
        oid = self._storage.newObjectId()
        obj = MinPO(12)
        self._dostore(oid, data=obj)
        self._storage.close()

    def testMultipleServers(self):
        # XXX crude test at first -- just start two servers and do a
        # commit at each one.

        self._newAddr()
        self._storage = self.openClientStorage('test', 100000)
        self._dostore()

        self.shutdownServer(index=0)
        self.startServer(index=1)

        # If we can still store after shutting down one of the
        # servers, we must be reconnecting to the other server.

        did_a_store = False
        for i in range(10):
            try:
                self._dostore()
                did_a_store = True
                break
            except ClientDisconnected:
                time.sleep(0.5)
                self._storage.sync()
        self.assert_(did_a_store)

    def testReadOnlyClient(self):
        # Open a read-only client to a read-write server; stores fail

        # Start a read-only client for a read-write server
        self._storage = self.openClientStorage(read_only=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

    def testReadOnlyServer(self):
        # Open a read-only client to a read-only *server*; stores fail

        # We don't want the read-write server created by setUp()
        self.shutdownServer()
        self._servers = []
        # Start a read-only server
        self.startServer(create=False, index=0, ro_svr=True)
        # Start a read-only client
        self._storage = self.openClientStorage(read_only=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

    def testReadOnlyFallbackWritable(self):
        # Open a fallback client to a read-write server; stores succeed

        # Start a read-only-fallback client for a read-write server
        self._storage = self.openClientStorage(read_only_fallback=True)
        # Stores should succeed here
        self._dostore()

    def testReadOnlyFallbackReadOnlyServer(self):
        # Open a fallback client to a read-only *server*; stores fail

        # We don't want the read-write server created by setUp()
        self.shutdownServer()
        self._servers = []
        # Start a read-only server
        self.startServer(create=False, index=0, ro_svr=True)
        # Start a read-only-fallback client
        self._storage = self.openClientStorage(read_only_fallback=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

    # XXX Compare checkReconnectXXX() here to checkReconnection()
    # further down.  Is the code here hopelessly naive, or is
    # checkReconnection() overwrought?

    def testReconnectWritable(self):
        # A read-write client reconnects to a read-write server

        # Start a client
        self._storage = self.openClientStorage()
        # Stores should succeed here
        self._dostore()

        # Shut down the server
        self.shutdownServer()
        self._servers = []
        # Poll until the client disconnects
        self.pollDown()
        # Stores should fail now
        self.assertRaises(ClientDisconnected, self._dostore)

        # Restart the server
        self.startServer(create=False)
        # Poll until the client connects
        self.pollUp()
        # Stores should succeed here
        self._dostore()

    def testDisconnectionError(self):
        # Make sure we get a ClientDisconnected when we try to read an
        # object when we're not connected to a storage server and the
        # object is not in the cache.
        self.shutdownServer()
        self._storage = self.openClientStorage('test', 1000, wait=False)
        self.assertRaises(ClientDisconnected,
                          self._storage.load, 'fredwash', '')

    def testDisconnectedAbort(self):
        self._storage = self.openClientStorage()
        self._dostore()
        oids = [self._storage.newObjectId() for i in range(5)]
        txn = Transaction()
        self._storage.tpcBegin(txn)
        for oid in oids:
            data, refs = zodb_pickle(MinPO(oid))
            self._storage.store(oid, None, data, refs, '', txn)
        self.shutdownServer()
        self.assertRaises(ClientDisconnected, self._storage.tpcVote, txn)
        self._storage.tpcAbort(txn)
        self.startServer(create=0)
        self._storage._wait()
        self._dostore()

    def testBasicPersistence(self):
        # Verify cached data persists across client storage instances.

        # To verify that the cache is being used, the test closes the
        # server and then starts a new client with the server down.
        # When the server is down, a load() gets the data from its cache.

        self._storage = self.openClientStorage('test', 100000)
        oid = self._storage.newObjectId()
        obj = MinPO(12)
        revid1 = self._dostore(oid, data=obj)
        self._storage.close()
        self.shutdownServer()
        self._storage = self.openClientStorage('test', 100000, wait=False)
        data, revid2 = self._storage.load(oid, '')
        self.assertEqual(zodb_unpickle(data), MinPO(12))
        self.assertEqual(revid1, revid2)
        self._storage.close()

    def testRollover(self):
        # Check that the cache works when the files are swapped.

        # In this case, only one object fits in a cache file.  When the
        # cache files swap, the first object is effectively uncached.

        self._storage = self.openClientStorage('test', 1000)
        oid1 = self._storage.newObjectId()
        obj1 = MinPO("1" * 500)
        self._dostore(oid1, data=obj1)
        oid2 = self._storage.newObjectId()
        obj2 = MinPO("2" * 500)
        self._dostore(oid2, data=obj2)
        self._storage.close()
        self.shutdownServer()
        self._storage = self.openClientStorage('test', 1000, wait=False)
        self._storage.load(oid1, '')
        self._storage.load(oid2, '')

    def testReconnection(self):
        # Check that the client reconnects when a server restarts.

        # XXX Seem to get occasional errors that look like this:
        # File ZEO/zrpc2.py, line 217, in handle_request
        # File ZEO/StorageServer.py, line 325, in storea
        # File ZEO/StorageServer.py, line 209, in _check_tid
        # StorageTransactionError: (None, <tid>)
        # could system reconnect and continue old transaction?

        self._storage = self.openClientStorage()
        oid = self._storage.newObjectId()
        obj = MinPO(12)
        self._dostore(oid, data=obj)
        self.logger.warn("checkReconnection: About to shutdown server")
        self.shutdownServer()
        self.logger.warn("checkReconnection: About to restart server")
        self.startServer(create=False)
        oid = self._storage.newObjectId()
        obj = MinPO(12)
        while 1:
            try:
                self._dostore(oid, data=obj)
                break
            except ClientDisconnected:
                self.logger.warn("checkReconnection: "
                                 "Error after server restart; retrying.",
                                 exc_info=True)
                get_transaction().abort()
                self._storage.sync()
        else:
            self.fail("Could not reconnect to server")
        self.logger.warn("checkReconnection: finished")

    def testBadMessage1(self):
        # not even close to a real message
        self._bad_message("salty")

    def testBadMessage2(self):
        # just like a real message, but with an unpicklable argument
        global Hack
        class Hack:
            pass

        msg = Marshaller().encode(1, 0, "foo", (Hack(),))
        self._bad_message(msg)
        del Hack

    def _bad_message(self, msg):
        # Establish a connection, then send the server an ill-formatted
        # request.  Verify that the connection is closed and that it is
        # possible to establish a new connection.

        self._storage = self.openClientStorage()
        self._dostore()

        # break into the internals to send a bogus message
        zrpc_conn = self._storage._server.rpc
        zrpc_conn.message_output(msg)

        try:
            self._dostore()
        except ClientDisconnected:
            pass
        else:
            self._storage.close()
            self.fail("Server did not disconnect after bogus message")
        self._storage.close()

        self._storage = self.openClientStorage()
        self._dostore()

    def testCrossDBInvalidations(self):
        db1 = DB(self.openClientStorage())
        c1 = db1.open()
        r1 = c1.root()

        r1["a"] = MinPO("a")
        get_transaction().commit()

        db2 = DB(self.openClientStorage())
        r2 = db2.open().root()

        self.assertEqual(r2["a"].value, "a")

        r2["b"] = MinPO("b")
        get_transaction().commit()

        # make sure the invalidation is received in the other client
        for i in range(10):
            c1._storage.sync()
            if r1._p_oid in c1._invalidated:
                break
            time.sleep(0.1)
        self.assert_(r1._p_oid in c1._invalidated)

        # force the invalidations to be applied...
        c1.sync()
        r1.keys() # unghostify
        self.assertEqual(r1._p_serial, r2._p_serial)

        db2.close()
        db1.close()

class ReconnectionTests(CommonSetupTearDown):
    keep = True
    forker_admin_retries = 20
    invq = 2

    def testReadOnlyStorage(self):
        # Open a read-only client to a read-only *storage*; stores fail

        # We don't want the read-write server created by setUp()
        self.shutdownServer()
        self._servers = []
        # Start a read-only server
        self.startServer(create=False, index=0, read_only=True)
        # Start a read-only client
        self._storage = self.openClientStorage(read_only=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

    def testReadOnlyFallbackReadOnlyStorage(self):
        # Open a fallback client to a read-only *storage*; stores fail

        # We don't want the read-write server created by setUp()
        self.shutdownServer()
        self._servers = []
        # Start a read-only server
        self.startServer(create=False, index=0, read_only=True)
        # Start a read-only-fallback client
        self._storage = self.openClientStorage(read_only_fallback=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

    def testReconnectReadOnly(self):
        # A read-only client reconnects from a read-write to a
        # read-only server

        # Start a client
        self._storage = self.openClientStorage(read_only=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

        # Shut down the server
        self.shutdownServer()
        self._servers = []
        # Poll until the client disconnects
        self.pollDown()
        # Stores should still fail
        self.assertRaises(ReadOnlyError, self._dostore)

        # Restart the server
        self.startServer(create=False, read_only=True)
        # Poll until the client connects
        self.pollUp()
        # Stores should still fail
        self.assertRaises(ReadOnlyError, self._dostore)

    def testReconnectFallback(self):
        # A fallback client reconnects from a read-write to a
        # read-only server

        # Start a client in fallback mode
        self._storage = self.openClientStorage(read_only_fallback=True)
        # Stores should succeed here
        self._dostore()

        # Shut down the server
        self.shutdownServer()
        self._servers = []
        # Poll until the client disconnects
        self.pollDown()
        # Stores should fail now
        self.assertRaises(ClientDisconnected, self._dostore)

        # Restart the server
        self.startServer(create=False, read_only=True)
        # Poll until the client connects
        self.pollUp()
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

    def testReconnectUpgrade(self):
        # A fallback client reconnects from a read-only to a
        # read-write server

        # We don't want the read-write server created by setUp()
        self.shutdownServer()
        self._servers = []
        # Start a read-only server
        self.startServer(create=False, read_only=True)
        # Start a client in fallback mode
        self._storage = self.openClientStorage(read_only_fallback=1)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

        # Shut down the server
        self.shutdownServer()
        self._servers = []
        # Poll until the client disconnects
        self.pollDown()
        # Stores should fail now
        self.assertRaises(ClientDisconnected, self._dostore)

        # Restart the server, this time read-write
        self.startServer(create=False)
        # Poll until the client sconnects
        self.pollUp()
        # Stores should now succeed
        self._dostore()

    def testReconnectSwitch(self):
        # A fallback client initially connects to a read-only server,
        # then discovers a read-write server and switches to that

        # We don't want the read-write server created by setUp()
        self.shutdownServer()
        self._servers = []
        # Allocate a second address (for the second server)
        self._newAddr()
        # Start a read-only server
        self.startServer(create=False, index=0, read_only=True)
        # Start a client in fallback mode
        self._storage = self.openClientStorage(read_only_fallback=True)
        # Stores should fail here
        self.assertRaises(ReadOnlyError, self._dostore)

        # Start a read-write server
        self.startServer(index=1, read_only=False)
        # After a while, stores should work
        for i in range(300): # Try for 30 seconds
            try:
                self._dostore()
                break
            except (ClientDisconnected, ReadOnlyError):
                time.sleep(0.1)
                self._storage.sync()
        else:
            self.fail("Couldn't store after starting a read-write server")

    def testNoVerificationOnServerRestart(self):
        self._storage = self.openClientStorage()
        # When we create a new storage, it should always do a full
        # verification
        self.assertEqual(self._storage.verify_result, "full verification")
        self._dostore()
        self.shutdownServer()
        self.pollDown()
        self._storage.verify_result = None
        self.startServer(create=0)
        self.pollUp()
        # There were no transactions committed, so no verification
        # should be needed.
        self.assertEqual(self._storage.verify_result, "no verification")

    def testNoVerificationOnServerRestartWith2Clients(self):
        perstorage = self.openClientStorage(cache="test")
        self.assertEqual(perstorage.verify_result, "full verification")

        self._storage = self.openClientStorage()
        oid = self._storage.newObjectId()
        # When we create a new storage, it should always do a full
        # verification
        self.assertEqual(self._storage.verify_result, "full verification")
        # do two storages of the object to make sure an invalidation
        # message is generated
        revid = self._dostore(oid)
        self._dostore(oid, revid)

        perstorage.load(oid, '')

        self.shutdownServer()

        self.pollDown()
        self._storage.verify_result = None
        perstorage.verify_result = None
        self.startServer(create=0)
        self.pollUp()
        self.pollUp(storage=perstorage)
        # There were no transactions committed, so no verification
        # should be needed.
        self.assertEqual(self._storage.verify_result, "no verification")
        self.assertEqual(perstorage.verify_result, "no verification")
        perstorage.close()

    def testQuickVerificationWith2Clients(self):
        perstorage = self.openClientStorage(cache="test")
        self.assertEqual(perstorage.verify_result, "full verification")

        self._storage = self.openClientStorage()
        oid = self._storage.newObjectId()
        # When we create a new storage, it should always do a full
        # verification
        self.assertEqual(self._storage.verify_result, "full verification")
        # do two storages of the object to make sure an invalidation
        # message is generated
        revid = self._dostore(oid)
        revid = self._dostore(oid, revid)

        perstorage.load(oid, '')
        perstorage.close()

        revid = self._dostore(oid, revid)

        perstorage = self.openClientStorage(cache="test")
        self.assertEqual(perstorage.verify_result, "quick verification")

        self.assertEqual(perstorage.load(oid, ''),
                         self._storage.load(oid, ''))
        perstorage.close()

    def testVerificationWith2ClientsInvqOverflow(self):
        perstorage = self.openClientStorage(cache="test")
        self.assertEqual(perstorage.verify_result, "full verification")

        self._storage = self.openClientStorage()
        oid = self._storage.newObjectId()
        # When we create a new storage, it should always do a full
        # verification
        self.assertEqual(self._storage.verify_result, "full verification")
        # do two storages of the object to make sure an invalidation
        # message is generated
        revid = self._dostore(oid)
        revid = self._dostore(oid, revid)

        perstorage.load(oid, '')
        perstorage.close()

        # the test code sets invq bound to 2
        for i in range(5):
            revid = self._dostore(oid, revid)

        perstorage = self.openClientStorage(cache="test")
        self.assertEqual(perstorage.verify_result, "full verification")
        t = time.time() + 30
        while not perstorage.end_verify.isSet():
            perstorage.sync()
            if time.time() > t:
                self.fail("timed out waiting for endVerify")

        self.assertEqual(self._storage.load(oid, '')[1], revid)
        self.assertEqual(perstorage.load(oid, ''),
                         self._storage.load(oid, ''))
        perstorage.close()

class TimeoutTests(CommonSetupTearDown):
    timeout = 1

    def testTimeout(self):
        storage = self.openClientStorage()
        txn = Transaction()
        storage.tpcBegin(txn)
        storage.tpcVote(txn)
        time.sleep(2)
        self.assertRaises(ClientDisconnected, storage.tpcFinish, txn)

    def testTimeoutOnAbort(self):
        storage = self.openClientStorage()
        txn = Transaction()
        storage.tpcBegin(txn)
        storage.tpcVote(txn)
        storage.tpcAbort(txn)

    def testTimeoutOnAbortNoLock(self):
        storage = self.openClientStorage()
        txn = Transaction()
        storage.tpcBegin(txn)
        storage.tpcAbort(txn)

class MSTThread(threading.Thread):

    __super_init = threading.Thread.__init__

    def __init__(self, testcase, name):
        self.__super_init(name=name)
        self.testcase = testcase
        self.clients = []

    def run(self):
        tname = self.getName()
        testcase = self.testcase

        # Create client connections to each server
        clients = self.clients
        for i in range(len(testcase.addr)):
            c = testcase.openClientStorage(addr=testcase.addr[i])
            c.__name = "C%d" % i
            clients.append(c)

        for i in range(testcase.ntrans):
            # Because we want a transaction spanning all storages,
            # we can't use _dostore().  This is several _dostore() calls
            # expanded in-line (mostly).

            # Create oid->serial mappings
            for c in clients:
                c.__oids = []
                c.__serials = {}

            # Begin a transaction
            t = Transaction()
            for c in clients:
                #print "%s.%s.%s begin\n" % (tname, c.__name, i),
                c.tpcBegin(t)

            for j in range(testcase.nobj):
                for c in clients:
                    # Create and store a new object on each server
                    oid = c.newObjectId()
                    c.__oids.append(oid)
                    data = MinPO("%s.%s.t%d.o%d" % (tname, c.__name, i, j))
                    #print data.value
                    data, refs = zodb_pickle(data)
                    s = c.store(oid, ZERO, data, refs, '', t)
                    c.__serials.update(handle_all_serials(oid, s))

            # Vote on all servers and handle serials
            for c in clients:
                #print "%s.%s.%s vote\n" % (tname, c.__name, i),
                s = c.tpcVote(t)
                c.__serials.update(handle_all_serials(None, s))

            # Finish on all servers
            for c in clients:
                #print "%s.%s.%s finish\n" % (tname, c.__name, i),
                c.tpcFinish(t)

            for c in clients:
                # Check that we got serials for all oids
                for oid in c.__oids:
                    testcase.failUnless(c.__serials.has_key(oid))
                # Check that we got serials for no other oids
                for oid in c.__serials.keys():
                    testcase.failUnless(oid in c.__oids)

    def closeclients(self):
        # Close clients opened by run()
        for c in self.clients:
            try:
                c.close()
            except:
                pass
