##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""A module used to test persistent module patching."""

from ZODB.utils import *

def aFunc():
    def nestedFunc():
        return aFunc
    return 1

class Foo(object):
    def meth(self):
        return 0

    class Nested(object):
        def bar(self):
            return 1

# put aFunc inside a function to be sure it is found
foo = (aFunc,)

class Bar:
    def bar(self, x):
        return 2 * x

    static = staticmethod(aFunc)
    alias = aFunc

    classbar = classmethod(bar)

class Sub(Bar):
    pass

def anotherFunc():
    class NotFound:
        pass


# import a module that won't be imported by something else:
from zodb.code.tests import tobeimportedbyatestmodule

