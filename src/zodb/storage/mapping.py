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
"""Very Simple Mapping ZODB storage

The Mapping storage provides an extremely simple storage
implementation that doesn't provide undo or version support.

It is meant to illustrate the simplest possible storage.

The Mapping storage uses a single data structure to map object ids to
data.

$Id: mapping.py,v 1.11 2003/07/10 17:40:05 bwarsaw Exp $
"""

from zodb import interfaces, utils
from zodb.storage.base import BaseStorage
from zodb.storage.interfaces import *
from zodb.timestamp import TimeStamp
from zope.interface import implements

class MappingStorage(BaseStorage):

    implements(IStorage)

    def __init__(self, name="Mapping Storage"):
        BaseStorage.__init__(self, name)
        self._index = {}
        self._tindex = []

    def close(self):
        pass

    def cleanup(self):
        pass

    def load(self, oid, version):
        self._lock_acquire()
        try:
            serial, data, refs = self._index[oid]
            return data, serial
        finally:
            self._lock_release()

    def store(self, oid, serial, data, refs, version, transaction):
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)

        if version:
            raise NotImplementedError

        self._lock_acquire()
        try:
            if self._index.has_key(oid):
                oserial, odata, orefs = self._index[oid]
                if serial != oserial:
                    raise interfaces.ConflictError(serials=(oserial, serial))
            serial = self._serial
            self._tindex.append((oid, serial, data, refs))
        finally:
            self._lock_release()
        return serial

    def _clear_temp(self):
        self._tindex = []

    def _finish(self, tid):
        for oid, serial, data, refs in self._tindex:
            self._index[oid] = serial, data, refs
        self._ltid = tid

    def pack(self, t, gc=True):
        """Perform a pack on the storage.

        There are two forms of packing: incremental and full gc.  In an
        incremental pack, only old object revisions are removed.  In a full gc
        pack, cyclic garbage detection and removal is also performed.

        t is the pack time.  All non-current object revisions older than t
        will be removed in an incremental pack.

        MappingStorage ignores the gc flag.  Every pack does both incremental
        and full gc packing.
        """
        self._lock_acquire()
        try:
            # Build an index of those objects reachable from the root.
            rootl = [ZERO]
            packmark = {}
            while rootl:
                oid = rootl.pop()
                if packmark.has_key(oid):
                    continue
                # Register this oid and append the objects referenced by this
                # object to the root search list.
                rec = self._index[oid]
                packmark[oid] = rec
                rootl.extend(rec[3])
            # Now delete any unreferenced entries:
            for oid in index.keys():
                if not packmark.has_key(oid):
                    del index[oid]
        finally:
            self._lock_release()

    def _splat(self):
        """Spit out a string showing state."""
        o = []
        o.append('Index:')
        keys = self._index.keys()
        keys.sort()
        for oid in keys:
            r = self._index[oid]
            o.append('  %s: %s, %s' %
                     (utils.u64(oid),TimeStamp(r[:8]),`r[8:]`))
        return "\n".join(o)
