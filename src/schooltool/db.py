#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
The persistent helper objects for SchoolTool.

$Id$
"""
import UserDict
from persistence import Persistent
from persistence.list import PersistentList
from persistence.dict import PersistentDict

__metaclass__ = type


class PersistentListSet(Persistent):
    """A set implemented with a PersistentList as a backend storage.

    This approach is not most efficient, but avoids the need of having
    a total ordering needed to employ OOSets
    (http://zope.org/Wikis/ZODB/FrontPage/guide/node6.html) or
    constant hashes (memory addresses) used for normal dicts.
    """

    def __init__(self):
        self._data = PersistentList()

    def add(self, item):
        if item not in self._data:
            self._data.append(item)

    def __iter__(self):
        return iter(self._data)

    def remove(self, item):
        self._data.remove(item)

    def __len__(self):
        return len(self._data)


class PersistentKeysDict(Persistent, UserDict.DictMixin):
    """A PersistentDict which uses persistent objects as keys by
    relying on their _p_oids.

    If an object used as a key does not yet have a _p_oid, it is added
    to self._p_jar and assigned a _p_oid.  Thus, PersistentKeysDict()
    has to be added to the ZODB connection before being used.
    """

    def __init__(self):
        # XXX: probably getting a connection or a persistent object
        # here is a good idea. Let's see how it gets used...
        self._data = PersistentDict()

    def __setitem__(self, key, value):
        """Adds a value to the dict.

        If a key object does not yet have _p_oid, it is added to the
        current connection (self._p_jar).
        """
        self.checkJar()
        self.checkKey(key)
        self._prepareExternalKey(key)
        self._data[self._toInternalKey(key)] = value

    def __getitem__(self, key):
        self.checkKey(key)
        return self._data[self._toInternalKey(key)]

    def __delitem__(self, key):
        self.checkKey(key)
        del self._data[self._toInternalKey(key)]

    def keys(self):
        self.checkJar()
        # XXX returning a lazy sequence is one optimization we might make
        toExternalKey = self._toExternalKey
        return [toExternalKey(key) for key in self._data]

    def __contains__(self, key):
        self.checkKey(key)
        return self._toInternalKey(key) in self._data

    def __iter__(self):
        self.checkJar()
        toExternalKey = self._toExternalKey
        for key in self._data:
            yield toExternalKey(key)

    def __len__(self):
        return len(self._data)

    def checkJar(self):
        if self._p_jar is None:
            raise TypeError("PersistentKeyDict %r must be added "
                            "to the connection before being used" % (self, ))

    # Override the next four methods in a subclass if you need to support
    # keys more complex than a single persistent object.

    def checkKey(self, key):
        if not hasattr(key, '_p_oid'):
            raise TypeError("The key must be persistent (got %r)" % (key, ))

    def _toExternalKey(self, key):
        return self._p_jar.get(key)

    def _toInternalKey(self, key):
        return key._p_oid

    def _prepareExternalKey(self, key):
        if key._p_oid is None:
            self._p_jar.add(key)


class PersistentTuplesDict(PersistentKeysDict):

    def __init__(self, pattern):
        """Create a new PersistentTuplesDict.

        Pattern is a tuple that illustrates which elements of the tuple
        are persistent objects.

        For example,

          ('o', 'o', 'p', 'o', 'p')

        or

          'oopop'

        means a five-tuple with a persistent object in the third or fifth
        positions, and any objects in the other positions.
        """
        if not isinstance(pattern, (tuple, basestring)):
            raise TypeError('pattern must be a tuple or string, not %r'
                            % (pattern,))
        self._patternlen = len(pattern)
        self._pindexes = []
        for count, item in enumerate(pattern):
            # This test isn't really needed if pattern is a string.
            # We could join a tuple to make it into a string, but we'd also
            # need to assert that each element of the tuple is a single
            # character.
            if not isinstance(item, basestring):
                raise TypeError(
                    "Pattern items must be characters 'p' or 'o': %r"
                    % (pattern,))
            if item.lower() == 'p':
                self._pindexes.append(count)
            elif item.lower() == 'o':
                pass
            else:
                raise ValueError(
                    "Pattern items must be characters 'p' or 'o': %r"
                    % (pattern,))
        self._pindexes = [count
                          for count, item in enumerate(pattern)
                          if item.lower() == 'p']
        PersistentKeysDict.__init__(self)

    def checkKey(self, key):
        if not isinstance(key, tuple):
            raise TypeError('key must be a tuple, but it is %r' % (key,))
        if not len(key) == self._patternlen:
            raise ValueError('key must be tuple of length %s, not %s' %
                             (self._patternlen, len(key)))

        for idx in self._pindexes:
            k = key[idx]
            if not hasattr(k, '_p_oid'):
                raise TypeError("item %s of the tuple must be persistent"
                                " (got %r)" % (idx, k))

    def _toExternalKey(self, key):
        get = self._p_jar.get
        pindexes = self._pindexes
        L = []
        for idx, K in enumerate(key):
            if idx in pindexes:
                L.append(get(K))
            else:
                L.append(K)
        return tuple(L)

    def _toInternalKey(self, key):
        pindexes = self._pindexes
        L = []
        for idx, K in enumerate(key):
            if idx in pindexes:
                L.append(K._p_oid)
            else:
                L.append(K)
        return tuple(L)

    def _prepareExternalKey(self, key):
        for idx in self._pindexes:
            if key[idx]._p_oid is None:
                self._p_jar.add(key[idx])


class HookablePJar:
    """A descriptor that proxies Persistent._p_jar with a callback on __set__.
    """

    def __init__(self, afterSet=None):
        self._afterSet = afterSet

    def __get__(self, inst, cls=None):
        return Persistent._p_jar.__get__(inst, cls)

    def __set__(self, inst, value):
        Persistent._p_jar.__set__(inst, value)
        if self._afterSet is not None:
            self._afterSet(inst, value)

    def __delete__(self, inst):
        Persistent._p_jar.__delete__(inst)

    def __doc__(self, inst):
        return Persistent._p_jar.__doc__(inst)


class PersistentKeysSet(Persistent):
    """A set for persistent objects that uses PersistentKeysDict as a
    backend.
    """

    def __init__(self):
        self._data = PersistentKeysDict()

    def add(self, item):
        if item not in self._data:
            self._data[item] = None

    def __iter__(self):
        return iter(self._data)

    def remove(self, item):
        del self._data[item]

    def __len__(self):
        return len(self._data)

    def setDataManager(self, datamanager):
        datamanager.add(self._data)

    _p_jar = HookablePJar(setDataManager)

