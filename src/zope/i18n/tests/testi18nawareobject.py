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

from zope.i18n.interfaces import II18nAware
from zope.i18n.tests.testii18naware import TestII18nAware
from zope.interface import implements


class I18nAwareContentObject(object):

    implements(II18nAware)

    def __init__(self):
        self.content = {}
        self.defaultLanguage = 'en'

    def getContent(self, language):
        return self.content[language]

    def queryContent(self, language, default=None):
        return self.content.get(language, default)

    def setContent(self, content, language):
        self.content[language] = content

    ############################################################
    # Implementation methods for interface
    # II18nAware.py

    def getDefaultLanguage(self):
        'See II18nAware'
        return self.defaultLanguage

    def setDefaultLanguage(self, language):
        'See II18nAware'
        self.defaultLanguage = language

    def getAvailableLanguages(self):
        'See II18nAware'
        return self.content.keys()

    #
    ############################################################


class TestI18nAwareObject(TestII18nAware):

    def _createObject(self):
        object = I18nAwareContentObject()
        object.setContent('English', 'en')
        object.setContent('Lithuanian', 'lt')
        object.setContent('French', 'fr')
        return object

    def testSetContent(self):
        self.object.setContent('German', 'de')
        self.assertEqual(self.object.content['de'], 'German')

    def testGetContent(self):
        self.assertEqual(self.object.getContent('en'), 'English')
        self.assertRaises(KeyError, self.object.getContent, 'es')

    def testQueryContent(self):
        self.assertEqual(self.object.queryContent('en'), 'English')
        self.assertEqual(self.object.queryContent('es', 'N/A'), 'N/A')


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(TestI18nAwareObject)


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
