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
Unit tests for schooltool.demographics.sampledata
"""

import unittest
import doctest

from zope.app.testing import setup
from zope.component import provideAdapter
from zope.component import provideUtility
from zope.interface import Interface
from zope.interface.verify import verifyObject

from schooltool.group.interfaces import IGroupContainer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.testing import setup as stsetup


def doctest_SampleStudents():
    """A sample data plugin that generates students

        >>> from schooltool.demographics.sampledata import SampleStudents
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleStudents()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin simply creates a 1000 persons with random names and
    usernames of a form 'student123'.

        >>> plugin.power
        1000

        >>> app = stsetup.setUpSchoolToolSite()

        >>> students = IGroupContainer(app)['students']

        >>> len(students.members)
        0

        >>> plugin.generate(app, 42)

        >>> len(students.members)
        1000

        >>> for i in range(5):
        ...     print app['persons']['student%03d' % i].title
        Freja Freeman
        Daniela Petersen
        Jeffery Hardy
        Thelma Vaughn
        Pip Stewart

    The students get their passwords set the same as their logins:

        >>> for i in range(5):
        ...     login = 'student%03d' % i
        ...     assert app['persons'][login].checkPassword(login)

    """


def doctest_SampleTeachers():
    """A sample data plugin that generates teachers

        >>> from schooltool.demographics.sampledata import SampleTeachers
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleTeachers()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin creates this many teachers:

        >>> plugin.power
        48

    This plugin creates a number of teachers and adds them to the
    Teachers group.

        >>> app = stsetup.setUpSchoolToolSite()

        >>> teachers = IGroupContainer(app)['teachers']

        >>> len(teachers.members)
        0

        >>> plugin.generate(app, 42)
        >>> len(teachers.members)
        48

    Teachers' names are different from the students' names above:

        >>> for i in range(5):
        ...     teacher = app['persons']['teacher%03d' % i]
        ...     print teacher.title, (teacher.nameinfo.first_name,
        ...                           teacher.nameinfo.last_name)
        Catherine Martin ('Catherine', 'Martin')
        Kimmy Cooper ('Kimmy', 'Cooper')
        Helen Patterson ('Helen', 'Patterson')
        Iris Laurent ('Iris', 'Laurent')
        Philippa Stewart ('Philippa', 'Stewart')

    The teachers get their passwords set the same as their logins:

        >>> for i in range(5):
        ...     login = 'teacher%03d' % i
        ...     assert app['persons'][login].checkPassword(login)

    """


def doctest_PersonFactoryUtility():
    """Tests for PersonFactoryUtility.

        >>> from schooltool.demographics.utility import PersonFactoryUtility
        >>> factory = PersonFactoryUtility()

        >>> from schooltool.person.interfaces import IPersonFactory
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IPersonFactory, factory)
        True

        >>> for column in factory.columns():
        ...     print "%s, %s" % (column.name, column.title)
        first_name, Name
        last_name, Surname

        >>> factory.sortOn()
        (('last_name', False),)

    """


def doctest_PersonFactoryUtility_createManagerUser():
    """Tests for PersonFactoryUtility.createManagerUser

    First let's create the utility:

        >>> from schooltool.demographics.utility import PersonFactoryUtility
        >>> utility = PersonFactoryUtility()

    The title of the manager user is set to the system name + Manager:

        >>> manager = utility.createManagerUser("manager_username", "SchoolTool")
        >>> manager.title
        'SchoolTool Manager'
        >>> manager.username
        'manager_username'

    The first_name and last_name are set as well:

        >>> manager.nameinfo.first_name
        'SchoolTool'
        >>> manager.nameinfo.last_name
        'Manager'

    """


def setUp(test):
    setup.placefulSetUp()
    from schooltool.term.term import getTermContainer
    from schooltool.term.interfaces import ITermContainer
    from schooltool.schoolyear.schoolyear import getSchoolYearContainer
    provideAdapter(getTermContainer, [Interface], ITermContainer)
    provideAdapter(getSchoolYearContainer)

    from schooltool.group.group import GroupContainer, Group
    groups = GroupContainer()
    provideAdapter(lambda context: groups,
                   adapts=[ISchoolToolApplication],
                   provides=IGroupContainer)
    groups['teachers'] = Group('Teachers')
    groups['students'] = Group('Students')

    from zope.annotation.interfaces import IAnnotatable
    from schooltool.relationship.interfaces import IRelationshipLinks
    from schooltool.relationship.annotatable import getRelationshipLinks
    provideAdapter(getRelationshipLinks, [IAnnotatable], IRelationshipLinks)


def tearDown(test):
    setup.placefulTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
