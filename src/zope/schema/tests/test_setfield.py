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
"""Set field tests.

$Id$
"""
from unittest import TestSuite, main, makeSuite
import sets

from zope.interface import implements, providedBy
from zope.schema import Field, Set, Int
from zope.schema.interfaces import IField
from zope.schema.interfaces import ICollection, IUnorderedCollection, ISet
from zope.schema.interfaces import NotAContainer, RequiredMissing
from zope.schema.interfaces import WrongContainedType, WrongType, NotUnique
from zope.schema.interfaces import TooShort, TooLong
from zope.schema.tests.test_field import FieldTestBase

class SetTest(FieldTestBase):
    """Test the Tuple Field."""

    _Field_Factory = Set

    def testValidate(self):
        field = Set(title=u'Set field', description=u'',
                    readonly=False, required=False)
        field.validate(None)
        field.validate(sets.Set())
        field.validate(sets.Set((1, 2)))
        field.validate(sets.Set((3,)))

        self.assertRaises(WrongType, field.validate, [1, 2, 3])
        self.assertRaises(WrongType, field.validate, 'abc')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, (1, 2, 3))

    def testValidateRequired(self):
        field = Set(title=u'Set field', description=u'',
                    readonly=False, required=True)
        field.validate(sets.Set())
        field.validate(sets.Set((1, 2)))
        field.validate(sets.Set((3,)))

        self.assertRaises(RequiredMissing, field.validate, None)

    def testValidateMinValues(self):
        field = Set(title=u'Set field', description=u'',
                    readonly=False, required=False, min_length=2)
        field.validate(None)
        field.validate(sets.Set((1, 2)))
        field.validate(sets.Set((1, 2, 3)))

        self.assertRaises(TooShort, field.validate, sets.Set(()))
        self.assertRaises(TooShort, field.validate, sets.Set((3,)))

    def testValidateMaxValues(self):
        field = Set(title=u'Set field', description=u'',
                    readonly=False, required=False, max_length=2)
        field.validate(None)
        field.validate(sets.Set())
        field.validate(sets.Set((1, 2)))

        self.assertRaises(TooLong, field.validate, sets.Set((1, 2, 3, 4)))
        self.assertRaises(TooLong, field.validate, sets.Set((1, 2, 3)))

    def testValidateMinValuesAndMaxValues(self):
        field = Set(title=u'Set field', description=u'',
                    readonly=False, required=False,
                    min_length=1, max_length=2)
        field.validate(None)
        field.validate(sets.Set((3,)))
        field.validate(sets.Set((1, 2)))

        self.assertRaises(TooShort, field.validate, sets.Set())
        self.assertRaises(TooLong, field.validate, sets.Set((1, 2, 3)))

    def testValidateValueTypes(self):
        field = Set(title=u'Set field', description=u'',
                    readonly=False, required=False,
                    value_type=Int())
        field.validate(None)
        field.validate(sets.Set((5,)))
        field.validate(sets.Set((2, 3)))

        self.assertRaises(WrongContainedType, field.validate, sets.Set(('',)))
        self.assertRaises(WrongContainedType, 
                          field.validate, sets.Set((3.14159,)))

    def testCorrectValueType(self):
        # TODO: We should not allow for a None valeu type. 
        Set(value_type=None)

        # do not allow arbitrary value types
        self.assertRaises(ValueError, Set, value_type=object())
        self.assertRaises(ValueError, Set, value_type=Field)

        # however, allow anything that implements IField
        Set(value_type=Field())
        class FakeField(object):
            implements(IField)
        Set(value_type=FakeField())
    
    def testNoUniqueArgument(self):
        self.assertRaises(TypeError, Set, unique=False)
        self.assertRaises(TypeError, Set, unique=True)
        self.failUnless(Set().unique)
    
    def testImplements(self):
        field = Set()
        self.failUnless(ISet.providedBy(field))
        self.failUnless(IUnorderedCollection.providedBy(field))
        self.failUnless(ICollection.providedBy(field))

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SetTest))
    return suite

if __name__ == '__main__':
    main(defaultTest='test_suite')
