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
"""Test of the Choice field.

$Id$
"""
import unittest

from zope.schema import vocabulary
from zope.schema import Choice
from zope.schema.interfaces import ConstraintNotSatisfied
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import InvalidValue, NotAContainer, NotUnique

from test_vocabulary import SampleVocabulary, DummyRegistry


class Value_ChoiceFieldTests(unittest.TestCase):
    """Tests of the Choice Field using values."""

    def test_create_vocabulary(self):
        choice = Choice(values=[1, 3])
        self.assertEqual([term.value for term in choice.vocabulary], [1, 3])

    def test_validate_int(self):
        choice = Choice(values=[1, 3])
        choice.validate(1)
        choice.validate(3)
        self.assertRaises(ConstraintNotSatisfied, choice.validate, 4)

    def test_validate_string(self):
        choice = Choice(values=['a', 'c'])
        choice.validate('a')
        choice.validate('c')
        choice.validate(u'c')
        self.assertRaises(ConstraintNotSatisfied, choice.validate, 'd')

    def test_validate_tuple(self):
        choice = Choice(values=[(1, 2), (5, 6)])
        choice.validate((1, 2))
        choice.validate((5, 6))
        self.assertRaises(ConstraintNotSatisfied, choice.validate, [5, 6])
        self.assertRaises(ConstraintNotSatisfied, choice.validate, ())

    def test_validate_mixed(self):
        choice = Choice(values=[1, 'b', (0.2,)])
        choice.validate(1)
        choice.validate('b')
        choice.validate((0.2,))
        self.assertRaises(ConstraintNotSatisfied, choice.validate, '1')
        self.assertRaises(ConstraintNotSatisfied, choice.validate, 0.2)
    

class Vocabulary_ChoiceFieldTests(unittest.TestCase):
    """Tests of the Choice Field using vocabularies."""

    def setUp(self):
        vocabulary._clear()

    def tearDown(self):
        vocabulary._clear()

    def check_preconstructed(self, cls, okval, badval):
        v = SampleVocabulary()
        field = cls(vocabulary=v)
        self.assert_(field.vocabulary is v)
        self.assert_(field.vocabularyName is None)
        bound = field.bind(None)
        self.assert_(bound.vocabulary is v)
        self.assert_(bound.vocabularyName is None)
        bound.default = okval
        self.assertEqual(bound.default, okval)
        self.assertRaises(ValidationError, setattr, bound, "default", badval)

    def test_preconstructed_vocabulary(self):
        self.check_preconstructed(Choice, 1, 42)

    def check_constructed(self, cls, okval, badval):
        vocabulary.setVocabularyRegistry(DummyRegistry())
        field = cls(vocabulary="vocab")
        self.assert_(field.vocabulary is None)
        self.assertEqual(field.vocabularyName, "vocab")
        o = object()
        bound = field.bind(o)
        self.assert_(isinstance(bound.vocabulary, SampleVocabulary))
        bound.default = okval
        self.assertEqual(bound.default, okval)
        self.assertRaises(ValidationError, setattr, bound, "default", badval)

    def test_constructed_vocabulary(self):
        self.check_constructed(Choice, 1, 42)

    def test_create_vocabulary(self):
        vocabulary.setVocabularyRegistry(DummyRegistry())
        field = Choice(vocabulary="vocab")
        o = object()
        bound = field.bind(o)
        self.assertEqual([term.value for term in bound.vocabulary],
                         [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Vocabulary_ChoiceFieldTests))
    suite.addTest(unittest.makeSuite(Value_ChoiceFieldTests))
    return suite

if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
