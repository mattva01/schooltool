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
"""This is a test for the II18nAware interface.

$Id$
"""
import unittest

def sorted(list):
    list.sort()
    return list

class TestII18nAware(unittest.TestCase):

    def setUp(self):
        self.object = self._createObject()
        self.object.setDefaultLanguage('fr')

    def _createObject(self):
        # Should create an object that has lt, en and fr as available
        # languages
        pass

    def testGetDefaultLanguage(self):
        self.assertEqual(self.object.getDefaultLanguage(), 'fr')

    def testSetDefaultLanguage(self):
        self.object.setDefaultLanguage('lt')
        self.assertEqual(self.object.getDefaultLanguage(), 'lt')

    def testGetAvailableLanguages(self):
        self.assertEqual(sorted(self.object.getAvailableLanguages()), ['en', 'fr', 'lt'])


def test_suite():
    return unittest.TestSuite() # Deliberatly empty
