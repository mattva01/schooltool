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
"""List field tests

$Id$
"""
from unittest import main, makeSuite

from zope.interface import implements
from zope.schema import Field, List, Int
from zope.schema.interfaces import IField
from zope.schema.interfaces import ICollection, ISequence, IList
from zope.schema.interfaces import NotAContainer, RequiredMissing
from zope.schema.interfaces import WrongContainedType, WrongType, NotUnique
from zope.schema.interfaces import TooShort, TooLong
from zope.schema.tests.test_field import FieldTestBase

class ListTest(FieldTestBase):
    """Test the List Field."""

    _Field_Factory = List

    def testValidate(self):
        field = List(title=u'List field', description=u'',
                     readonly=False, required=False)
        field.validate(None)
        field.validate([])
        field.validate([1, 2])
        field.validate([3,])

    def testValidateRequired(self):
        field = List(title=u'List field', description=u'',
                     readonly=False, required=True)
        field.validate([])
        field.validate([1, 2])
        field.validate([3,])

        self.assertRaises(RequiredMissing, field.validate, None)

    def testValidateMinValues(self):
        field = List(title=u'List field', description=u'',
                     readonly=False, required=False, min_length=2)
        field.validate(None)
        field.validate([1, 2])
        field.validate([1, 2, 3])

        self.assertRaises(TooShort, field.validate, [])
        self.assertRaises(TooShort, field.validate, [1,])

    def testValidateMaxValues(self):
        field = List(title=u'List field', description=u'',
                     readonly=False, required=False, max_length=2)
        field.validate(None)
        field.validate([])
        field.validate([1, 2])

        self.assertRaises(TooLong, field.validate, [1, 2, 3, 4])
        self.assertRaises(TooLong, field.validate, [1, 2, 3])

    def testValidateMinValuesAndMaxValues(self):
        field = List(title=u'List field', description=u'',
                     readonly=False, required=False,
                     min_length=1, max_length=2)
        field.validate(None)
        field.validate([1, ])
        field.validate([1, 2])

        self.assertRaises(TooShort, field.validate, [])
        self.assertRaises(TooLong, field.validate, [1, 2, 3])

    def testValidateValueTypes(self):
        field = List(title=u'List field', description=u'',
                     readonly=False, required=False,
                     value_type=Int())
        field.validate(None)
        field.validate([5,])
        field.validate([2, 3])

        self.assertRaises(WrongContainedType, field.validate, ['',] )
        self.assertRaises(WrongContainedType, field.validate, [3.14159,] )

    def testCorrectValueType(self):
        # TODO: We should not allow for a None valeu type. 
        List(value_type=None)

        # do not allow arbitrary value types
        self.assertRaises(ValueError, List, value_type=object())
        self.assertRaises(ValueError, List, value_type=Field)

        # however, allow anything that implements IField
        List(value_type=Field())
        class FakeField(object):
            implements(IField)
        List(value_type=FakeField())

    def testUnique(self):
        field = self._Field_Factory(title=u'test field', description=u'',
                                    readonly=False, required=True, unique=True)
        field.validate([1, 2])
        self.assertRaises(NotUnique, field.validate, [1, 2, 1])
    
    def testImplements(self):
        field = List()
        self.failUnless(IList.providedBy(field))
        self.failUnless(ISequence.providedBy(field))
        self.failUnless(ICollection.providedBy(field))

def test_suite():
    return makeSuite(ListTest)

if __name__ == '__main__':
    main(defaultTest='test_suite')
