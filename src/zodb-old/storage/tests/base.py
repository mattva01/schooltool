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

"""Provide a mixin base class for storage tests.

The StorageTestBase class provides basic setUp() and tearDown()
semantics (which you can override), and it also provides a helper
method _dostore() which performs a complete store transaction for a
single object revision.
"""

import os
import sys
import time
import errno
import shutil
import unittest

from persistence import Persistent
from transaction import get_transaction

from zodb.db import DB
from zodb.serialize import ConnectionObjectReader, ObjectWriter, findrefs
from zodb.conflict import ResolveObjectReader
from zodb.ztransaction import Transaction
from zodb.storage.tests.minpo import MinPO
from zodb.storage.base import ZERO, BerkeleyConfig

DBHOME = 'test-db'


def snooze():
    # In Windows, it's possible that two successive time.time() calls return
    # the same value.  Tim guarantees that time never runs backwards.  You
    # usually want to call this before you pack a storage, or must make other
    # guarantees about increasing timestamps.
    now = time.time()
    while now == time.time():
        time.sleep(0.1)

def zodb_pickle(obj):
    """Create a pickle in the format expected by ZODB."""
    w = ObjectWriter(obj._p_jar)
    state = w.getState(obj)
    w.close()
    return state

class FakeCache(dict):
    def set(self, k, v):
        self[k] = v

def zodb_unpickle(data):
    """Unpickle an object stored using the format expected by ZODB."""
    # Use a ResolveObjectReader because we don't want to load any
    # object referenced by this one.
    u = ResolveObjectReader()
    return u.getObject(data)

def handle_all_serials(oid, *args):
    """Return dict of oid to serialno from store() and tpc_vote().

    Raises an exception if one of the calls raised an exception.

    The storage interface got complicated when ZEO was introduced.
    Any individual store() call can return None or a sequence of
    2-tuples where the 2-tuple is either oid, serialno or an
    exception to be raised by the client.

    The original interface just returned the serialno for the
    object.
    """
    d = {}
    for arg in args:
        if isinstance(arg, str):
            d[oid] = arg
        elif arg is None:
            pass
        else:
            for oid, serial in arg:
                if not isinstance(serial, str):
                    raise serial # error from ZEO server
                d[oid] = serial
    return d

def handle_serials(oid, *args):
    """Return the serialno for oid based on multiple return values.

    A helper for function _handle_all_serials().
    """
    return handle_all_serials(oid, *args)[oid]

def import_helper(name):
    __import__(name)
    return sys.modules[name]

class C(Persistent):
    pass


class Jar:
    def __init__(self, storage):
        self._storage = storage
        
    def newObjectId(self):
        return self._storage.newObjectId()

    def register(self, obj):
        obj._p_oid = self.newObjectId()


class StorageTestBase(unittest.TestCase, object):

    # XXX It would be simpler if concrete tests didn't need to extend
    # setUp() and tearDown().

    def setUp(self):
        # You need to override this with a setUp that creates self._storage
        self._storage = None

    def _close(self):
        # You should override this if closing your storage requires additional
        # shutdown operations.
        if self._storage is not None:
            self._storage.close()

    def tearDown(self):
        self._close()

    def _dostore(self, oid=None, revid=None, data=None, version=None,
                 already_pickled=False, user=None, description=None):
        """Do a complete storage transaction.  The defaults are:

         - oid=None, ask the storage for a new oid
         - revid=None, use a revid of ZERO
         - data=None, pickle up some arbitrary data (the integer 7)
         - version=None, use the empty string version

        Returns the object's new revision id.
        """
        if oid is None:
            oid = self._storage.newObjectId()
        if revid is None:
            revid = ZERO
        refs = []
        if data is None:
            data = MinPO(7)
        if isinstance(data, int):
            data = MinPO(data)
        if not already_pickled:
            data, refs = zodb_pickle(data)
        elif isinstance(data, tuple):
            data, refs = data
        else:
            refs = findrefs(data)
        if version is None:
            version = ''
        # Begin the transaction
        t = Transaction()
        if user is not None:
            t.user = user
        if description is not None:
            t.description = description
        try:
            self._storage.tpcBegin(t)
            # Store an object
            r1 = self._storage.store(oid, revid, data, refs, version, t)
            # Finish the transaction
            r2 = self._storage.tpcVote(t)
            revid = handle_serials(oid, r1, r2)
            self._storage.tpcFinish(t)
        except:
            self._storage.tpcAbort(t)
            raise
        return revid

    def _dostoreNP(self, oid=None, revid=None, data=None, version=None,
                   user=None, description=None):
        return self._dostore(oid, revid, data, version, already_pickled=True,
                             user=user, description=description)
    # The following methods depend on optional storage features.

    def _undo(self, tid, oid=None):
        # Undo a tid that affects a single object (oid).
        # XXX This is very specialized
        t = Transaction()
        t.note("undo")
        self._storage.tpcBegin(t)
        oids = self._storage.undo(tid, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        if oid is not None:
            self.assertEqual(len(oids), 1)
            self.assertEqual(oids[0], oid)
        return self._storage.lastTransaction()

    def _commitVersion(self, src, dst):
        t = Transaction()
        t.note("commit %r to %r" % (src, dst))
        self._storage.tpcBegin(t)
        oids = self._storage.commitVersion(src, dst, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        return oids

    def _abortVersion(self, ver):
        t = Transaction()
        t.note("abort %r" % ver)
        self._storage.tpcBegin(t)
        oids = self._storage.abortVersion(ver, t)
        self._storage.tpcVote(t)
        self._storage.tpcFinish(t)
        return oids

    # some helper functions for setting up a valid root so that
    # the storage can be packed

    def _initroot(self):
        self._jar = jar = Jar(self._storage)
        self._reader = ConnectionObjectReader(jar, {})
        try:
            self._storage.load(ZERO, '')
        except KeyError:
            root = self._newobj()
            t = Transaction()
            t.note("initial database creation")
            self._storage.tpcBegin(t)
            data, refs = zodb_pickle(root)
            self._storage.store(ZERO, None, data, refs, '', t)
            self._storage.tpcVote(t)
            self._storage.tpcFinish(t)

    def _newobj(self):
        obj = C()
        obj._p_jar = self._jar
        return obj

    def _linked_newobj(self):
        # Create a new object and make sure the root has a reference to it.
        # Returns the object, the root, and the revid of the root.
        data, revid0 = self._storage.load(ZERO, '')
        root = self._reader.getObject(data)
        obj = self._newobj()
        # Link the root object to the persistent object, in order to keep the
        # persistent object alive.  XXX Order here is important: an attribute
        # on the root object must be set first, so that it gets oid 0, /then/
        # the attribute on the obj can be set.
        root.obj = obj
        obj.value = 0
        root.value = 0
        root._p_jar = self._jar
        revid0 = self._dostore(ZERO, revid=revid0, data=root)
        return obj, root, revid0


class BerkeleyTestBase(StorageTestBase):
    def _config(self):
        # Checkpointing just slows the tests down because we have to wait for
        # the thread to properly shutdown.  This can take up to 10 seconds, so
        # for the purposes of the test suite we shut off this thread.
        config = BerkeleyConfig()
        config.interval = 0
        return config

    def _envdir(self):
        return DBHOME

    def open(self):
        self._storage = self.ConcreteStorage(self._envdir(), self._config())

    def _zap_dbhome(self, dir=None):
        if dir is None:
            dir = self._envdir()
        if os.path.isdir(dir):
            shutil.rmtree(dir)

    def _mk_dbhome(self, dir=None):
        if dir is None:
            dir = self._get_envdir()
        os.mkdir(dir)
        try:
            return self.ConcreteStorage(dir, config=self._config())
        except:
            self._zap_dbhome()
            raise

    def setUp(self):
        StorageTestBase.setUp(self)
        self._zap_dbhome()
        self.open()

    def tearDown(self):
        StorageTestBase.tearDown(self)
        self._zap_dbhome()



class ZODBTestBase(BerkeleyTestBase):
    def setUp(self):
        BerkeleyTestBase.setUp(self)
        self._db = None
        try:
            self._db = DB(self._storage)
            self._conn = self._db.open()
            self._root = self._conn.root()
        except:
            self.tearDown()
            raise

    def _close(self):
        if self._db is not None:
            self._db.close()
            self._db = self._storage = self._conn = self._root = None

    def tearDown(self):
        # If the tests exited with any uncommitted objects, they'll blow up
        # subsequent tests because the next transaction commit will try to
        # commit those object.  But they're tied to closed databases, so
        # that's broken.  Aborting the transaction now saves us the headache.
        try:
            get_transaction().abort()
            self._close()
        finally:
            BerkeleyTestBase.tearDown(self)
