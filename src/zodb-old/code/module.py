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
"""Persistent Module."""

__metaclass__ = type

from zope.interface import implements

from persistence import Persistent
from persistence._persistence import GHOST
from zodb.code.interfaces import IPersistentModuleManager
from zodb.code.interfaces \
     import IPersistentModuleImportRegistry, IPersistentModuleUpdateRegistry
from zodb.code.patch import NameFinder, convert

# builtins are explicitly assigned when a module is unpickled
import __builtin__

# Modules aren't picklable by default, but we'd like them to be
# pickled just like classes (by name).
import copy_reg

def _pickle_module(mod):
    return _unpickle_module, (mod.__name__,)

def _unpickle_module(modname):
    mod = __import__(modname)
    if "." in modname:
        parts = modname.split(".")[1:]
        for part in parts:
            mod = getattr(mod, part)
    return mod

copy_reg.pickle(type(copy_reg), _pickle_module, _unpickle_module)

# XXX Is this comment still relevant?
#
# There seems to be something seriously wrong with a module pickle
# that contains objects pickled via save_global().  These objects are
# pickled using references to the module.  It appears that unpickling the
# object in the module causes the persistence machinery to fail.
#
# My suspicion is that the assignment to po_state before trying to
# load the state confuses things.  The first call to setstate attempts
# to reference an attribute of the module.  That getattr() fails because
# the module is not a ghost, but does have any empty dict.  Since
# that getattr() fails, its state can't be unpickled.
#
# Not sure what to do about this.

class PersistentModule(Persistent):

    def __init__(self, name):
        self.__name__ = name

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.__name__)

    # XXX need getattr &c. hooks to update _p_changed?
    # XXX what about code that modifies __dict__ directly?
    # XXX one example is a function that rebinds a global

    def __getstate__(self):
        d = self.__dict__.copy()
        try:
            del d["__builtins__"]
        except KeyError:
            pass
        return d

    def __setstate__(self, state):
        state["__builtins__"] = __builtin__
        self.__dict__.update(state)

class PersistentPackage(PersistentModule):
    # XXX Is it okay that these packages don't have __path__?

    # A PersistentPackage can exist in a registry without a manager.
    # It only gets a manager if someone creates an __init__ module for
    # the package.

    def __init__(self, name):
        self.__name__ = name

__persistent_module_registry__ = "__persistent_module_registry__"

def newModule(registry, name, source):
    """Return a manager object for a newly created module."""
    mgr = PersistentModuleManager(registry)
    mgr.new(name, source)
    return mgr


def compileModule(module, registry, source):
    # Try to prevent compilation errors from files without trailing
    # newlines.
    if source and source[-1] != "\n":
        source += "\n"
    module._p_changed = True
    moddict = module.__dict__
    old_names = NameFinder(module)
    moddict[__persistent_module_registry__] = registry
    # XXX need to be able to replace sys.std{in,out,err} at this point
    exec source in moddict
    # XXX and restore them here.
    del moddict[__persistent_module_registry__]
    new_names = NameFinder(module)
    replacements = new_names.replacements(old_names)
    convert(module, replacements)

class PersistentModuleManager(Persistent):

    implements(IPersistentModuleManager)

    def __init__(self, registry):
        self._registry = registry
        self._module = None
        self.name = None
        self.source = None

    def new(self, name, source):
        """Return a new module from a name and source text."""
        if self._module is not None:
            raise ValueError, "module already exists"
        if "." in name:
            parent = self._new_package(name)
        else:
            parent = None
            self._module = PersistentModule(name)
        try:
            self._registry.setModule(name, self._module)
        except ValueError:
            self._module = None
            raise
        self.name = name
        try:
            self.update(source)
        except:
            self._registry.delModule(name)
            raise
        if parent is not None:
            modname = name.split(".")[-1]
            setattr(parent, modname, self._module)

    def update(self, source):
        # Try to prevent compilation errors from files without trailing
        # newlines.
        compileModule(self._module, self._registry, source)
        self.source = source

    def remove(self):
        self._registry.delModule(self._module.__name__)
        self._module = None

    def _new_package(self, name):
        parent = self._get_parent(name)
        modname = name.split(".")[-1]
        if modname == "__init__":
            self._module = parent
            return None
        else:
            self._module = PersistentModule(name)
            return parent

    def _get_parent(self, name):
        # If a module is being created in a package, automatically
        # create parent packages that do no already exist.
        parts = name.split(".")[:-1]
        parent = None
        for i in range(len(parts)):
            if parts[i] == "__init__":
                raise ValueError, "__init__ can not be a package"
            pname = ".".join(parts[:i+1])
            package = self._registry.findModule(pname)
            if package is None:
                package = PersistentPackage(pname)
                self._registry.setModule(pname, package)
                if parent is not None:
                    setattr(parent, parts[i], package)
            elif not isinstance(package, PersistentPackage):
                raise ValueError, "%s is module" % pname
            parent = package
        return parent

class PersistentModuleImporter:
    """An import hook that loads persistent modules.

    The importer cooperates with other objects to make sure imports of
    persistent modules work correctly.  The default importer depends
    on finding a persistent module registry in the globals passed to
    __import__().  It looks for the name __persistent_module_registry__.
    A PersistentModuleManager places its registry in the globals used
    to exec module source.

    It is important that the registry be activated before it is used
    to handle imports.  If a ghost registry is used for importing, a
    circular import occurs.  The second import occurs when the
    machinery searches for the class of the registry.  It will re-use
    the registry and fail, because the registry will be marked as
    changed but not yet have its stated loaded.  XXX There ought to be
    a way to deal with this.
    """

    # The import hook doesn't use sys.modules, because Zope might want
    # to have placeful registries.  That is, a particular module might
    # execute in a context where there is more than one persistent
    # module registry active.  In this case, it isn't safe to use
    # sys.modules, because each registry could have a different binding
    # for a particular name.

    def __init__(self):
        self._saved_import = None

    def install(self):
        self._saved_import = __builtin__.__import__
        __builtin__.__import__ = self.__import__

    def uninstall(self):
        __builtin__.__import__ = self._saved_import

    def _import(self, registry, name, parent, fromlist):
        mod = None
        if parent is not None:
            fullname = "%s.%s" % (parent, name)
            mod = registry.findModule(fullname)
            if mod is None:
                parent = None
        if mod is None: # no parent or didn't find in parent
            mod = registry.findModule(name)
        if mod is None:
            return None
        if fromlist:
            if isinstance(mod, PersistentPackage):
                self._import_fromlist(registry, mod, fromlist)
            return mod
        else:
            i = name.find(".")
            if i == -1:
                return mod
            name = name[:i]
            if parent:
                name = "%s.%s" % (parent, name)
            top = registry.findModule(name)
            assert top is not None, "No package for module %s" % name
            return top

    def _import_fromlist(self, registry, mod, fromlist):
        for name in fromlist:
            if not hasattr(mod, name):
                fullname = "%s.%s" % (mod.__name__, name)
                self._import(registry, fullname, None, [])

    def __import__(self, name, globals={}, locals={}, fromlist=[]):
        registry = globals.get(__persistent_module_registry__)
        if registry is not None:
            mod = self._import(registry, name, self._get_parent(globals),
                               fromlist)
            if mod is not None:
                return mod
        return self._saved_import(name, globals, locals, fromlist)

    def _get_parent(self, globals):
        name = globals.get("__name__")
        if name is None or "." not in name:
            return None
        i = name.rfind(".")
        return name[:i]

class PersistentModuleRegistry(Persistent):
    """A collection of persistent modules.

    The registry is similar in purpose to sys.modules.  A persistent
    module manager stores its modules in a registry, and the importer
    looks for them there.
    """

    implements(IPersistentModuleImportRegistry,
               IPersistentModuleUpdateRegistry)

    def __init__(self):
        self._modules = {}

    def findModule(self, name):
        assert self._p_state != GHOST
        return self._modules.get(name)

    def setModule(self, name, module):
        if name in self._modules:
            # The name is already in use.
            # XXX should raise a better error
            raise ValueError, name
        self._p_changed = True
        self._modules[name] = module

    def delModule(self, name):
        self._p_changed = True
        del self._modules[name]

    def modules(self):
        """Return a list of the modules in the registry."""
        return self._modules.keys()
    
class ManagedRegistry(PersistentModuleRegistry):
    """A collection of persistent modules and their managers.

    An extension of the persistent module registry that also collects
    the managers.  For persistent modules to be useful, the managers
    must be stored in the database.  This registry stores managers
    as well as their modules, so that all objects related to the modules
    in the registry are reachable from the registry.
    """

    def __init__(self):
        super(ManagedRegistry, self).__init__()
        self._mgrs = {}

    def newModule(self, name, source):
        mgr = PersistentModuleManager(self)
        mgr.new(name, source)
        self._p_changed = True
        self._mgrs[name] = mgr

    def updateModule(self, name, source):
        self._mgrs[name].update(source)

    def removeModule(self, name):
        self._mgrs[name].remove()
        self._p_changed = True
        del self._mgrs[name]
