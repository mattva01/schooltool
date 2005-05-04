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
Unit tests for schooltool.app.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app import zapi
from zope.interface.verify import verifyObject
from zope.app.testing import setup, ztapi


def doctest_SchoolToolApplication():
    """SchoolToolApplication

    Let's check that the interface is satisfied:

        >>> from schooltool.app import SchoolToolApplication
        >>> from schooltool.interfaces import ISchoolToolApplication
        >>> from zope.interface.verify import verifyObject

        >>> app = SchoolToolApplication()
        >>> verifyObject(ISchoolToolApplication, app)
        True

    Also, the app is a schoolbell application:

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> verifyObject(ISchoolBellApplication, app)
        True

    Make sure the default groups and resources are created

        >>> from schoolbell.app.interfaces import IGroup
        >>> staff = app['groups']['staff']
        >>> verifyObject(IGroup, staff)
        True
        >>> learners = app['groups']['learners']
        >>> verifyObject(IGroup, learners)
        True
        >>> courses = app['groups']['courses']
        >>> verifyObject(IGroup, courses)
        True

    """


def doctest_Course():
    r"""Tests for course groups.

        >>> from schooltool.app import Course
        >>> algebraI= Course("Algebra I", "First year math.")
        >>> from schooltool.interfaces import ICourse
        >>> verifyObject(ICourse, algebraI)
        True
        >>> from schoolbell.app.interfaces import IGroup
        >>> verifyObject(IGroup, algebraI)
        True

    """


def doctest_Section():
    r"""Tests for course section groups.

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schoolbell.relationship import getRelatedObjects
        >>> setUp()

        >>> from schooltool.app import Section
        >>> section = Section()
        >>> from schooltool.interfaces import ISection
        >>> verifyObject(ISection, section)
        True

    We'll add an instructor to the section.

        >>> from schoolbell.app.app import Person
        >>> from schoolbell.app.interfaces import IPerson
        >>> teacher = Person('teacher', 'Mr. Jones')
        >>> section.instructors.add(teacher)

    Now we'll add some learners to the Section.

        >>> section.learners.add(Person('first','First'))
        >>> section.learners.add(Person('second','Second'))
        >>> section.learners.add(Person('third','Third'))

        >>> for person in section.learners:
        ...     print person.title
        First
        Second
        Third

        >>> for person in section.instructors:
        ...     print person.title
        Mr. Jones

    Sections are generally shown in the interface by their label.  Labels are
    created from the list of instructors, courses, and XXX time (not yet).

        >>> section.label
        u'Mr. Jones section of '

    Labels are updated dynamically when more instructors are added.

        >>> section.instructors.add(Person('teacher2', 'Mrs. Smith'))
        >>> section.label
        u'Mr. Jones Mrs. Smith section of '

    Labels should include the courses that a Section is part of:
        >>> from schooltool.app import Course
        >>> course = Course(title="US History")
        >>> course.members.add(section)
        >>> section.label
        u'Mr. Jones Mrs. Smith section of US History'

        >>> tearDown()

    """


def doctest_getSchoolToolApplication():
    """Tests for getSchoolToolApplication.

      >>> setup.placelessSetUp()

    Let's say we have a SchoolTool app, which is a site.

      >>> from schooltool.app import SchoolToolApplication, Person
      >>> from zope.app.component.site import LocalSiteManager
      >>> app = SchoolToolApplication()
      >>> app.setSiteManager(LocalSiteManager(app))

    If site is not a SchoolToolApplication, we get an error

      >>> from schooltool import getSchoolToolApplication
      >>> getSchoolToolApplication()
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolToolApplication

    If current site is a SchoolToolApplication, we get it:

      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolToolApplication() is app
      True

      >>> setup.placelessTearDown()
    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.app',
                                     optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
