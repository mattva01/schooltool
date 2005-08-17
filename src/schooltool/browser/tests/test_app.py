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

import schooltool.course.course
import schooltool.course.section
from schooltool import timetable
from schooltool.interfaces import ApplicationInitializationEvent
from schoolbell.app.browser.tests.setup import setUp, tearDown
from schoolbell.app.group.group import GroupContainer
from schoolbell.app.person.person import PersonContainer
from schoolbell.app.resource.resource import ResourceContainer


def setUpSchool():
    from schooltool.app import SchoolToolApplication
    from zope.app.component.hooks import setSite
    from zope.app.component.site import LocalSiteManager
    app = SchoolToolApplication()


    # Usually automatically called subscribers
    # XXX: Use future test setup
    app['resources'] = ResourceContainer()
    app['persons'] = PersonContainer()
    app['groups'] = GroupContainer()

    schooltool.course.course.addCourseContainerToApplication(
        ApplicationInitializationEvent(app))
    schooltool.course.section.addSectionContainerToApplication(
        ApplicationInitializationEvent(app))
    timetable.addToApplication(ApplicationInitializationEvent(app))

    app.setSiteManager(LocalSiteManager(app))
    directlyProvides(app, IContainmentRoot)
    setSite(app)
    return app


def doctest_SchoolBellApplicationView():
    r"""Test for SchoolBellApplicationView

    Some setup

        >>> from schooltool.app import getApplicationPreferences
        >>> from schooltool.interfaces import IApplicationPreferences
        >>> from schooltool.interfaces import ISchoolToolApplication

        >>> app = setUpSchool()

        >>> ztapi.provideAdapter(ISchoolToolApplication,
        ...                      IApplicationPreferences,
        ...                      getApplicationPreferences)

        >>> directlyProvides(app, IContainmentRoot)

    Now lets create a view

        >>> from schooltool.browser.app import SchoolToolApplicationView
        >>> request = TestRequest()
        >>> view = SchoolToolApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        302
        >>> request.response.getHeaders()['Location']
        'http://127.0.0.1/calendar'

    If we change a the front page preference, we should not be redirected

        >>> IApplicationPreferences(app).frontPageCalendar = False
        >>> request = TestRequest()
        >>> view = SchoolToolApplicationView(app, request)
        >>> view.update()

        >>> request.response.getStatus()
        599

    """




def doctest_LocationResourceVocabulary():
    r"""Tests for location choice vocabulary.

        >>> from schooltool.browser.app import LocationResourceVocabulary

    We should be able to choose any Resource in the resource container that is
    marked with isLocation.

        >>> app = setUpSchool()

    There's no potential terms:

        >>> vocab = LocationResourceVocabulary(app['sections'])
        >>> vocab.by_token
        {}

    Now we'll add some resources

        >>> from schoolbell.app.resource.resource import Resource
        >>> import pprint
        >>> app['resources']['room1'] = room1 = Resource("Room 1",
        ...                                               isLocation=True)
        >>> app['resources']['room2'] = room2 = Resource("Room 2",
        ...                                               isLocation=True)
        >>> app['resources']['room3'] = room3 = Resource("Room 3",
        ...                                               isLocation=True)
        >>> app['resources']['printer'] = printer = Resource("Printer")

    All of our rooms are available, but the printer is not.

        >>> vocab = LocationResourceVocabulary(app['sections'])
        >>> pprint.pprint(vocab.by_token)
        {'Room 1': <zope.schema.vocabulary.SimpleTerm object at ...,
         'Room 2': <zope.schema.vocabulary.SimpleTerm object at ...,
         'Room 3': <zope.schema.vocabulary.SimpleTerm object at ...}

    """


def doctest_PersonView():
    r"""Test for PersonView

    Let's create a view for a person:

        >>> from schooltool.browser.app import PersonView
        >>> from schoolbell.app.person.person import Person
        >>> from schoolbell.app.person.interfaces import IPerson
        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schoolbell.app.person.details import getPersonDetails
        >>> from schoolbell.app.person.interfaces import IPersonDetails
        >>> setup.setUpAnnotations()
        >>> setUp()
        >>> ztapi.provideAdapter(IPerson, IPersonDetails, getPersonDetails)

        >>> from schooltool.app import SchoolToolApplication
        >>> school = setUpSchool()
        >>> persons = school['persons']
        >>> sections = school['sections']

        >>> persons['teacher'] = teacher = Person("Teacher")
        >>> teacher_view = PersonView(teacher, TestRequest())

    Not a teacher yet:

        >>> teacher_view.isTeacher()
        False

    We'll need something to teach:

        >>> from schooltool.course.section import Section
        >>> sections['section'] = section = Section(title="History")
        >>> sections['section2'] = section2 = Section(title="Algebra")
        >>> section.instructors.add(teacher)

    Now we're teaching:

        >>> teacher_view.isTeacher()
        True
        >>> teacher_view.isLearner()
        False

    We'll teach 2 courses this semester, and we'll need an easy way to get a
    list of all the courses we're teaching.

        >>> section2.instructors.add(teacher)
        >>> teacher_view = PersonView(teacher, TestRequest())
        >>> [section.title for section in teacher_view.instructorOf()]
        ['History', 'Algebra']

    Let's create a student

        >>> persons['student'] = student = Person("Student")
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

        >>> sections['section3'] = section3 = Section(title="English")
        >>> sections['section4'] = section4 = Section(title="Gym")

    Our student is taking several classes

        >>> section3.members.add(student)
        >>> student_view = PersonView(student, TestRequest())

        >>> [section['section'].title for section in student_view.learnerOf()]
        ['Algebra', 'English']

    Students can also participate in sections as part of a group, say all 10th
    grade students must take gym:

        >>> from schoolbell.app.group.group import Group
        >>> tenth_grade = Group(title="Tenth Grade")
        >>> tenth_grade.members.add(student)
        >>> section4.members.add(tenth_grade)

        >>> student_view = PersonView(student, TestRequest())
        >>> [section['section'].title for section in student_view.learnerOf()]
        ['Algebra', 'English', 'Gym']

    One thing that might confuse is that learnerOf may be similar to but not
    the same as view.context.groups

        >>> [group.title for group in student_view.context.groups]
        ['Algebra', 'English', 'Tenth Grade']

    We want to display the generic groups a person is part of that aren't
    sections so we have a filter in the view:

        >>> team = Group(title="Sports Team")
        >>> team.members.add(student)
        >>> student_view = PersonView(student, TestRequest())
        >>> [group.title for group in student_view.memberOf()]
        ['Tenth Grade', 'Sports Team']

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
