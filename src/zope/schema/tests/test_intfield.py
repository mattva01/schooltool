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
"""Integer field tests

$Id$
"""
from unittest import main, makeSuite
from zope.schema import Int
from zope.schema.interfaces import RequiredMissing, InvalidValue
from zope.schema.interfaces import TooSmall, TooBig
from zope.schema.tests.test_field import FieldTestBase

class IntTest(FieldTestBase):
    """Test the Int Field."""

    _Field_Factory = Int

    def testValidate(self):
        field = self._Field_Factory(title=u'Int field', description=u'',
                                    readonly=False, required=False)
        field.validate(None)
        field.validate(10)
        field.validate(0)
        field.validate(-1)

    def testValidateRequired(self):
        field = self._Field_Factory(title=u'Int field', description=u'',
                                    readonly=False, required=True)
        field.validate(10)
        field.validate(0)
        field.validate(-1)

        self.assertRaises(RequiredMissing, field.validate, None)

    def testValidateMin(self):
        field = self._Field_Factory(title=u'Int field', description=u'',
                                    readonly=False, required=False, min=10)
        field.validate(None)
        field.validate(10)
        field.validate(20)

        self.assertRaises(TooSmall, field.validate, 9)
        self.assertRaises(TooSmall, field.validate, -10)

    def testValidateMax(self):
        field = self._Field_Factory(title=u'Int field', description=u'',
                                    readonly=False, required=False, max=10)
        field.validate(None)
        field.validate(5)
        field.validate(9)

        self.assertRaises(TooBig, field.validate, 11)
        self.assertRaises(TooBig, field.validate, 20)

    def testValidateMinAndMax(self):
        field = self._Field_Factory(title=u'Int field', description=u'',
                                    readonly=False, required=False,
                                    min=0, max=10)
        field.validate(None)
        field.validate(0)
        field.validate(5)
        field.validate(10)

        self.assertRaises(TooSmall, field.validate, -10)
        self.assertRaises(TooSmall, field.validate, -1)
        self.assertRaises(TooBig, field.validate, 11)
        self.assertRaises(TooBig, field.validate, 20)


def test_suite():
    suite = makeSuite(IntTest)
    return suite

if __name__ == '__main__':
    main(defaultTest='test_suite')
