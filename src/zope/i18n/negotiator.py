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
"""Language Negotiator

$Id$
"""
from zope.i18n.interfaces import INegotiator
from zope.i18n.interfaces import IUserPreferredLanguages
from zope.interface import implements

def normalize_lang(lang):
    lang = lang.strip().lower()
    lang = lang.replace('_', '-')
    lang = lang.replace(' ', '')
    return lang

def normalize_langs(langs):
    # Make a mapping from normalized->original so we keep can match
    # the normalized lang and return the original string.
    n_langs = {}
    for l in langs:
        n_langs[normalize_lang(l)] = l
    return n_langs

class Negotiator(object):
    implements(INegotiator)

    def getLanguage(self, langs, env):
        envadapter = IUserPreferredLanguages(env)
        userlangs = envadapter.getPreferredLanguages()
        # Prioritize on the user preferred languages.  Return the
        # first user preferred language that the object has available.
        langs = normalize_langs(langs)
        for lang in userlangs:
            if lang in langs:
                return langs.get(lang)
            # If the user asked for a specific variation, but we don't
            # have it available we may serve the most generic one,
            # according to the spec (eg: user asks for ('en-us',
            # 'de'), but we don't have 'en-us', then 'en' is preferred
            # to 'de').
            parts = lang.split('-')
            if len(parts) > 1 and parts[0] in langs:
                return langs.get(parts[0])
        return None


negotiator = Negotiator()
