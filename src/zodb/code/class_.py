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
"""Persistent Classes."""

__metaclass__ = type

from zope.interface import implements
from persistent.cPersistence import UPTODATE, CHANGED, GHOST
from persistence.interfaces import IPersistent
from zodb.code.function import PersistentFunction

import time

# XXX There is a lot of magic here to give classes and instances
# separate sets of attributes.  This code should be documented, as it
# it quite delicate, and it should be move to a separate module.

class SimpleDescriptor(object):

    missing = object()

    def __init__(self, value):
        self._value = value

    def __get__(self, obj, cls):
        if self._value is self.missing:
            raise AttributeError
        return self._value

    def __set__(self, obj, value):
        self._value = value

    def __delete__(self, obj):
        if self._value is self.missing:
            raise AttributeError
        del self._value

class ExtClassDescr:
    """Maintains seperate class and instance descriptors for an attribute.

    This allows a class to provide methods and attributes without
    intefering with normal use of instances.  The class and its
    instances can each have methods with the same name.

    This does interfere with introspection on the class.
    """

    def __init__(self, name, instdescr):
        self.name = name
        self.instdescr = instdescr

    def __get__(self, obj, cls):
        if obj is None:
            return self.clsget(cls)
        else:
            return self.instdescr.__get__(obj, cls)

    def __set__(self, obj, val):
        if obj is None:
            self.clsset(val)
        else:
            if self.instdescr is None:
                raise AttributeError, self.name
            return self.instdescr.__set__(obj, val)

    def __delete__(self, obj):
        if self.instdescr is None:
            raise AttributeError, self.name
        return self.instdescr.__delete__(obj)

    # subclass should override

    def clsget(self, cls):
        pass

    def clsset(self, val):
        pass

    def clsdelete(self):
        pass

class MethodMixin:

    def __init__(self, name, descr, func):
        if not hasattr(descr, "__get__"):
            # If the object defined in the metaclass is not a descriptor,
            # create one for it.
            descr = SimpleDescriptor(descr)
        super(MethodMixin, self).__init__(name, descr)
        self.func = func

    def clsget(self, cls):
        def f(*args, **kwargs):
            try:
                return self.func(cls, *args, **kwargs)
            except TypeError:
                print `self.func`, `cls`, `args`, `kwargs`
                raise
        return f

class DataMixin:

    def __init__(self, name, descr, val):
        if not hasattr(descr, "__get__"):
            # If the object defined in the metaclass is not a descriptor,
            # create one for it.
            descr = SimpleDescriptor(descr)
        super(DataMixin, self).__init__(name, descr)
        self.val = val

    def clsget(self, cls):
        return self.val

    def clsset(self, val):
        self.val = val

    def clsdelete(self):
        del self.val

class ExtClassMethodDescr(MethodMixin, ExtClassDescr):
    pass

class ExtClassDataDescr(DataMixin, ExtClassDescr):
    pass

class ExtClassHookDataDescr(ExtClassDataDescr):
    # Calls a hook when clsset() is called.

    def __init__(self, name, descr, val, hook):
        super(ExtClassHookDataDescr, self).__init__(name, descr, val)
        self.hook = hook

    def clsset(self, val):
        self.val = val
        self.hook()

# The next three classes conspire to make a PersistentFunction
# behave like a method when found in a class's __dict__.

class PersistentMethod:
    """Make PersistentFunctions into methods."""
    def __init__(self, klass, inst, func):
        self.im_class = klass
        self.im_self = inst
        self.im_func = func

    def __repr__(self):
        if self.im_self is None:
            fmt = "<persistent unbound method %s.%s>"
        else:
            fmt = "<persistent bound method %%s.%%s of %s>" % (self.im_self,)
        return fmt % (self.im_class.__name__, self.im_func.__name__)

    def __call__(self, *args, **kwargs):
        if self.im_self is None:
            if not isinstance(args[0], self.im_class):
                raise TypeError("unbound method %s() must be called "
                                "with %s instance as first argument ("
                                "got %s instead)" % (self.im_func.__name__,
                                                     self.im_class.__name__,
                                                     type(args[0]).__name__))
        else:
            return self.im_func(self.im_self, *args, **kwargs)

class PersistentDescriptor:

    def __init__(self, objclass, func):
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__objclass__ = objclass
        self._func = func
        # Delegate __getstate__ and __setstate__ to the persistent func.
        # The patch module will use these methods to update persistent
        # methods in place.
        self.__getstate__ = func.__getstate__
        self.__setstate__ = func.__setstate__

    def __repr__(self):
        return "<persistent descriptor %s.%s>" % (self.__objclass__.__name__,
                                                  self.__name__)

    def __get__(self, object, klass=None):
        if object is None:
            return PersistentMethod(klass or self.__objclass__, None,
                                    self._func)
        else:
            return PersistentMethod(klass or self.__objclass__, object,
                                    self._func)


_missing = object()

def findattr(cls, attr, default):
    """Walk the mro of cls to find attr."""
    for c in cls.__mro__:
        o = c.__dict__.get(attr, _missing)
        if o is not _missing:
            return o
    return default

class StateChangeDataDescr(ExtClassDataDescr):
    # A data descriptor for _p_changed.
    pass

class PersistentClassMetaClass(type):

    # An attempt to make persistent classes look just like other
    # persistent objects by providing class attributes and methods
    # that behave like the persistence machinery.

    # The chief limitation of this approach is that class.attr won't
    # always behave the way it does for normal classes

    # A persistent class can never be a ghost, because there are too
    # many places where Python will attempt to inspect the class
    # without using getattr().  As a result, it would be impossible to
    # guarantee that the class would be unghostified at the right
    # time.  It's really difficult to guarantee this property without
    # help from the connection, because a ghost can't be unghosted
    # until after the connection sets its _p_jar.

    # The hack solution is to have a hook for _p_jar that activates
    # the object the first time it is set.

    #implements(IPersistent)
    __implements__ = IPersistent

    # A class is normally created in the UPTODATE state, but when a
    # new ghost is created for it the serialization machinery passes
    # GHOST instead of UPTODATE.  See __getnewargs__().

    def __new__(meta, name, bases, dict, state=UPTODATE):

        if "__dict__" in dict:
            del dict["__dict__"]
        cls = super(PersistentClassMetaClass, meta).__new__(
            meta, name, bases, dict)
        cls._pc_init = False

        # helper functions
        def extend_attr(attr, v):
            prev = findattr(cls, attr, SimpleDescriptor.missing)
            setattr(cls, attr, ExtClassDataDescr(attr, prev, v))

        def extend_meth(attr, m):
            prev = findattr(cls, attr, SimpleDescriptor.missing)
            setattr(cls, attr, ExtClassMethodDescr(attr, prev, m))

        extend_attr("_p_oid", None)
        extend_attr("_p_atime", time.time() % 86400)
        extend_attr("_p_state", state)
        extend_attr("_p_changed", None)
        extend_meth("_p_activate", meta._p_activate)
        extend_meth("_p_deactivate", meta._p_deactivate)
        # XXX _p_invalidate

        # Create a descriptor that calls _p_activate() when _p_jar is set.
        inst_jar_descr = findattr(cls, "_p_jar", None)
        setattr(cls, "_p_jar",
                ExtClassHookDataDescr("_p_jar", inst_jar_descr, None,
                                      getattr(cls, "_p_activate")))

        for k, v in dict.items():
            if isinstance(v, PersistentFunction):
                setattr(cls, k, PersistentDescriptor(cls, v))

        # A class could define any of these attributes, thus we
        # need to create extended descriptors so that the class
        # and its instances have separate versions.
        extend_meth("__getstate__", meta.__getstate__)
        extend_meth("__setstate__", meta.__setstate__)

        # Don't need this with interface geddon
        # extend_attr("__implements__", meta.__implements__)

        cls._pc_init = True
        return cls

    def __getattribute__(cls, name):
        # XXX I'm not sure I understand this code any more.
        super_meth = super(PersistentClassMetaClass, cls).__getattribute__

        # If we are initializing the class, don't trying to check variables
        # like _p_state, since they may not be initialized.
        if not super_meth("_pc_init"):
            return super_meth(name)
        if (name[0] != "_" or
            not (name.startswith("_p_") or name.startswith("_pc_") or
                 name == "__dict__")):
            if cls._p_state == GHOST:
                cls._p_activate()
                cls._p_atime = int(time.time() % 86400)
        return super_meth(name)

    # XXX There needs to be an _p_changed flag so that classes get
    # registered with the txn when they are modified.

    def __setattr__(cls, attr, val):
        if not attr.startswith("_pc_") and cls._pc_init:
            descr = cls.__dict__.get(attr)
            if descr is not None:
                set = getattr(descr, "__set__", None)
                if set is not None:
                    set(None, val)
##                    cls._p_changed = True
                    return
        super(PersistentClassMetaClass, cls).__setattr__(attr, val)

    def __delattr__(cls, attr):
        if attr.startswith('_p_'):
            # XXX what should happen with these?
            return
        super(PersistentClassMetaClass, cls).__delattr__(attr)

    def __repr__(cls):
        return "<persistent class %s.%s>" % (cls.__module__,
                                             cls.__name__)

    # It should be possible for getstate / setstate to deal with
    # arbitrary class attributes.  That goal is hard to achieve,
    # because there are several funny descriptors that need to
    # be handled specially.

    def __getstate__(cls):
        dict = {}

        for k in cls.__dict__.keys():
            v = getattr(cls, k)
            if isinstance(v, PersistentMethod):
                dict[k] = v.im_func
                continue
            if (k in ["__module__", "__weakref__", "__dict__"]
                or k.startswith("_p_") or k.startswith("_pc_")):
                continue
            # XXX The following test isn't right because overriding
            # must be allowed, but I haven't figured that out yet.
            # __getstate__ and __setstate__ might be overridden
            # __implements__ might be overridden
            if k in ["__getstate__", "__setstate__", "__implements__"]:
                continue
            dict[k] = v
        return dict

    def __setstate__(cls, dict):
        for k, v in dict.items():
            if isinstance(v, PersistentFunction):
                setattr(cls, k, PersistentDescriptor(cls, v))
            else:
                setattr(cls, k, v)

    # XXX Should the object get marked as a ghost when it is, in fact,
    # not a ghost?  The most obvious answer is no.  But if we don't
    # then we need some other attribute that can be used to handle
    # invalidations of classes and make _p_activate() work as expected.
    # Need to decide on a good answer.

    def _p_deactivate(cls):
        # do nothing but mark the state change for now
        cls._p_state = GHOST

    def _p_activate(cls):
        # The logic here is:
        # If the class hasn't finished executing __new__(), don't
        # try to load its state.
        # If the class has a jar but no oid, it's a new object
        # and doesn't have state in the database.

        if cls._p_state == GHOST and cls._pc_init:
            dm = cls._p_jar
            if dm is not None and cls._p_oid:
                cls._p_state = CHANGED
                try:
                    # XXX Make sure the object is in the cache before
                    # calling setstate().
                    dm._cache[cls._p_oid] = cls
                    dm.setstate(cls)
                finally:
                    # XXX Should really put in special inconsistent state
                    cls._p_state = UPTODATE
            else:
                print id(cls), "dm", dm, "oid", cls._p_oid

    # Methods below here are not wrapped to be class-only attributes.
    # They are available as methods of classes using this metaclass.

    def __getnewargs__(cls):
        # XXX This should really be _p_getnewargs() or something like that.

        # If the class is later loaded and unghostified, the arguments
        # passed to __new__() won't have an __module__.  It seems that
        # the module gets set to zodb.code.class_ in that case, which
        # is wrong.
        return (cls.__name__, cls.__bases__,
                {"__module__": cls.__module__}, GHOST)

    def _p_newstate(cls, acls):
        # Update a class's __dict__ in place.  Must use setattr and
        # delattr because __dict__ is a read-only proxy.
        # XXX This doesn't handle __methods__ correctly.

        # XXX I'm not sure how this is supposed to handle the
        # ExtClassDataDescrs.  As a hack, I'm deleting _p_oid
        # and _p_jar from the keys dict, because I know they
        # will be descrs and they won't change as a result of
        # update.  It appears that if the new class has a descr
        # that isn't set on the class, it will stomp on the old
        # class's value.  Not sure if this is a problem in general.
        
        def getkeys(cls):
            L = [n for n in cls.__dict__.keys()
                 if (not (n.startswith("__") and n.endswith("__"))
                     and not n.startswith("_p_"))
                 ]
            d = {}
            for elt in L:
                d[elt] = True
            return d
        oldnames = getkeys(cls)
        newnames = getkeys(acls)
        for name in oldnames:
            if not name in newnames:
                delattr(cls, name)
        for name in newnames:
            setattr(cls, name, acls.__dict__[name])

