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

"""In-memory ZODB storage

This module provides two storages, both of which keep all their data
in-memory.  When the storage is closed, all data is lost.  There is a full
storage with versions, undo, etc., and a minimal storage which retains no
old object revisions.

The implementation piggybacks on the Berkeley storages by providing a layer
that fakes enough of the BerkeleyDB (bsddb module) API with built-in data
structures.

These storages can be used to

  - provide an example implementation of a full storage without
    distracting storage details,

  - provide a volatile storage that is useful for giving demonstrations.

These storages are different than the demo storage which provides for a
`shadow` read-only storage, although the demo storage uses a FullMemoryStorage
as the fronting storage.
"""

import bisect

from zodb.storage.base import db
from zodb.storage.bdbfull import BDBFullStorage
from zodb.storage.bdbminimal import BDBMinimalStorage


class MemoryFullStorage(BDBFullStorage):
    # Override BerkeleyDB specific stuff so that everything's created in the
    # memory and is set up to use dictionaries and lists instead of Berkeley
    # tables and queues.
    def _newenv(self, envdir):
        return FakeEnv(), FakeLockFile()

    def _setupDB(self, name, flags=0, dbtype=None, reclen=None):
        if dbtype is None:
            if flags & db.DB_DUP:
                return FakeDupBTree()
            return FakeBTree()
        if dbtype == db.DB_QUEUE:
            # Ignore the reclen, we don't care about it
            return FakeQueue()


class MemoryMinimalStorage(BDBMinimalStorage):
    # Override BerkeleyDB specific stuff so that everything's created in the
    # memory and is set up to use dictionaries and lists instead of Berkeley
    # tables and queues.
    def _newenv(self, envdir):
        return FakeEnv(), FakeLockFile()

    def _setupDB(self, name, flags=0, dbtype=None, reclen=None):
        if dbtype is None:
            if flags & db.DB_DUP:
                return FakeDupBTree()
            return FakeBTree()
        if dbtype == db.DB_QUEUE:
            # Ignore the reclen, we don't care about it
            return FakeQueue()



# These data structures fake enough of the BerkeleyDB APIs to get away with
# this implementation trick...  I think. :)
class FakeLockFile:
    def close(self):
        pass


class FakeEnv:
    # Environments and the transactions on them
    def txn_checkpoint(self, *args):
        pass

    def txn_begin(self):
        return self

    def abort(self):
        pass

    def commit(self):
        pass

    def close(self):
        pass


class FakeBTree:
    # Both BTrees and the cursors on them
    def __init__(self):
        self._keys = []
        self._vals = []
        self._pos = None
        self._cursors = []

    def close(self):
        # If we're closing a cursor, pop the last one off the stack
        if self._pos is not None:
            if self._cursors:
                self._pos = self._cursors.pop()
                return
        self._pos = None

    def __len__(self):
        assert len(self._keys) == len(self._vals)
        return len(self._keys)

    def has_key(self, key):
        i = bisect.bisect_left(self._keys, key)
        return i < len(self) and self._keys[i] == key

    def __getitem__(self, key):
        i = bisect.bisect_left(self._keys, key)
        if i < len(self) and self._keys[i] == key:
            return self._vals[i]
        raise KeyError

    def get(self, key, default=None, txn=None):
        i = bisect.bisect_left(self._keys, key)
        if i < len(self) and self._keys[i] == key:
            return self._vals[i]
        return default

    def keys(self):
        return self._keys[:]

    def items(self):
        return zip(self._keys, self._vals)

    def put(self, key, val, txn=None):
        i = bisect.bisect_left(self._keys, key)
        if i < len(self) and self._keys[i] == key:
            # Replace
            self._vals[i] = val
        else:
            self._keys.insert(i, key)
            self._vals.insert(i, val)

    def truncate(self, txn=None):
        del self._keys[:]
        del self._vals[:]

    # Cursor operations
    # Assumptions:
    # - we never use more than one cursor on a btree
    # - close() is a no-op
    # - we never call set_both() on a non DUP btree
    # - we never call btree.delete() with an open cursor (use cursor.delete()
    #   instead)

    def cursor(self, txn=None):
        # Push any current cursor onto the stack
        if self._pos is not None:
            self._cursors.append(self._pos)
        self._pos = None
        return self

    def _getrec(self, pos=0):
        self._pos = pos
        if not 0 <= self._pos < len(self):
            return None
        key = self._keys[self._pos]
        val = self._vals[self._pos]
        return key, val

    def first(self):
        return self._getrec()

    def last(self):
        return self._getrec(len(self)-1)

    def next(self):
        if self._pos is None:
            return self.first()
        return self._getrec(self._pos+1)

    def prev(self):
        if self._pos is None:
            return self.last()
        return self._getrec(self._pos-1)

    def next_dup(self):
        key = self._keys[self._pos]
        self._pos += 1
        if self._pos >= len(self):
            return None
        if key == self._keys[self._pos]:
            return key, self._vals[self._pos]
        return None

    def next_nodup(self):
        key = self._keys[self._pos]
        val = self._vals[self._pos]
        while True:
            self._pos += 1
            if self._pos >= len(self):
                return None
            ikey = self._keys[self._pos]
            ival = self._vals[self._pos]
            if key <> ikey or val <> ival:
                return ikey, ival

    def set_both(self, key, val):
        i = bisect.bisect_left(self._keys, key)
        if i >= len(self) or self._keys[i] <> key:
            raise db.DBNotFoundError
        while self._keys[i] == key and self._vals[i] <> val:
            i += 1
            if i >= len(self):
                raise db.DBNotFoundError
        return self._getrec(i)

    def set(self, key):
        i = bisect.bisect_left(self._keys, key)
        if i >= len(self):
            raise db.DBNotFoundError
        ikey = self._keys[i]
        if ikey <> key:
            raise db.DBNotFoundError
        self._pos = i
        ival = self._vals[i]
        return ikey, ival

    def set_range(self, key):
        i = bisect.bisect_left(self._keys, key)
        if i >= len(self):
            raise db.DBNotFoundError
        return self._getrec(i)

    def delete(self, key=None, txn=None):
        if key is None and self._pos is not None:
            # We're doing a cursor delete
            del self._keys[self._pos]
            del self._vals[self._pos]
            # XXX This is cheating, but we know cursor deletes are always
            # followed by a next or set_both call.  We don't care about the
            # latter, but for the former, decrement the position so the
            # subequent next will work "correctly".
            self._pos -= 1
        else:
            # We're doing a btree delete
            i = bisect.bisect_left(self._keys, key)
            if i < len(self) and self._keys[i] == key:
                del self._keys[i]
                del self._vals[i]
            else:
                raise db.DBNotFoundError


class FakeDupBTree(FakeBTree):
    def put(self, key, val, txn=None):
        # Duplicates are allowed.  Find the range of matching keys, then do
        # another bisect on the values to find where the sorted insert should
        # be.  I believe the semantics are to sort on both the keys and vals.
        i = bisect.bisect_left(self._keys, key)
        j = bisect.bisect_right(self._keys, key)
        if i <> j:
            i = bisect.bisect_left(self._vals, val, i, j)
        self._keys.insert(i, key)
        self._vals.insert(i, val)


class FakeQueue(list):
    def consume(self, txn=None):
        if not self:
            return None
        # Return the record number (which the storages ignore) and the value.
        return 'ignored', self.pop(0)

    def close(self):
        pass

    def truncate(self, txn=None):
        del self[:]

    def append(self, val, txn=None):
        super(FakeQueue, self).append(val)

    def values(self):
        return self
