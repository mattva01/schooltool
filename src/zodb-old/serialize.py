##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
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
"""Support for ZODB object serialization.

ZODB serializes objects using a custom format based on Python pickles.
When an object is unserialized, it can be loaded as either a ghost or
a real object.  A ghost is a persistent object of the appropriate type
but without any state.  The first time a ghost is accessed, the
persistence machinery traps access and loads the actual state.  A
ghost allows many persistent objects to be loaded while minimizing the
memory consumption of referenced but otherwise unused objects.

Pickle format
-------------

ZODB pickles objects using a custom format.  Each object pickle had
two parts: the class metadata and the object state.  The class
description must provide enough information to call the class's
``__new__`` and create an empty object.  Once the object exists as a
ghost, its state is passed to ``__setstate__``.

The class metadata is a two-tuple containing the class object and a
tuple of arguments to pass to ``__new__``.  The second element may be
None if the only argument to ``__new__`` is the class.  Since the
first argument is a class, it will normally be pickled as a global
reference.  If the class is itself a persistent object, then the first
part of its instances class metadata will be a persistent reference to
the class.

If a type requires extra arguments to ``__new__``, then instances of
that type must never be in the ghost state.  A ghost is an object with
no state, but if extra arguments are passed to ``__new__`` then the
object has state as soon as it is constructed.  If a ghost object is
found, it is assumed that ``__getnewargs__`` would return None.

Persistent references
---------------------

A persistent reference is a pair containing an oid and class metadata.
When one persistent object pickle refers to another persistent object,
the database uses a persistent reference.  The format allows a
significant optimization, because ghosts can be created directly from
persistent references.  If the reference was just an oid, a database
access would be required to determine the class of the ghost.

Because the persistent reference includes the class, it is not
possible to change the class of a persistent object.  If a transaction
changed the class of an object, a new record with new class metadata
would be written but all the old references would still include the
old class.

$Id: serialize.py,v 1.23 2003/09/21 17:29:59 jim Exp $
"""

__metaclass__ = type

import logging
import cPickle
from cStringIO import StringIO

from zodb.interfaces import ZERO, InvalidObjectReference


def getClassMetadata(obj):
    if obj._p_state == 3:
        newargs = None
    else:
        newargs = getattr(obj, "__getnewargs__", None)
        if newargs is not None:
            newargs = newargs()
    return type(obj), newargs

class RootJar:
    def newObjectId(self):
        return ZERO

def getDBRoot():
    """Return a serialized database root object."""
    # Need for the initial bootstrap
    writer = ObjectWriter(RootJar())
    from persistence.dict import PersistentDict
    root = PersistentDict()
    state = writer.getState(root)
    writer.close()
    return state

_marker = object()

class ObjectWriter:
    """Serializes objects for storage in the database.

    The ObjectWriter creates object pickles in the ZODB format.  It
    also detects new persistent objects reachable from the current
    object.

    The client is responsible for calling the close() method to avoid
    leaking memory.  The ObjectWriter uses a Pickler internally, and
    Pickler objects do not participate in garbage collection.
    """

    def __init__(self, jar=None):
        self._file = StringIO()
        self._p = cPickle.Pickler(self._file, 1)
        self._p.persistent_id = self._persistent_id
        self._stack = []
        if jar is not None:
            assert hasattr(jar, "newObjectId")
        self._jar = jar

    def close(self):
        # Explicitly break cycle involving pickler
        self._p.persistent_id = None
        self._p = None

    def _persistent_id(self, obj):
        """Test if an object is persistent, returning an oid if it is.

        This function is used by the pickler to test whether an object
        is persistent.  If it isn't, the function returns None and the
        object is included in the pickle for the current persistent
        object.

        If it is persistent, it returns the oid and sometimes a tuple
        with other stuff.
        """
        oid = getattr(obj, "_p_oid", _marker)
        if oid is _marker:
            return None

        # I'd like to write something like this --
        # if isinstance(oid, types.MemberDescriptor):
        # -- but I can't because the type doesn't have a canonical name.
        # Instead, we'll assert that an oid must always be a string
        if not (oid is None or isinstance(oid, str)):
            # XXX log a warning
            return None

        if oid is None:
            oid = self._jar.newObjectId()
            obj._p_jar = self._jar
            obj._p_oid = oid
            self._stack.append(obj)
        elif obj._p_jar is not self._jar:
            raise InvalidObjectReference(obj, self._jar)

        return oid, getClassMetadata(obj)

    def newObjects(self, obj):
        # The modified object is also a "new" object.
        # XXX Should only call newObjects() once per Pickler.
        self._stack.append(obj)
        return NewObjectIterator(self._stack)

    def getState(self, obj):
        data = self._dump(getClassMetadata(obj), obj.__getstate__())
        refs = findrefs(data)
        return data, refs

    def getStateFromResolved(self, ghost, state):
        # This method is only used in the ResolvedObjectWriter subclass,
        # but it is defined here to keep all the details of the data
        # record format internal to this module.
        data = self._dump(getClassMetadata(ghost), state)
        refs = findrefs(data)
        return data, refs

    def _dump(self, classmeta, state):
        # To reuse the existing cStringIO object, we must reset
        # the file position to 0 and truncate the file after the
        # new pickle is written.
        self._file.seek(0)
        self._p.clear_memo()
        self._p.dump(classmeta)
        self._p.dump(state)
        self._file.truncate()
        return self._file.getvalue()

class NewObjectIterator:

    # The pickler is used as a forward iterator when the connection
    # is looking for new objects to pickle.

    def __init__(self, stack):
        self._stack = stack

    def __iter__(self):
        return self

    def next(self):
        if self._stack:
            elt = self._stack.pop()
            return elt
        else:
            raise StopIteration

class BaseObjectReader:

    def _persistent_load(self, oid):
        # subclasses must define _persistent_load().
        raise NotImplementedError

    def _get_unpickler(self, pickle):
        file = StringIO(pickle)
        unpickler = cPickle.Unpickler(file)
        unpickler.persistent_load = self._persistent_load
        return unpickler

    def _new_object(self, klass, newargs=None):
        if newargs is None:
            obj = klass.__new__(klass)
        else:
            obj = klass.__new__(klass, *newargs)

        return obj

    def getClassName(self, pickle):
        unpickler = self._get_unpickler(pickle)
        cls, newargs = unpickler.load()
        return cls.__name__

    def getGhost(self, pickle):
        unpickler = self._get_unpickler(pickle)
        klass, newargs = unpickler.load()
        return self._new_object(klass, newargs)

    def getState(self, pickle):
        unpickler = self._get_unpickler(pickle)
        unpickler.load() # skip the class metadata
        state = unpickler.load()
        return state

    def setGhostState(self, object, pickle):
        state = self.getState(pickle)
        object.__setstate__(state)

    def getObject(self, pickle):
        unpickler = self._get_unpickler(pickle)
        klass, newargs = unpickler.load()
        obj = self._new_object(klass, newargs)
        state = unpickler.load()
        obj.__setstate__(state)
        return obj

class SimpleObjectReader(BaseObjectReader):
    """Minimal reader for a single data record."""

    def _persistent_load(self, oid):
        return None

class ConnectionObjectReader(BaseObjectReader):

    def __init__(self, conn, cache):
        self._conn = conn
        self._cache = cache

    def _persistent_load(self, oid):
        # persistent_load function to pass to ObjectReader
        if isinstance(oid, tuple):
            # XXX We get here via new_persistent_id()

            # Quick instance reference.  We know all we need to know
            # to create the instance w/o hitting the db, so go for it!
            oid, classmeta = oid
            obj = self._cache.get(oid)
            if obj is not None:
                return obj

            obj = self._new_object(*classmeta)

            # XXX should be done by connection
            obj._p_oid = oid
            obj._p_jar = self._conn
            # When an object is created, it is put in the UPTODATE
            # state.  We must explicitly deactivate it to turn it into
            # a ghost.
            obj._p_deactivate()

            self._cache.set(oid, obj)
            return obj

        obj = self._cache.get(oid)
        if obj is not None:
            return obj
        return self._conn.get(oid)

class CopyReference:
    def __init__(self, ref):
        self.ref = ref

class CopyObjectReader(BaseObjectReader):

    def __init__(self, storage, created, oids):
        self._storage = storage
        self._created = created
        self._cache = oids

    def _persistent_load(self, oid):
        if isinstance(oid, tuple):
            oid, classmeta = oid
        else:
            classmeta = None
        new_ref = self._cache.get(oid)
        if new_ref is None:
            newObjectId = self._storage.newObjectId()
            self._created.add(newObjectId)
            self._cache[oid] = new_ref = newObjectId, classmeta
        return CopyReference(new_ref)

    def readPickle(self, pickle):
        unpickler = self._get_unpickler(pickle)
        classmeta = unpickler.load()
        state = unpickler.load()
        return classmeta, state

class CopyObjectWriter(ObjectWriter):

    def _persistent_id(self, obj):
        if isinstance(obj, CopyReference):
            return obj.ref
        else:
            return super(CopyObjectWriter, self)._persistent_id(obj)

class ObjectCopier:

    def __init__(self, jar, storage, created):
        self.oids = {}
        self._reader = CopyObjectReader(storage, created, self.oids)
        self._writer = CopyObjectWriter(jar)

    def close(self):
        self._writer.close()

    def copy(self, pickle):
        classmeta, state = self._reader.readPickle(pickle)
        data = self._writer._dump(classmeta, state)
        return data, findrefs(data)

def findrefs(p):
    f = StringIO(p)
    u = cPickle.Unpickler(f)
    u.persistent_load = L = []
    u.noload()
    try:
        u.noload()
    except EOFError, err:
        logging.warn("zodb: Bad pickled: %s", err)
    # Iterator over L and convert persistent references to simple oids.
    oids = []
    for ref in L:
        if isinstance(ref, tuple):
            oids.append(ref[0])
        else:
            oids.append(ref)
    return oids
