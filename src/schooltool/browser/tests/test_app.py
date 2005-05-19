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
from zope.interface import directlyProvides
from zope.app.traversing.interfaces import IContainmentRoot
from zope.i18n import translate

from schoolbell.app.browser.tests.setup import setUp, tearDown

# Used for CourseAddView and SectionAddView
from zope.app.container.browser.adding import Adding


class AddingStub(Adding):
    pass


def doctest_CourseContainerView():
    r"""View for the courses container.

        >>> from schooltool.browser.app import CourseContainerView
        >>> from schooltool.app import CourseContainer
        >>> cc = CourseContainer()
        >>> request = TestRequest()
        >>> view = CourseContainerView(cc, request)

    """


def doctest_CourseView():
    r"""View for courses.

    Lets create a simple view for a course:

        >>> from schooltool.browser.app import CourseView
        >>> from schooltool.app import Course
        >>> course = Course(title="Algebra 1")
        >>> request = TestRequest()
        >>> view = CourseView(course, request)

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
        >>> container = app['courses']
        >>> request = TestRequest()
        >>> context = AddingStub(container, request)
        >>> context = container

        >>> view = CourseAddViewForTesting(context, request)
        >>> view.update()

        >>> request = TestRequest()
        >>> request.form = {'field.title' : 'math'}
        >>> context = AddingStub(context, request)
        >>> view = CourseAddViewForTesting(context, request)
        >>> view.update()

    """


def doctest_SectionContainerView():
    r"""View for the sections container.

        >>> from schooltool.browser.app import SectionContainerView
        >>> from schooltool.app import SectionContainer
        >>> sc = SectionContainer()
        >>> request = TestRequest()
        >>> view = SectionContainerView(sc, request)

    """


def doctest_SectionView():
    r"""View for sections

    Lets create a simple view for a section:

        >>> from schooltool.browser.app import SectionView
        >>> from schooltool.app import Section
        >>> section = Section()
        >>> request = TestRequest()
        >>> view = SectionView(section, request)
        >>> view.getPersons()
        []
        >>> view.getGroups()
        []

    Let's create some students and a group:

        >>> from schooltool.app import Group, Person
        >>> person1 = Person(title='Person1')
        >>> person2 = Person(title='Person2')
        >>> person3 = Person(title='Person3')
        >>> person4 = Person(title='Person4')
        >>> form = Group('Form1')
        >>> form.members.add(person3)
        >>> form.members.add(person4)

    Let's add the individuals and the group to the section:

        >>> section.members.add(person1)
        >>> section.members.add(person2)
        >>> section.members.add(form)
        >>> view = SectionView(section, request)
        >>> [p.title for p in view.getPersons()]
        ['Person1', 'Person2']
        >>> [g.title for g in view.getGroups()]
        ['Form1']

    TODO in the future we should probably prevent users being direct memebers
    of a section if they're transitive members.

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
        >>> from schooltool.interfaces import IGroupContainer
        >>> from zope.app.traversing.browser.interfaces import IAbsoluteURL
        >>> ztapi.browserViewProviding(IGroupContainer, FakeURL, \
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

    create a SchoolTool instance:

        >>> from schooltool.app import SchoolToolApplication
        >>> app = SchoolToolApplication()
        >>> from zope.app.component.site import LocalSiteManager
        >>> app.setSiteManager(LocalSiteManager(app))
        >>> from zope.app.component.hooks import setSite
        >>> setSite(app)
        >>> directlyProvides(app, IContainmentRoot)
        >>> sections = app['sections']
        >>> courses = app['courses']
        >>> course = Course(title="Algebra I")
        >>> courses['algebraI'] = course

    On to the actual work...

    Sections are special types of groups meant to represent one meeting time
    of a course.  If they don't have a course, they can't be created "stand
    alone".

    First a request without a course reference sets the view error.

        >>> request = TestRequest()
        >>> context = AddingStub(sections, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.error
        u'Need a course ID.'
        >>> view.update()

    A request with course_id doesn't

        >>> request = TestRequest()
        >>> request.form = {'field.course_id' : 'algebraI'}
        >>> context = AddingStub(sections, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.error is None
        True
        >>> view.update()

    if there's a course_id in the request that doesn't match any known courses
    the error is different.

        >>> request = TestRequest()
        >>> request.form = {'field.course_id' : 'math'}
        >>> context = AddingStub(sections, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.error
        u'No such course.'
        >>> view.update()

    Currently our course has no sections

        >>> for section in course.sections:
        ...     print section

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': True,
        ...                 'field.course_id' : 'algebraI'}
        >>> context = AddingStub(sections, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view.update()
        ''

        >>> translate(view.label)
        u'Add a Section to Algebra I'

    Our section is now a member of the Course, we use a generic title for
    sections

        >>> for section in course.sections:
        ...     print section.__name__
        Section

        >>> tearDown()

    """


def doctest_SectionInstructorView():
    r"""Tests for adding sections.

    lets setup a schooltool instance with some members.

        >>> from schooltool.app import SchoolToolApplication
        >>> from schoolbell.app.app import Person
        >>> school = SchoolToolApplication()
        >>> persons = school['persons']
        >>> directlyProvides(school, IContainmentRoot)
        >>> sections = school['sections']
        >>> persons['smith'] = Person('smith', 'Mr. Smith')
        >>> persons['jones'] = Person('jones', 'Mrs. Jones')
        >>> persons['stevens'] = Person('stevens', 'Ms. Stevens')

    SecionInstructorView is used to relate persons to the section with the
    URIInstruction relationship.

        >>> from schooltool.app import Section
        >>> from schooltool.browser.app import SectionInstructorView
        >>> section = Section()
        >>> sections['section'] = section
        >>> request = TestRequest()
        >>> view = SectionInstructorView(section, request)
        >>> view.update()

    No instructors yet:

        >>> [i.title for i in section.instructors]
        []

    lets see who's available to be an instructor:

        >>> [i.title for i in view.getPotentialInstructors()]
        ['Mrs. Jones', 'Mr. Smith', 'Ms. Stevens']

    let's make Mr. Smith the instructor:

        >>> request = TestRequest()
        >>> request.form = {'instructor.smith': 'on', 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionInstructorView(section, request)
        >>> view.update()

    He should have joined:

        >>> [i.title for i in section.instructors]
        ['Mr. Smith']

    And we should be directed to the group info page:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/sections/section'

    Someone might want to cancel a change.

        We can cancel an action if we want to:

        >>> request = TestRequest()
        >>> request.form = {'instructor.jones': 'on', 'CANCEL': 'Cancel'}
        >>> view = SectionInstructorView(section, request)
        >>> view.update()
        >>> [person.title for person in section.instructors]
        ['Mr. Smith']
        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/sections/section'

    a Section can have more than one instructor:

        >>> request.form = {'instructor.smith': 'on',
        ...                 'instructor.stevens': 'on',
        ...                 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionInstructorView(section, request)
        >>> request = TestRequest()
        >>> view.update()

        >>> [person.title for person in section.instructors]
        ['Mr. Smith', 'Ms. Stevens']

    We can remove an instructor:

        >>> request.form = {'instructor.stevens': 'on',
        ...                 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionInstructorView(section, request)
        >>> request = TestRequest()
        >>> view.update()

    Goodbye Mr. Smith:

        >>> [person.title for person in section.instructors]
        ['Ms. Stevens']


    """


def doctest_SectionLearnerView():
    r"""Tests for adding sections.

    lets setup a schooltool instance with some members.

        >>> from schooltool.app import SchoolToolApplication
        >>> from schoolbell.app.app import Person
        >>> school = SchoolToolApplication()
        >>> persons = school['persons']
        >>> directlyProvides(school, IContainmentRoot)
        >>> sections = school['sections']
        >>> persons['smith'] = Person('smith', 'John Smith')
        >>> persons['jones'] = Person('jones', 'Sally Jones')
        >>> persons['stevens'] = Person('stevens', 'Bob Stevens')

    SecionLearnerView is used to relate persons to the section with the
    URIMembership relationship.  Persons with standard membership in a section
    are considered 'learners' or 'students':

        >>> from schooltool.app import Section
        >>> from schooltool.browser.app import SectionLearnerView
        >>> section = Section()
        >>> sections['section'] = section
        >>> request = TestRequest()
        >>> view = SectionLearnerView(section, request)
        >>> view.update()

    No learners yet:

        >>> [i.title for i in section.members]
        []

    lets see who's available to be an learner:

        >>> [i.title for i in view.getPotentialLearners()]
        ['Sally Jones', 'John Smith', 'Bob Stevens']

    let's make Mr. Smith the learner:

        >>> request = TestRequest()
        >>> request.form = {'member.smith': 'on', 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionLearnerView(section, request)
        >>> view.update()

    He should have joined:

        >>> [i.title for i in section.members]
        ['John Smith']

    And we should be directed to the group info page:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/sections/section'

    Someone might want to cancel a change.

        We can cancel an action if we want to:

        >>> request = TestRequest()
        >>> request.form = {'member.jones': 'on', 'CANCEL': 'Cancel'}
        >>> view = SectionLearnerView(section, request)
        >>> view.update()
        >>> [person.title for person in section.members]
        ['John Smith']
        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/sections/section'

    a Section can have more than one learner:

        >>> request.form = {'member.smith': 'on',
        ...                 'member.stevens': 'on',
        ...                 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionLearnerView(section, request)
        >>> request = TestRequest()
        >>> view.update()

        >>> [person.title for person in section.members]
        ['John Smith', 'Bob Stevens']

    We can remove an learner:

        >>> request.form = {'member.stevens': 'on',
        ...                 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionLearnerView(section, request)
        >>> request = TestRequest()
        >>> view.update()

    Goodbye Mr. Smith:

        >>> [person.title for person in section.members]
        ['Bob Stevens']

    """


def doctest_SectionLearnerGroupView():
    r"""Tests for adding groups of students to sections.

    lets setup a schooltool instance with some members.

        >>> from schooltool.browser.app import SectionLearnerGroupView
        >>> from schooltool.app import SchoolToolApplication
        >>> from schoolbell.app.app import Person, Group
        >>> school = SchoolToolApplication()
        >>> persons = school['persons']
        >>> groups = school['groups']
        >>> directlyProvides(school, IContainmentRoot)
        >>> sections = school['sections']

    Some People:

        >>> persons['smith'] = smith = Person('smith', 'John Smith')
        >>> persons['jones'] = jones = Person('jones', 'Sally Jones')
        >>> persons['stevens'] = stevens = Person('stevens', 'Bob Stevens')

    We'll need a group:

        >>> groups['form1'] = form1 = Group(title="Form 1")
        >>> form1.members.add(smith)
        >>> form1.members.add(jones)

        >>> from schooltool.app import Section
        >>> section = Section()
        >>> sections['section'] = section
        >>> request = TestRequest()


        >>> view = SectionLearnerGroupView(section, request)
        >>> view.update()

    Let's see what's available to add:

        >>> [g.title for g in view.getPotentialLearners()]
        ['Form 1']

    No learners yet:

        >>> [i.title for i in section.members]
        []

    Lets add the Group as a member:

        >>> request = TestRequest()
        >>> request.form = {'member.form1': 'on', 'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionLearnerGroupView(section, request)
        >>> view.update()

        >>> [g.title for g in section.members]
        ['Form 1']

    We can delete it like we would a Person:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply'}
        >>> view = SectionLearnerGroupView(section, request)
        >>> view.update()

        >>> [g.title for g in section.members]
        []

    """


def doctest_PersonView():
    r"""Test for PersonView

    Let's create a view for a person:

        >>> from schooltool.browser.app import PersonView
        >>> from schooltool.app import Person
        >>> from schooltool.interfaces import IPerson
        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schoolbell.app.app import getPersonDetails
        >>> from schoolbell.app.interfaces import IPersonDetails
        >>> setup.setUpAnnotations()
        >>> setUp()
        >>> ztapi.provideAdapter(IPerson, IPersonDetails, getPersonDetails)
        >>> teacher = Person()
        >>> teacher_view = PersonView(teacher, TestRequest())

    Not a teacher yet:

        >>> teacher_view.isTeacher()
        False

    We'll need something to teach:

        >>> from schooltool.app import Section
        >>> section = Section()
        >>> section.instructors.add(teacher)

    Now we're teaching:

        >>> teacher_view.isTeacher()
        True
        >>> teacher_view.isLearner()
        False

    Let's create a student

        >>> student = Person()
        >>> student_view = PersonView(student, TestRequest())

        >>> student_view.isTeacher()
        False
        >>> student_view.isLearner()
        False

    Membership in a Section implies being a learner:

        >>> section.members.add(student)
        >>> student_view.isTeacher()
        False
        >>> student_view.isLearner()
        True

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
