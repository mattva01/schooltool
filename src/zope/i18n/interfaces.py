##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Internationalization of content objects.

This is just a subset of zope.i18n.interfaces.  Original version was:
  $Id: __init__.py,v 1.5 2004/03/08 23:36:00 srichter Exp $
"""
from zope.interface import Interface, Attribute


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

    domain = Attribute("The name of the domain this object represents.")

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

