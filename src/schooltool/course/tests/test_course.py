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

$Id$
"""
import unittest
from zope.testing import doctest
from zope.interface.verify import verifyObject

from schooltool.relationship.tests import setUp, tearDown


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

        >>> from schooltool.app.relationships import enforceCourseSectionConstraint
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

    """


def doctest_Section():
    r"""Tests for course section groups.

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
    created from the list of instructors and the section title.

        >>> from zope.i18n import translate
        >>> translate(section.label)
        u'Mr. Jones -- section 1'

    Labels are updated dynamically when more instructors are added.

        >>> section.instructors.add(Person('teacher2', 'Mrs. Smith'))
        >>> translate(section.label)
        u'Mr. Jones Mrs. Smith -- section 1'

    The course should be listed in courses:

        >>> from schooltool.course.course import Course
        >>> course = Course(title="US History")
        >>> course.sections.add(section)
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

    """


def doctest_Section_linking():
    r"""Tests for course section linking properties (previous, next and
    linked_sections)

    The purpose of this test is to check that:
    * sections can be linked via Section.previous and Section.next.
    * Section.linked_sections return sections linked with the Section
      in a correct order.
    * it is impossible to create linking loops.

        >>> from schooltool.course.section import Section

        >>> def section_link_str(s):
        ...     return '%s <- %s -> %s' % (
        ...         not s.previous and 'None' or s.previous.title,
        ...         s.title,
        ...         not s.next and 'None' or s.next.title)

        >>> def print_sections(sections):
        ...     '''Print prev and next links for all sections in section_list'''
        ...     for s in sections:
        ...         print section_link_str(s)

        >>> def print_linked(section_list):
        ...     '''Print linked sections for all sections in section_list'''
        ...     for section in section_list:
        ...         linked_str = ', '.join(
        ...             [s.title for s in section.linked_sections])
        ...         print section.title, 'spans:', linked_str

    Create some sections.

        >>> sections = [Section('Sec0'), Section('Sec1'), Section('Sec2')]

    By default sections are not linked.

        >>> print_sections(sections)
        None <- Sec0 -> None
        None <- Sec1 -> None
        None <- Sec2 -> None

    And each section spans only itself.

        >>> print_linked(sections)
        Sec0 spans: Sec0
        Sec1 spans: Sec1
        Sec2 spans: Sec2

    Assign s0 as previous section to s1.  s0 'next' section is also updated.
    A list of linked sections updated for s0 and s1.

        >>> sections[1].previous = sections[0]

        >>> print_sections(sections)
        None <- Sec0 -> Sec1
        Sec0 <- Sec1 -> None
        None <- Sec2 -> None

        >>> print_linked(sections)
        Sec0 spans: Sec0, Sec1
        Sec1 spans: Sec0, Sec1
        Sec2 spans: Sec2

    Assign s2 as next section to s1.

        >>> sections[1].next = sections[2]

        >>> print_sections(sections)
        None <- Sec0 -> Sec1
        Sec0 <- Sec1 -> Sec2
        Sec1 <- Sec2 -> None

        >>> print_linked(sections)
        Sec0 spans: Sec0, Sec1, Sec2
        Sec1 spans: Sec0, Sec1, Sec2
        Sec2 spans: Sec0, Sec1, Sec2

    Let's test section unlinking...

        >>> sections[1].previous = None
        >>> print_sections(sections)
        None <- Sec0 -> None
        None <- Sec1 -> Sec2
        Sec1 <- Sec2 -> None

        >>> print_linked(sections)
        Sec0 spans: Sec0
        Sec1 spans: Sec1, Sec2
        Sec2 spans: Sec1, Sec2

        >>> sections[2].previous = None
        >>> print_sections(sections)
        None <- Sec0 -> None
        None <- Sec1 -> None
        None <- Sec2 -> None

        >>> print_linked(sections)
        Sec0 spans: Sec0
        Sec1 spans: Sec1
        Sec2 spans: Sec2

    And now some extreme cases.  Try the section as next/prev to itself.

        >>> sections[0].previous = sections[0]
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException: Cannot assign section as previous to itself

        >>> sections[0].next = sections[0]
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException: Cannot assign section as next to itself

    Create a long list of linked sections.

        >>> sections = [Section('Sec0')]
        >>> for n in range(5):
        ...     new_sec = Section('Sec%d' % (n+1))
        ...     new_sec.previous = sections[-1]
        ...     sections.append(new_sec)

        >>> print_sections(sections)
        None <- Sec0 -> Sec1
        Sec0 <- Sec1 -> Sec2
        Sec1 <- Sec2 -> Sec3
        Sec2 <- Sec3 -> Sec4
        Sec3 <- Sec4 -> Sec5
        Sec4 <- Sec5 -> None

    Try to introduce a loop by assigning a previous section.

        >>> sections[4].previous = sections[1]

    Note that sections 2 and 3 are removed from the linked list thus avoiding
    the loop.

        >>> print_sections(sections)
        None <- Sec0 -> Sec1
        Sec0 <- Sec1 -> Sec4
        None <- Sec2 -> None
        None <- Sec3 -> None
        Sec1 <- Sec4 -> Sec5
        Sec4 <- Sec5 -> None

        >>> [s.title for s in sections[0].linked_sections]
        ['Sec0', 'Sec1', 'Sec4', 'Sec5']

    Let's reubild the list of 5 linked sections.

        >>> sections[4].previous = sections[3]
        >>> sections[3].previous = sections[2]
        >>> sections[2].previous = sections[1]

        >>> print_linked(sections)
        Sec0 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec1 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec2 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec3 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec4 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec5 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5


    Try to introduce a loop by assigning a next section.

        >>> sections[1].next = sections[4]

    Note that sections 2 and 3 are removed from the linked list thus avoiding
    the loop again.

        >>> print_sections(sections)
        None <- Sec0 -> Sec1
        Sec0 <- Sec1 -> Sec4
        None <- Sec2 -> None
        None <- Sec3 -> None
        Sec1 <- Sec4 -> Sec5
        Sec4 <- Sec5 -> None

        >>> [s.title for s in sections[0].linked_sections]
        ['Sec0', 'Sec1', 'Sec4', 'Sec5']

    Let's reubild the list of 5 linked sections.

        >>> sections[3].next = sections[4]
        >>> sections[2].next = sections[3]
        >>> sections[1].next = sections[2]

        >>> print_linked(sections)
        Sec0 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec1 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec2 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec3 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec4 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5
        Sec5 spans: Sec0, Sec1, Sec2, Sec3, Sec4, Sec5

    And try to introduce another loop.

        >>> sections[0].previous = sections[3]

    Sections between Sec0 and Sec3 were unlinked to avoid the loop.

        >>> print_linked(sections)
        Sec0 spans: Sec3, Sec0
        Sec1 spans: Sec1
        Sec2 spans: Sec2
        Sec3 spans: Sec3, Sec0
        Sec4 spans: Sec4, Sec5
        Sec5 spans: Sec4, Sec5

    """


def doctest_PersonInstructorCrowd():
    """Unit test for the PersonInstructorCrowd

    We'll need a section, a group, and a couple of persons:

        >>> from schooltool.course.section import Section
        >>> from schooltool.person.person import Person
        >>> section = Section(title="section 1", description="advanced")
        >>> teacher = Person('teacher', 'Mr. Jones')
        >>> p1 = Person('p1','First')
        >>> p2 = Person('p2','Second')

    Let the first pupil be a direct member of the section taught by Mr. Jones.

        >>> section.instructors.add(teacher)
        >>> section.members.add(p1)

    The PersonInstructorCrowd should contain the teacher for p1, but not p2:

        >>> from schooltool.course.section import PersonInstructorsCrowd
        >>> PersonInstructorsCrowd(p1).contains(teacher)
        True
        >>> PersonInstructorsCrowd(p2).contains(teacher)
        False

    Non-teachers are not in the crowd:

        >>> PersonInstructorsCrowd(p2).contains(p2)
        False
        >>> PersonInstructorsCrowd(p2).contains(p1)
        False

    """


def doctest_PersonLearnerAdapter(self):
    """Tests for PersonLearnerAdapter.

    We'll need a person, a group, and a couple of sections:

        >>> from schooltool.course.section import Section
        >>> from schooltool.person.person import Person
        >>> section1 = Section(title="section 1", description="advanced")
        >>> section2 = Section(title="section 2", description="advanced")
        >>> student = Person('student', 'Mr. Peter')

     Let's add the student to the two sections.

        >>> section1.members.add(student)
        >>> section2.members.add(student)

    sections method of the adapter should list us both sections:

        >>> from schooltool.course.section import PersonLearnerAdapter
        >>> learner = PersonLearnerAdapter(student)
        >>> [section.title for section in learner.sections()]
        ['section 1', 'section 2']

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
