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
"""Field equality tests

$Id$
"""
from unittest import TestCase, TestSuite, makeSuite
from zope.schema import Text, Int

class FieldEqualityTests(TestCase):

    equality = [
        'Text(title=u"Foo", description=u"Bar")',
        'Int(title=u"Foo", description=u"Bar")',
        ]

    def test_equality(self):
        for text in self.equality:
            self.assertEquals(eval(text), eval(text))

def test_suite():
    return TestSuite(
        [makeSuite(FieldEqualityTests)])
