"""
Unit tests for schoolbell.app.app.
"""

import unittest

from zope.testing import doctest
from zope.interface.verify import verifyObject


# When this file grows too big, move the following tests to
# test_app.py

def doctest_SchoolBellApplication():
    r"""Tests for SchoolBellApplication.

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> app = SchoolBellApplication()

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> verifyObject(ISchoolBellApplication, app)
        True

    Person, group and resource containers are reachable as items of the
    application object.

        >>> from schoolbell.app.interfaces import IPersonContainer
        >>> persons = app['persons']
        >>> verifyObject(IPersonContainer, persons)
        True

    For Zopeish reasons these containers must know where they come from

        >>> persons.__parent__ is app
        True
        >>> persons.__name__
        u'persons'
        
    TODO: groups, resources

    """


class TestPersonContainer(unittest.TestCase):

    def test(self):
        from schoolbell.app.interfaces import IPersonContainer
        from schoolbell.app.app import PersonContainer
        c = PersonContainer()
        verifyObject(IPersonContainer, c)


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                unittest.makeSuite(TestPersonContainer),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
