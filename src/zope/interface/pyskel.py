#!/usr/bin/env python
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
"""
Generate method skeletons for intefaces.

Usage: python pyskel.py dotted_name

Example:

    cd lib/python
    python zope/interface/pyskel.py zope.app.interfaces.pigs.IPigService

The dotted name is the module name and interface object name connected
with a dot.

Revision information: $Id: pyskel.py,v 1.5 2004/01/14 22:55:30 chrism Exp $
"""

import sys, os, re

sys.path.insert(0, os.getcwd())

from types import ModuleType
from zope.interface.interface import Method
from zope.interface import Attribute

class_re = re.compile(r'\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)')
def_re = re.compile(r'\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)')
attr_re = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*Attribute')


def rskel(iface, top, print_iface=1):
    name = "%s.%s" % (iface.__module__, iface.__name__)

    file = resolve(iface.__module__).__file__
    if file.endswith('pyc'):
        file = file[:-1]
    order = guessOrder(open(file))
    namesAndDescriptions =  getAttributesInOrder(iface, order)

    namesAndDescriptions = filter(lambda ades:
                                  isinstance(ades[1], Method) or
                                  isinstance(ades[1], Attribute),
                                  namesAndDescriptions)

    for aname, ades in namesAndDescriptions:
        if isinstance(ades, Method):
            sig = ades.getSignatureString()[1:-1]
            if sig: sig = "self, %s" % sig
            else:   sig = "self"
            print
            print "    def %s(%s):" % (aname, sig)
            print '        "See %s"' % name

        elif isinstance(ades, Attribute):
            print
            print "    # See %s" % name
            print "    %s = None" %aname

        else:
            print
            print 'Waaaa', ades

    for base in iface.__bases__:
        if base.__name__ not in ('Interface',):
            rskel(base, top)

def skel(name):
    iface = resolve(name)
    class_name = iface.__name__
    if class_name.startswith('I'):
        class_name = class_name[1:]
    print "from zope.interface import implements"
    print "from %s import %s" % (iface.__module__, iface.getName())
    print
    print "class %s:" %class_name
    print "    __doc__ = %s.__doc__" % iface.getName()
    print
    print "    implements(%s)" %iface.getName()
    print

    rskel(iface, iface, 0)


def resolve(name, _silly=('__doc__',), _globals={}):
    # Support for file path syntax; this way I can use TAB to search for
    # the module.
    if '/' in name or name.endswith('.py'):
        # We got a relative path. Let's try to get the full one and then
        # make a package path out of it.
        if not name.startswith('/'):
            cwd = os.getcwd()
            for path in sys.path[1:]: # Yeah, we need to exclude the cwd itself
                path = str(path)
                if path != '' and cwd.startswith(path):
                    name = os.path.join(cwd[len(path)+1:], name)
                    name = os.path.normpath(name)
                    break

        # get rid of the file ending :)
        if name.endswith('.py'):
            name = name[:-3]
        name = name.replace('/', '.')

    # Now to the regular lookup
    if name[:1]=='.':
        name = 'zopeproducts' + name

    if name[-1:] == '.':
        name = name[:-1]
        repeat = 1
    else:
        repeat = 0

    names=name.split('.')
    last=names[-1]
    mod='.'.join(names[:-1])

    while 1:
        m=__import__(mod, _globals, _globals, _silly)
        try:
            a=getattr(m, last)
        except AttributeError:
            pass
        else:
            if not repeat or (type(a) is not ModuleType):
                return a
        mod += '.' + last


def guessOrder(source_file):
    order = {}  # { class name -> list of methods }
    lines = source_file.readlines()
    class_name = None
    for line in lines:
        m = class_re.match(line)
        if m and m.groups():
            class_name = m.groups()[0]
        else:
            for m in (def_re.match(line),
                      attr_re.match(line)):
                if m and m.groups():
                    def_name = m.groups()[0]
                    name_order = order.get(class_name)
                    if name_order is None:
                        name_order = []
                        order[class_name] = name_order
                    name_order.append(def_name)

    return order


def getAttributesInOrder(interface, order):
    # order is the dictionary returned from guessOrder().
    # interface is a metaclass-based interface object.
    name_order = order.get(interface.getName())

    if name_order is None:
        # Something's wrong.  Oh well.
        items = interface.namesAndDescriptions()
        items.sort()
        return items
    else:
        items = []
        for key, value in interface.namesAndDescriptions():
            if key in name_order:
                items.append((name_order.index(key), key, value))
            else:
                items.append((99999, key, value))  # Go to end.
        items.sort()
        return map(lambda item: item[1:], items)



if __name__ == '__main__':
    for a in sys.argv[1:]:
        skel(a)
