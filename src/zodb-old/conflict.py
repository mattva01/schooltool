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

# It's hard to draw a clear separation between these two modules,
# because conflict resolution depends (for efficiency and safety) on
# working with the raw object state instead of instantiated objects.

__metaclass__ = type

from cPickle import PicklingError
import logging

from zodb.interfaces import ConflictError
from zodb.serialize import BaseObjectReader, ObjectWriter
from zodb.interfaces import _fmt_oid
from zodb.utils import u64

ResolvedSerial = "rs"

class PersistentReference:

    __slots__ = "oid",

    def __init__(self, oid):
        self.oid = oid

# This class needs to deal with PersistentReference objects, instead of
# regular persistent objects.
class ResolvedObjectWriter(ObjectWriter):

    def _persistent_id(self, obj):
        if isinstance(obj, PersistentReference):
            return obj.oid
        else:
            return None

class ResolveObjectReader(BaseObjectReader):

    # The bad_classes attribute tracks all classes for which an
    # _p_resolveConflict() method could not be found.  It is used
    # to avoid repeating work to load classes when it is known
    # that they can't be imported or don't resolve conflicts.
    bad_classes = {}

    def __init__(self):
        self._refs = {}

    def _persistent_load(self, oid):
        ref = self._refs.get(oid)
        if ref is None:
            ref = self._refs[oid] = PersistentReference(oid)
        return ref

    def unresolvable(cls, klass):
        """Returns True if class does not support conflict resolution.

        The exact rules are implementation dependent.  This method was
        written to make testing easier.
        """
        # In a ZEO environment, this method isn't as useful.  If the
        # method is called from a client, it will always return False,
        # because the conflict resolution code runs on the server.

        # This method depends on the representation of class metadata
        # that is otherwise only used inside zodb.serialize.
        return (klass, None) in cls.bad_classes

    unresolvable = classmethod(unresolvable)

    def getClassMetadata(self, pickle):
        unpickler = self._get_unpickler(pickle)
        classmeta = unpickler.load()
        return classmeta

    def getResolver(self, pickle):
        # Get the conflict resolution method from a ghost rather
        # than actually instantiating the object.  _p_resolveConflict()
        # is really a static method.
        meta = self.getClassMetadata(pickle)
        if meta in self.bad_classes:
            return None
        try:
            ghost = self._new_object(*meta)
        except ImportError:
            # log failure to import?
            self.bad_classes[meta] = True
            return None
        if ghost is None:
            return None
        resolve = getattr(ghost, "_p_resolveConflict", None)
        if resolve is None:
            self.bad_classes[meta] = True
            return None
        else:
            return resolve

def get_self(method):
    # a method defined in Python
    self = getattr(method, "im_self", None)
    if self is not None:
        return self
    # a builtin method
    return getattr(method, "__self__")

class ConflictResolver:

    def __init__(self, storage):
        self._storage = storage

    def resolve(self, oid, committedSerial, oldSerial, newpickle,
                committedData=None):
        """Attempt to resolve conflict for object oid.

        Raises ConflictError if the conflict can no be resolved.  If
        the object oid defines an _p_resolveConflict() method, call it
        to resolve the conflict.
        """
        r = self._resolve(oid, committedSerial, oldSerial, newpickle,
                          committedData)
        if r is None:
            raise ConflictError(oid=oid,
                                serials=(committedSerial, oldSerial))
        return r

    def _resolve(self, oid, committedSerial, oldSerial, newpickle,
                 committedData):
        reader = ResolveObjectReader()
        resolve = reader.getResolver(newpickle)
        if resolve is None:
            return None
        newstate = reader.getState(newpickle)

        p = self._storage.loadSerial(oid, oldSerial)
        try:
            old = reader.getState(p)
        except (EOFError, PicklingError), err:
            logging.warn("CR: Error loading object: %s", err)
            return None
        if committedData is None:
            try:
                committedData = self._storage.loadSerial(oid, committedSerial)
            except KeyError:
                logging.debug("CR: Could not load committed state "
                              "oid=%s serial=%s" % (_fmt_oid(oid),
                                                    u64(committedSerial)))
                return None
        try:
            committed = reader.getState(committedData)
        except (EOFError, PicklingError), err:
            logging.warn("CR: Error loading object: %s", err)
            return None
        resolved = resolve(old, committed, newstate)

        writer = ResolvedObjectWriter()
        state = writer.getStateFromResolved(get_self(resolve), resolved)
        writer.close()
        return state
