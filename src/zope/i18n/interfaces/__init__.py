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
"""Internationalization of content objects.

$Id$
"""
from zope.interface import Interface, Attribute
from zope.schema import TextLine, Dict, Choice


class II18nAware(Interface):
    """Internationalization aware content object."""

    def getDefaultLanguage():
        """Return the default language."""

    def setDefaultLanguage(language):
        """Set the default language, which will be used if the language is not
        specified, or not available.
        """

    def getAvailableLanguages():
        """Find all the languages that are available."""


class IMessageCatalog(Interface):
    """A catalog (mapping) of message ids to message text strings.

    This interface provides a method for translating a message or message id,
    including text with interpolation.  The message catalog basically serves
    as a fairly simple mapping object.

    A single message catalog represents a specific language and domain.
    Therefore you will have the following constructor arguments:

    language -- The language of the returned messages.  This is a read-only
                attribute.

    domain -- The translation domain for these messages.  This is a read-only
              attribute.  See ITranslationService.

    When we refer to text here, we mean text that follows the standard Zope 3
    text representation.

    Note: The IReadMessageCatalog is the absolut minimal version required for
          the TranslationService to function.
    """

    def getMessage(msgid):
        """Get the appropriate text for the given message id.

        An exception is raised if the message id is not found.
        """

    def queryMessage(msgid, default=None):
        """Look for the appropriate text for the given message id.

        If the message id is not found, default is returned.
        """

    language = TextLine(
        title=u"Language",
        description=u"The language the catalog translates to.",
        required=True)

    domain = TextLine(
        title=u"Domain",
        description=u"The domain the catalog is registered for.",
        required=True)

    def getIdentifier():
        """Return a identifier for this message catalog. Note that this
        identifier does not have to be unique as several message catalog
        could serve the same domain and language.

        Also, there are no restrictions on the form of the identifier.
        """


class IGlobalMessageCatalog(IMessageCatalog):

    def reload():
        """Reload and parse .po file"""


class ITranslationDomain(Interface):
    """The Translation Domain utility

    This interface provides methods for translating text, including text with
    interpolation.

    When we refer to text here, we mean text that follows the standard Zope 3
    text representation.

    The domain is used to specify which translation to use.  Different
    products will often use a specific domain naming translations supplied
    with the product.
    
    A favorite example is: How do you translate 'Sun'? Is it our star, the
    abbreviation of Sunday or the company?  Specifying the domain, such as
    'Stars' or 'DaysOfWeek' will solve this problem for us.

    Standard arguments in the methods described below:

        msgid -- The id of the message that should be translated.  This may be
                 an implicit or an explicit message id.

        mapping -- The object to get the interpolation data from.

        target_language -- The language to translate to.

        context -- An object that provides contextual information for
                   determining client language preferences.  It must implement
                   or have an adapter that implements IUserPreferredLanguages.
                   It will be to determine the language to translate to if
                   target_language is not specified explicitly.

        Also note that language tags are defined by RFC 1766.
    """

    domain = TextLine(
        title=u"Domain Name",
        description=u"The name of the domain this object represents.",
        required=True)

    def translate(msgid, mapping=None, context=None, target_language=None,
                  default=None):
        """Return the translation for the message referred to by msgid.

        Return the default if no translation is found.

        However, the method does a little more than a vanilla translation.
        The method also looks for a possible language to translate to.
        After a translation it also replaces any $name variable variables
        inside the post-translation string.

        Note: The TranslationDomain interface does not support simplified
        translation methods, since it is totally hidden by ZPT and in
        Python you should use a Domain object, since it supports all
        the simplifications.
        """


class ITranslator(Interface):
    """A collaborative object which contains the domain, context, and locale.

    It is expected that object be constructed with enough information to find
    the domain, context, and target language.
    """

    def translate(msgid, mapping=None, default=None):
        """Translate the source msgid using the given mapping.

        See ITranslationService for details.
        """


class IMessageImportFilter(Interface):
    """The Import Filter for Translation Service Messages.

       Classes implementing this interface should usually be Adaptors, as
       they adapt the IEditableTranslationService interface."""


    def importMessages(domains, languages, file):
        """Import all messages that are defined in the specified domains and
           languages.

           Note that some implementations might limit to only one domain and
           one language. A good example for that is a GettextFile.
        """


class ILanguageAvailability(Interface):

    def getAvailableLanguages():
        """Return a sequence of language tags for available languages
        """


class IUserPreferredLanguages(Interface):
    """This interface provides language negotiation based on user preferences.

    See: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.4
    """

    def getPreferredLanguages():
        """Return a sequence of user preferred languages.
        """


class IMessageExportFilter(Interface):
    """The Export Filter for Translation Service Messages.

       Classes implementing this interface should usually be Adaptors, as
       they adapt the IEditableTranslationService interface."""


    def exportMessages(domains, languages):
        """Export all messages that are defined in the specified domains and
           languages.

           Note that some implementations might limit to only one domain and
           one language. A good example for that is a GettextFile.
        """


class INegotiator(Interface):
    """A language negotiation service.
    """

    def getLanguage(langs, env):
        """Return the matching language to use.

        The decision of which language to use is based on the list of
        available languages, and the given user environment.  An
        IUserPreferredLanguages adapter for the environment is obtained and
        the list of acceptable languages is retrieved from the environment.

        If no match is found between the list of available languages and the
        list of acceptable languages, None is returned.

        Arguments:

        langs -- sequence of languages (not necessarily ordered)

        env  -- environment passed to the service to determine a sequence
                of user prefered languages
        """

        # TODO: I'd like for there to be a symmetric interface method, one in
        # which an adapter is gotten for both the first arg and the second
        # arg.  I.e. getLanguage(obj, env)
        # But this isn't a good match for the ITranslationService.translate()
        # method. :(


class IUserPreferredCharsets(Interface):
    """This interface provides charset negotiation based on user preferences.
    """

    def getPreferredCharsets():
        """Return a sequence of user preferred charsets. Note that the order
           should describe the order of preference. Therefore the first
           character set in the list is the most preferred one.
        """


class IFormat(Interface):
    """A generic formatting class. It basically contains the parsing and
    construction method for the particular object the formatting class
    handles.

    The constructor will always require a pattern (specific to the object).
    """

    def setPattern(pattern):
        """Overwrite the old formatting pattern with the new one."""

    def getPattern():
        """Get the currently used pattern."""

    def parse(text, pattern=None):
        """Parse the text and convert it to an object, which is returned."""

    def format(obj, pattern=None):
        """Format an object to a string using the pattern as a rule."""



class INumberFormat(IFormat):
    u"""Specific number formatting interface. Here are the formatting
    rules (I modified the rules from ICU a bit, since I think they did not
    agree well with the real world XML formatting strings):

      posNegPattern      := ({subpattern};{subpattern} | {subpattern})
      subpattern         := {padding}{prefix}{padding}{integer}{fraction}
                            {exponential}{padding}{suffix}{padding}
      prefix             := '\u0000'..'\uFFFD' - specialCharacters *
      suffix             := '\u0000'..'\uFFFD' - specialCharacters *
      integer            := {digitField}'0'
      fraction           := {decimalPoint}{digitField}
      exponential        := E integer
      digitField         := ( {digitField} {groupingSeparator} |
                              {digitField} '0'* |
                              '0'* |
                              {optionalDigitField} )
      optionalDigitField := ( {digitField} {groupingSeparator} |
                              {digitField} '#'* |
                              '#'* )
      groupingSeparator  := ,
      decimalPoint       := .
      padding            := * '\u0000'..'\uFFFD'


    Possible pattern symbols:

      0    A digit. Always show this digit even if the value is zero.
      #    A digit, suppressed if zero
      .    Placeholder for decimal separator
      ,    Placeholder for grouping separator
      E    Separates mantissa and exponent for exponential formats
      ;    Separates formats (that is, a positive number format verses a
           negative number format)
      -    Default negative prefix. Note that the locale's minus sign
           character is used.
      +    If this symbol is specified the locale's plus sign character is
           used.
      %    Multiply by 100, as percentage
      ?    Multiply by 1000, as per mille
      \u00A4    This is the currency sign. it will be replaced by a currency
           symbol. If it is present in a pattern, the monetary decimal
           separator is used instead of the decimal separator.
      \u00A4\u00A4   This is the international currency sign. It will be replaced
           by an international currency symbol.  If it is present in a
           pattern, the monetary decimal separator is used instead of
           the decimal separator.
      X    Any other characters can be used in the prefix or suffix
      '    Used to quote special characters in a prefix or suffix
    """

    symbols = Dict(
        title=u"Number Symbols",
        key_type=Choice(
            title=u"Dictionary Class",
            values=(u'decimal', u'group', u'list', u'percentSign',
                    u'nativeZeroDigit', u'patternDigit', u'plusSign',
                    u'minusSign', u'exponential', u'perMille',
                    u'infinity', u'nan')),
        value_type=TextLine(title=u"Symbol"))


class IDateTimeFormat(IFormat):
    """DateTime formatting and parsing interface. Here is a list of
    possible characters and their meaning:

      Symbol Meaning               Presentation      Example

      G      era designator        (Text)            AD
      y      year                  (Number)          1996
      M      month in year         (Text and Number) July and 07
      d      day in month          (Number)          10
      h      hour in am/pm (1~12)  (Number)          12
      H      hour in day (0~23)    (Number)          0
      m      minute in hour        (Number)          30
      s      second in minute      (Number)          55
      S      millisecond           (Number)          978
      E      day in week           (Text)            Tuesday
      D      day in year           (Number)          189
      F      day of week in month  (Number)          2 (2nd Wed in July)
      w      week in year          (Number)          27
      W      week in month         (Number)          2
      a      am/pm marker          (Text)            pm
      k      hour in day (1~24)    (Number)          24
      K      hour in am/pm (0~11)  (Number)          0
      z      time zone             (Text)            Pacific Standard Time
      '      escape for text
      ''     single quote                            '

    Meaning of the amount of characters:

      Text

        Four or more, use full form, <4, use short or abbreviated form if it
        exists. (for example, "EEEE" produces "Monday", "EEE" produces "Mon")

      Number

        The minimum number of digits. Shorter numbers are zero-padded to this
        amount (for example, if "m" produces "6", "mm" produces "06"). Year is
        handled specially; that is, if the count of 'y' is 2, the Year will be
        truncated to 2 digits. (for example, if "yyyy" produces "1997", "yy"
        produces "97".)

      Text and Number

        Three or over, use text, otherwise use number. (for example, "M"
        produces "1", "MM" produces "01", "MMM" produces "Jan", and "MMMM"
        produces "January".)  """

    calendar = Attribute("""This object must implement ILocaleCalendar. See
                            this interface's documentation for details.""")


