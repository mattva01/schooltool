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
Unit tests for schooltool.person.sampledata

$Id$
"""

import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing import setup as stsetup
from schooltool.relationship.tests import setUpRelationships
from schooltool.app.interfaces import ISchoolToolCalendar


def setUp(test):
    setup.placefulSetUp()
    stsetup.setupCalendaring()

def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleStudents():
    """A sample data plugin that generates students

        >>> from schooltool.person.sampledata import SampleStudents
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleStudents()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin simply creates a 1000 persons with random names and
    usernames of a form 'student123'.

        >>> plugin.power
        1000

        >>> app = stsetup.setupSchoolToolSite()
        >>> len(app['persons'])
        0

        >>> plugin.generate(app, 42)

        >>> len(app['persons'])
        1000

        >>> for i in range(5):
        ...     print app['persons']['student%03d' % i].title
        Freja Freeman
        Klara Phillips
        Cath Rodriguez
        Daniela Petersen
        Gabbie Cunningham

    The students get their passwords set the same as their logins:

        >>> for i in range(5):
        ...     login = 'student%03d' % i
        ...     assert app['persons'][login].checkPassword(login)

    """


def doctest_SampleTeachers():
    """A sample data plugin that generates students

        >>> setUpRelationships()

        >>> from schooltool.person.sampledata import SampleTeachers
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
        >>> app = stsetup.setupSchoolToolSite()
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
        ...     print app['persons']['teacher%03d' % i].title
        Catherine Martin
        Kimmy Cooper
        Helen Patterson
        Iris Laurent
        Philippa Stewart

    The teachers get their passwords set the same as their logins:

        >>> for i in range(5):
        ...     login = 'teacher%03d' % i
        ...     assert app['persons'][login].checkPassword(login)

    """


def doctest_SamplePersonalEvents():
    """A sample data plugin that generates random personal events.

        >>> setUpRelationships()

        >>> from schooltool.person.sampledata import SamplePersonalEvents
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SamplePersonalEvents()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> from schooltool.group.group import Group
        >>> app = stsetup.setupSchoolToolSite()
        >>> app['groups']['teachers'] = Group('Teachers')

        >>> from schooltool.person.sampledata import SampleStudents
        >>> from schooltool.person.sampledata import SampleTeachers
        >>> from schooltool.timetable.sampledata import SampleTerms
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
        142
        124
        149
        140
        131

        >>> person = app['persons']['teacher000']
        >>> calendar = ISchoolToolCalendar(person)
        >>> len(calendar)
        154

        >>> events = list(calendar)
        >>> events.sort()
        >>> for event in events[0:5]:
        ...     print event.dtstart,
        ...     print event.duration,
        ...     print event.title
        2005-08-22 10:30:00+00:00 5:00:00 Birding
        2005-08-23 23:30:00+00:00 3:30:00 Soccer
        2005-08-24 20:30:00+00:00 0:30:00 Flashmob
        2005-08-27 06:00:00+00:00 3:30:00 Circus
        2005-08-29 14:00:00+00:00 6:00:00 Boating
    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
