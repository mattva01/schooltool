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
"""Iterable field tests

$Id$
"""
from UserDict import UserDict, IterableUserDict
from unittest import main, makeSuite
from zope.schema import Iterable
from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import NotAContainer, NotAnIterator
from zope.schema.tests.test_field import FieldTestBase

class IterableTest(FieldTestBase):
    """Test the Iterable Field."""

    _Field_Factory = Iterable

    def testValidate(self):
        field = self._Field_Factory(title=u'test field', description=u'',
                                    readonly=False, required=False)
        field.validate(None)
        field.validate('')
        field.validate('abc')
        field.validate([1, 2, 3])
        field.validate({'a': 1, 'b': 2})
        field.validate(IterableUserDict())

        self.assertRaises(NotAContainer, field.validate, 1)
        self.assertRaises(NotAContainer, field.validate, True)
        self.assertRaises(NotAnIterator, field.validate, UserDict)

    def testValidateRequired(self):
        field = self._Field_Factory(title=u'test field', description=u'',
                                    readonly=False, required=True)

        field.validate('')

        self.assertRaises(RequiredMissing, field.validate, None)


def test_suite():
    return makeSuite(IterableTest)

if __name__ == '__main__':
    main(defaultTest='test_suite')
