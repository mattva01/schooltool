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
import itertools
from persistent import Persistent
from persistent.dict import PersistentDict
from schooltool.interfaces import ILocation
from zope.interface import implements

__metaclass__ = type


class PersistentKeysDict(Persistent, UserDict.DictMixin):
    """A PersistentDict which uses persistent objects as keys by
    relying on their _p_oids.

    If an object used as a key does not yet have a _p_oid, it is added
    to self._p_jar and assigned a _p_oid.  Thus, PersistentKeysDict()
    has to be added to the ZODB connection before being used.
    """

    def _getvdata(self):
        if not hasattr(self, '_v_data'):
            self._v_data = {}
        return self._v_data
    _tmpdata = property(_getvdata)

    def __init__(self):
        self._data = PersistentDict()

    def __setitem__(self, key, value):
        """Adds a value to the dict.

        If a key object does not yet have _p_oid, it is added to the
        current connection (self._p_jar).
        """
        self.checkKey(key)
        if key._p_oid is None or self._p_jar is None:
            self._tmpdata[id(key)] = (key, value)
            self._p_changed = True
        else:
            self._data[key._p_oid] = value

    def __getitem__(self, key):
        self.checkKey(key)
        try:
            if id(key) in self._tmpdata:
                return self._tmpdata[id(key)][1]
            else:
                return self._data[key._p_oid]
        except KeyError:
            raise KeyError, key

    def __delitem__(self, key):
        self.checkKey(key)
        try:
            if id(key) in self._tmpdata:
                del self._tmpdata[id(key)]
            else:
                del self._data[key._p_oid]
        except KeyError:
            raise KeyError, key

    def keys(self):
        jar = self._p_jar
        return ([jar[key] for key in self._data] +
                [key for key, value in self._tmpdata.itervalues()])

    def __contains__(self, key):
        self.checkKey(key)
        return id(key) in self._tmpdata or key._p_oid in self._data

    def __iter__(self):
        jar = self._p_jar
        for key in self._data:
            yield jar[key]
        for key, value in self._tmpdata.itervalues():
            yield key

    def __len__(self):
        return len(self._data) + len(self._tmpdata)

    def checkKey(self, key):
        if not hasattr(key, '_p_oid'):
            raise TypeError("The key must be persistent (got %r)" % (key, ))

    def __getstate__(self):
        data = self._data
        jar = self._p_jar
        assert jar is not None
        for key, value in self._tmpdata.itervalues():
            if key._p_oid is None:
                jar.add(key)
            data[key._p_oid] = value
        self._tmpdata.clear()
        return Persistent.__getstate__(self)


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

    def clear(self):
        self._data.clear()


class MaybePersistentKeysSet(Persistent):
    """A set for persistent and non-persistent but picklable objects that
    uses PersistentKeysDict as a backend.
    """

    def __init__(self):
        self._pdata = PersistentKeysDict()
        self._npdata = PersistentDict()

    def add(self, item):
        data = self._dataSourceFor(item)
        if item not in data:
            data[item] = None

    def __iter__(self):
        return itertools.chain(self._pdata, self._npdata)

    def remove(self, item):
        del self._dataSourceFor(item)[item]

    def __len__(self):
        return len(self._pdata) + len(self._npdata)

    def _isPersistent(self, obj):
        return hasattr(obj, '_p_oid')

    def _dataSourceFor(self, obj):
        if self._isPersistent(obj):
            return self._pdata
        else:
            return self._npdata

    def clear(self):
        self._pdata.clear()
        self._npdata.clear()


class PersistentPairKeysDict(Persistent, UserDict.DictMixin):
    """A dict indexed strictly by pairs (persistent, hashable)."""

    def __init__(self):
        self._data = PersistentKeysDict()

    def __setitem__(self, (persistent, hashable), value):
        if persistent not in self._data:
            self._data[persistent] = {}
        d = self._data[persistent]
        d[hashable] = value
        self._data[persistent] = d

    def __getitem__(self, (persistent, hashable)):
        return self._data[persistent][hashable]

    def __delitem__(self, (persistent, hashable)):
        d = self._data[persistent]
        del d[hashable]
        if d:
            self._data[persistent] = d
        else:
            del self._data[persistent]

    def keys(self):
        L = []
        data = self._data
        for persistent in data:
            L += [(persistent, hashable)
                  for hashable in data[persistent]]
        return L

    def __contains__(self, (persistent, hashable)):
        return (persistent in self._data and
                hashable in self._data[persistent])

    def __len__(self):
        count = 0
        data = self._data
        for persistent in data:
            count += len(data[persistent])
        return count

    def __iter__(self):
        data = self._data
        for persistent in data:
            for hashable in data[persistent]:
                yield persistent, hashable

    def iteritems(self):
        data = self._data
        for persistent in data:
            for hashable, value in data[persistent].iteritems():
                yield (persistent, hashable), value


class UniqueNamesMixin:

    def __init__(self, name_length=3):
        self._names = PersistentDict()
        self._names['__next'] = 1
        self._format = '%%0%dd' % name_length

    def getNames(self):
        return [name for name in self._names if name != '__next']

    def _newName(self):
        next = self._names['__next']
        self._names['__next'] = next + 1
        return self._format % next

    def newName(self, ob, value=None, name=None):
        if ob.__name__ is not None:
            raise ValueError('object already has a name', ob.__name__, ob)
        if name is None:
            name = self._newName()
            while name in self._names:
                name = self._newName()
        elif name in self._names:
            raise ValueError('name already used', name, ob)
        self._names[name] = value
        ob.__name__ = name

    def valueForName(self, name):
        return self._names[name]

    def removeName(self, name):
        del self._names[name]

    def clearNames(self):
        next = self._names['__next']
        self._names.clear()
        self._names['__next'] = next


class PersistentKeysSetWithNames(Persistent, UniqueNamesMixin):

    def __init__(self, name_length=3):
        self._data = PersistentKeysDict()
        UniqueNamesMixin.__init__(self, name_length)

    def add(self, item, name=None):
        if item not in self._data:
            self.newName(item, item, name=name)
            self._data[item] = None

    def __iter__(self):
        return iter(self._data)

    def remove(self, item):
        assert item.__name__ in self.getNames()
        del self._data[item]
        self.removeName(item.__name__)

    def __len__(self):
        return len(self._data)

    def clear(self):
        self._data.clear()
        self.clearNames()


class PersistentPairKeysDictWithNames(PersistentPairKeysDict,
                                      UniqueNamesMixin):

    def __init__(self):
        PersistentPairKeysDict.__init__(self)
        UniqueNamesMixin.__init__(self, name_length=4)

    def __setitem__(self, key, value):
        PersistentPairKeysDict.__setitem__(self, key, value)
        self.newName(value, value)

    def __delitem__(self, key):
        name = self[key].__name__
        PersistentPairKeysDict.__delitem__(self, key)
        self.removeName(name)


class PersistentKeysSetContainer(PersistentKeysSetWithNames):
    """A container based on PersistentKeysSetWithNames.

    This container sets __parent__ of added objects to self.  In addition,
    it can check that all added objects implement an interface.
    """
    # XXX I'm not entirely sure that this class belongs in schooltool.db:
    #     it deals with interfaces and locations; none of the other classes do.

    implements(ILocation)

    def __init__(self, name, parent, value_interface=None):
        PersistentKeysSetWithNames.__init__(self)
        self.__name__ = name
        self.__parent__ = parent
        self.value_interface = value_interface

    def add(self, obj, name=None):
        if (self.value_interface is not None
            and not self.value_interface.providedBy(obj)):
            raise ValueError("%r does not implement %r"
                             % (obj, self.value_interface))
        PersistentKeysSetWithNames.add(self, obj, name=name)
        # TODO: check if obj implements ILocation?
        #       or maybe IContained? (That's what Zope 3 containers check)
        obj.__parent__ = self

    def remove(self, obj):
        PersistentKeysSetWithNames.remove(self, obj)
        obj.__parent__ = None
