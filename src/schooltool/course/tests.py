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
Unit tests for course and section implementations.

$Id: test_app.py 4750 2005-08-16 19:13:10Z srichter $
"""
import unittest
from zope.testing import doctest
from zope.interface.verify import verifyObject


def doctest_CourseContainer():
    r"""Schooltool toplevel container for Courses.

        >>> from schooltool.course.interfaces import ICourseContainer
        >>> from schooltool.course.course import CourseContainer
        >>> courses = CourseContainer()
        >>> verifyObject(ICourseContainer, courses)
        True

    It should only be able to contain courses

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from zope.app.container.constraints import checkObject
        >>> checkObject(courses, 'name', Course())

        >>> checkObject(courses, 'name', Section())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...
    """


def doctest_Course():
    r"""Tests for Courses

    Courses are similar to SchoolBell groups but have sections instead of
    members.

        >>> from schooltool.course.course import Course
        >>> algebraI = Course("Algebra I", "First year math.")
        >>> from schooltool.course.interfaces import ICourse
        >>> verifyObject(ICourse, algebraI)
        True

    Basic properties:

        >>> algebraI.title
        'Algebra I'
        >>> algebraI.description
        'First year math.'

    Courses are instructional content that is taught in Sections, the Sections
    are related to the course with the schooltool URICourseSections
    relationship.

    To test the relationship we need to do some setup:

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.relationships import enforceCourseSectionConstraint
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceCourseSectionConstraint)

    We need some sections and a person to test:

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from schooltool.person.person import Person
        >>> section1 = Section(title="section1")
        >>> section2 = Section(title="section2")
        >>> section3 = Section(title="section3")
        >>> person = Person()

    Our course doesn't have any sections yet:

        >>> for section in algebraI.sections:
        ...     print section

    Lets add one:

        >>> algebraI.sections.add(section1)
        >>> for section in algebraI.sections:
        ...     print section.title
        section1

    Lets try to add a person to the course:

        >>> algebraI.sections.add(person)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    Lets try to add a course to the course:

        >>> history = Course()
        >>> algebraI.sections.add(history)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    No luck, you can only add sections:

        >>> algebraI.sections.add(section2)
        >>> algebraI.sections.add(section3)
        >>> for section in algebraI.sections:
        ...     print section.title
        section1
        section2
        section3

    That's it:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()
    """


def doctest_Section():
    r"""Tests for course section groups.

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.relationship import getRelatedObjects
        >>> setUp()

        >>> from schooltool.course.section import Section
        >>> section = Section(title="section 1", description="advanced")
        >>> from schooltool.course.interfaces import ISection
        >>> verifyObject(ISection, section)
        True

    sections have some basic properties:

        >>> section.title
        'section 1'
        >>> section.description
        'advanced'
        >>> section.size
        0

    We'll add an instructor to the section.

        >>> from schooltool.person.person import Person
        >>> from schooltool.person.interfaces import IPerson
        >>> teacher = Person('teacher', 'Mr. Jones')
        >>> section.instructors.add(teacher)

    Now we'll add some learners to the Section with the sections membership
    RelationshipProperty.

        >>> section.members.add(Person('first','First'))
        >>> section.members.add(Person('second','Second'))
        >>> section.members.add(Person('third','Third'))

        >>> for person in section.members:
        ...     print person.title
        First
        Second
        Third
        >>> section.size
        3

    We can add a Group as a member

        >>> from schooltool.group.group import Group
        >>> group = Group('group','Group')
        >>> section.members.add(group)
        >>> for member in section.members:
        ...     print member.title
        First
        Second
        Third
        group

    That group is empty so the size of our section doesn't change:

        >>> section.size
        3

    If the group grows, our section grows as well:

        >>> group.members.add(Person('fourth','Fourth'))
        >>> group.members.add(Person('fifth','Fifth'))
        >>> section.size
        5

        >>> for person in section.instructors:
        ...     print person.title
        Mr. Jones

    Sections are generally shown in the interface by their label.  Labels are
    created from the list of instructors, courses, and XXX time (not yet).

        >>> from zope.i18n import translate
        >>> translate(section.label)
        u'Mr. Jones -- '

    Labels are updated dynamically when more instructors are added.

        >>> section.instructors.add(Person('teacher2', 'Mrs. Smith'))
        >>> translate(section.label)
        u'Mr. Jones Mrs. Smith -- '

    Label s should include the courses that a Section is part of:

        >>> from schooltool.course.course import Course
        >>> course = Course(title="US History")
        >>> course.sections.add(section)
        >>> translate(section.label)
        u'Mr. Jones Mrs. Smith -- US History'

    The course should be listed in courses:

        >>> for course in section.courses:
        ...     print course.title
        US History

    Sections can be part of more than one Course:

        >>> english = Course(title="English")
        >>> section.courses.add(english)
        >>> for course in section.courses:
        ...     print course.title
        US History
        English

    Sections can have a location resource to indicate where the section
    regularly meets.

        >>> from schooltool.resource.resource import Resource
        >>> section.location is None
        True

        >>> room123 = Resource("Room123", isLocation=True)
        >>> section.location = room123
        >>> section.location.title
        'Room123'

    Locations have to be marked with isLocation, so printers can't be
    locations:

        >>> printer = Resource("Laser Printer")
        >>> section.location = printer
        Traceback (most recent call last):
        ...
        TypeError: Locations must be location resources.

    Things other than resources can't be locations:

        >>> section.location = Course()
        Traceback (most recent call last):
        ...
        TypeError: Locations must be location resources.

        >>> section.location = None

    We're done:

        >>> tearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
