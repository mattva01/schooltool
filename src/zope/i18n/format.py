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
"""Basic Object Formatting

This module implements basic object formatting functionality, such as
date/time, number and money formatting.

$Id$
"""
import re
import math
import datetime

from zope.i18n.interfaces import IDateTimeFormat, INumberFormat
from zope.interface import implements

class DateTimeParseError(Exception):
    """Error is raised when parsing of datetime failed."""

class DateTimeFormat(object):
    __doc__ = IDateTimeFormat.__doc__

    implements(IDateTimeFormat)

    _DATETIMECHARS = "aGyMdEDFwWhHmsSkKz"

    def __init__(self, pattern=None, calendar=None):
        if calendar is not None:
            self.calendar = calendar
        self._pattern = pattern
        self._bin_pattern = None
        if self._pattern is not None:
            self._bin_pattern = parseDateTimePattern(self._pattern,
                                                     self._DATETIMECHARS)

    def setPattern(self, pattern):
        "See zope.i18n.interfaces.IFormat"
        self._pattern = pattern
        self._bin_pattern = parseDateTimePattern(self._pattern,
                                                 self._DATETIMECHARS)

    def getPattern(self):
        "See zope.i18n.interfaces.IFormat"
        return self._pattern

    def parse(self, text, pattern=None, asObject=True):
        "See zope.i18n.interfaces.IFormat"
        # Make or get binary form of datetime pattern
        if pattern is not None:
            bin_pattern = parseDateTimePattern(pattern)
        else:
            bin_pattern = self._bin_pattern
        # Generate the correct regular expression to parse the date and parse.
        regex = ''
        info = buildDateTimeParseInfo(self.calendar)
        for elem in bin_pattern:
            regex += info.get(elem, elem)
        try:
            results = re.match(regex, text).groups()
        except AttributeError:
            raise DateTimeParseError(
                  'The datetime string did not match the pattern.')
        # Sometimes you only want the parse results
        if not asObject:
            return results
        # Map the parsing results to a datetime object
        ordered = [0, 0, 0, 0, 0, 0, 0]
        bin_pattern = filter(lambda x: isinstance(x, tuple), bin_pattern)
        # Handle years
        if ('y', 2) in bin_pattern:
            year = int(results[bin_pattern.index(('y', 2))])
            if year > 30:
                ordered[0] = 1900 + year
            else:
                ordered[0] = 2000 + year
        if ('y', 4) in bin_pattern:
            ordered[0] = int(results[bin_pattern.index(('y', 4))])
        # Handle months
        if ('M', 3) in bin_pattern:
            abbr = results[bin_pattern.index(('M', 3))]
            ordered[1] = self.calendar.getMonthTypeFromAbbreviation(abbr)
        if ('M', 4) in bin_pattern:
            name = results[bin_pattern.index(('M', 4))]
            ordered[1] = self.calendar.getMonthTypeFromName(name)
        # Handle AM/PM hours
        for length in (1, 2):
            id = ('h', length)
            if id in bin_pattern:
                hour = int(results[bin_pattern.index(id)])
                ampm = self.calendar.pm == results[
                    bin_pattern.index(('a', 1))]
                if hour == 12:
                    ampm = not ampm
                ordered[3] = (hour + 12*ampm)%24
        # Shortcut for the simple int functions
        dt_fields_map = {'M': 1, 'd': 2, 'H': 3, 'm': 4, 's': 5, 'S': 6}
        for field in dt_fields_map.keys():
            for length in (1, 2):
                id = (field, length)
                if id in bin_pattern:
                    pos = dt_fields_map[field]
                    ordered[pos] = int(results[bin_pattern.index(id)])

        if ordered[3:] == [0, 0, 0, 0]:
            return datetime.date(*ordered[:3])
        elif ordered[:3] == [0, 0, 0]:
            return datetime.time(*ordered[3:])
        else:
            return datetime.datetime(*ordered)


    def format(self, obj, pattern=None):
        "See zope.i18n.interfaces.IFormat"
        # Make or get binary form of datetime pattern
        if pattern is not None:
            bin_pattern = parseDateTimePattern(pattern)
        else:
            bin_pattern = self._bin_pattern

        text = ''
        info = buildDateTimeInfo(obj, self.calendar)
        for elem in bin_pattern:
            text += info.get(elem, elem)

        return text


class NumberParseError(Exception):
    """Error that can be raised when smething unexpected happens during the
    number parsing process."""


class NumberFormat(object):
    __doc__ = INumberFormat.__doc__

    implements(INumberFormat)

    def __init__(self, pattern=None, symbols={}):
        # setup default symbols
        self.symbols = {
            u'decimal': u'.',
            u'group': u',',
            u'list':  u';',
            u'percentSign': u'%',
            u'nativeZeroDigit': u'0',
            u'patternDigit': u'#',
            u'plusSign': u'+',
            u'minusSign': u'-',
            u'exponential': u'E',
            u'perMille': u'\xe2\x88\x9e',
            u'infinity': u'\xef\xbf\xbd',
            u'nan': '' }
        self.symbols.update(symbols)
        self._pattern = pattern
        self._bin_pattern = None
        if self._pattern is not None:
            self._bin_pattern = parseNumberPattern(self._pattern)

    def setPattern(self, pattern):
        "See zope.i18n.interfaces.IFormat"
        self._pattern = pattern
        self._bin_pattern = parseNumberPattern(self._pattern)

    def getPattern(self):
        "See zope.i18n.interfaces.IFormat"
        return self._pattern

    def parse(self, text, pattern=None):
        "See zope.i18n.interfaces.IFormat"
        # Make or get binary form of datetime pattern
        if pattern is not None:
            bin_pattern = parseNumberPattern(pattern)
        else:
            bin_pattern = self._bin_pattern
        # Determine sign
        num_res = [None, None]
        for sign in (0, 1):
            regex = ''
            if bin_pattern[sign][PADDING1] is not None:
                regex += '[' + bin_pattern[sign][PADDING1] + ']+'
            if bin_pattern[sign][PREFIX] != '':
                regex += '[' + bin_pattern[sign][PREFIX] + ']'
            if bin_pattern[sign][PADDING2] is not None:
                regex += '[' + bin_pattern[sign][PADDING2] + ']+'
            regex += '([0-9'
            min_size = bin_pattern[sign][INTEGER].count('0')
            if bin_pattern[sign][GROUPING]:
                regex += self.symbols['group']
                min_size += min_size/3
            regex += ']{%i,100}' %(min_size)
            if bin_pattern[sign][FRACTION]:
                max_precision = len(bin_pattern[sign][FRACTION])
                min_precision = bin_pattern[sign][FRACTION].count('0')
                regex += '['+self.symbols['decimal']+']'
                regex += '[0-9]{%i,%i}' %(min_precision, max_precision)
            if bin_pattern[sign][EXPONENTIAL] != '':
                regex += self.symbols['exponential']
                min_exp_size = bin_pattern[sign][EXPONENTIAL].count('0')
                pre_symbols = self.symbols['minusSign']
                if bin_pattern[sign][EXPONENTIAL][0] == '+':
                    pre_symbols += self.symbols['plusSign']
                regex += '[%s]?[0-9]{%i,100}' %(pre_symbols, min_exp_size)
            regex +=')'
            if bin_pattern[sign][PADDING3] is not None:
                regex += '[' + bin_pattern[sign][PADDING3] + ']+'
            if bin_pattern[sign][SUFFIX] != '':
                regex += '[' + bin_pattern[sign][SUFFIX] + ']'
            if bin_pattern[sign][PADDING4] is not None:
                regex += '[' + bin_pattern[sign][PADDING4] + ']+'
            num_res[sign] = re.match(regex, text)

        if num_res[0] is not None:
            num_str = num_res[0].groups()[0]
            sign = +1
        elif num_res[1] is not None:
            num_str = num_res[1].groups()[0]
            sign = -1
        else:
            raise NumberParseError, 'Not a valid number for this pattern.'
        # Remove possible grouping separators
        num_str = num_str.replace(self.symbols['group'], '')
        # Extract number
        type = int
        if self.symbols['decimal'] in num_str:
            type = float
        if self.symbols['exponential'] in num_str:
            type = float
            num_str.replace(self.symbols['exponential'], 'E')
        return sign*type(num_str)

    def _format_integer(self, integer, pattern):
        size = len(integer)
        min_size = pattern.count('0')
        if size < min_size:
            integer = self.symbols['nativeZeroDigit']*(min_size-size) + integer
        return integer

    def _format_fraction(self, fraction, pattern):
        max_precision = len(pattern)
        min_precision = pattern.count('0')
        precision = len(fraction)
        roundInt = False
        if precision > max_precision:
            round = int(fraction[max_precision]) >= 5
            fraction = fraction[:max_precision]
            if round:
                if fraction != '':
                    # add 1 to the fraction, maintaining the decimal
                    # precision; if the result >= 1, need to roundInt
                    fractionLen = len(fraction)
                    rounded = int(fraction) + 1
                    fraction = ('%0' + str(fractionLen) + 'i') % rounded
                    if len(fraction) > fractionLen:	# rounded fraction >= 1
                        roundInt = True
                        fraction = fraction[1:]
                else:
                    # fraction missing, e.g. 1.5 -> 1. -- need to roundInt
                    roundInt = True

        if precision < min_precision:
            fraction += self.symbols['nativeZeroDigit']*(min_precision -
                                                         precision)
        if fraction != '':
            fraction = self.symbols['decimal'] + fraction
        return fraction, roundInt

    def format(self, obj, pattern=None):
        "See zope.i18n.interfaces.IFormat"
        # Make or get binary form of datetime pattern
        if pattern is not None:
            bin_pattern = parseNumberPattern(pattern)
        else:
            bin_pattern = self._bin_pattern
        # Get positive or negative sub-pattern
        if obj >= 0:
            bin_pattern = bin_pattern[0]
        else:
            bin_pattern = bin_pattern[1]


        if bin_pattern[EXPONENTIAL] != '':
            obj_int_frac = str(obj).split('.')
            # The exponential might have a mandatory sign; remove it from the
            # bin_pattern and remember the setting
            exp_bin_pattern = bin_pattern[EXPONENTIAL]
            plus_sign = u''
            if exp_bin_pattern.startswith('+'):
                plus_sign = self.symbols['plusSign']
                exp_bin_pattern = exp_bin_pattern[1:]
            # We have to remove the possible '-' sign
            if obj < 0:
                obj_int_frac[0] = obj_int_frac[0][1:]
            if obj_int_frac[0] == '0':
                # abs() of number smaller 1
                if len(obj_int_frac) > 1:
                    res = re.match('(0*)[0-9]*', obj_int_frac[1]).groups()[0]
                    exponent = self._format_integer(str(len(res)+1),
                                                    exp_bin_pattern)
                    exponent = self.symbols['minusSign']+exponent
                    number = obj_int_frac[1][len(res):]
                else:
                    # We have exactly 0
                    exponent = self._format_integer('0', exp_bin_pattern)
                    number = self.symbols['nativeZeroDigit']
            else:
                exponent = self._format_integer(str(len(obj_int_frac[0])-1),
                                                exp_bin_pattern)
                number = ''.join(obj_int_frac)

            fraction, roundInt = self._format_fraction(number[1:],
                                                       bin_pattern[FRACTION])
            if roundInt:
                number = str(int(number[0]) + 1) + fraction
            else:
                number = number[0] + fraction

            # We might have a plus sign in front of the exponential integer
            if not exponent.startswith('-'):
                exponent = plus_sign + exponent

            pre_padding = len(bin_pattern[FRACTION]) - len(number) + 2
            post_padding = len(exp_bin_pattern) - len(exponent)
            number += self.symbols['exponential'] + exponent

        else:
            obj_int_frac = str(obj).split('.')
            if len(obj_int_frac) > 1:
                fraction, roundInt = self._format_fraction(obj_int_frac[1],
                                                 bin_pattern[FRACTION])
            else:
                fraction = ''
                roundInt = False
            if roundInt:
                obj = round(obj)
            integer = self._format_integer(str(int(math.fabs(obj))),
                                           bin_pattern[INTEGER])
            # Adding grouping
            if bin_pattern[GROUPING] == 1:
                help = ''
                for pos in range(1, len(integer)+1):
                    if (pos-1)%3 == 0 and pos != 1:
                        help = self.symbols['group'] + help
                    help = integer[-pos] + help
                integer = help
            pre_padding = len(bin_pattern[INTEGER]) - len(integer)
            post_padding = len(bin_pattern[FRACTION]) - len(fraction)+1
            number = integer + fraction

        # Put it all together
        text = ''
        if bin_pattern[PADDING1] is not None and pre_padding > 0:
            text += bin_pattern[PADDING1]*pre_padding
        text += bin_pattern[PREFIX]
        if bin_pattern[PADDING2] is not None and pre_padding > 0:
            if bin_pattern[PADDING1] is not None:
                text += bin_pattern[PADDING2]
            else:
                text += bin_pattern[PADDING2]*pre_padding
        text += number
        if bin_pattern[PADDING3] is not None and post_padding > 0:
            if bin_pattern[PADDING4] is not None:
                text += bin_pattern[PADDING3]
            else:
                text += bin_pattern[PADDING3]*post_padding
        text += bin_pattern[SUFFIX]
        if bin_pattern[PADDING4] is not None and post_padding > 0:
            text += bin_pattern[PADDING4]*post_padding

        # TODO: Need to make sure unicode is everywhere
        return unicode(text)



DEFAULT = 0
IN_QUOTE = 1
IN_DATETIMEFIELD = 2

class DateTimePatternParseError(Exception):
    """DateTime Pattern Parse Error"""

class BinaryDateTimePattern(list):

    def append(self, item):
        if isinstance(item, tuple) and item[1] > 4:
            raise DateTimePatternParseError, \
                  ('A datetime field character sequence can never be '
                   'longer than 4 characters. You have: %i' %item[1])
        super(BinaryDateTimePattern, self).append(item)


def parseDateTimePattern(pattern, DATETIMECHARS="aGyMdEDFwWhHmsSkKz"):
    """This method can handle everything: time, date and datetime strings."""
    result = BinaryDateTimePattern()
    state = DEFAULT
    helper = ''
    char = ''
    quote_start = -2

    for pos in range(len(pattern)):
        prev_char = char
        char = pattern[pos]
        # Handle quotations
        if char == "'":
            if state == DEFAULT:
                quote_start = pos
                state = IN_QUOTE
            elif state == IN_QUOTE and prev_char == "'":
                helper += char
                state = DEFAULT
            elif state == IN_QUOTE:
                # Do not care about putting the content of the quote in the
                # result. The next state is responsible for that.
                quote_start = -1
                state = DEFAULT
            elif state == IN_DATETIMEFIELD:
                result.append((helper[0], len(helper)))
                helper = ''
                quote_start = pos
                state = IN_QUOTE
        elif state == IN_QUOTE:
            helper += char

        # Handle regular characters
        elif char not in DATETIMECHARS:
            if state == IN_DATETIMEFIELD:
                result.append((helper[0], len(helper)))
                helper = char
                state = DEFAULT
            elif state == DEFAULT:
                helper += char

        # Handle special formatting characters
        elif char in DATETIMECHARS:
            if state == DEFAULT:
                # Clean up helper first
                if helper:
                    result.append(helper)
                helper = char
                state = IN_DATETIMEFIELD

            elif state == IN_DATETIMEFIELD and prev_char == char:
                helper += char

            elif state == IN_DATETIMEFIELD and prev_char != char:
                result.append((helper[0], len(helper)))
                helper = char

    # Some cleaning up
    if state == IN_QUOTE:
        if quote_start == -1:
            raise DateTimePatternParseError, \
                  'Waaa: state = IN_QUOTE and quote_start = -1!'
        else:
            raise DateTimePatternParseError, \
                  ('The quote starting at character %i is not closed.' %
                   quote_start)
    elif state == IN_DATETIMEFIELD:
        result.append((helper[0], len(helper)))
    elif state == DEFAULT:
        result.append(helper)

    return result



def buildDateTimeParseInfo(calendar):
    """This method returns a dictionary that helps us with the parsing.
    It also depends on the locale of course."""
    return {
        ('a', 1): r'(%s|%s)' %(calendar.am, calendar.pm),
        # TODO: works for gregorian only right now
        ('G', 1): r'(%s|%s)' %(calendar.eras[1][1], calendar.eras[2][1]),
        ('y', 2): r'([0-9]{2})',
        ('y', 4): r'([0-9]{4})',
        ('M', 1): r'([0-9]{1,2})',
        ('M', 2): r'([0-9]{2})',
        ('M', 3): r'('+'|'.join(calendar.getMonthAbbreviations())+')',
        ('M', 4): r'('+'|'.join(calendar.getMonthNames())+')',
        ('d', 1): r'([0-9]{1,2})',
        ('d', 2): r'([0-9]{2})',
        ('E', 1): r'([0-9])',
        ('E', 2): r'([0-9]{2})',
        ('E', 3): r'('+'|'.join(calendar.getDayAbbreviations())+')',
        ('E', 4): r'('+'|'.join(calendar.getDayNames())+')',
        ('D', 1): r'([0-9]{1,3})',
        ('w', 1): r'([0-9])',
        ('w', 2): r'([0-9]{2})',
        ('h', 1): r'([0-9]{1,2})',
        ('h', 2): r'([0-9]{2})',
        ('H', 1): r'([0-9]{1,2})',
        ('H', 2): r'([0-9]{2})',
        ('m', 1): r'([0-9]{1,2})',
        ('m', 2): r'([0-9]{2})',
        ('s', 1): r'([0-9]{1,2})',
        ('s', 2): r'([0-9]{2})',
        ('S', 1): r'([0-9]{0,6})',
        ('S', 2): r'([0-9]{6})',
        ('F', 1): r'([0-9])',
        ('F', 2): r'([0-9]{1,2})',
        ('W', 1): r'([0-9])',
        ('W', 2): r'([0-9]{2})',
        ('k', 1): r'([0-9]{1,2})',
        ('k', 2): r'([0-9]{2})',
        ('K', 1): r'([0-9]{1,2})',
        ('K', 2): r'([0-9]{2})',
        ('z', 1): r'([\+-][0-9]{3,4})',
        ('z', 2): r'([\+-][0-9]{2}:[0-9]{2})',
        ('z', 3): r'([a-zA-Z]{3})',
        ('z', 4): r'([a-zA-Z /\.]*)',
        }


def buildDateTimeInfo(dt, calendar):
    """Create the bits and pieces of the datetime object that can be put
    together."""
    if isinstance(dt, datetime.time):
        dt = datetime.datetime(1969, 01, 01, dt.hour, dt.minute, dt.second,
                               dt.microsecond)
    elif (isinstance(dt, datetime.date) and
          not isinstance(dt, datetime.datetime)):
        dt = datetime.datetime(dt.year, dt.month, dt.day)

    if dt.hour >= 12:
        ampm = calendar.pm
    else:
        ampm = calendar.am

    h = dt.hour%12
    if h == 0:
        h = 12

    weekday = dt.weekday()+1

    return {
        ('a', 1): ampm,
        ('G', 1): 'AD',
        ('y', 2): str(dt.year)[2:],
        ('y', 4): str(dt.year),
        ('M', 1): str(dt.month),
        ('M', 2): "%.2i" %dt.month,
        ('M', 3): calendar.months[dt.month][1],
        ('M', 4): calendar.months[dt.month][0],
        ('d', 1): str(dt.day),
        ('d', 2): "%.2i" %dt.day,
        ('E', 1): str(weekday),
        ('E', 2): "%.2i" %weekday,
        ('E', 3): calendar.days[weekday][1],
        ('E', 4): calendar.days[weekday][0],
        ('D', 1): dt.strftime('%j'),
        ('w', 1): dt.strftime('%W'),
        ('w', 2): dt.strftime('%.2W'),
        ('h', 1): str(h),
        ('h', 2): "%.2i" %(h),
        ('H', 1): str(dt.hour),
        ('H', 2): "%.2i" %dt.hour,
        ('m', 1): str(dt.minute),
        ('m', 2): "%.2i" %dt.minute,
        ('s', 1): str(dt.second),
        ('s', 2): "%.2i" %dt.second,
        ('S', 1): str(dt.microsecond),
        ('S', 2): "%.6i" %dt.microsecond,
        # TODO: Implement the following symbols. This requires the handling of
        # timezones.
        ('F', 1): str(2),
        ('F', 2): "%.2i" %(2),
        ('W', 1): str(2),
        ('W', 2): "%.2i" %(2),
        ('k', 1): str(dt.hour+1),
        ('k', 2): "%.2i" %(dt.hour+1),
        ('K', 1): str(dt.hour%12),
        ('K', 2): "%.2i" %(dt.hour%12),
        ('z', 1): "+000",
        ('z', 2): "+00:00",
        ('z', 3): "UTC",
        ('z', 4): "Greenwich Time",
            }


# Number Pattern Parser States
BEGIN = 0
READ_PADDING_1 = 1
READ_PREFIX = 2
READ_PREFIX_STRING = 3
READ_PADDING_2 = 4
READ_INTEGER = 5
READ_FRACTION = 6
READ_EXPONENTIAL = 7
READ_PADDING_3 = 8
READ_SUFFIX = 9
READ_SUFFIX_STRING = 10
READ_PADDING_4 = 11
READ_NEG_SUBPATTERN = 12

# Binary Pattern Locators
PADDING1 = 0
PREFIX = 1
PADDING2 = 2
INTEGER = 3
FRACTION = 4
EXPONENTIAL = 5
PADDING3 = 6
SUFFIX = 7
PADDING4 = 8
GROUPING = 9

class NumberPatternParseError(Exception):
    """Number Pattern Parse Error"""


def parseNumberPattern(pattern):
    """Parses all sorts of number pattern."""
    prefix = ''
    padding_1 = None
    padding_2 = None
    padding_3 = None
    padding_4 = None
    integer = ''
    fraction = ''
    exponential = ''
    suffix = ''
    grouping = 0
    neg_pattern = None

    SPECIALCHARS = "*.,#0;E'"

    length = len(pattern)
    state = BEGIN
    helper = ''
    for pos in range(length):
        char = pattern[pos]
        if state == BEGIN:
            if char == '*':
                state = READ_PADDING_1
            elif char not in SPECIALCHARS:
                state = READ_PREFIX
                prefix += char
            elif char == "'":
                state = READ_PREFIX_STRING
            elif char in '#0':
                state = READ_INTEGER
                helper += char
            else:
                raise NumberPatternParseError, \
                      'Wrong syntax at beginning of pattern.'

        elif state == READ_PADDING_1:
            padding_1 = char
            state = READ_PREFIX

        elif state == READ_PREFIX:
            if char == "*":
                state = READ_PADDING_2
            elif char == "'":
                state = READ_PREFIX_STRING
            elif char == "#" or char == "0":
                state = READ_INTEGER
                helper += char
            else:
                prefix += char

        elif state == READ_PREFIX_STRING:
            if char == "'":
                state = READ_PREFIX
            else:
                prefix += char

        elif state == READ_PADDING_2:
            padding_2 = char
            state = READ_INTEGER

        elif state == READ_INTEGER:
            if char == "#" or char == "0":
                helper += char
            elif char == ",":
                grouping = 1
            elif char == ".":
                integer = helper
                helper = ''
                state = READ_FRACTION
            elif char == "E":
                integer = helper
                helper = ''
                state = READ_EXPONENTIAL
            elif char == "*":
                integer = helper
                helper = ''
                state = READ_PADDING_3
            elif char == ";":
                integer = helper
                state = READ_NEG_SUBPATTERN
            elif char == "'":
                integer = helper
                state = READ_SUFFIX_STRING
            else:
                integer = helper
                suffix += char
                state = READ_SUFFIX

        elif state == READ_FRACTION:
            if char == "#" or char == "0":
                helper += char
            elif char == "E":
                fraction = helper
                helper = ''
                state = READ_EXPONENTIAL
            elif char == "*":
                fraction = helper
                helper = ''
                state = READ_PADDING_3
            elif char == ";":
                fraction = helper
                state = READ_NEG_SUBPATTERN
            elif char == "'":
                fraction = helper
                state = READ_SUFFIX_STRING
            else:
                fraction = helper
                suffix += char
                state = READ_SUFFIX

        elif state == READ_EXPONENTIAL:
            if char in ('0', '#', '+'):
                helper += char
            elif char == "*":
                exponential = helper
                helper = ''
                state = READ_PADDING_3
            elif char == ";":
                exponential = helper
                state = READ_NEG_SUBPATTERN
            elif char == "'":
                exponential = helper
                state = READ_SUFFIX_STRING
            else:
                exponential = helper
                suffix += char
                state = READ_SUFFIX

        elif state == READ_PADDING_3:
            padding_3 = char
            state = READ_SUFFIX

        elif state == READ_SUFFIX:
            if char == "*":
                state = READ_PADDING_4
            elif char == "'":
                state = READ_SUFFIX_STRING
            elif char == ";":
                state = READ_NEG_SUBPATTERN
            else:
                suffix += char

        elif state == READ_SUFFIX_STRING:
            if char == "'":
                state = READ_SUFFIX
            else:
                suffix += char

        elif state == READ_PADDING_4:
            if char == ';':
                state = READ_NEG_SUBPATTERN
            else:
                padding_4 = char

        elif state == READ_NEG_SUBPATTERN:
            neg_pattern = parseNumberPattern(pattern[pos:])[0]
            break

    # Cleaning up states after end of parsing
    if state == READ_INTEGER:
        integer = helper
    if state == READ_FRACTION:
        fraction = helper
    if state == READ_EXPONENTIAL:
        exponential = helper

    pattern = (padding_1, prefix, padding_2, integer, fraction, exponential,
               padding_3, suffix, padding_4, grouping)

    if neg_pattern is None:
        neg_pattern = pattern

    return pattern, neg_pattern


