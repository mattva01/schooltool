##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""Example vocabulary for tab completion.

$Id$
"""
from zope.schema.interfaces import ITerm, IVocabulary, IVocabularyQuery
from zope.interface import implements


class IPrefixQuery(IVocabularyQuery):
    """Interface for prefix queries."""

    def queryForPrefix(prefix):
        """Return a vocabulary that contains terms beginning with
        prefix."""


class Term(object):
    implements(ITerm)

    def __init__(self, value):
        self.value = value


class CompletionVocabulary(object):
    implements(IVocabulary)

    def __init__(self, values):
        # In practice, something more dynamic could be used to
        # get the list possible completions.
        # We force a _values to be a list so we can use .index().
        self._values = list(values)
        self._terms = map(Term, self._values)

    def __contains__(self, value):
        return value in self._values

    def __iter__(self):
        return iter(self._terms)

    def __len__(self):
        return len(self._values)

    def getQuery(self):
        return PrefixQuery(self)

    def getTerm(self, value):
        if value in self._values:
            return self._terms[self._values.index(value)]
        raise LookupError(value)


class PrefixQuery(object):
    implements(IPrefixQuery)

    def __init__(self, vocabulary):
        self.vocabulary = vocabulary

    def queryForPrefix(self, prefix):
        L = [v for v in self.vocabulary._values if v.startswith(prefix)]
        if L:
            return CompletionVocabulary(L)
        else:
            raise LookupError("no entries matching prefix %r" % prefix)
