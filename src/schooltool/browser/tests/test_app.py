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
from zope.app.testing import setup, ztapi
from zope.publisher.browser import TestRequest

from schoolbell.app.browser.tests.setup import setUp, tearDown

# Used for CourseAddView and SectionAddView
from zope.app.container.browser.adding import Adding
class AddingStub(Adding):
    pass


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


def doctest_CourseAddView():
    r"""

        >>> from schooltool.browser.app import CourseAddView
        >>> from schooltool.app import Course
        >>> from schooltool.interfaces import ICourse

        >>> class CourseAddViewForTesting(CourseAddView):
        ...     schema = ICourse
        ...     fieldNames = ('title', 'description')
        ...     _factory = Course


        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> container = app['groups']
        >>> request = TestRequest()
        >>> context = AddingStub(container, request)
        >>> context = container

        >>> view = CourseAddViewForTesting(context, request)

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

        >>> from schooltool.browser.app import SectionAddView
        >>> from schooltool.app import Section, Course
        >>> from schooltool.interfaces import ISection

    We need some setup to make traversal work in a unit test.

        >>> setUp()

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self): return "http://localhost/frogpond/groups"
        ...
        >>> from schooltool.interfaces import ISchoolToolGroupContainer
        >>> from zope.app.traversing.browser.interfaces import IAbsoluteURL
        >>> ztapi.browserViewProviding(ISchoolToolGroupContainer, FakeURL, \
        ...                            providing=IAbsoluteURL)

    we need to stub out the widgets

        >>> from zope.app.form.interfaces import IInputWidget
        >>> from zope.app.form.browser.objectwidget import ObjectWidget
        >>> from zope.schema.interfaces import IObject
        >>> ztapi.browserViewProviding(IObject, ObjectWidget, IInputWidget)

    fake the ZCML

        >>> class SectionAddViewForTesting(SectionAddView):
        ...     schema = ISection
        ...     fieldNames = ('title', 'description')
        ...     _factory = Section
        ...     _arguments = []
        ...     _keyword_arguments = []
        ...     _set_before_add = 'title',
        ...     _set_after_add = []

    create a schooltool instance:

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> from zope.app.component.site import LocalSiteManager
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> from zope.app.component.hooks import setSite
        >>> setSite(app)
        >>> container = app['groups']
        >>> course = Course(title="Algebra I")
        >>> container['algebraI'] = course

    on to the actual work

    Sections are special types of groups meant to represent one meeting time
    of a course.  If they don't have a course, they can't be created "stand
    alone".

    first a request without a course reference sets the view error.

        >>> request = TestRequest()
        >>> context = AddingStub(container, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.error
        u'Need a course ID.'
        >>> view.update()

    A request with course_id doesn't

        >>> request = TestRequest()
        >>> request.form = {'field.course_id' : 'algebraI'}
        >>> context = AddingStub(container, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.error is None
        True
        >>> view.update()

    if there's a course_id in the request that doesn't match any known courses
    the error is different.

        >>> request = TestRequest()
        >>> request.form = {'field.course_id' : 'math'}
        >>> context = AddingStub(container, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.error
        u'No such course.'
        >>> view.update()

    Currently our course has no members

        >>> for member in course.members:
        ...     print member

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': True,
        ...                 'field.course_id' : 'algebraI',
        ...                 'field.title': 'Section 1'}
        >>> context = AddingStub(container, request)
        >>> view = SectionAddViewForTesting(context, request)

    taking this out for the moment because I'm missing some test setup

        >>> #view.update()

    if you call view.update() this will actually work, printing 'Section 1'
        >>> for member in course.members:
        ...     print member.title

        >>> tearDown()

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
