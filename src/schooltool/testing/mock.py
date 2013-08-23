#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys, imp

from zope.testing import cleanup


class ModulesSnapshot(object):

    def __init__(self):
        self.originals = dict(sys.modules)
        self.faked_attrs = {}
        self.imported = set()

    def mock(self, values):
        """Usage:
        mock({'my.module.Foo': FooClass,
              'my.module.another.GLOBAL_VAL': 1,
              })
        """
        for full_name in sorted(values):
            names = full_name.split('.')
            attr_name = names[-1]
            module_name = '.'.join(names[:-1])
            assert module_name
            self.mock_attr(module_name, attr_name, fake=values[full_name])

    def mock_attr(self, modulename, name, fake=None):
        module = self.get_module(modulename)
        if modulename not in self.faked_attrs:
            self.faked_attrs[modulename] = {
                'injected': [],
                'replaced': {},
                }
        faked = self.faked_attrs[modulename]
        if hasattr(module, name):
            if (name not in faked['injected'] and
                name not in faked['replaced']):
                faked['replaced'][name] = getattr(module, name)
        else:
            faked['injected'].append(name)
        setattr(module, name, fake)

    def mock_module(self, modulename, fake=None):
        if fake is None:
            fake = imp.new_module(modulename)
        names = modulename.split('.')
        this_name = names[-1]
        parent_name = '.'.join(names[:-1])
        if parent_name:
            self.mock_attr(parent_name, this_name, fake)
        sys.modules[modulename] = fake
        self.imported.add(modulename)

    def get_module(self, modulename):
        try:
            sys.modules[modulename]
        except:
            self.mock_module(modulename)
        return sys.modules[modulename]

    def restore(self):
        for module_name, faked in self.faked_attrs.items():
            try:
                module = sys.modules[module_name]
            except:
                continue
            for name in faked['injected']:
                del module.__dict__[name]
            for name, old_value in faked['replaced'].items():
                setattr(module, name, old_value)

        for name in list(sys.modules):
            if name in self.imported:
                del sys.modules[name]
            elif name in self.originals:
                sys.modules[name] = self.originals[name]


_snapshot = None

def getSnapshot():
    global _snapshot
    if _snapshot is None:
        _snapshot = ModulesSnapshot()
    return _snapshot

def restoreModules():
    global _snapshot
    if _snapshot is not None:
        _snapshot.restore()
        _snapshot = None


cleanup.addCleanUp(restoreModules)


def module(module_name):
    """A decorator to put method or class to the given module."""
    snapshot = getSnapshot()
    if type(module_name) == type(sys):
        module_name = module_name.__name__
    def mock_something(something):
        name = getattr(something, '__name__', None)
        snapshot.mock_attr(module_name, name, fake=something)
        return something
    return mock_something


def fake_global(module_name, name, value):
    """Set a global variable to a module."""
    snapshot = getSnapshot()
    if type(module_name) == type(sys):
        module_name = module_name.__name__
    snapshot.mock_attr(module_name, name, fake=value)


def fake_module(module_name, other=None):
    """Replace a module with a fake one."""
    snapshot = getSnapshot()
    if type(module_name) == type(sys):
        module_name = module_name.__name__
    snapshot.mock_module(module_name, fake=other)
