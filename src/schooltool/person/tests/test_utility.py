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
Unit tests for schooltool.person.utility.
"""
import unittest
import doctest


def doctest_PersonFactoryUtility():
    """Tests for PersonFactoryUtility.

    First let's create the utility:

        >>> from schooltool.person.utility import PersonFactoryUtility
        >>> utility = PersonFactoryUtility()

    By default only 1 column is being displayed in the person tables:

        >>> columns = utility.columns()
        >>> len(columns) == 1
        True

    The getter of the column returns the title of the person:

        >>> person = utility("john", "John")
        >>> columns[0].getter(person, None)
        'John'

    The name of the columns is the same as the default sorting column:

        >>> columns[0].name == utility.sortOn()[0][0]
        True

    The title of the manager user is set to the system name + Manager:

        >>> manager = utility.createManagerUser("manager_username", "SchoolTool")
        >>> manager.title
        'SchoolTool Manager'
        >>> manager.username
        'manager_username'

    """

def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.ELLIPSIS)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
