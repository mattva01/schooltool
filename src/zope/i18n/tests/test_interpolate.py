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
"""This is an 'abstract' test for the ITranslationDomain interface.

$Id$
"""
import unittest
from zope.i18n import interpolate


class TestInterpolation(unittest.TestCase):

    def testInterpolation(self):
        mapping = {'name': 'Zope', 'version': '3x', 'number': 3}
        # Test simple interpolations
        self.assertEqual(
            interpolate('This is $name.', mapping), 'This is Zope.')
        self.assertEqual(
            interpolate('This is ${name}.', mapping), 'This is Zope.')
        # Test more than one interpolation variable
        self.assertEqual(
            interpolate('This is $name version $version.', mapping),
            'This is Zope version 3x.')
        self.assertEqual(
            interpolate('This is ${name} version $version.', mapping),
            'This is Zope version 3x.')
        self.assertEqual(
            interpolate('This is $name version ${version}.', mapping),
            'This is Zope version 3x.')
        self.assertEqual(
            interpolate('This is ${name} version ${version}.', mapping),
            'This is Zope version 3x.')
        # Test escaping the $
        self.assertEqual(
            interpolate('This is $$name.', mapping), 'This is $$name.')
        self.assertEqual(
            interpolate('This is $${name}.', mapping), 'This is $${name}.')
        # Test interpolation of non-string objects
        self.assertEqual(interpolate('Number $number.', mapping), 'Number 3.')
        

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TestInterpolation),
        ))

if __name__=='__main__':
    unittest.TextTestRunner().run(test_suite())
