#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for basic person.
"""
import unittest
import doctest

from zope.app.testing import setup


def doctest_BasicPerson():
    """Tests for BasicPerson.

         >>> from zope.interface.verify import verifyObject
         >>> from schooltool.basicperson.person import BasicPerson
         >>> person = BasicPerson("peter", "Peter", "Johnson")

         >>> from schooltool.basicperson.interfaces import IBasicPerson
         >>> verifyObject(IBasicPerson, person)
         True

         >>> person.title
         'Peter Johnson'

    """


def doctest_PersonFactoryUtility():
    """Tests for PersonFactoryUtility.

        >>> from schooltool.basicperson.person import PersonFactoryUtility
        >>> factory = PersonFactoryUtility()

        >>> from schooltool.person.interfaces import IPersonFactory
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IPersonFactory, factory)
        True

        >>> for column in factory.columns():
        ...     print "%s, %s" % (column.name, column.title)
        first_name, First Name
        last_name, Last Name

        >>> factory.sortOn()
        (('last_name', False),)

    """


def doctest_PersonFactoryUtility_createManagerUser():
    """Tests for PersonFactoryUtility.createManagerUser

    First let's create the utility:

        >>> from schooltool.basicperson.person import PersonFactoryUtility
        >>> utility = PersonFactoryUtility()

    The title of the manager user is set to "Administratorius" + system name:

        >>> manager = utility.createManagerUser("manager_username", "SchoolTool")
        >>> manager.title
        'SchoolTool Administrator'
        >>> manager.username
        'manager_username'

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
