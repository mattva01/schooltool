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

$Id$
"""

import unittest

from zope.component import provideAdapter
from zope.interface import Interface
from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.schoolyear.schoolyear import getSchoolYearContainer
from schooltool.term.interfaces import ITermContainer
from schooltool.term.term import getTermContainer
from schooltool.testing import setup as stsetup
from schooltool.relationship.tests import setUpRelationships
from schooltool.app.interfaces import ISchoolToolCalendar


def setUp(test):
    setup.placefulSetUp()
    stsetup.setUpCalendaring()
    provideAdapter(getTermContainer, [Interface], ITermContainer)
    provideAdapter(getSchoolYearContainer)


def tearDown(test):
    setup.placefulTearDown()


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
        >>> len(app['persons'])
        0

        >>> plugin.generate(app, 42)

        >>> len(app['persons'])
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
    """A sample data plugin that generates students

        >>> setUpRelationships()

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

        >>> from schooltool.group.group import Group
        >>> app = stsetup.setUpSchoolToolSite()
        >>> teachers = app['groups']['teachers'] = Group('Teachers')
        >>> len(app['persons'])
        0
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


def doctest_SamplePersonalEvents():
    """A sample data plugin that generates random personal events.

        >>> setUpRelationships()

        >>> from schooltool.demographics.sampledata import SamplePersonalEvents
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SamplePersonalEvents()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> from schooltool.group.group import Group
        >>> app = stsetup.setUpSchoolToolSite()
        >>> app['groups']['teachers'] = Group('Teachers')

        >>> from schooltool.demographics.sampledata import SampleStudents
        >>> from schooltool.demographics.sampledata import SampleTeachers
        >>> from schooltool.term.sampledata import SampleTerms
        >>> plugin_students = SampleStudents()
        >>> plugin_students.power = 20
        >>> plugin_teachers = SampleTeachers()
        >>> plugin_teachers.power = 3
        >>> plugin_terms = SampleTerms()
        >>> plugin_students.generate(app, 42)
        >>> plugin_teachers.generate(app, 42)
        >>> plugin_terms.generate(app, 42)

    Probability of person having event on any day in percents:

        >>> plugin.probability
        10

        >>> plugin.probability = 50

    Create random events for all students and teachers.

        >>> plugin.generate(app, 42)

        >>> for i in range(5):
        ...     person = app['persons']['student%03d' % i]
        ...     calendar = ISchoolToolCalendar(person)
        ...     print len(calendar)
        233
        250
        227
        252
        248

        >>> person = app['persons']['teacher000']
        >>> calendar = ISchoolToolCalendar(person)
        >>> len(calendar)
        240

        >>> events = list(calendar)
        >>> events.sort()
        >>> for event in events[0:5]:
        ...     print event.dtstart,
        ...     print event.duration,
        ...     print event.title
        2005-08-24 12:00:00+00:00 5:00:00 Tribal dances
        2005-08-25 17:30:00+00:00 1:30:00 Dentist
        2005-08-27 11:30:00+00:00 4:00:00 Concert
        2005-08-28 23:30:00+00:00 3:30:00 Quake tournament
        2005-08-29 19:00:00+00:00 6:00:00 Boating
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

    The fisrt_name and last_name are set as well:

        >>> manager.nameinfo.first_name
        'SchoolTool'
        >>> manager.nameinfo.last_name
        'Manager'

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
