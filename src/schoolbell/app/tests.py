#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for schoolbell.app.app.

$Id$
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

        >>> from schoolbell.app.interfaces import IGroupContainer
        >>> groups = app['groups']
        >>> verifyObject(IGroupContainer, groups)
        True

        >>> from schoolbell.app.interfaces import IResourceContainer
        >>> resources = app['resources']
        >>> verifyObject(IResourceContainer, resources)
        True

    For Zopeish reasons these containers must know where they come from

        >>> persons.__parent__ is app
        True
        >>> persons.__name__
        u'persons'

        >>> groups.__parent__ is app
        True
        >>> groups.__name__
        u'groups'

        >>> resources.__parent__ is app
        True
        >>> resources.__name__
        u'resources'

    """


def doctest_PersonContainer():
    """Tests for PersonContainer

        >>> from schoolbell.app.interfaces import IPersonContainer
        >>> from schoolbell.app.app import PersonContainer
        >>> c = PersonContainer()
        >>> verifyObject(IPersonContainer, c)
        True

    Let's make sure it acts like a proper container should act

        >>> from zope.app.container.tests.test_btree import TestBTreeContainer
        >>> class Test(TestBTreeContainer):
        ...    def makeTestObject(self):
        ...        return PersonContainer()
        >>> run_unit_tests(Test)

    """


def doctest_GroupContainer():
    """Tests for GroupContainer

        >>> from schoolbell.app.interfaces import IGroupContainer
        >>> from schoolbell.app.app import GroupContainer
        >>> c = GroupContainer()
        >>> verifyObject(IGroupContainer, c)
        True

    Let's make sure it acts like a proper container should act

        >>> from zope.app.container.tests.test_btree import TestBTreeContainer
        >>> class Test(TestBTreeContainer):
        ...    def makeTestObject(self):
        ...        return GroupContainer()
        >>> run_unit_tests(Test)

    """


def doctest_ResourceContainer():
    """Tests for ResourceContainer

        >>> from schoolbell.app.interfaces import IResourceContainer
        >>> from schoolbell.app.app import ResourceContainer
        >>> c = ResourceContainer()
        >>> verifyObject(IResourceContainer, c)
        True

    Let's make sure it acts like a proper container should act

        >>> from zope.app.container.tests.test_btree import TestBTreeContainer
        >>> class Test(TestBTreeContainer):
        ...    def makeTestObject(self):
        ...        return ResourceContainer()
        >>> run_unit_tests(Test)

    """


def doctest_Person():
    r"""Tests for Person

        >>> from schoolbell.app.interfaces import IPersonContained
        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> verifyObject(IPersonContained, person)
        True

    Persons initially have no password

        >>> person.hasPassword()
        False

    When a person has no password, he cannot log in

        >>> person.checkPassword('')
        False
        >>> person.checkPassword(None)
        False

    You can set the password

        >>> person.setPassword('secret')
        >>> person.hasPassword()
        True
        >>> person.checkPassword('secret')
        True
        >>> person.checkPassword('justguessing')
        False

    Note that the password is not stored in plain text and cannot be recovered

        >>> import pickle
        >>> 'secret' not in pickle.dumps(person)
        True

    You can lock out the user's accound by setting the password to None

        >>> person.setPassword(None)
        >>> person.hasPassword()
        False
        >>> person.checkPassword('')
        False
        >>> person.checkPassword(None)
        False

    Note that you can set the password to an empty string, although that is
    not a secure password

        >>> person.setPassword('')
        >>> person.hasPassword()
        True
        >>> person.checkPassword('')
        True
        >>> person.checkPassword(None)
        False

    It is probably not a very good idea to use non-ASCII characters in
    passwords, but you can do that

        >>> person.setPassword(u'\u1234')
        >>> person.checkPassword(u'\u1234')
        True

    """


def doctest_Group():
    r"""Tests for Group

        >>> from schoolbell.app.interfaces import IGroupContained
        >>> from schoolbell.app.app import Group
        >>> group = Group()
        >>> verifyObject(IGroupContained, group)
        True

    """


def doctest_Resource():
    r"""Tests for Resource

        >>> from schoolbell.app.interfaces import IResourceContained
        >>> from schoolbell.app.app import Resource
        >>> resource = Resource()
        >>> verifyObject(IResourceContained, resource)
        True

    """


def run_unit_tests(testcase):
    r"""Hack to call into unittest from doctests.

        >>> import unittest
        >>> class SampleTestCase(unittest.TestCase):
        ...     def test1(self):
        ...         self.assertEquals(2 + 2, 4)
        >>> run_unit_tests(SampleTestCase)

        >>> class BadTestCase(SampleTestCase):
        ...     def test2(self):
        ...         self.assertEquals(2 * 2, 5)
        >>> run_unit_tests(BadTestCase) # doctest: +REPORT_NDIFF
        .F
        ======================================================================
        FAIL: test2 (schoolbell.app.tests.BadTestCase)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
          File "<doctest schoolbell.app.tests.run_unit_tests[3]>", line 3, in test2
            self.assertEquals(2 * 2, 5)
          File "/usr/lib/python2.3/unittest.py", line 302, in failUnlessEqual
            raise self.failureException, \
        AssertionError: 4 != 5
        <BLANKLINE>
        ----------------------------------------------------------------------
        Ran 2 tests in ...s
        <BLANKLINE>
        FAILED (failures=1)

    """
    import unittest
    from StringIO import StringIO
    testsuite = unittest.makeSuite(testcase)
    output = StringIO()
    result = unittest.TextTestRunner(output).run(testsuite)
    if not result.wasSuccessful():
        print output.getvalue(),


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schoolbell.app.app'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
