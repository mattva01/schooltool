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
"""Persistent functions."""

import dis
import new
import sys
# in 2.3, this will be spelled new.function and new.code
from types import FunctionType as function, CodeType as code

from persistence import Persistent

_STORE_GLOBAL = chr(dis.opname.index("STORE_GLOBAL"))

def has_side_effect(func):
    # will find this as an opcode or oparg
    return _STORE_GLOBAL in func.func_code.co_code

class CodeWrapper:
    """Package a code object so that it can be pickled."""

    nested = 0

    def __init__(self, co):
        consts = co.co_consts
        nested = [(i, c) for i, c in zip(range(len(consts)), consts)
                  if isinstance(c, code)]
        if nested:
            self.nested = 1
            L = list(consts)
            for i, c in nested:
                L[i] = CodeWrapper(c)
            consts = tuple(L)

        # args stores the arguments to new.code in order
        self.args = [co.co_argcount,
                     co.co_nlocals,
                     co.co_stacksize,
                     co.co_flags,
                     co.co_code,
                     consts,
                     co.co_names,
                     co.co_varnames,
                     co.co_filename,
                     co.co_name,
                     co.co_firstlineno,
                     co.co_lnotab,
                     co.co_freevars,
                     co.co_cellvars]

    def ascode(self):
        if self.nested:
            L = list(self.args[5])
            for i, elt in zip(range(len(L)), L):
                if isinstance(elt, CodeWrapper):
                    L[i] = elt.ascode()
            self.args[5] = tuple(L)
        return new.code(*self.args)

def get_code_args(co):
    """Return args from code object suitable for passing to constructor."""

class PersistentFunction(Persistent):

    def __init__(self, func, module):
        # Use _pf_ as the prefix to minimize the possibility that
        # these attribute names will conflict with function attributes
        # found in user code.  It would have been nice to use _p_
        # since it's already an reserved attribute prefix, but the
        # base persistent getattr function does not unghostify an
        # object on refences to _p_ attributes.
        self._pf_func = func
        self._v_side_effect = has_side_effect(func)
        self._pf_module = module
        self._pf_code = {}
        # Python doesn't provide enough rope to recreate a closure.  The
        # cell objects are opaque which means Python code can't extra
        # the objects from them or recreate them on unpickling.  In
        # principle this code be fixed with C code, but it should be
        # done in Python, not Zope.
        if func.func_code.co_freevars:
            raise TypeError, "persistent function can not have free variables"

    def __repr__(self):
        return "<PersistentFunction %s.%s>" % (self._pf_module.__name__,
                                               self._pf_func.func_name)

    # We need attribute hooks to handle access to _pf_ attributes in a
    # special way.  All other attributes should be looked up on
    # _pf_func.

    def __getattr__(self, attr):
        # If it wasn't found in __dict__, then it must be a function
        # attribute.
        return getattr(self._pf_func, attr)

    def __setattr__(self, attr, value):
        if not self._p_setattr(attr, value):
            # the persistence machinery didn't handle this attribute,
            # it must be ours
            if attr.startswith('_pf_'):
                self.__dict__[attr] = value
                if attr == "_pf_func":
                    self._v_side_effect = has_side_effect(self._pf_func)
            else:
                setattr(self._pf_func, attr, value)

    def __delattr__(self, attr):
        if not self._p_delattr(attr):
            # the persistence machinery didn't handle this attribute,
            # it must be ours
            if attr.startswith('_pf_'):
                del self.__dict__[attr]
            else:
                delattr(self._pf_func, attr)

    def __call__(self, *args, **kwargs):
        # We must make sure that _module is loaded when func is
        # executed because the function may reference a global
        # variable and that global variable must be in the module's
        # __dict__.  We can't use a PersistentDict because the
        # interpreter requires that globals be a real dict.
        self._pf_module._p_activate()

        # XXX What if the function module is deactivated while the
        # function is executing?  It seems like we need to expose
        # refcounts at the Python level to guarantee that this will
        # work.

        try:
            return self._pf_func(*args, **kwargs)
        finally:
            # If the func has a side-effect, the module must be marked
            # as changed.  We use the conservative approximation that
            # any function with a STORE_GLOBAL opcode has a
            # side-effect, regardless of whether a a particular call
            # of the function actually executes STORE_GLOBAL.

            # XXX Is this sufficient?
            if self._v_side_effect:
                self._pf_module._p_changed = True

    def __getstate__(self):
        # If func_dict is empty, store None to avoid creating a dict
        # unnecessarily when the function is unpickled
        # XXX new.function doesn't accept a closure
        func = self._pf_func
        func_state = func.func_defaults, func.func_dict or None

        # Store the code separately from the function
        code = func.func_code

        # The code object is can only be reused in an interpreter
        # running the same version of Python and with the same
        # __debug__ value.  Store code in a dict keyed by these two values.

        key = sys.version_info, __debug__
        if key not in self._pf_code:
            self._pf_code[key] = CodeWrapper(code)

        return func_state, self._pf_code, self._pf_module

    def __setstate__(self, (func, code, mod)):
        self._pf_code = code
        self._pf_module = mod

        # recreate the code object
        code = None
        key = sys.version_info, __debug__
        cowrap = self._pf_code.get(key, None)
        if cowrap is None:
            assert False, "not implemented yet"
        else:
            code = cowrap.ascode()

        func_defaults, func_dict = func
        if func_defaults:
            func = new.function(code, mod.__dict__, None, func_defaults)
        else:
            func = new.function(code, mod.__dict__)
        if func_dict:
            func.func_dict.update(func_dict)
        self._pf_func = func
        self._v_side_effect = has_side_effect(func)
