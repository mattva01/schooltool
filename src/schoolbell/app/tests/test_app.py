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

    Containers are adaptable to ISchoolBellApplication

        >>> ISchoolBellApplication(persons) is app
        True
        >>> ISchoolBellApplication(groups) is app
        True
        >>> ISchoolBellApplication(resources) is app
        True

    """


def doctest_PersonContainer():
    """Tests for PersonContainer

        >>> from schoolbell.app.interfaces import IPersonContainer
        >>> from schoolbell.app.app import PersonContainer
        >>> c = PersonContainer()
        >>> verifyObject(IPersonContainer, c)
        True

    PersonContainer uses the `username` attribute of persons as the key

        >>> from schoolbell.app.app import Person
        >>> person = Person(username="itsme")
        >>> c['doesnotmatter'] = person
        >>> c['itsme'] is person
        True
        >>> c.get('doesnotmatter') is None
        True

    Adaptation (i.e. __conform__) is tested in doctest_SchoolBellApplication.
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

    Adaptation (i.e. __conform__) is tested in doctest_SchoolBellApplication.
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

    Adaptation (i.e. __conform__) is tested in doctest_SchoolBellApplication.
    """


def doctest_Person():
    r"""Tests for Person

        >>> from schoolbell.app.interfaces import IPersonContained
        >>> from schoolbell.app.app import Person
        >>> person = Person('person')
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

    Persons have a calendar:

        >>> person.calendar.__name__
        'calendar'
        >>> person.calendar.__parent__ is person
        True
        >>> len(person.calendar)
        0

    Persons can be adapted to ISchoolBellApplication

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> from schoolbell.app.app import SchoolBellApplication
        >>> app = SchoolBellApplication()
        >>> app['persons']['guest'] = person
        >>> ISchoolBellApplication(person) is app
        True

    """


def doctest_Group():
    r"""Tests for Group

        >>> from schoolbell.app.interfaces import IGroupContained
        >>> from schoolbell.app.app import Group
        >>> group = Group()
        >>> verifyObject(IGroupContained, group)
        True

    Groups can be adapted to ISchoolBellApplication

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> from schoolbell.app.app import SchoolBellApplication
        >>> app = SchoolBellApplication()
        >>> app['groups']['friends'] = group
        >>> ISchoolBellApplication(group) is app
        True

    """


def doctest_Resource():
    r"""Tests for Resource

        >>> from schoolbell.app.interfaces import IResourceContained
        >>> from schoolbell.app.app import Resource
        >>> resource = Resource()
        >>> verifyObject(IResourceContained, resource)
        True

    Resources can be adapted to ISchoolBellApplication

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> from schoolbell.app.app import SchoolBellApplication
        >>> app = SchoolBellApplication()
        >>> app['resources']['book1'] = resource
        >>> ISchoolBellApplication(resource) is app
        True

    """


def doctest_getSchoolBellApplication():
    """Tests for getSchoolBellApplication.

    Let's say we have a SchoolBell app, a persons container and a person.

      >>> from schoolbell.app.app import SchoolBellApplication, Person

      >>> p = Person(u'1')
      >>> app = SchoolBellApplication()
      >>> app['persons']['1'] = p

    getSchoolBellApplication returns the app object for all these contexts:

      >>> from schoolbell.app.app import getSchoolBellApplication
      >>> getSchoolBellApplication(app) is app
      True

      >>> getSchoolBellApplication(app['persons']) is app
      True

      >>> getSchoolBellApplication(p) is app
      True

    However, this function raises an error if the object does not have
    an ISchoolBellApplication among its ancestors:

      >>> from zope.interface import implements
      >>> from zope.app.location.interfaces import ILocation
      >>> class Foo:
      ...     implements(ILocation)
      ...     __parent__ = None
      ...     def __repr__(self):
      ...         return "Foo()"
      ...
      >>> foo = Foo()
      >>> getSchoolBellApplication(foo)
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolBellApplication from Foo()

    Also, it raises the same error if the object is not a location:

      >>> getSchoolBellApplication("string")
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolBellApplication from 'string'

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
        FAIL: test2 (schoolbell.app.tests.test_app.BadTestCase)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
        ...
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
                doctest.DocTestSuite('schoolbell.app.membership'),
                doctest.DocFileSuite('../security.txt',
                                     optionflags=doctest.ELLIPSIS)
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
