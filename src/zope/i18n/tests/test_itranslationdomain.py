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
"""This is an 'abstract' test for the ITranslationDomain interface.

$Id$
"""
import unittest
from zope.interface.verify import verifyObject
from zope.interface import implements

from zope.component import getService
from zope.component.servicenames import Utilities
from zope.component.tests.placelesssetup import PlacelessSetup

from zope.i18n.negotiator import negotiator
from zope.i18n.interfaces import INegotiator, IUserPreferredLanguages
from zope.i18n.interfaces import ITranslationDomain

class Environment(object):

    implements(IUserPreferredLanguages)

    def __init__(self, langs=()):
        self.langs = langs

    def getPreferredLanguages(self):
        return self.langs

class TestITranslationDomain(PlacelessSetup):

    # This should be overwritten by every class that inherits this test
    def _getTranslationDomain(self):
        pass

    def setUp(self):
        super(TestITranslationDomain, self).setUp()
        self._domain = self._getTranslationDomain()

        # Setup the negotiator utility
        utilities = getService(Utilities)
        utilities.provideUtility(INegotiator, negotiator)        

    def testInterface(self):
        verifyObject(ITranslationDomain, self._domain)

    def testSimpleTranslate(self):
        translate = self._domain.translate
        eq = self.assertEqual
        # Test that a given message id is properly translated in a supported
        # language
        eq(translate('short_greeting', target_language='de'), 'Hallo!')
        # Same test, but use the context argument
        context = Environment(('de', 'en'))
        eq(translate('short_greeting', context=context), 'Hallo!')

    def testDynamicTranslate(self):
        translate = self._domain.translate
        eq = self.assertEqual
        # Testing both translation and interpolation
        eq(translate('greeting', mapping={'name': 'Stephan'},
                     target_language='de'),
           'Hallo Stephan, wie geht es Dir?')
        # Testing default value interpolation
        eq(translate('greeting', mapping={'name': 'Philipp'},
                     target_language='fr',
                     default="Hello $name, how are you?"),
           'Hello Philipp, how are you?')

    def testNoTranslation(self):
        translate = self._domain.translate
        eq = self.assertEqual
        # Test that an unknown message id returns None as a translation
        eq(translate('glorp_smurf_hmpf', target_language='en'),
           None)
        # Test default value behaviour
        eq(translate('glorp_smurf_hmpf', target_language='en',
                     default='Glorp Smurf Hmpf'),
           'Glorp Smurf Hmpf')

    def testNoTargetLanguage(self):
        translate = self._domain.translate
        eq = self.assertEqual
        # Test that default is returned when no language can be negotiated
        context = Environment(('xx', ))
        eq(translate('short_greeting', context=context, default=42), 42)

        # Test that default is returned when there's no destination language
        eq(translate('short_greeting', default=42), 42)


def test_suite():
    return unittest.TestSuite() # Deliberately empty
