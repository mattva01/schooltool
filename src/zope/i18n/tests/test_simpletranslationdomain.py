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
"""This module tests the regular persistent Translation Domain.

$Id$
"""
import unittest
from zope.i18n.simpletranslationdomain import SimpleTranslationDomain
from zope.i18n.tests.test_itranslationdomain import TestITranslationDomain


data = {
    ('en', 'short_greeting'): 'Hello!',
    ('de', 'short_greeting'): 'Hallo!',
    ('en', 'greeting'): 'Hello $name, how are you?',
    ('de', 'greeting'): 'Hallo $name, wie geht es Dir?'}


class TestSimpleTranslationDomain(unittest.TestCase, TestITranslationDomain):

    def setUp(self):
        TestITranslationDomain.setUp(self)

    def _getTranslationDomain(self):
        domain = SimpleTranslationDomain('default', data)
        return domain


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSimpleTranslationDomain))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
