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
"""Float field tests

$Id$
"""
from unittest import main, makeSuite
from zope.schema import Float
from zope.schema.interfaces import RequiredMissing, InvalidValue
from zope.schema.interfaces import TooSmall, TooBig
from zope.schema.tests.test_field import FieldTestBase

class FloatTest(FieldTestBase):
    """Test the Float Field."""

    _Field_Factory = Float

    def testValidate(self):
        field = self._Field_Factory(title=u'Float field', description=u'',
                                    readonly=False, required=False)
        field.validate(None)
        field.validate(10.0)
        field.validate(0.93)
        field.validate(1000.0003)

    def testValidateRequired(self):
        field = self._Field_Factory(title=u'Float field', description=u'',
                                    readonly=False, required=True)
        field.validate(10.0)
        field.validate(0.93)
        field.validate(1000.0003)

        self.assertRaises(RequiredMissing, field.validate, None)

    def testValidateMin(self):
        field = self._Field_Factory(title=u'Float field', description=u'',
                                    readonly=False, required=False, min=10.5)
        field.validate(None)
        field.validate(10.6)
        field.validate(20.2)

        self.assertRaises(TooSmall, field.validate, -9.0)
        self.assertRaises(TooSmall, field.validate, 10.4)

    def testValidateMax(self):
        field = self._Field_Factory(title=u'Float field', description=u'',
                                    readonly=False, required=False, max=10.5)
        field.validate(None)
        field.validate(5.3)
        field.validate(-9.1)

        self.assertRaises(TooBig, field.validate, 10.51)
        self.assertRaises(TooBig, field.validate, 20.7)

    def testValidateMinAndMax(self):
        field = self._Field_Factory(title=u'Float field', description=u'',
                                    readonly=False, required=False,
                                    min=-0.6, max=10.1)
        field.validate(None)
        field.validate(0.0)
        field.validate(-0.03)
        field.validate(10.0001)

        self.assertRaises(TooSmall, field.validate, -10.0)
        self.assertRaises(TooSmall, field.validate, -1.6)
        self.assertRaises(TooBig, field.validate, 11.45)
        self.assertRaises(TooBig, field.validate, 20.02)


def test_suite():
    suite = makeSuite(FloatTest)
    return suite

if __name__ == '__main__':
    main(defaultTest='test_suite')
