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
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Demo ZODB storage

The Demo storage provides for a two-level storage: there is a read-only
backing storage and an writable fronting storage.  There are at least two use
cases for a demo storage:

- The backing storage can be on CDROM

- Functional tests can load up the backing storage with initial state, then
  easily get back to that initial state by zapping the front storages.

The fronting storage is an in-memory storage.

$Id: demo.py,v 1.11 2003/06/06 15:24:20 stevea Exp $
"""

from zope.interface import implements

from zodb.interfaces import VersionLockError
from zodb.storage.memory import MemoryFullStorage
from zodb.storage.interfaces import *


class DemoStorage(MemoryFullStorage):
    """Support ephemeral updates to a read-only backing storage.

    The DemoStorage extends a read-only base storage so that ephemeral
    transactions can be commited in the demo.  The transactions are only
    stored in memory; the base storage is not modified and updates are lost
    when the DemoStorage object is closed.
    """

    implements(IStorage, IUndoStorage, IVersionStorage)

    def __init__(self, name, backstorage, config=None):
        self._back = backstorage
        super(DemoStorage, self).__init__(name, config)
        # After initializing the memory storage, be sure to initialize the
        # last transaction id from the backing storage.
        self._ltid = self._back.lastTransaction()
        self._oid = self._back.lastObjectId()

    def close(self):
        super(DemoStorage, self).close()
        self._back.close()

    def cleanup(self):
        # XXX Don't cleanup the backing storage
        pass

    def _datarec(self, storage, oid, version=''):
        # We want a record containing the oid, serial, data, refs, version,
        # previous serial, the rec_version and the rec_nonversion.
        #
        # See if we have the current record for the object
        try:
            data, serial = storage.load(oid, version)
        except KeyError:
            return None
        it = iter(storage.iterator(serial))
        txnrec = it.next()
        assert txnrec.tid == serial
        for datarec in txnrec:
            if datarec.oid == oid:
                return datarec
        return None

    def load(self, oid, version=''):
        self._lock_acquire()
        try:
            try:
                return super(DemoStorage, self).load(oid, version)
            except KeyError:
                return self._back.load(oid, version)
        finally:
            self._lock_release()

    def loadSerial(self, oid, serial):
        self._lock_acquire()
        try:
            try:
                return super(DemoStorage, self).loadSerial(oid, serial)
            except KeyError:
                return self._back.loadSerial(oid, serial)
        finally:
            self._lock_release()

    def getSerial(self, oid):
        self._lock_acquire()
        try:
            try:
                return super(DemoStorage, self).getSerial(oid)
            except KeyError:
                return self._back.getSerial(oid)
        finally:
            self._lock_release()

    def lastSerial(self, oid):
        self._lock_acquire()
        try:
            serial = super(DemoStorage, self).lastSerial(oid)
            if serial is None:
                return self._back.lastSerial(oid)
        finally:
            self._lock_release()

    def modifiedInVersion(self, oid):
        version = super(DemoStorage, self).modifiedInVersion(oid)
        if version == '':
            # See if the backing storage has this object in a version, but
            # watch out for KeyErrors that might occur if the back knows
            # nothing about the object.
            try:
                backvers = self._back.modifiedInVersion(oid)
            except KeyError:
                pass
            else:
                version = backvers
        return version

    def versions(self):
        vset = {}
        for v in super(DemoStorage, self).versions():
            vset[v] = True
        for v in self._back.versions():
            vset[v] = True
        return vset.keys()

    def store(self, oid, serial, data, refs, version, txn):
        superself = super(DemoStorage, self)
        if txn is not self._transaction:
            raise StorageTransactionError(self, txn)
        self._lock_acquire()
        try:
            # See if we have the current record for the oid in the version
            datarec = self._datarec(superself, oid, version)
            if datarec is None:
                # Try to get the datarec from the backing storage
                try:
                    v = self._back.modifiedInVersion(oid)
                except KeyError:
                    datarec = None
                else:
                    datarec = self._datarec(self._back, oid, v)
                if datarec is not None:
                    if datarec.version and datarec.version <> version:
                        raise VersionLockError(oid, datarec.version)
                    if datarec.serial <> serial:
                        data, refs = self._conflict.resolve(
                            oid, datarec.serial, serial, data)
            # Either this is the first store of this object or we have the
            # current revision, not the backing storage.  Either way, we can
            # store the new revision.
            return superself.store(oid, serial, data, refs, version, txn)
        finally:
            self._lock_release()
