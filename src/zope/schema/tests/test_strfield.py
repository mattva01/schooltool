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
"""String field tests

$Id$
"""
from unittest import TestSuite, main, makeSuite
from zope.schema import Bytes, BytesLine, Text, TextLine
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import RequiredMissing, InvalidValue
from zope.schema.interfaces import TooShort, TooLong, ConstraintNotSatisfied
from zope.schema.tests.test_field import FieldTestBase

class StrTest(FieldTestBase):
    """Test the Str Field."""

    def testValidate(self):
        field = self._Field_Factory(title=u'Str field', description=u'',
                                    readonly=False, required=False)
        field.validate(None)
        field.validate(self._convert('foo'))
        field.validate(self._convert(''))

    def testValidateRequired(self):

        # Note that if we want to require non-empty strings,
        # we need to set the min-length to 1.

        field = self._Field_Factory(
            title=u'Str field', description=u'',
            readonly=False, required=True, min_length=1)
        field.validate(self._convert('foo'))

        self.assertRaises(RequiredMissing, field.validate, None)
        self.assertRaises(TooShort, field.validate, self._convert(''))

    def testValidateMinLength(self):
        field = self._Field_Factory(
            title=u'Str field', description=u'',
            readonly=False, required=False, min_length=3)
        field.validate(None)
        field.validate(self._convert('333'))
        field.validate(self._convert('55555'))

        self.assertRaises(TooShort, field.validate, self._convert(''))
        self.assertRaises(TooShort, field.validate, self._convert('22'))
        self.assertRaises(TooShort, field.validate, self._convert('1'))

    def testValidateMaxLength(self):
        field = self._Field_Factory(
            title=u'Str field', description=u'',
            readonly=False, required=False, max_length=5)
        field.validate(None)
        field.validate(self._convert(''))
        field.validate(self._convert('333'))
        field.validate(self._convert('55555'))

        self.assertRaises(TooLong, field.validate, self._convert('666666'))
        self.assertRaises(TooLong, field.validate, self._convert('999999999'))

    def testValidateMinLengthAndMaxLength(self):
        field = self._Field_Factory(
            title=u'Str field', description=u'',
            readonly=False, required=False,
            min_length=3, max_length=5)

        field.validate(None)
        field.validate(self._convert('333'))
        field.validate(self._convert('4444'))
        field.validate(self._convert('55555'))

        self.assertRaises(TooShort, field.validate, self._convert('22'))
        self.assertRaises(TooShort, field.validate, self._convert('22'))
        self.assertRaises(TooLong, field.validate, self._convert('666666'))
        self.assertRaises(TooLong, field.validate, self._convert('999999999'))


class MultiLine(object):

    def test_newlines(self):
        field = self._Field_Factory(title=u'Str field')
        field.validate(self._convert('hello\nworld'))


class BytesTest(StrTest, MultiLine):
    _Field_Factory = Bytes
    _convert = str

    def testBadStringType(self):
        field = self._Field_Factory()
        self.assertRaises(ValidationError, field.validate, u'hello')


class TextTest(StrTest, MultiLine):
    _Field_Factory = Text
    def _convert(self, v):
        return unicode(v, 'ascii')

    def testBadStringType(self):
        field = self._Field_Factory()
        self.assertRaises(ValidationError, field.validate, 'hello')

class SingleLine(object):

    def test_newlines(self):
        field = self._Field_Factory(title=u'Str field')
        self.assertRaises(ConstraintNotSatisfied,
                                    field.validate,
                                    self._convert('hello\nworld'))

class LineTest(SingleLine, BytesTest):
    _Field_Factory = BytesLine

class TextLineTest(SingleLine, TextTest):
    _Field_Factory = TextLine


def test_suite():
    return TestSuite((
        makeSuite(BytesTest),
        makeSuite(TextTest),
        makeSuite(LineTest),
        makeSuite(TextLineTest),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
