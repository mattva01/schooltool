##############################################################################
#
# Copyright (c) 2002, 2003 Zope Corporation and Contributors.
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
"""This module tests the Formats and everything that goes with it.

$Id$
"""
import os
import datetime
from unittest import TestCase, TestSuite, makeSuite

from zope.i18n.interfaces import IDateTimeFormat
from zope.i18n.format import DateTimeFormat
from zope.i18n.format import parseDateTimePattern, buildDateTimeParseInfo
from zope.i18n.format import DateTimePatternParseError, DateTimeParseError

from zope.i18n.interfaces import INumberFormat
from zope.i18n.format import NumberFormat
from zope.i18n.format import parseNumberPattern

class LocaleStub(object):
    pass

class LocaleCalendarStub(object):

    type = u'gregorian'

    months = { 1: ('Januar', 'Jan'),     2: ('Februar', 'Feb'),
               3: ('Maerz', 'Mrz'),      4: ('April', 'Apr'),
               5: ('Mai', 'Mai'),        6: ('Juni', 'Jun'),
               7: ('Juli', 'Jul'),       8: ('August', 'Aug'),
               9: ('September', 'Sep'), 10: ('Oktober', 'Okt'),
              11: ('November', 'Nov'),  12: ('Dezember', 'Dez')}

    days = {1: ('Montag', 'Mo'), 2: ('Dienstag', 'Di'),
            3: ('Mittwoch', 'Mi'), 4: ('Donnerstag', 'Do'),
            5: ('Freitag', 'Fr'), 6: ('Samstag', 'Sa'),
            7: ('Sonntag', 'So')}

    am = 'vorm.'
    pm = 'nachm.'

    eras = {1: (None, 'v. Chr.'), 2: (None, 'n. Chr.')}

    def getMonthNames(self):
        return [self.months.get(type, (None, None))[0] for type in range(1, 13)]

    def getMonthTypeFromName(self, name):
        for item in self.months.items():
            if item[1][0] == name:
                return item[0]

    def getMonthAbbreviations(self):
        return [self.months.get(type, (None, None))[1] for type in range(1, 13)]

    def getMonthTypeFromAbbreviation(self, abbr):
        for item in self.months.items():
            if item[1][1] == abbr:
                return item[0]

    def getDayNames(self):
        return [self.days.get(type, (None, None))[0] for type in range(1, 8)]

    def getDayTypeFromName(self, name):
        for item in self.days.items():
            if item[1][0] == name:
                return item[0]

    def getDayAbbreviations(self):
        return [self.days.get(type, (None, None))[1] for type in range(1, 8)]

    def getDayTypeFromAbbreviation(self, abbr):
        for item in self.days.items():
            if item[1][1] == abbr:
                return item[0]


class TestDateTimePatternParser(TestCase):
    """Extensive tests for the ICU-based-syntax datetime pattern parser."""

    def testParseSimpleTimePattern(self):
        self.assertEqual(parseDateTimePattern('HH'),
                         [('H', 2)])
        self.assertEqual(parseDateTimePattern('HH:mm'),
                         [('H', 2), ':', ('m', 2)])
        self.assertEqual(parseDateTimePattern('HH:mm:ss'),
                         [('H', 2), ':', ('m', 2), ':', ('s', 2)])
        self.assertEqual(parseDateTimePattern('mm:ss'),
                         [('m', 2), ':', ('s', 2)])
        self.assertEqual(parseDateTimePattern('H:m:s'),
                         [('H', 1), ':', ('m', 1), ':', ('s', 1)])

    def testParseGermanTimePattern(self):
        # German full
        self.assertEqual(parseDateTimePattern("H:mm' Uhr 'z"),
                         [('H', 1), ':', ('m', 2), ' Uhr ', ('z', 1)])
        # German long
        self.assertEqual(parseDateTimePattern("HH:mm:ss z"),
                         [('H', 2), ':', ('m', 2), ':', ('s', 2), ' ',
                          ('z', 1)])
        # German medium
        self.assertEqual(parseDateTimePattern("HH:mm:ss"),
                         [('H', 2), ':', ('m', 2), ':', ('s', 2)])
        # German short
        self.assertEqual(parseDateTimePattern("HH:mm"),
                         [('H', 2), ':', ('m', 2)])

    def testParseRealDate(self):
        # German full
        self.assertEqual(parseDateTimePattern("EEEE, d. MMMM yyyy"),
                         [('E', 4), ', ', ('d', 1), '. ', ('M', 4),
                          ' ', ('y', 4)])
        # German long
        self.assertEqual(parseDateTimePattern("d. MMMM yyyy"),
                         [('d', 1), '. ', ('M', 4), ' ', ('y', 4)])
        # German medium
        self.assertEqual(parseDateTimePattern("dd.MM.yyyy"),
                         [('d', 2), '.', ('M', 2), '.', ('y', 4)])
        # German short
        self.assertEqual(parseDateTimePattern("dd.MM.yy"),
                         [('d', 2), '.', ('M', 2), '.', ('y', 2)])

    def testParseRealDateTime(self):
        # German full
        self.assertEqual(
            parseDateTimePattern("EEEE, d. MMMM yyyy H:mm' Uhr 'z"),
            [('E', 4), ', ', ('d', 1), '. ', ('M', 4), ' ', ('y', 4),
             ' ', ('H', 1), ':', ('m', 2), ' Uhr ', ('z', 1)])
        # German long
        self.assertEqual(
            parseDateTimePattern("d. MMMM yyyy HH:mm:ss z"),
            [('d', 1), '. ', ('M', 4), ' ', ('y', 4),
             ' ', ('H', 2), ':', ('m', 2), ':', ('s', 2), ' ', ('z', 1)])
        # German medium
        self.assertEqual(
            parseDateTimePattern("dd.MM.yyyy HH:mm:ss"),
            [('d', 2), '.', ('M', 2), '.', ('y', 4),
             ' ', ('H', 2), ':', ('m', 2), ':', ('s', 2)])
        # German short
        self.assertEqual(
            parseDateTimePattern("dd.MM.yy HH:mm"),
            [('d', 2), '.', ('M', 2), '.', ('y', 2),
             ' ', ('H', 2), ':', ('m', 2)])

    def testParseQuotesInPattern(self):
        self.assertEqual(parseDateTimePattern("HH''mm"),
                         [('H', 2), "'", ('m', 2)])
        self.assertEqual(parseDateTimePattern("HH'HHmm'mm"),
                         [('H', 2), 'HHmm', ('m', 2)])
        self.assertEqual(parseDateTimePattern("HH':'''':'mm"),
                         [('H', 2), ":':", ('m', 2)])
        self.assertEqual(parseDateTimePattern("HH':' ':'mm"),
                         [('H', 2), ": :", ('m', 2)])

    def testParseDateTimePatternError(self):
        # Quote not closed
        try:
            parseDateTimePattern("HH' Uhr")
        except DateTimePatternParseError, err:
            self.assertEqual(
                str(err), 'The quote starting at character 2 is not closed.')
        # Test correct length of characters in datetime fields
        try:
            parseDateTimePattern("HHHHH")
        except DateTimePatternParseError, err:
            self.assert_(str(err).endswith('You have: 5'))


class TestBuildDateTimeParseInfo(TestCase):
    """This class tests the functionality of the buildDateTimeParseInfo()
    method with the German locale.
    """

    info = buildDateTimeParseInfo(LocaleCalendarStub())

    def testEra(self):
        self.assertEqual(self.info[('G', 1)], '(v. Chr.|n. Chr.)')

    def testMonthNames(self):
        names = [u'Januar', u'Februar', u'Maerz', u'April',
                 u'Mai', u'Juni', u'Juli', u'August', u'September', u'Oktober',
                 u'November', u'Dezember']
        self.assertEqual(self.info[('M', 4)], '('+'|'.join(names)+')')

    def testMonthAbbr(self):
        names = ['Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug',
                 'Sep', 'Okt', 'Nov', 'Dez']
        self.assertEqual(self.info[('M', 3)], '('+'|'.join(names)+')')

    def testWeekdayNames(self):
        names = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag',
                 'Freitag', 'Samstag', 'Sonntag']
        self.assertEqual(self.info[('E', 4)], '('+'|'.join(names)+')')

    def testWeekdayAbbr(self):
        names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        self.assertEqual(self.info[('E', 3)], '('+'|'.join(names)+')')


class TestDateTimeFormat(TestCase):
    """Test the functionality of an implmentation of the ILocaleProvider
    interface."""

    format = DateTimeFormat(calendar=LocaleCalendarStub())

    def testInterfaceConformity(self):
        self.assert_(IDateTimeFormat.providedBy(self.format))

    def testParseSimpleDateTime(self):
        # German short
        self.assertEqual(
            self.format.parse('02.01.03 21:48', 'dd.MM.yy HH:mm'),
            datetime.datetime(2003, 01, 02, 21, 48))

    def testParseRealDateTime(self):
        # German medium
        self.assertEqual(
            self.format.parse('02.01.2003 21:48:01', 'dd.MM.yyyy HH:mm:ss'),
            datetime.datetime(2003, 01, 02, 21, 48, 01))

        # German long
        # TODO: The parser does not support timezones yet.
        self.assertEqual(self.format.parse(
            '2. Januar 2003 21:48:01 +100',
            'd. MMMM yyyy HH:mm:ss z'),
            datetime.datetime(2003, 01, 02, 21, 48, 01))

        # German full
        # TODO: The parser does not support timezones yet.
        self.assertEqual(self.format.parse(
            'Donnerstag, 2. Januar 2003 21:48 Uhr +100',
            "EEEE, d. MMMM yyyy H:mm' Uhr 'z"),
            datetime.datetime(2003, 01, 02, 21, 48))

    def testParseAMPMDateTime(self):
        self.assertEqual(
            self.format.parse('02.01.03 09:48 nachm.', 'dd.MM.yy hh:mm a'),
            datetime.datetime(2003, 01, 02, 21, 48))

    def testDateTimeParseError(self):
        self.assertRaises(DateTimeParseError,
            self.format.parse, '02.01.03 21:48', 'dd.MM.yyyy HH:mm')

    def testParse12PM(self):
        self.assertEqual(
            self.format.parse('01.01.03 12:00 nachm.', 'dd.MM.yy hh:mm a'),
            datetime.datetime(2003, 01, 01, 12, 00, 00, 00))

    def testFormatSimpleDateTime(self):
        # German short
        self.assertEqual(
            self.format.format(datetime.datetime(2003, 01, 02, 21, 48),
                              'dd.MM.yy HH:mm'),
            '02.01.03 21:48')

    def testFormatRealDateTime(self):
        # German medium
        self.assertEqual(
            self.format.format(datetime.datetime(2003, 01, 02, 21, 48, 01),
                              'dd.MM.yyyy HH:mm:ss'),
            '02.01.2003 21:48:01')

        # German long
        # TODO: The parser does not support timezones yet.
        self.assertEqual(self.format.format(
            datetime.datetime(2003, 01, 02, 21, 48, 01),
            'd. MMMM yyyy HH:mm:ss z'),
            '2. Januar 2003 21:48:01 +000')

        # German full
        # TODO: The parser does not support timezones yet.
        self.assertEqual(self.format.format(
            datetime.datetime(2003, 01, 02, 21, 48),
            "EEEE, d. MMMM yyyy H:mm' Uhr 'z"),
            'Donnerstag, 2. Januar 2003 21:48 Uhr +000')

    def testFormatAMPMDateTime(self):
        self.assertEqual(self.format.format(
            datetime.datetime(2003, 01, 02, 21, 48),
            'dd.MM.yy hh:mm a'),
            '02.01.03 09:48 nachm.')

    def test_formatAllWeekdays(self):
        for day in range(1, 8):
            self.assertEqual(self.format.format(
                datetime.datetime(2003, 01, day+5, 21, 48),
                "EEEE, d. MMMM yyyy H:mm' Uhr 'z"),
                '%s, %i. Januar 2003 21:48 Uhr +000' %(
                self.format.calendar.days[day][0], day+5))

    def testFormatSimpleHourRepresentation(self):
        self.assertEqual(
            self.format.format(datetime.datetime(2003, 01, 02, 23, 00),
                               'dd.MM.yy h:mm:ss a'),
            '02.01.03 11:00:00 nachm.')
        self.assertEqual(
            self.format.format(datetime.datetime(2003, 01, 02, 02, 00),
                               'dd.MM.yy h:mm:ss a'),
            '02.01.03 2:00:00 vorm.')
        self.assertEqual(
            self.format.format(datetime.time(0, 15), 'h:mm a'), 
            '12:15 vorm.')
        self.assertEqual(
            self.format.format(datetime.time(1, 15), 'h:mm a'), 
            '1:15 vorm.')
        self.assertEqual(
            self.format.format(datetime.time(12, 15), 'h:mm a'), 
            '12:15 nachm.')
        self.assertEqual(
            self.format.format(datetime.time(13, 15), 'h:mm a'), 
            '1:15 nachm.')


class TestNumberPatternParser(TestCase):
    """Extensive tests for the ICU-based-syntax number pattern parser."""

    def testParseSimpleIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('###0'),
            ((None, '', None, '###0', '', '', None, '', None, 0),
             (None, '', None, '###0', '', '', None, '', None, 0)))

    def testParseScientificIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('###0E#0'),
            ((None, '', None, '###0', '', '#0', None, '', None, 0),
             (None, '', None, '###0', '', '#0', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0E+#0'),
            ((None, '', None, '###0', '', '+#0', None, '', None, 0),
             (None, '', None, '###0', '', '+#0', None, '', None, 0)))

    def testParsePosNegAlternativeIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('###0;#0'),
            ((None, '', None, '###0', '', '', None, '', None, 0),
             (None, '', None,   '#0', '', '', None, '', None, 0)))

    def testParsePrefixedIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('+###0'),
            ((None, '+', None, '###0', '', '', None, '', None, 0),
             (None, '+', None, '###0', '', '', None, '', None, 0)))

    def testParsePosNegIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('+###0;-###0'),
            ((None, '+', None, '###0', '', '', None, '', None, 0),
             (None, '-', None, '###0', '', '', None, '', None, 0)))

    def testParseScientificPosNegIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('+###0E0;-###0E#0'),
            ((None, '+', None, '###0', '', '0', None, '', None, 0),
             (None, '-', None, '###0', '', '#0', None, '', None, 0)))

    def testParseThousandSeparatorIntegerPattern(self):
        self.assertEqual(
            parseNumberPattern('#,##0'),
            ((None, '', None, '###0', '', '', None, '', None, 1),
             (None, '', None, '###0', '', '', None, '', None, 1)))

    def testParseSimpleDecimalPattern(self):
        self.assertEqual(
            parseNumberPattern('###0.00#'),
            ((None, '', None, '###0', '00#', '', None, '', None, 0),
             (None, '', None, '###0', '00#', '', None, '', None, 0)))

    def testParseScientificDecimalPattern(self):
        self.assertEqual(
            parseNumberPattern('###0.00#E#0'),
            ((None, '', None, '###0', '00#', '#0', None, '', None, 0),
             (None, '', None, '###0', '00#', '#0', None, '', None, 0)))

    def testParsePosNegAlternativeFractionPattern(self):
        self.assertEqual(
            parseNumberPattern('###0.00#;#0.0#'),
            ((None, '', None, '###0', '00#', '', None, '', None, 0),
             (None, '', None,   '#0',  '0#', '', None, '', None, 0)))

    def testParsePosNegFractionPattern(self):
        self.assertEqual(
            parseNumberPattern('+###0.0##;-###0.0##'),
            ((None, '+', None, '###0', '0##', '', None, '', None, 0),
             (None, '-', None, '###0', '0##', '', None, '', None, 0)))

    def testParseScientificPosNegFractionPattern(self):
        self.assertEqual(
            parseNumberPattern('+###0.0##E#0;-###0.0##E0'),
            ((None, '+', None, '###0', '0##', '#0', None, '', None, 0),
             (None, '-', None, '###0', '0##', '0', None, '', None, 0)))

    def testParseThousandSeparatorFractionPattern(self):
        self.assertEqual(
            parseNumberPattern('#,##0.0#'),
            ((None, '', None, '###0', '0#', '', None, '', None, 1),
             (None, '', None, '###0', '0#', '', None, '', None, 1)))

    def testParsePadding1WithoutPrefixPattern(self):
        self.assertEqual(
            parseNumberPattern('* ###0'),
            ((' ', '', None, '###0', '', '', None, '', None, 0),
             (' ', '', None, '###0', '', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('* ###0.0##'),
            ((' ', '', None, '###0', '0##', '', None, '', None, 0),
             (' ', '', None, '###0', '0##', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('* ###0.0##;*_###0.0##'),
            ((' ', '', None, '###0', '0##', '', None, '', None, 0),
             ('_', '', None, '###0', '0##', '', None, '', None, 0)))

    def testParsePadding1WithPrefixPattern(self):
        self.assertEqual(
            parseNumberPattern('* +###0'),
            ((' ', '+', None, '###0', '', '', None, '', None, 0),
             (' ', '+', None, '###0', '', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('* +###0.0##'),
            ((' ', '+', None, '###0', '0##', '', None, '', None, 0),
             (' ', '+', None, '###0', '0##', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('* +###0.0##;*_-###0.0##'),
            ((' ', '+', None, '###0', '0##', '', None, '', None, 0),
             ('_', '-', None, '###0', '0##', '', None, '', None, 0)))

    def testParsePadding1Padding2WithPrefixPattern(self):
        self.assertEqual(
            parseNumberPattern('* +* ###0'),
            ((' ', '+', ' ', '###0', '', '', None, '', None, 0),
             (' ', '+', ' ', '###0', '', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('* +* ###0.0##'),
            ((' ', '+', ' ', '###0', '0##', '', None, '', None, 0),
             (' ', '+', ' ', '###0', '0##', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('* +* ###0.0##;*_-*_###0.0##'),
            ((' ', '+', ' ', '###0', '0##', '', None, '', None, 0),
             ('_', '-', '_', '###0', '0##', '', None, '', None, 0)))

    def testParsePadding3WithoutSufffixPattern(self):
        self.assertEqual(
            parseNumberPattern('###0* '),
            ((None, '', None, '###0', '', '', ' ', '', None, 0),
             (None, '', None, '###0', '', '', ' ', '', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0.0##* '),
            ((None, '', None, '###0', '0##', '', ' ', '', None, 0),
             (None, '', None, '###0', '0##', '', ' ', '', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0.0##* ;###0.0##*_'),
            ((None, '', None, '###0', '0##', '', ' ', '', None, 0),
             (None, '', None, '###0', '0##', '', '_', '', None, 0)))

    def testParsePadding3InScientificPattern(self):
        self.assertEqual(
            parseNumberPattern('###0E#0* '),
            ((None, '', None, '###0', '', '#0', ' ', '', None, 0),
             (None, '', None, '###0', '', '#0', ' ', '', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0.0##E0* '),
            ((None, '', None, '###0', '0##', '0', ' ', '', None, 0),
             (None, '', None, '###0', '0##', '0', ' ', '', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0.0##E#0* ;###0.0##E0*_'),
            ((None, '', None, '###0', '0##', '#0', ' ', '', None, 0),
             (None, '', None, '###0', '0##', '0', '_', '', None, 0)))

    def testParsePadding3WithSufffixPattern(self):
        self.assertEqual(
            parseNumberPattern('###0* /'),
            ((None, '', None, '###0', '', '', ' ', '/', None, 0),
             (None, '', None, '###0', '', '', ' ', '/', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0.0#* /'),
            ((None, '', None, '###0', '0#', '', ' ', '/', None, 0),
             (None, '', None, '###0', '0#', '', ' ', '/', None, 0)))
        self.assertEqual(
            parseNumberPattern('###0.0#* /;###0.0#*_/'),
            ((None, '', None, '###0', '0#', '', ' ', '/', None, 0),
             (None, '', None, '###0', '0#', '', '_', '/', None, 0)))

    def testParsePadding3And4WithSuffixPattern(self):
        self.assertEqual(
            parseNumberPattern('###0* /* '),
            ((None, '', None, '###0', '', '', ' ', '/', ' ', 0),
              (None, '', None, '###0', '', '', ' ', '/', ' ', 0)))
        self.assertEqual(
            parseNumberPattern('###0* /* ;###0*_/*_'),
            ((None, '', None, '###0', '', '', ' ', '/', ' ', 0),
             (None, '', None, '###0', '', '', '_', '/', '_', 0)))

    def testParseMultipleCharacterPrefix(self):
        self.assertEqual(
            parseNumberPattern('DM###0'),
            ((None, 'DM', None, '###0', '', '', None, '', None, 0),
             (None, 'DM', None, '###0', '', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern('DM* ###0'),
            ((None, 'DM', ' ', '###0', '', '', None, '', None, 0),
             (None, 'DM', ' ', '###0', '', '', None, '', None, 0)))

    def testParseStringEscapedPrefix(self):
        self.assertEqual(
            parseNumberPattern("'DEM'###0"),
            ((None, 'DEM', None, '###0', '', '', None, '', None, 0),
             (None, 'DEM', None, '###0', '', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern("D'EM'###0"),
            ((None, 'DEM', None, '###0', '', '', None, '', None, 0),
             (None, 'DEM', None, '###0', '', '', None, '', None, 0)))
        self.assertEqual(
            parseNumberPattern("D'E'M###0"),
            ((None, 'DEM', None, '###0', '', '', None, '', None, 0),
             (None, 'DEM', None, '###0', '', '', None, '', None, 0)))

    def testParseStringEscapedSuffix(self):
        self.assertEqual(
            parseNumberPattern("###0'DEM'"),
            ((None, '', None, '###0', '', '', None, 'DEM', None, 0),
             (None, '', None, '###0', '', '', None, 'DEM', None, 0)))
        self.assertEqual(
            parseNumberPattern("###0D'EM'"),
            ((None, '', None, '###0', '', '', None, 'DEM', None, 0),
             (None, '', None, '###0', '', '', None, 'DEM', None, 0)))
        self.assertEqual(
            parseNumberPattern("###0D'E'M"),
            ((None, '', None, '###0', '', '', None, 'DEM', None, 0),
             (None, '', None, '###0', '', '', None, 'DEM', None, 0)))


class TestNumberFormat(TestCase):
    """Test the functionality of an implmentation of the NumberFormat."""

    format = NumberFormat(symbols={
        'decimal': '.', 'group': ',', 'list': ';', 'percentSign': '%',
        'nativeZeroDigit': '0', 'patternDigit': '#', 'plusSign': '+',
        'minusSign': '-', 'exponential': 'E', 'perMille': 'o/oo',
        'infinity': 'oo', 'nan': 'N/A'})

    def testInterfaceConformity(self):
        self.assert_(INumberFormat.providedBy(self.format))

    def testParseSimpleInteger(self):
        self.assertEqual(self.format.parse('23341', '###0'),
                         23341)
        self.assertEqual(self.format.parse('041', '#000'),
                         41)

    def testParseScientificInteger(self):
        self.assertEqual(self.format.parse('2.3341E4', '0.0###E0'),
                         23341)
        self.assertEqual(self.format.parse('4.100E01', '0.000##E00'),
                         41)
        self.assertEqual(self.format.parse('1E0', '0E0'),
                         1)
        self.assertEqual(self.format.parse('0E0', '0E0'),
                         0)
        # This is a special case I found not working, but is used frequently
        # in the new LDML Locale files.  
        self.assertEqual(self.format.parse('2.3341E+04', '0.000###E+00'),
                         23341)

    def testParsePosNegAlternativeInteger(self):
        self.assertEqual(self.format.parse('23341', '#000;#00'),
                         23341)
        self.assertEqual(self.format.parse('041', '#000;#00'),
                         41)
        self.assertEqual(self.format.parse('41', '#000;#00'),
                         -41)
        self.assertEqual(self.format.parse('01', '#000;#00'),
                         -1)

    def testParsePrefixedInteger(self):
        self.assertEqual(self.format.parse('+23341', '+###0'),
                         23341)
        self.assertEqual(self.format.parse('+041', '+#000'),
                         41)

    def testParsePosNegInteger(self):
        self.assertEqual(self.format.parse('+23341', '+###0;-###0'),
                         23341)
        self.assertEqual(self.format.parse('+041', '+#000;-#000'),
                         41)
        self.assertEqual(self.format.parse('-23341', '+###0;-###0'),
                         -23341)
        self.assertEqual(self.format.parse('-041', '+#000;-#000'),
                         -41)

    def testParseThousandSeparatorInteger(self):
        self.assertEqual(self.format.parse('+23,341', '+#,##0;-#,##0'),
                         23341)
        self.assertEqual(self.format.parse('-23,341', '+#,##0;-#,##0'),
                         -23341)
        self.assertEqual(self.format.parse('+0,041', '+#0,000;-#0,000'),
                         41)
        self.assertEqual(self.format.parse('-0,041', '+#0,000;-#0,000'),
                         -41)

    def testParseDecimal(self):
        self.assertEqual(self.format.parse('23341.02', '###0.0#'),
                         23341.02)
        self.assertEqual(self.format.parse('23341.1', '###0.0#'),
                         23341.1)
        self.assertEqual(self.format.parse('23341.020', '###0.000#'),
                         23341.02)

    def testParseScientificDecimal(self):
        self.assertEqual(self.format.parse('2.334102E04', '0.00####E00'),
                         23341.02)
        self.assertEqual(self.format.parse('2.3341020E004', '0.0000000E000'),
                         23341.02)
        self.assertEqual(self.format.parse('0.0E0', '0.0#E0'),
                         0.0)

    def testParseScientificDecimalSmallerOne(self):
        self.assertEqual(self.format.parse('2.357E-02', '0.00####E00'),
                         0.02357)
        self.assertEqual(self.format.parse('2.0000E-02', '0.0000E00'),
                         0.02)

    def testParsePadding1WithoutPrefix(self):
        self.assertEqual(self.format.parse(' 41', '* ##0;*_##0'),
                         41)
        self.assertEqual(self.format.parse('_41', '* ##0;*_##0'),
                         -41)

    def testParsePadding1WithPrefix(self):
        self.assertEqual(self.format.parse(' +41', '* +##0;*_-##0'),
                         41)
        self.assertEqual(self.format.parse('_-41', '* +##0;*_-##0'),
                         -41)

    def testParsePadding1Padding2WithPrefix(self):
        self.assertEqual(self.format.parse('  + 41', '* +* ###0;*_-*_###0'),
                         +41)
        self.assertEqual(self.format.parse('__-_41', '* +* ###0;*_-*_###0'),
                         -41)

    def testParsePadding1Scientific(self):
        self.assertEqual(self.format.parse('  4.102E1',
                                            '* 0.0####E0;*_0.0####E0'),
                         41.02)
        self.assertEqual(self.format.parse('__4.102E1',
                                            '* 0.0####E0;*_0.0####E0'),
                         -41.02)
        self.assertEqual(self.format.parse(' +4.102E1',
                                           '* +0.0###E0;*_-0.0###E0'),
                         41.02)
        self.assertEqual(self.format.parse('_-4.102E1',
                                           '* +0.0###E0;*_-0.0###E0'),
                         -41.02)

    def testParsePadding3WithoutSufffix(self):
        self.assertEqual(self.format.parse('41.02  ', '#0.0###* ;#0.0###*_'),
                         41.02)
        self.assertEqual(self.format.parse('41.02__', '#0.0###* ;#0.0###*_'),
                         -41.02)

    def testParsePadding3WithSufffix(self):
        self.assertEqual(
            self.format.parse('[41.02  ]', '[#0.0###* ];(#0.0###*_)'),
            41.02)
        self.assertEqual(
            self.format.parse('(41.02__)', '[#0.0###* ];(#0.0###*_)'),
            -41.02)

    def testParsePadding3Scientific(self):
        self.assertEqual(self.format.parse('4.102E1  ',
                                           '0.0##E0##* ;0.0##E0##*_'),
                         41.02)
        self.assertEqual(self.format.parse('4.102E1__',
                                           '0.0##E0##* ;0.0##E0##*_'),
                         -41.02)
        self.assertEqual(self.format.parse('(4.102E1  )',
                                           '(0.0##E0##* );0.0E0'),
                         41.02)
        self.assertEqual(self.format.parse('[4.102E1__]',
                                           '0.0E0;[0.0##E0##*_]'),
                         -41.02)

    def testParsePadding3Padding4WithSuffix(self):
        self.assertEqual(self.format.parse('(41.02 )  ', '(#0.0###* )* '),
                         41.02)
        self.assertEqual(self.format.parse('(4.102E1 )  ', '(0.0##E0##* )* '),
                         41.02)

    def testFormatSimpleInteger(self):
        self.assertEqual(self.format.format(23341, '###0'),
                         '23341')
        self.assertEqual(self.format.format(41, '#000'),
                         '041')

    def testFormatScientificInteger(self):
        self.assertEqual(self.format.format(23341, '0.000#E0'),
                         '2.3341E4')
        self.assertEqual(self.format.format(23341, '0.000#E00'),
                         '2.3341E04')
        self.assertEqual(self.format.format(1, '0.##E0'),
                         '1E0')
        self.assertEqual(self.format.format(1, '0.00E00'),
                         '1.00E00')
        # This is a special case I found not working, but is used frequently
        # in the new LDML Locale files.  
        self.assertEqual(self.format.format(23341, '0.000###E+00'),
                         '2.3341E+04')

    def testFormatScientificZero(self):
        self.assertEqual(self.format.format(0, '0.00E00'),
                         '0.00E00')
        self.assertEqual(self.format.format(0, '0E0'),
                         '0E0')

    def testFormatPosNegAlternativeInteger(self):
        self.assertEqual(self.format.format(23341, '#000;#00'),
                         '23341')
        self.assertEqual(self.format.format(41, '#000;#00'),
                         '041')
        self.assertEqual(self.format.format(-23341, '#000;#00'),
                         '23341')
        self.assertEqual(self.format.format(-41, '#000;#00'),
                         '41')
        self.assertEqual(self.format.format(-1, '#000;#00'),
                         '01')

    def testFormatPrefixedInteger(self):
        self.assertEqual(self.format.format(23341, '+###0'),
                         '+23341')
        self.assertEqual(self.format.format(41, '+#000'),
                         '+041')
        self.assertEqual(self.format.format(-23341, '+###0'),
                         '+23341')
        self.assertEqual(self.format.format(-41, '+#000'),
                         '+041')

    def testFormatPosNegInteger(self):
        self.assertEqual(self.format.format(23341, '+###0;-###0'),
                         '+23341')
        self.assertEqual(self.format.format(41, '+#000;-#000'),
                         '+041')
        self.assertEqual(self.format.format(-23341, '+###0;-###0'),
                         '-23341')
        self.assertEqual(self.format.format(-41, '+#000;-#000'),
                         '-041')

    def testFormatPosNegScientificInteger(self):
        self.assertEqual(self.format.format(23341, '+0.00###E00;-0.00###E00'),
                         '+2.3341E04')
        self.assertEqual(self.format.format(23341, '-0.00###E00;-0.00###E00'),
                         '-2.3341E04')

    def testFormatThousandSeparatorInteger(self):
        self.assertEqual(self.format.format(23341, '+#,##0;-#,##0'),
                         '+23,341')
        self.assertEqual(self.format.format(-23341, '+#,##0;-#,##0'),
                         '-23,341')
        self.assertEqual(self.format.format(41, '+#0,000;-#0,000'),
                         '+0,041')
        self.assertEqual(self.format.format(-41, '+#0,000;-#0,000'),
                         '-0,041')

    def testFormatDecimal(self):
        self.assertEqual(self.format.format(23341.02357, '###0.0#'),
                         '23341.02')
        self.assertEqual(self.format.format(23341.02357, '###0.000#'),
                         '23341.0236')
        self.assertEqual(self.format.format(23341.02, '###0.000#'),
                         '23341.020')
                         
    def testRounding(self):
        self.assertEqual(self.format.format(0.5, '#'), '1')
        self.assertEqual(self.format.format(0.49, '#'), '0')
        self.assertEqual(self.format.format(0.45, '0.0'), '0.5')
        self.assertEqual(self.format.format(150, '0E0'), '2E2')
        self.assertEqual(self.format.format(149, '0E0'), '1E2')
        self.assertEqual(self.format.format(1.9999, '0.000'), '2.000')
        self.assertEqual(self.format.format(1.9999, '0.0000'), '1.9999')
        

    def testFormatScientificDecimal(self):
        self.assertEqual(self.format.format(23341.02357, '0.00####E00'),
                         '2.334102E04')
        self.assertEqual(self.format.format(23341.02, '0.0000000E000'),
                         '2.3341020E004')

    def testFormatScientificDecimalSmallerOne(self):
        self.assertEqual(self.format.format(0.02357, '0.00####E00'),
                         '2.357E-02')
        self.assertEqual(self.format.format(0.02, '0.0000E00'),
                         '2.0000E-02')

    def testFormatPadding1WithoutPrefix(self):
        self.assertEqual(self.format.format(41, '* ##0;*_##0'),
                         ' 41')
        self.assertEqual(self.format.format(-41, '* ##0;*_##0'),
                         '_41')

    def testFormatPadding1WithPrefix(self):
        self.assertEqual(self.format.format(41, '* +##0;*_-##0'),
                         ' +41')
        self.assertEqual(self.format.format(-41, '* +##0;*_-##0'),
                         '_-41')

    def testFormatPadding1Scientific(self):
        self.assertEqual(self.format.format(41.02, '* 0.0####E0;*_0.0####E0'),
                         '  4.102E1')
        self.assertEqual(self.format.format(-41.02, '* 0.0####E0;*_0.0####E0'),
                         '__4.102E1')
        self.assertEqual(self.format.format(41.02, '* +0.0###E0;*_-0.0###E0'),
                         ' +4.102E1')
        self.assertEqual(self.format.format(-41.02, '* +0.0###E0;*_-0.0###E0'),
                         '_-4.102E1')

    def testFormatPadding1Padding2WithPrefix(self):
        self.assertEqual(self.format.format(41, '* +* ###0;*_-*_###0'),
                         '  + 41')
        self.assertEqual(self.format.format(-41, '* +* ###0;*_-*_###0'),
                         '__-_41')

    def testFormatPadding3WithoutSufffix(self):
        self.assertEqual(self.format.format(41.02, '#0.0###* ;#0.0###*_'),
                         '41.02  ')
        self.assertEqual(self.format.format(-41.02, '#0.0###* ;#0.0###*_'),
                         '41.02__')

    def testFormatPadding3WithSufffix(self):
        self.assertEqual(self.format.format(41.02, '[#0.0###* ];(#0.0###*_)'),
                         '[41.02  ]')
        self.assertEqual(self.format.format(-41.02, '[#0.0###* ];(#0.0###*_)'),
                         '(41.02__)')

    def testFormatPadding3Scientific(self):
        self.assertEqual(self.format.format(41.02, '0.0##E0##* ;0.0##E0##*_'),
                         '4.102E1  ')
        self.assertEqual(self.format.format(-41.02, '0.0##E0##* ;0.0##E0##*_'),
                         '4.102E1__')
        self.assertEqual(self.format.format(41.02, '(0.0##E0##* );0.0E0'),
                         '(4.102E1  )')
        self.assertEqual(self.format.format(-41.02, '0.0E0;[0.0##E0##*_]'),
                         '[4.102E1__]')

    def testFormatPadding3Padding4WithSuffix(self):
        self.assertEqual(self.format.format(41.02, '(#0.0###* )* '),
                         '(41.02 )  ')
        self.assertEqual(self.format.format(41.02, '(0.0##E0##* )* '),
                         '(4.102E1 )  ')


def test_suite():
    return TestSuite((
        makeSuite(TestDateTimePatternParser),
        makeSuite(TestBuildDateTimeParseInfo),
        makeSuite(TestDateTimeFormat),
        makeSuite(TestNumberPatternParser),
        makeSuite(TestNumberFormat),
       ))
