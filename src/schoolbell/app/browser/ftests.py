"""
Functional tests for schoolbell.app.app.
"""

import os
import unittest

from zope.app.tests.functional import FunctionalTestSetup
from zope.app.tests.functional import FunctionalDocFileSuite


def test_suite():
    # Hack to make the test work with SchoolTool's test runner:
    # tell zope.app.tests.functional that ftesting.zcml resides
    # in the Zope3 subdirectory
    try:
        FunctionalTestSetup(os.path.join('Zope3', 'ftesting.zcml'))
    except NotImplementedError:
        pass # FunctionalTestSetup raises NotImplementedError when called twice
             # with a different config_file argument.  For us this indicates
             # that Zope 3's test runner already configured the functional
             # testing machinery with the correct ftesting.zcml.
    return unittest.TestSuite([
                FunctionalDocFileSuite('ftest.txt'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
