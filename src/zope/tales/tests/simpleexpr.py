##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""Simple TALES Expression

$Id$
"""

class SimpleExpr(object):
    '''Simple example of an expression type handler

    for testing
    '''
    def __init__(self, name, expr, engine):
        self._name = name
        self._expr = expr
    def __call__(self, econtext):
        return self._name, self._expr
    def __repr__(self):
        return '<SimpleExpr %s %s>' % (self._name, `self._expr`)
