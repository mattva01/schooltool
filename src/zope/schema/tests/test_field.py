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
"""Generic field tests

$Id$
"""
from unittest import TestCase, TestSuite, main, makeSuite
from zope.schema import Field, Text, Int
from zope.schema.interfaces import ValidationError, RequiredMissing
from zope.schema.interfaces import ConstraintNotSatisfied
from zope.testing.doctestunit import DocTestSuite

class FieldTestBase(TestCase):

    def test_bind(self):
        field = self._Field_Factory(
            __name__ = 'x',
            title=u'Not required field', description=u'',
            readonly=False, required=False)

        class C(object):
            x=None

        c = C()
        field2 = field.bind(c)

        self.assertEqual(field2.context, c)
        for n in ('__class__', '__name__', 'title', 'description',
                  'readonly', 'required'):
            self.assertEquals(getattr(field2, n), getattr(field, n), n)

    def testValidate(self):
        field = self._Field_Factory(
            title=u'Not required field', description=u'',
            readonly=False, required=False)
        field.validate(None)
        field.validate('foo')
        field.validate(1)
        field.validate(0)
        field.validate('')

    def testValidateRequired(self):
        field = self._Field_Factory(
            title=u'Required field', description=u'',
            readonly=False, required=True)
        field.validate('foo')
        field.validate(1)
        field.validate(0)
        field.validate('')

        self.assertRaises(RequiredMissing, field.validate, None)


class FieldTest(FieldTestBase):
    """Test generic Field."""

    _Field_Factory = Field

    def testSillyDefault(self):
        self.assertRaises(ValidationError, Text, default="")

    def test__doc__(self):
        field = Text(title=u"test fiield",
                     description=(
                         u"To make sure that\n"
                         u"doc strings are working correctly\n"
                         )
                     )
        self.assertEqual(
            field.__doc__,
            u"test fiield\n\n"
            u"To make sure that\n"
            u"doc strings are working correctly\n"
            )

    def testOrdering(self):

        from zope.interface import Interface

        class S1(Interface):
            a = Text()
            b = Text()

        self.failUnless(S1['a'].order < S1['b'].order)

        class S2(Interface):
            b = Text()
            a = Text()

        self.failUnless(S2['a'].order > S2['b'].order)

    def testConstraint(self):
        def isodd(x):
            return x % 2 == 1

        i = Int(title=u'my constrained integer',
                constraint=isodd)

        i.validate(11)
        self.assertRaises(ConstraintNotSatisfied, i.validate, 10)


class FieldDefaultBehaviour(TestCase):
    def test_required_defaults_to_true(self):
        class MyField(Field):
            pass
        field = MyField(title=u'my')
        self.assert_(field.required)

def test_suite():
    return TestSuite((
        makeSuite(FieldTest),
        makeSuite(FieldDefaultBehaviour),
        DocTestSuite("zope.schema._field"),
        DocTestSuite("zope.schema._bootstrapfields"),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
