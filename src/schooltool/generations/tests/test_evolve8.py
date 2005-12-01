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
Unit tests for schooltool.generations.evolve6

$Id: test_evolve8.py 5268 2005-10-14 19:15:43Z alga $
"""

import unittest
from datetime import date, time, timedelta
from pprint import pprint

from zope.app.testing import setup
from zope.testing import doctest
from zope.app.container.btree import BTreeContainer
from zope.interface import implements
from zope.interface import classImplements
from zope.app.annotation.interfaces import IAttributeAnnotatable

from schooltool.group.group import Group
from schooltool.generations.tests import ContextStub
import schooltool.app # Dead chicken to avoid issue 390
from schooltool.testing import setup as stsetup


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()
    setup.setUpDependable()


def tearDown(test):
    setup.placelessTearDown()


def doctest_evolve8_convert_exceptions():
    """Evolution to generation 8.

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.timetable.interfaces import ITimetableModel
        >>> class MockSchoolTool(dict):
        ...     implements(ISchoolToolApplication)

        >>> context = ContextStub()
        >>> app = MockSchoolTool()
        >>> app['groups'] = BTreeContainer()
        >>> context.root_folder['app'] = app

    Suppose we have a nice fresh install of an older SchoolTool:

        >>> app['groups']['manager'] = Group('Manager', 'Manager Group.')
        >>> group = Group('Manager', 'Manager group.')

        >>> from schooltool.generations.evolve8 import evolve
        >>> evolve(context)

     We should have groups with these names:

        >>> group_names = ['administrators', 'clerks', 'manager', 'students',
        ...                'teachers']

     Proper titles should get set up:

        >>> for name in sorted(group_names):
        ...     group = app['groups'][name]
        ...     print '%-15s %-25s %s' % (name, group.title, group.description)
        administrators  School Administrators     School Administrators.
        clerks          Clerks                    Clerks.
        manager         Manager                   Manager Group.
        students        Students                  Students.
        teachers        Teachers                  Teachers.

    As well as dependencies:

        >>> from zope.app.dependable.interfaces import IDependable
        >>> for group in app['groups'].values():
        ...     assert IDependable(group).dependents() == ('/',)

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
