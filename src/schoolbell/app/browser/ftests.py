"""
Functional tests for schoolbell.app.app.
"""

import os
import unittest

from zope.app.tests.functional import FunctionalTestSetup
from zope.app.tests.functional import FunctionalDocFileSuite


def test_suite():
    # Trigger the loading of ftesting.zcml to avoid bloating the time of the
    # first test.  This is a no-operation if done already.
    FunctionalTestSetup()
    return unittest.TestSuite([
                FunctionalDocFileSuite('ftest.txt'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
