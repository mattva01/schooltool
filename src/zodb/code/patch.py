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
"""Patch references to auto-persistent objects in a module.

When a persistent module is compiled, all classes and functions should
be converted to persistent classes and functions.  When a module is
updated, it is compiled and its persistent functions and classes are
updated in place so that clients of the module see the update.

The specific semantics of the convert and update-in-place operations
are still being determined.  Here are some rough notes:

- Classes and functions are not converted in place.  New objects are
  created to replace the builtin functions and classes.

- Every function object is converted to a PersistentFunction.

- Every class is converted to a new class that is created by calling
  the PersistentClassMetaClass with the name, bases, and dict of the
  class being converted.

- The conversion operation must preserve object identity.  If an
  object created by a def or class statement is referenced elsewhere
  in the module, all references must be replaced with references to
  the converted object.

Implementation notes:

The conversion operation is implemented using a pickler.  It wasn't
possible to use the copy module, because it isn't possible to extend
the copy module in a safe way.  The copy module depends on module globals.

The pickler uses a Wrapper object that creates the appropriate new
object or updates an old one when it is unpickled.  The wrapper also
causes parts of the wrapped object's state to be traversed by the
pickler, for example the func_defaults of a function object.  This
traversal is necessary because references to convertable objects could
be contained in the state and must be updated to refer to the new
objects.

What semantics do we want for update-in-place in the presence of aliases?

Semantics based on per-namespace updates don't work in the presence of
aliases.  If an update changes an alias, then the old binding will be
updated with the state of the new binding.

Semantics based on containing namespaces seem to work.  The outermost
namespace that contains a name is updated in place.  Aliases are
simple rebinding operations that do not update in place.

The containment approach seems to have a problem with bound methods,
where an instance can stash a copy of a bound method created via an
alias.  When the class is updated, the alias changes, but the bound
method isn't.  Then the bound method can invoke an old method on a new
object, which may not be legal.  It might sufficient to outlaw this case.

XXX Open issues

Can we handle metaclasses within this framework?  That is, what if an
object's type is not type, but a subclass of type.

How do we handle things like staticmethods?  We'd like the code to be
able to use them, but Python doesn't expose an introspection on them.

What if the same object is bound to two different names in the same
namespace?  Example:
    x = lambda: 1
    y = x
If the module is updated to:
    x = lambda: 1
    y = lambda: 2
What are the desired semantics?
"""

__metaclass__ = type

from copy_reg import dispatch_table
from cStringIO import StringIO
import pickle
import sys
from types import *

from zodb.code.class_ import PersistentClassMetaClass, PersistentDescriptor
from zodb.code.function import PersistentFunction

class Wrapper:
    """Implement pickling reduce protocol for update-able object.

    The Pickler creates a Wrapper instance and uses it as the reduce
    function.  The Unpickler calls the instance to recreate the
    object.
    """
    __safe_for_unpickling__ = True

    def __init__(self, obj, module, replace=None):
        self._obj = obj
        self._module = module
        self._replace = replace

    def __call__(self, *args):
        new = self.unwrap(*args)
        if self._replace is not None:
            # XXX Hack: Use _p_newstate for persistent classes, because
            # a persistent class's persistent state is a fairly limited
            # subset of the dict and we really want to replace everything.
            if hasattr(self._replace, "_p_newstate"):
                self._replace._p_newstate(new)
            else:
                self._replace.__setstate__(new.__getstate__())
            return self._replace
        else:
            return new

class FunctionWrapper(Wrapper):

    def unwrap(self, defaults, dict):
        self._obj.func_defaults = defaults
        self._obj.func_dict.update(dict)
        return PersistentFunction(self._obj, self._module)

class TypeWrapper(Wrapper):

    def unwrap(self, bases, dict):
        return PersistentClassMetaClass(self._obj.__name__, bases, dict)

def registerWrapper(atype, wrapper, unwrap_args, getstate=None):
    """Register a patch wrapper for an external object type."""
    Pickler.dispatch[atype] = Pickler.save_external
    Pickler.external[atype] = wrapper, unwrap_args, getstate

marker = object()

_module_cache = {}

def whichmodule(func, funcname):
    """Return a likely candidate for the module that defines obj,
    where context is the name of the module in which obj was found.

    Use a trick suggested by Guido to make sure we found the right
    module: Compare the function's globals with the module's globals.
    You've found the right module only when they match.
    """
    mod = getattr(func, "__module__", None)
    if mod is not None:
        return mod
    mod = _module_cache.get(func)
    if mod is not None:
        return mod
    for name, module in sys.modules.items():
        if module is None:
            continue # skip dummy package entries
        if getattr(module, funcname, None) is func:
            if module.__dict__ is func.func_globals:
                break
    else:
        name = '__main__'
    _module_cache[func] = name
    return name
    

class Pickler(pickle.Pickler):

    dispatch = pickle.Pickler.dispatch.copy()

    def __init__(self, file, module, memo, replacements):
        # The pickler must be created in binary mode, because
        # it pickles instances using the OBJ code.  The text-mode
        # pickler uses a different strategy that explicitly
        # stores the name of the instance's class which defeats
        # the desire to replace references to classes with
        # persistent classes.
        pickle.Pickler.__init__(self, file, bin=True)
        
        self._pmemo = memo
        self._wrapped = {} # set of objects already wrapped
        self._module = module
        self._module_name = module.__name__
        self._repl = replacements
        self._builtins = module.__builtins__

    def wrap(self, wrapperclass, obj):
        return wrapperclass(obj, self._module, self._repl.get(id(obj)))

    def persistent_id(self, obj, force=False):
        if (isinstance(obj, Wrapper)
            or isinstance(obj, ModuleType)
            or obj is self._builtins
            or force):
            oid = id(obj)
            self._pmemo[oid] = obj
            return oid
        else:
            # If the object is a real persistent object, patch it by
            # persistent id, too.  This case is specifically intended
            # to catch persistent classes imported from other modules.
            # They are classes, but can't be pickled as globals because
            # pickle looks in sys.modules and the persistent import
            # doesn't use sys.modules.

            # If we find a class, pickle it via save_type()
            if isinstance(obj, PersistentClassMetaClass):
                return None
            
            # XXX Is this safe in all cases?
            oid = getattr(obj, "_p_oid", marker)
            if oid is marker:
                return None
            elif oid is None:
                # It's a persistent object, but it's newly created.
                oid = object()
            descr = getattr(oid, "__get__", None)
            if descr is not None:
                return None
            self._pmemo[oid] = obj
            return oid

    def save_type(self, atype):
        if atype.__module__ == self._module_name:
            self.save_reduce(self.wrap(TypeWrapper, atype),
                             (atype.__bases__, atype.__dict__),
                             obj=atype)
        else:
            if isinstance(atype, PersistentClassMetaClass):
                self.save_pers(self.persistent_id(atype, True))
            else:
                self.save_global(atype)

    dispatch[TypeType] = save_type
    dispatch[ClassType] = save_type
    dispatch[type] = save_type
    dispatch[PersistentClassMetaClass] = save_type

    def save_function(self, func):
        modname = whichmodule(func, func.__name__)
        if modname == self._module_name or modname == "__main__":
            self.save_reduce(self.wrap(FunctionWrapper, func),
                             (func.func_defaults, func.func_dict),
                             obj=func)
        else:
            self.save_global(func)

    dispatch[FunctionType] = save_function

    external = {}

    def save_external(self, obj):
        # XXX Will this object always have an __module__?
        if obj.__module__ == self._module_name:
            # Save an external type registered through registerWrapper
            objtype = type(obj)
            wrapper, unwrap_args, getstate = self.external[objtype]
            if getstate is not None:
                self.save_reduce(self.wrap(wrapper, obj), unwrap_args(obj),
                                 getstate(obj),
                                 obj=obj)
            else:
                self.save_reduce(self.wrap(wrapper, obj), unwrap_args(obj),
                                 obj=obj)
        else:
            # In general, we don't know how to pickle this object,
            # so pickle it by reference to the original.
            self.save_pers(self.persistent_id(obj, True))

    # New-style classes don't have real dicts.  They have dictproxies.
    # There's no official way to spell the dictproxy type, so we have
    # to get it by using type() on an example.
    dispatch[type(Wrapper.__dict__)] = pickle.Pickler.save_dict

    def save(self, obj, ignore=None):
        # Override the save() implementation from pickle.py, because
        # we don't ever want to invoke __reduce__() on builtin types
        # that aren't picklable.  Instead, we'd like to pickle all of
        # those objects using the persistent_id() mechanism.  There's
        # no need to cover every type with this pickler, because it
        # isn't being used for persistent just to create a copy.

        # The ignored parameter is for compatible with Python 2.2,
        # which has the old inst_persistent_id feature.
        pid = self.persistent_id(obj)
        if pid is not None:
            self.save_pers(pid)
            return

        d = id(obj)
        t = type(obj)
        if (t is TupleType) and (len(obj) == 0):
            if self.bin:
                self.save_empty_tuple(obj)
            else:
                self.save_tuple(obj)
            return

        if d in self.memo:
            self.write(self.get(self.memo[d][0]))
            return

        try:
            f = self.dispatch[t]
        except KeyError:
            try:
                issc = issubclass(t, TypeType)
            except TypeError: # t is not a class
                issc = 0
            if issc:
                self.save_global(obj)
                return

            try:
                reduce = dispatch_table[t]
            except KeyError:
                self.save_pers(self.persistent_id(obj, True))
                return
            else:
                tup = reduce(obj)

            if type(tup) is StringType:
                self.save_global(obj, tup)
                return
            if type(tup) is not TupleType:
                raise pickle.PicklingError("Value returned by %s must be a "
                                           "tuple" % reduce)

            l = len(tup)
            if (l != 2) and (l != 3):
                raise pickle.PicklingError("tuple returned by %s must "
                                           "contain only two or three "
                                           "elements" % reduce)

            callable = tup[0]
            arg_tup  = tup[1]
            if l > 2:
                state = tup[2]
            else:
                state = None

            if type(arg_tup) is not TupleType and arg_tup is not None:
                raise pickle.PicklingError("Second element of tuple "
                                           "returned by %s must be a "
                                           "tuple" % reduce)

            self.save_reduce(callable, arg_tup, state, obj=obj)
            return

        f(self, obj)

    def save_reduce(self, callable, arg_tup, state = None, obj = None):
        write = self.write
        save = self.save

        save(callable)
        save(arg_tup)
        write(pickle.REDUCE)

        if obj is not None:
            memo_len = len(self.memo)
            self.write(self.put(memo_len))
            self.memo[id(obj)] = (memo_len, obj)

        if state is not None:
            save(state)
            write(pickle.BUILD)

class Unpickler(pickle.Unpickler):

    def __init__(self, file, pmemo):
        pickle.Unpickler.__init__(self, file)
        self._pmemo = pmemo

    def persistent_load(self, oid):
        return self._pmemo[oid]

class NameFinder:
    """Find a canonical name for each update-able object."""

    # XXX should we try to handle descriptors?  If it looks like a
    # descriptor, try calling it and passing the class object?

    classTypes = {
        TypeType: True,
        ClassType: True,
        PersistentClassMetaClass: True,
        }

    types = {
        FunctionType: True,
        PersistentFunction: True,
        PersistentDescriptor: True,
        }
    types.update(classTypes)

    def __init__(self, module):
        self._names = {} # map object ids to (canonical name, obj) pairs
        self.walkModule(module)

    def names(self):
        return [n for n, o in self._names.itervalues()]

    def _walk(self, obj, name, fmt):
        classes = []
        for k, v in obj.__dict__.items():
            aType = type(v)
            anId = id(v)
            if aType in self.types and not anId in self._names:
                self._names[anId] = fmt % (name, k), v
                if aType in self.classTypes:
                    classes.append((v, k))
        for _klass, _name in classes:
            self.walkClass(_klass, fmt % (name, _name))

    def walkModule(self, mod):
        self._walk(mod, "", "%s%s")

    def walkClass(self, klass, name):
        self._walk(klass, name, "%s.%s")

    def replacements(self, aFinder):
        """Return a dictionary of replacements.

        self and aFinder are two NameFinder instances.  Return a dict
        of all the objects in the two that share the same name.  The
        keys are the ids in self and the values are the objects in
        aFinder.
        """
        temp = {}
        result = {}
        for anId, (name, obj) in self._names.iteritems():
            temp[name] = anId
        for anId, (name, obj) in aFinder._names.iteritems():
            if name in temp:
                result[temp[name]] = obj
        return result

def convert(module, replacements):
    """Convert object to persistent objects in module.

    Use replacements dictionary to determine which objects to update
    in place.
    """
    f = StringIO()
    memo = {}
    p = Pickler(f, module, memo, replacements)
    moddict = module.__dict__
    p.dump(moddict)
    f.seek(0)
    u = Unpickler(f, memo)
    newdict = u.load()
    module.__dict__.clear()
    module.__dict__.update(newdict)

if __name__ == "__main__":
    pass
