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
from zope.component import provideAdapter
from zope.interface import implements

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationPreferences


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

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication, IApplicationPreferences)
        ...     def __init__(self):
        ...         self.name_sorting = 'last_name'
        >>> app = AppStub()
        >>> provideAdapter(lambda _: app,
        ...                adapts=(None, ), provides=ISchoolToolApplication)

        >>> for column in factory.columns():
        ...     print "%s, %s" % (column.name, column.title)
        last_name, Last Name
        first_name, First Name

        >>> factory.sortOn()
        (('last_name', False), ('first_name', False))

    If we change name sorting order, both the sort and column order changes:

        >>> app.name_sorting = 'first_name'
        >>> for column in factory.columns():
        ...     print "%s, %s" % (column.name, column.title)
        first_name, First Name
        last_name, Last Name

        >>> factory.sortOn()
        (('first_name', False), ('last_name', False))

    """


def doctest_PersonFactoryUtility_createManagerUser():
    """Tests for PersonFactoryUtility.createManagerUser

    First let's create the utility:

        >>> from schooltool.basicperson.person import PersonFactoryUtility
        >>> utility = PersonFactoryUtility()

    The title of the manager user is set to "Administratorius" + system name:

        >>> manager = utility.createManagerUser("manager_username")
        >>> manager.title
        'Default Manager'
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
