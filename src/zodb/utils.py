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
from zodb.timestamp import TimeStamp
import struct
import time

def p64(v):
    """Pack an integer or long into a 8-byte string"""
    return struct.pack(">Q", v)

def u64(v):
    """Unpack an 8-byte string into a 64-bit long integer."""
    return struct.unpack(">Q", v)[0]

def cp(f1, f2, l):
    read = f1.read
    write = f2.write
    n = 8192

    while l > 0:
        if n > l:
            n = l
        d = read(n)
        if not d:
            break
        write(d)
        l = l - len(d)

try:
    from sets import Set
except ImportError:
    # This must be Python 2.2, which doesn't have a standard sets module.
    # ZODB needs only a very limited subset of the Set API.
    class Set(dict):
        def __init__(self, arg=None):
            if arg:
                if isinstance(arg, dict):
                    self.update(arg)
                else:
                    # XXX the proper sets version is much more robust
                    for o in arg:
                        self[o] = 1
        def add(self, o):
            self[o] = 1
        def remove(self, o):
            del self[o]
        def __ior__(self, other):
            if not isinstance(other, Set):
                return NotImplemented
            self.update(other)
            return self

