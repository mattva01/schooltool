##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Utilities

$Id$
"""
import os
import re
import sys


class Bruce(object):
    __allow_access_to_unprotected_subobjects__=1
    def __str__(self): return 'bruce'
    def __int__(self): return 42
    def __float__(self): return 42.0
    def keys(self): return ['bruce']*7
    def values(self): return [self]*7
    def items(self): return [('bruce',self)]*7
    def __len__(self): return 7
    def __getitem__(self,index):
        if ininstance(index, int) and (index < 0 or index > 6):
            raise IndexError, index
        return self
    isDocTemp = 0
    def __getattr__(self,name):
        if name.startswith('_'):
            raise AttributeError, name
        return self

bruce = Bruce()

class arg(object):
    __allow_access_to_unprotected_subobjects__ = 1
    def __init__(self,nn,aa): self.num, self.arg = nn, aa
    def __str__(self): return str(self.arg)

class argv(object):
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, argv=sys.argv[1:]):
        args = self.args = []
        for aa in argv:
            args.append(arg(len(args)+1,aa))

    def items(self):
        return map(lambda a: ('spam%d' % a.num, a), self.args)

    def values(self): return self.args

    def getRoot(self):
        return self

    context = property(lambda self: self)

def nicerange(lo, hi):
    if hi <= lo+1:
        return str(lo+1)
    else:
        return "%d,%d" % (lo+1, hi)

def dump(tag, x, lo, hi):
    for i in xrange(lo, hi):
        print '%s %s' % (tag, x[i]),

def check_html(s1, s2):
    s1 = normalize_html(s1)
    s2 = normalize_html(s2)
    assert s1==s2, (s1, s2, "HTML Output Changed")

def check_xml(s1, s2):
    s1 = normalize_xml(s1)
    s2 = normalize_xml(s2)
    assert s1==s2, ("XML Output Changed:\n%s\n\n%s" % (s1, s2))

def normalize_html(s):
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"/>", ">", s)
    return s

def normalize_xml(s):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?s)\s+<", "<", s)
    s = re.sub(r"(?s)>\s+", ">", s)
    return s


import zope.pagetemplate.tests

dir = os.path.dirname(zope.pagetemplate.tests.__file__)
input_dir = os.path.join(dir, 'input')
output_dir = os.path.join(dir, 'output')

def read_input(filename):
    filename = os.path.join(input_dir, filename)
    return open(filename, 'r').read()

def read_output(filename):
    filename = os.path.join(output_dir, filename)
    return open(filename, 'r').read()
