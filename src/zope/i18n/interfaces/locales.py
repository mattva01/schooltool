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
"""Interfaces related to Locales

$Id$
"""
import re
from zope.interface import Interface, Attribute
from zope.schema import \
     Field, Text, TextLine, Int, Bool, Tuple, List, Dict, Date
from zope.schema import Container, Choice

class ILocaleProvider(Interface):
    """This interface is our connection to the Zope 3 service. From it
    we can request various Locale objects that can perform all sorts of
    fancy operations.

    This service will be singelton global service, since it doe not make much
    sense to have many locale facilities, especially since this one will be so
    complete, since we will the ICU XML Files as data.  """

    def loadLocale(language=None, country=None, variant=None):
        """Load the locale with the specs that are given by the arguments of
        the method. Note that the LocaleProvider must know where to get the
        locales from."""

    def getLocale(language=None, country=None, variant=None):
        """Get the Locale object for a particular language, country and
        variant."""


class ILocaleIdentity(Interface):
    """Identity information class for ILocale objects.

    Three pieces of information are required to identify a locale:

      o language -- Language in which all of the locale text information are
        returned.

      o script -- Script in which all of the locale text information are
        returned.

      o territory -- Territory for which the locale's information are
        appropriate. None means all territories in which language is spoken.

      o variant -- Sometimes there are regional or historical differences even
        in a certain country. For these cases we use the variant field. A good
        example is the time before the Euro in Germany for example. Therefore
        a valid variant would be 'PREEURO'.

    Note that all of these attributes are read-only once they are set (usually
    done in the constructor)!

    This object is also used to uniquely identify a locale.
    """

    language = TextLine(
        title = u"Language Type",
        description = u"The language for which a locale is applicable.",
        constraint = re.compile(r'[a-z]{2}').match,
        required = True,
        readonly = True)

    script = TextLine(
        title = u"Script Type",
        description = u"""The script for which the language/locale is
                       applicable.""",
        constraint = re.compile(r'[a-z]*').match)

    territory = TextLine(
        title = u"Territory Type",
        description = u"The territory for which a locale is applicable.",
        constraint = re.compile(r'[A-Z]{2}').match,
        required = True,
        readonly = True)

    variant = TextLine(
        title = u"Variant Type",
        description = u"The variant for which a locale is applicable.",
        constraint = re.compile(r'[a-zA-Z]*').match,
        required = True,
        readonly = True)

    version = Field(
        title = u"Locale Version",
        description = u"The value of this field is an ILocaleVersion object.",
        readonly = True)
        
    def __repr__(self):
        """Defines the representation of the id, which should be a compact
        string that references the language, country and variant."""


class ILocaleVersion(Interface):
    """Represents the version of a locale.

    The locale version is part of the ILocaleIdentity object.
    """
    
    number = TextLine(
        title = u"Version Number",
        description = u"The version number of the locale.",
        constraint = re.compile(r'^([0-9].)*[0-9]$').match,
        required = True,
        readonly = True)

    generationDate = Date(
        title = u"Generation Date",
        description = u"Specifies the creation date of the locale.",
        constraint = lambda date: date < datetime.now(),
        readonly = True)

    notes = Text(
        title = u"Notes",
        description = u"Some release notes for the version of this locale.",
        readonly = True)


class ILocaleDisplayNames(Interface):
    """Localized Names of common text strings.

    This object contains localized strings for many terms, including
    language, script and territory names. But also keys and types used
    throughout the locale object are localized here.
    """
    
    languages = Dict(
        title = u"Language type to translated name",
        key_type = TextLine(title=u"Language Type"),
        value_type = TextLine(title=u"Language Name"))

    scripts = Dict(
        title = u"Script type to script name",
        key_type = TextLine(title=u"Script Type"),
        value_type = TextLine(title=u"Script Name"))

    territories = Dict(
        title = u"Territory type to translated territory name",
        key_type = TextLine(title=u"Territory Type"),
        value_type = TextLine(title=u"Territory Name"))

    variants = Dict(
        title = u"Variant type to name",
        key_type = TextLine(title=u"Variant Type"),
        value_type = TextLine(title=u"Variant Name"))

    keys = Dict(
        title = u"Key type to name",
        key_type = TextLine(title=u"Key Type"),
        value_type = TextLine(title=u"Key Name"))

    types = Dict(
        title = u"Type type and key to localized name",
        key_type = Tuple(title=u"Type Type and Key"),
        value_type = TextLine(title=u"Type Name"))


class ILocaleTimeZone(Interface):
    """Represents and defines various timezone information. It mainly manages
    all the various names for a timezone and the cities contained in it.

    Important: ILocaleTimeZone objects are not intended to provide
    implementations for the standard datetime module timezone support. They
    are merily used for Locale support.
    """

    type = TextLine(
        title = u"Time Zone Type",
        description = u"Standard name of the timezone for unique referencing.",
        required = True,
        readonly = True)

    cities = List(
        title = u"Cities",
        description = u"Cities in Timezone",
        value_type = TextLine(title=u"City Name"),
        required = True,
        readonly = True)


    names = Dict(
        title = u"Time Zone Names",
        description = u"Various names of the timezone.",
        key_type = Choice(
                   title = u"Time Zone Name Type",
                   values = (u'generic', u'standard', u'daylight')),
        value_type = Tuple(title=u"Time Zone Name and Abbreviation",
                           min_length=2, max_length=2),
        required = True,
        readonly = True)


class ILocaleFormat(Interface):
    """Specifies a format for a particular type of data."""

    type = TextLine(
        title=u"Format Type",
        description=u"The name of the format",
        required = False,
        readonly = True)

    displayName = TextLine(
        title = u"Display Name",
        description = u"Name of the calendar, for example 'gregorian'.",
        required = False,
        readonly = True)

    pattern = TextLine(
        title = u"Format Pattern",
        description = u"The pattern that is used to format the object.",
        required = True,
        readonly = True)


class ILocaleFormatLength(Interface):
    """The format length describes a class of formats."""
    
    type = Choice(
        title = u"Format Length Type",
        description = u"Name of the format length",
        values = (u'full', u'long', u'medium', u'short')
        )

    default = TextLine(
        title=u"Default Format",
        description=u"The name of the defaulkt format.")

    formats = Dict(
        title = u"Formats",
        description = u"Maps format types to format objects",
        key_type = TextLine(title = u"Format Type"),
        value_type = Field(
                         title = u"Format Object",
                         description = u"Values are ILocaleFormat objects."),
        required = True,
        readonly = True)


class ILocaleCalendar(Interface):
    """There is a massive amount of information contained in the calendar,
    which made it attractive to be added."""

    type = TextLine(
        title=u"Calendar Type",
        description=u"Name of the calendar, for example 'gregorian'.")

    months = Dict(
        title = u"Month Names",
        description = u"A mapping of all month names and abbreviations",
        key_type = Int(title=u"Type", min=1, max=12),
        value_type = Tuple(title=u"Month Name and Abbreviation",
                           min_length=2, max_length=2))

    days = Dict(
        title=u"Weekdays Names",
        description = u"A mapping of all month names and abbreviations",
        key_type = Choice(title=u"Type",
                            values=(u'sun', u'mon', u'tue', u'wed',
                                    u'thu', u'fri', u'sat')),
        value_type = Tuple(title=u"Weekdays Name and Abbreviation",
                           min_length=2, max_length=2))

    week = Dict(
        title=u"Week Information",
        description = u"Contains various week information",
        key_type = Choice(
            title=u"Type",
            description=u"""
            Varies Week information:

              - 'minDays' is just an integer between 1 and 7.

              - 'firstDay' specifies the first day of the week by integer.

              - The 'weekendStart' and 'weekendEnd' are tuples of the form
                (weekDayNumber, datetime.time)
            """,
            values=(u'minDays', u'firstDay',
                            u'weekendStart', u'weekendEnd')))

    am = TextLine(title=u"AM String")

    pm = TextLine(title=u"PM String")

    eras = Dict(
        title = u"Era Names",
        key_type = Int(title=u"Type", min=0),
        value_type = Tuple(title=u"Era Name and Abbreviation",
                           min_length=2, max_length=2))

    defaultDateFormat = TextLine(title=u"Default Date Format Type")

    dateFormats = Dict(
        title=u"Date Formats",
        description = u"Contains various Date Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    defaultTimeFormat = TextLine(title=u"Default Time Format Type")

    timeFormats = Dict(
        title=u"Time Formats",
        description = u"Contains various Time Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    defaultDateTimeFormat = TextLine(title=u"Default Date-Time Format Type")

    dateTimeFormats = Dict(
        title=u"Date-Time Formats",
        description = u"Contains various Date-Time Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    def getMonthNames():
        """Return a list of month names."""

    def getMonthTypeFromName(name):
        """Return the type of the month with the right name."""

    def getMonthAbbreviations():
        """Return a list of month abbreviations."""

    def getMonthTypeFromAbbreviation(abbr):
        """Return the type of the month with the right abbreviation."""

    def getDayNames():
        """Return a list of weekday names."""

    def getDayTypeFromName(name):
        """Return the id of the weekday with the right name."""

    def getDayAbbr():
        """Return a list of weekday abbreviations."""

    def getDayTypeFromAbbr(abbr):
        """Return the id of the weekday with the right abbr."""

    def isWeekend(datetime):
        """Determines whether a the argument lies in a weekend."""

    def getFirstDayName():
        """Return the the type of the first day in the week.""" 


class ILocaleDates(Interface):
    """This object contains various data about dates, times and time zones."""

    localizedPatternChars = TextLine(
        title = u"Localized Pattern Characters",
        description = u"Localized pattern characters used in dates and times")

    calendars = Dict(
        title = u"Calendar type to ILocaleCalendar",
        key_type = Choice(
            title=u"Calendar Type",
            values=(u'gregorian',
                            u'arabic',
                            u'chinese',
                            u'civil-arabic',
                            u'hebrew',
                            u'japanese',
                            u'thai-buddhist')),
        value_type=Field(title=u"Calendar",
                         description=u"This is a ILocaleCalendar object."))

    timezones = Dict(
        title=u"Time zone type to ILocaleTimezone",
        key_type=TextLine(title=u"Time Zone type"),
        value_type=Field(title=u"Time Zone",
                         description=u"This is a ILocaleTimeZone object."))

    def getFormatter(category, length=None, name=None, calendar=u'gregorian'):
        """Get a date/time formatter."""


class ILocaleCurrency(Interface):
    """Defines a particular currency."""

    type = TextLine(title=u'Type')

    symbol = TextLine(title=u'Symbol')

    displayName = TextLine(title=u'Official Name')

    symbolChoice = Bool(title=u'Symbol Choice') 

class ILocaleNumbers(Interface):
    """This object contains various data about numbers and currencies."""

    symbols = Dict(
        title = u"Number Symbols",
        key_type = Choice(
            title = u"Format Name",
            values = (u'decimal', u'group', u'list', u'percentSign',
                              u'nativeZeroDigit', u'patternDigit', u'plusSign',
                              u'minusSign', u'exponential', u'perMille',
                              u'infinity', u'nan')),
        value_type=TextLine(title=u"Symbol"))

    defaultDecimalFormat = TextLine(title=u"Default Decimal Format Type")

    decimalFormats = Dict(
        title=u"Decimal Formats",
        description = u"Contains various Decimal Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    defaultScientificFormat = TextLine(title=u"Default Scientific Format Type")

    scientificFormats = Dict(
        title=u"Scientific Formats",
        description = u"Contains various Scientific Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    defaultPercentFormat = TextLine(title=u"Default Percent Format Type")

    percentFormats = Dict(
        title=u"Percent Formats",
        description = u"Contains various Percent Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    defaultCurrencyFormat = TextLine(title=u"Default Currency Format Type")

    currencyFormats = Dict(
        title=u"Currency Formats",
        description = u"Contains various Currency Formats.",
        key_type = Choice(
                      title=u"Type",
                      description = u"Name of the format length",
                      values = (u'full', u'long', u'medium', u'short')),
        value_type = Field(title=u"ILocaleFormatLength object"))

    currencies = Dict(
        title=u"Currencies",
        description = u"Contains various Currency data.",
        key_type = TextLine(
                      title=u"Type",
                      description = u"Name of the format length"),
        value_type = Field(title=u"ILocaleCurrency object"))


    def getFormatter(category, length=None, name=u''):
        """Get the NumberFormat based on the category, length and name of the
        format.

        The 'category' specifies the type of number format you would like to
        have. The available options are: 'decimal', 'percent', 'scientific',
        'currency'.

        The 'length' specifies the output length of the number. The allowed
        values are: 'short', 'medium', 'long' and 'full'. If no length was
        specified, the default length is chosen.

        Every length can have actually several formats. In this case these
        formats are named and you can specify the name here. If no name was
        specified, the first unnamed format is chosen.
        """

    def getDefaultCurrency():
        """Get the default currency."""


class ILocale(Interface):
    """This class contains all important information about the locale.

    Usually a Locale is identified using a specific language, country and
    variant.  However, the country and variant are optional, so that a lookup
    hierarchy develops.  It is easy to recognize that a locale that is missing
    the variant is more general applicable than the one with the variant.
    Therefore, if a specific Locale does not contain the required information,
    it should look one level higher.  There will be a root locale that
    specifies none of the above identifiers.
    """

    id = Field(
        title = u"Locale identity",
        description = u"ILocaleIdentity object identifying the locale.",
        required = True,
        readonly = True)

    displayNames = Field(
        title = u"Display Names",
        description = u"""ILocaleDisplayNames object that contains localized
                        names.""")

    dates = Field(
        title = u"Dates",
        description = u"ILocaleDates object that contains date/time data.")

    numbers = Field(
        title = u"Numbers",
        description = u"ILocaleNumbers object that contains number data.")

    delimiters = Dict(
        title=u"Delimiters",
        description = u"Contains various Currency data.",
        key_type = Choice(
            title=u"Delimiter Type",
            description = u"Delimiter name.",
            values=(u'quotationStart', u'quotationEnd',
                            u'alternateQuotationStart',
                            u'alternateQuotationEnd')),
        value_type = Field(title=u"Delimiter symbol"))

    def getLocaleID():
        """Return a locale id as specified in the LDML specification"""


class ILocaleInheritance(Interface):
    """Locale inheritance support.

    Locale-related objects implementing this interface are able to ask for its
    inherited self. For example, 'en_US.dates.monthNames' can call on itself
    'getInheritedSelf()' and get the value for 'en.dates.monthNames'. 
    """

    __parent__ = Attribute("The parent in the location hierarchy")

    __name__ = TextLine(
        title = u"The name within the parent",
        description=u"""The parent can be traversed with this name to get
                      the object.""")

    def getInheritedSelf():
        """Return itself but in the next higher up Locale."""


class IAttributeInheritance(ILocaleInheritance):
    """Provides inheritance properties for attributes"""

    def __setattr__(name, value):
        """Set a new attribute on the object.

        When a value is set on any inheritance-aware object and the value
        also implements ILocaleInheritance, then we need to set the
        '__parent__' and '__name__' attribute on the value.
        """

    def __getattributes__(name):
        """Return the value of the attribute with the specified name.

        If an attribute is not found or is None, the next higher up Locale
        object is consulted."""


class IDictionaryInheritance(ILocaleInheritance):
    """Provides inheritance properties for dictionary keys"""

    def __setitem__(key, value):
        """Set a new item on the object.

        Here we assume that the value does not require any inheritance, so
        that we do not set '__parent__' or '__name__' on the value.
        """

    def __getitem__(key):
        """Return the value of the item with the specified name.

        If an key is not found or is None, the next higher up Locale
        object is consulted.
        """
