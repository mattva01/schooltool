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
"""This module tests the LocaleProvider and everything that goes with it.

$Id$
"""
import os
import datetime
from unittest import TestCase, TestSuite, makeSuite

from zope.i18n.interfaces.locales import ILocaleProvider
from zope.i18n.locales import locales
from zope.i18n.locales.provider import LocaleProvider, LoadLocaleError

import zope.i18n
datadir = os.path.join(os.path.dirname(zope.i18n.__file__), 'locales', 'data')

class TestILocaleProvider(TestCase):
    """Test the functionality of an implmentation of the ILocaleProvider
    interface."""

    def _makeNewProvider(self):
        raise NotImplemented

    def setUp(self):
        self.locales = self._makeNewProvider()

    def testInterfaceConformity(self):
        self.assert_(ILocaleProvider.providedBy(self.locales))

    def test_getLocale(self):
        locale = self.locales.getLocale(None, None, None)
        self.assertEqual(locale.id.language, None)
        self.assertEqual(locale.id.territory, None)
        self.assertEqual(locale.id.variant, None)

        locale = self.locales.getLocale('en', None, None)
        self.assertEqual(locale.id.language, 'en')
        self.assertEqual(locale.id.territory, None)
        self.assertEqual(locale.id.variant, None)

        locale = self.locales.getLocale('en', 'US', None)
        self.assertEqual(locale.id.language, 'en')
        self.assertEqual(locale.id.territory, 'US')
        self.assertEqual(locale.id.variant, None)

        locale = self.locales.getLocale('en', 'US', 'POSIX')
        self.assertEqual(locale.id.language, 'en')
        self.assertEqual(locale.id.territory, 'US')
        self.assertEqual(locale.id.variant, 'POSIX')


class TestLocaleProvider(TestILocaleProvider):

    def _makeNewProvider(self):
        return LocaleProvider(datadir)

    def test_loadLocale(self):
        self.locales.loadLocale(None, None, None)
        self.assertEqual(self.locales._locales.keys(), [(None, None, None)])

        self.locales.loadLocale('en', None, None)
        self.assert_(('en', None, None) in self.locales._locales.keys())

    def test_loadLocaleFailure(self):
        self.assertRaises(LoadLocaleError, self.locales.loadLocale, 'zzz')


class TestLocaleAndProvider(TestCase):

    # Set the locale on the class so that test cases don't have
    # to pay to construct a new one each time.

    locales.loadLocale(None, None, None)
    locales.loadLocale('en', None, None)
    locales.loadLocale('en', 'US', None)
    locales.loadLocale('en', 'US', 'POSIX')
    locale = locales.getLocale('en', 'US', 'POSIX')

    def test_getTimeFormatter(self):
        formatter = self.locale.dates.getFormatter('time', 'medium')
        self.assertEqual(formatter.getPattern(), 'h:mm:ss a')
        self.assertEqual(formatter.format(datetime.time(12, 30, 10)),
                         '12:30:10 PM')
        self.assertEqual(formatter.parse('12:30:10 PM'),
                         datetime.time(12, 30, 10))

    def test_getDateFormatter(self):
        formatter = self.locale.dates.getFormatter('date', 'medium')
        self.assertEqual(formatter.getPattern(), 'MMM d, yyyy')
        self.assertEqual(formatter.format(datetime.date(2003, 01, 02)),
                         'Jan 2, 2003')
        self.assertEqual(formatter.parse('Jan 2, 2003'),
                         datetime.date(2003, 01, 02))

    def test_getDateTimeFormatter(self):
        formatter = self.locale.dates.getFormatter('dateTime', 'medium')
        self.assertEqual(formatter.getPattern(), 'MMM d, yyyy h:mm:ss a')
        self.assertEqual(
            formatter.format(datetime.datetime(2003, 01, 02, 12, 30)),
            'Jan 2, 2003 12:30:00 PM')
        self.assertEqual(formatter.parse('Jan 2, 2003 12:30:00 PM'),
                         datetime.datetime(2003, 01, 02, 12, 30))

    def test_getNumberFormatter(self):
        formatter = self.locale.numbers.getFormatter('decimal')
        self.assertEqual(formatter.getPattern(), '###0.###;-###0.###')
        self.assertEqual(formatter.format(1234.5678), '1234.568')
        self.assertEqual(formatter.format(-1234.5678), '-1234.568')
        self.assertEqual(formatter.parse('1234.567'), 1234.567)
        self.assertEqual(formatter.parse('-1234.567'), -1234.567)


class TestGlobalLocaleProvider(TestCase):

    def testLoading(self):
        locales.loadLocale(None, None, None)
        self.assert_(locales._locales.has_key((None, None, None)))
        locales.loadLocale('en', None, None)
        self.assert_(locales._locales.has_key(('en', None, None)))
        locales.loadLocale('en', 'US', None)
        self.assert_(locales._locales.has_key(('en', 'US', None)))
        locales.loadLocale('en', 'US', 'POSIX')
        self.assert_(locales._locales.has_key(('en', 'US', 'POSIX')))

    def test_getLocale(self):
        locale = locales.getLocale('en', 'GB')
        self.assertEqual(locale.id.language, 'en')
        self.assertEqual(locale.id.territory, 'GB')
        self.assertEqual(locale.id.variant, None)


def test_suite():
    return TestSuite((
        makeSuite(TestLocaleProvider),
        makeSuite(TestLocaleAndProvider),
        makeSuite(TestGlobalLocaleProvider),
        ))
