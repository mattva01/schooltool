##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTLAR PURPOSE.
#
##############################################################################
"""Testing all XML Locale functionality.

$Id$
"""
import os
from unittest import TestCase, TestSuite, makeSuite

from zope.i18n.locales.xmlfactory import LocaleFactory
from zope.i18n.format import parseDateTimePattern, parseNumberPattern
import zope.i18n

class LocaleXMLFileTestCase(TestCase):
    """This test verifies that every locale XML file can be loaded."""

    def __init__(self, path):
        self.__path = path
        TestCase.__init__(self)
        
    def runTest(self):
        # Loading Locale object 
        locale = LocaleFactory(self.__path)()

        # Making sure all number format patterns parse
        for category in (u'decimal', u'scientific', u'percent', u'currency'):
            for length in getattr(locale.numbers, category+'Formats').values():
                for format in length.formats.values():
                    self.assert_(parseNumberPattern(format.pattern) is not None)

        # Making sure all datetime patterns parse
        for calendar in locale.dates.calendars.values():
            for category in ('date', 'time', 'dateTime'):
                for length in getattr(calendar, category+'Formats').values():
                    for format in length.formats.values():
                        self.assert_(
                            parseDateTimePattern(format.pattern) is not None)
                
                    

##def test_suite():
##    suite = TestSuite()
##    locale_dir = os.path.join(os.path.dirname(zope.i18n.__file__),
##                              'locales', 'data')
##    for path in os.listdir(locale_dir):
##        if not path.endswith(".xml"):
##            continue
##        path = os.path.join(locale_dir, path)
##        case = LocaleXMLFileTestCase(path)
##        suite.addTest(case)
##    return suite

# Note: These tests are disabled, just because they take a long time to run.
#       You should run these tests if you update the parsing code and/or
#       update the Locale XML Files.
def test_suite():
    return None
