##############################################################################
#
# Copyright (c) 2002, 2003 Zope Corporation and Contributors.
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
"""Configuration data structure."""

import ZConfig

from ZConfig.datatypes import asBoolean


class Configuration:
    def __init__(self, container, type, name, url):
        self.container = container
        self.type = type
        self.name = name or None
        self.delegate = None
        self.url = url
        self._sections_by_name = {}
        self._sections = []
        self._data = {}

    def __repr__(self):
        klass = self.__class__
        classname = "%s.%s" % (klass.__module__, klass.__name__)
        if self.name:
            return "<%s for %s (type %s) at %#x>" \
                   % (classname, repr(self.name),
                      repr(self.type), id(self))
        elif self.type:
            return "<%s (type %s) at 0x%x>" \
                   % (classname, repr(self.type), id(self))
        else:
            return "<%s at 0x%x>" % (classname, id(self))

    def finish(self):
        pass

    def setDelegate(self, section):
        if self.delegate is not None:
            raise ZConfig.ConfigurationError("cannot modify delegation")
        self.delegate = section

    def addChildSection(self, section):
        """Add a section that is a child of this one."""
        if section.name:
            self.addNamedSection(section)
        elif not section.type:
            raise ValueError("'type' must be specified")
        self._sections.append(section)

    def addNamedSection(self, section):
        """Add a named section that may"""
        name = section.name
        type = section.type
        if not type:
            raise ValueError("'type' must be specified")
        key = type, name
        child = self._sections_by_name.get(key)
        if child is None or child.url != self.url:
            self._sections_by_name[key] = section
        else:
            raise ZConfig.ConfigurationError(
                "cannot replace existing named section")

    def getSection(self, type, name=None):
        # get section by name, relative to this section
        type = type.lower()
        if name:
            key = (type, name.lower())
            try:
                return self._sections_by_name[key]
            except KeyError:
                raise ZConfig.ConfigurationMissingSectionError(type, name)
        else:
            L = []
            for sect in self._sections:
                if sect.type == type:
                    L.append(sect)
            if len(L) > 1:
                raise ZConfig.ConfigurationConflictingSectionError(type, name)
            if L:
                return L[0]
            elif self.delegate:
                return self.delegate.getSection(type)
            else:
                return None

    def getChildSections(self, type=None):
        if type is None:
            return self._sections[:]
        else:
            type = type.lower()
            return [sect for sect in self._sections if sect.type == type]

    def addValue(self, key, value, position=None):
        # position is needed for interface compatibility, but isn't used here
        key = key.lower()
        try:
            self._data[key]
        except KeyError:
            self._data[key] = value
        else:
            raise ZConfig.ConfigurationError("cannot add existing key")

    def has_key(self, key):
        key = key.lower()
        have = self._data.has_key(key)
        if self.delegate and not have:
            have = self.delegate.has_key(key)
        return have

    def items(self):
        """Returns a list of key-value pairs for this section.

        The returned list includes pairs retrieved from the delegation chain.
        """
        if self.delegate is None:
            return self._data.items()
        else:
            L = [self._data]
            while self.delegate is not None:
                self = self.delegate
                L.append(self._data)
            d = L.pop().copy()
            L.reverse()
            for m in L:
                d.update(m)
            return d.items()

    def keys(self):
        if self.delegate is None:
            return self._data.keys()
        else:
            L1 = self.delegate.keys()
            L2 = self._data.keys()
            for k in L1:
                if k not in L2:
                    L2.append(k)
            return L2

    def get(self, key, default=None):
        key = key.lower()
        try:
            return self._data[key]
        except KeyError:
            if self.delegate is None:
                return default
            else:
                return self.delegate.get(key, default)

    def getbool(self, key, default=None):
        missing = []
        s = self.get(key, missing)
        if s is missing:
            return default
        else:
            return asBoolean(s)

    def getfloat(self, key, default=None, min=None, max=None):
        missing = []
        s = self.get(key, missing)
        if s is missing:
            return default
        x = float(self.get(key))
        self._check_range(key, x, min, max)
        return x

    def getint(self, key, default=None, min=None, max=None):
        missing = []
        s = self.get(key, missing)
        if s is missing:
            return default
        x = int(s)
        self._check_range(key, x, min, max)
        return x

    def _check_range(self, key, x, min, max):
        if min is not None and x < min:
            raise ValueError("value for %s must be at least %s, found %s"
                             % (repr(key), min, x))
        if max is not None and x > max:
            raise ValueError("value for %s must be no more than %s, found %s"
                             % (repr(key), max, x))

    def getlist(self, key, default=None):
        missing = []
        s = self.get(key, missing)
        if s is missing:
            return default
        else:
            return s.split()
