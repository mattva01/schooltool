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
"""Container field tests

$Id$
"""
from UserDict import UserDict
from unittest import main, makeSuite
from zope.schema import Container
from zope.schema.interfaces import RequiredMissing, NotAContainer
from zope.schema.tests.test_field import FieldTestBase

class ContainerTest(FieldTestBase):
    """Test the Container Field."""

    _Field_Factory = Container

    def testValidate(self):
        field = self._Field_Factory(title=u'test field', description=u'',
                                    readonly=False, required=False)
        field.validate(None)
        field.validate('')
        field.validate('abc')
        field.validate([1, 2, 3])
        field.validate({'a': 1, 'b': 2})
        field.validate(UserDict())

        self.assertRaises(NotAContainer, field.validate, 1)
        self.assertRaises(NotAContainer, field.validate, True)

    def testValidateRequired(self):
        field = self._Field_Factory(title=u'test field', description=u'',
                                    readonly=False, required=True)

        field.validate('')

        self.assertRaises(RequiredMissing, field.validate, None)


def test_suite():
    return makeSuite(ContainerTest)

if __name__ == '__main__':
    main(defaultTest='test_suite')
