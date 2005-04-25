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
Tests for schooltool views.

$Id: test_app.py 3481 2005-04-21 15:28:29Z bskahan $
"""

import unittest

from zope.testing import doctest
from zope.publisher.browser import TestRequest

from schoolbell.app.browser.tests.setup import setUp, tearDown


def doctest_CourseView():
    r"""View for courses.

    Lets create a simple view for a course:

        >>> from schooltool.browser.app import CourseView
        >>> from schooltool.app import Course
        >>> course = Course()
        >>> request = TestRequest()
        >>> view = CourseView(course, request)

        >>> from schooltool.app import Section
        >>> course.members.add(Section(title='First'))
        >>> course.members.add(Section(title='Last'))
        >>> course.members.add(Section(title='Intermediate'))

    get sections returns all the members of the course, we'll restrict
    membership to Sections later.

        >>> titles = [person.title for person in view.getSections()]
        >>> titles.sort()
        >>> titles
        ['First', 'Intermediate', 'Last']

    """


def doctest_SectionView():
    r"""View for sections

    Lets create a simple view for a section:

        >>> from schooltool.browser.app import SectionView
        >>> from schooltool.app import Section
        >>> section = Section()
        >>> request = TestRequest()
        >>> view = SectionView(section, request)

        >>> from schoolbell.app.app import Person, Resource
        >>> section.learners.add(Person(title='First Student'))
        >>> section.learners.add(Person(title='Last Student'))
        >>> section.learners.add(Person(title='Intermediate Student'))

        >>> titles = [person.title for person in view.getLearners()]
        >>> titles.sort()
        >>> titles
        ['First Student', 'Intermediate Student', 'Last Student']

    Lets add some instructors to the section.

        >>> section.instructors.add(Person(title='First Teacher'))
        >>> section.instructors.add(Person(title='Last Teacher'))

        >>> titles = [person.title for person in view.getInstructors()]
        >>> titles.sort()
        >>> titles
        ['First Teacher', 'Last Teacher']

    """


def doctest_SectionAddView():
    r"""Tests for adding sections.

    Sections are special types of groups meant to represent one meeting time
    of a course.  If they don't have a course, they can't be created "stand
    alone".

        >>> from schooltool.browser.app import SectionAddView
        >>> from schoolbell.app.app import GroupContainer
        >>> container = GroupContainer()

    first a request with a course reference raises an error.

        >>> request = TestRequest()
        >>> view = SectionAddView(container, request)
        Traceback (most recent call last):
        ...
        NotImplementedError

    A request with course_id doesn't

        >>> request = TestRequest(course_id='algebraI')
        >>> view = SectionAddView(container, request)
        >>> view.update()

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
