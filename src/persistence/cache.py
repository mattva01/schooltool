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
from time import time
from sys import getrefcount
from weakref import ref

import logging

from zope.interface import implements

from persistence.interfaces import ICache
from persistence._persistence import GHOST

class Cache(object):

    implements(ICache)

    def __init__(self, size=500, inactive=300):
        self._ghosts = {}
        self.__gget = self._ghosts.get
        self._active = {}
        self.__aget = self._active.get
        self._size = size
        self._inactive = inactive
        self._logger = logging.getLogger("persistence.cache")

    def get(self, oid, default=None):
        o = self.__gget(oid, None)
        if o is None:
            o = self._active.get(oid, None)
            if o is None:
                return default
        o = o()
        if o is None:
            return default
        else:
            return o

    def set(self, oid, obj):
        if obj._p_changed is None:
            # ghost
            self._ghosts[oid] = ref(obj, _dictdel(oid, self._ghosts))
        else:
            self._active[oid] = ref(obj, _dictdel(oid, self._active))

    def remove(self, oid):
        # XXX The oid should always be in one of these dicts, else
        # there would be no need to remove it.
        if oid in self._ghosts:
            del self._ghosts[oid]
        else:
            del self._active[oid]

    def __len__(self):
        return len(self._ghosts) + len(self._active)

    def activate(self, oid):
        wref = self._ghosts.get(oid)
        if wref is None:
            assert oid in self._active
            return
        del self._ghosts[oid]
        self._active[oid] = ref(wref(), _dictdel(oid, self._active))

    def shrink(self):
        na = len(self._active)
        if na < 1:
            return

        now = int(time() % 86400)

        # Implement a trivial LRU cache by sorting the items by access
        # time and trundling over the list until we've reached our
        # target size.  The number of objects in the cache should be
        # relatively small (thousands) so the memory for the list is
        # pretty minimal.  Caution:  Don't use iteritems().  Because of
        # weakrefs, if garbage collection happens to occur, __active
        # can change size.
        L = []
        for oid, ob in self._active.items():
            if ob is not None:
                ob = ob()
            if ob is None:
                continue
            # The _p_atime field is seconds since the start of the day.
            # When we start a new day, we'll expect to see most of the
            # _p_atime values be greater than now.
            if ob._p_atime > now:
                deltat = (86400 - ob._p_atime) + now
            else:
                deltat = now - ob._p_atime
            L.append((deltat, oid, ob))

        # Sort on deltat so that the least recently used objects --
        # those with the largest deltat -- are at the front.
        L.sort()
        L.reverse()

        if na > self._size:
            # If the cache is full, ghostify everything up to the cache
            # limit.
            n = na - self._size
            must_go = L[:n]
            L = L[n:]
            for atime, oid, ob in must_go:
                self._ghostify(oid, ob)

        # ghostify old objects regardless of cache size
        for deltat, oid, ob in L:
            if deltat < self._inactive:
                break
            self._ghostify(oid, ob)

        self._logger.debug("incrgc reduced size from %d to %d",
                           na, len(self._active))

    def _ghostify(self, oid, ob):
        ob._p_deactivate()
        if ob._p_changed == None:
            del self._active[oid]
            self._ghosts[oid] = ref(ob, _dictdel(oid, self._ghosts))

    def _invalidate(self, oid):
        ob = self.__aget(oid)
        if ob is None:
            return
        ob = ob()
        ob._p_deactivate(force=True)
        assert ob._p_state == GHOST
        del self._active[oid]
        self._ghosts[oid] = ref(ob, _dictdel(oid, self._ghosts))

    def invalidate(self, oids):
        for oid in oids:
            self._invalidate(oid)

    def clear(self):
        self.invalidate(self._active.keys())

    def statistics(self):
        return {
            'ghosts': len(self._ghosts),
            'active': len(self._active),
            }

class _dictdel(object):

    __slots__ = 'oid', 'dict'

    def __init__(self, oid, dict):
        self.oid, self.dict = oid, dict

    def __call__(self, ref):
        del self.dict[self.oid]
