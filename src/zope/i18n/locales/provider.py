##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
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
"""Locale Provider

The Locale Provider looks up locales and loads them from the XML data, if
necessary.

$Id$
"""
import os
from zope.interface import implements
from zope.i18n.interfaces.locales import ILocaleProvider

class LoadLocaleError(Exception):
    """This error is raised if a locale cannot be loaded."""


class LocaleProvider(object):
    """A locale provider that get's its data from the XML data."""

    implements(ILocaleProvider)

    def __init__(self, locale_dir):
        self._locales = {}
        self._locale_dir = locale_dir

    def loadLocale(self, language=None, country=None, variant=None):
        """See zope.i18n.interfaces.locales.ILocaleProvider"""
        # Creating the filename
        if language == None and country == None and variant == None:
            filename = 'root.xml'
        else:
            filename = language
            if country is not None:
                filename += '_'+country
            if variant is not None:
                if '_' not in filename:
                    filename += '_'
                filename += '_'+variant
            filename += '.xml'

        # Making sure we have this locale
        path = os.path.join(self._locale_dir, filename)
        if not os.path.exists(path):
            raise LoadLocaleError, \
                  'The desired locale is not available.\nPath: %s' %path

        # Import here to avoid circular imports
        from zope.i18n.locales.xmlfactory import LocaleFactory

        # Let's get it!
        locale = LocaleFactory(path)()
        self._locales[(language, country, variant)] = locale

    def getLocale(self, language=None, country=None, variant=None):
        """See zope.i18n.interfaces.locales.ILocaleProvider"""
        # We want to be liberal in what we accept, but the standard is lower
        # case language codes, upper case country codes, and upper case
        # variants, so coerce case here.
        if language:
            language = language.lower()
        if country:
            country = country.upper()
        if variant:
            variant = variant.upper()
        if not self._locales.has_key((language, country, variant)):
            self.loadLocale(language, country, variant)
        return self._locales[(language, country, variant)]
