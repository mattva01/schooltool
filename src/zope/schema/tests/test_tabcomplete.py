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
"""Tests of the 'tab completion' example vocabulary.

$Id$
"""
import unittest

from zope.schema.interfaces import ITerm, IVocabularyQuery
from zope.schema.tests import tabcomplete


class TabCompletionTests(unittest.TestCase):

    def setUp(self):
        self.vocab = tabcomplete.CompletionVocabulary(['abc', 'def'])

    def test_successful_query(self):
        query = self.vocab.getQuery()
        subset = query.queryForPrefix("a")
        L = [term.value for term in subset]
        self.assertEqual(L, ["abc"])
        subset = query.queryForPrefix("def")
        L = [term.value for term in subset]
        self.assertEqual(L, ["def"])

    def test_failed_query(self):
        query = self.vocab.getQuery()
        self.assertRaises(LookupError, query.queryForPrefix, "g")

    def test_query_interface(self):
        query = self.vocab.getQuery()
        self.assert_(IVocabularyQuery.providedBy(query))

    def test_getTerm(self):
        term = self.vocab.getTerm("abc")
        self.assert_(ITerm.providedBy(term))
        self.assertEqual(term.value, "abc")


def test_suite():
    return unittest.makeSuite(TabCompletionTests)

if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
