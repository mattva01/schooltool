"""
Unit tests for schoolbell.app.app.
"""

import unittest

from zope.interface.verify import verifyObject


class TestSchoolBellApplication(unittest.TestCase):

    def test(self):
        from schoolbell.app.interfaces import ISchoolBellApplication
        from schoolbell.app.app import SchoolBellApplication
        app = SchoolBellApplication()
        verifyObject(ISchoolBellApplication, app)


def test_suite():
    return unittest.TestSuite(map(unittest.makeSuite, [
                TestSchoolBellApplication,
           ]))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
