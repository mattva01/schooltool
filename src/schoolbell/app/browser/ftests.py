"""
Functional tests for schoolbell.app.app.
"""

import unittest

from zope.app.tests.functional import FunctionalDocFileSuite


def test_suite():
    return unittest.TestSuite([
                FunctionalDocFileSuite('ftest.txt'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
