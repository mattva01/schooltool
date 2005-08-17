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
Unit tests for schooltool.relationships

$Id: test_app.py 3504 2005-04-22 16:34:13Z bskahan $
"""

import unittest
from zope.testing import doctest
from zope.app import zapi
from zope.interface.verify import verifyObject
from zope.interface import implements


def doctest_Instruction():
    r"""Tests for Instruction URIs and methods

        >>> from schooltool.relationships import *

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceInstructionConstraints)

    We will need some sample persons and sections for the demonstration

        >>> from schoolbell.app.person.person import Person
        >>> from schooltool.course.section import Section
        >>> jonas = Person()
        >>> petras = Person()
        >>> developers = Section()
        >>> admins = Section()

    There are some constraints: Only objects providing ISection can be
    Sections.

        >>> Instruction(instructor=jonas, section=petras)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_CourseSections():
    r"""Tests for CourseSections relationship

    Lets import the pieces of CourseSections

        >>> from schooltool.relationships import URICourseSections, URICourse
        >>> from schooltool.relationships import CourseSections
        >>> from schooltool.relationships import URISectionOfCourse
        >>> from schooltool.relationships import enforceCourseSectionConstraint

    Relationship tests require some setup:

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceCourseSectionConstraint)

    We will need a course and several sections:

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from schoolbell.app.person.person import Person
        >>> history = Course()
        >>> section1 = Section(title = "section1")
        >>> section2 = Section(title = "section2")
        >>> section3 = Section(title = "section3")
        >>> section4 = Section(title = "section4")
        >>> person = Person()

    Our course doesn't have any sections yet:

        >>> for section in history.sections:
        ...     print section

    Lets add one:

        >>> history.sections.add(section1)
        >>> for section in history.sections:
        ...     print section.title
        section1

    Lets try to add a person to the course:

        >>> history.sections.add(person)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    Lets try to add a course to the course:

        >>> algebra = Course()
        >>> history.sections.add(algebra)
        Traceback (most recent call last):
        ...
        InvalidRelationship: Sections must provide ISection.

    No luck, you can only add sections:

        >>> history.sections.add(section2)
        >>> history.sections.add(section3)
        >>> for section in history.sections:
        ...     print section.title
        section1
        section2
        section3

    You can use the Relationship to relate sections and courses:

        >>> CourseSections(course=history, section=section4)
        >>> for section in history.sections:
        ...     print section.title
        section1
        section2
        section3
        section4

    That's it:

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_updateInstructorCalendars():
    r"""
        >>> from schooltool.relationships import updateInstructorCalendars
        >>> from schooltool.relationships import URIInstruction
        >>> from schooltool.relationships import URISection, URIInstructor
        >>> from schoolbell.relationship.interfaces import \
        ...                                         IRelationshipAddedEvent
        >>> from schoolbell.relationship.interfaces import \
        ...                                         IRelationshipRemovedEvent
        >>> from schoolbell.app.person.person import Person
        >>> from schooltool.course.section import Section
        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

        >>> class AddEventStub(dict):
        ...     rel_type = URIInstruction
        ...     implements(IRelationshipAddedEvent)

        >>> class RemoveEventStub(dict):
        ...     rel_type = URIInstruction
        ...     implements(IRelationshipRemovedEvent)

        >>> class OtherEventStub(dict):
        ...     rel_type = URIInstruction

        >>> person = Person()
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []
        >>> section = Section(title="SectionA")

    When the person is made the instructor of a section the sections calendar
    is added to the overlaid calendars:

        >>> add = AddEventStub()
        >>> add[URIInstructor] = person
        >>> add[URISection] = section
        >>> updateInstructorCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionA']

    The calendar is removed when the instructor is no longer in the section:

        >>> remove = RemoveEventStub()
        >>> remove[URIInstructor] = person
        >>> remove[URISection] = section
        >>> updateInstructorCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    If a person allready has that calendar nothing changes:

        >>> sectionb = Section(title="SectionB")
        >>> person.overlaid_calendars.add(sectionb.calendar)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

        >>> add = AddEventStub()
        >>> add[URIInstructor] = person
        >>> add[URISection] = sectionb
        >>> updateInstructorCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

    If the person removes the calendar manually, that's ok:

        >>> person.overlaid_calendars.remove(sectionb.calendar)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []


        >>> remove = RemoveEventStub()
        >>> remove[URIInstructor] = person
        >>> remove[URISection] = sectionb
        >>> updateInstructorCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    Events that aren't RelationshipAdded/Removed are ignored:

        >>> other = OtherEventStub()
        >>> other[URIInstructor] = person
        >>> other[URISection] = sectionb
        >>> updateInstructorCalendars(other)

        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []


        >>> tearDown()

    """


def doctest_updateStudentCalendars():
    r"""
        >>> from schooltool.relationships import updateStudentCalendars
        >>> from schoolbell.app.membership import URIMembership
        >>> from schoolbell.app.membership import URIGroup, URIMember
        >>> from schoolbell.relationship.interfaces import \
        ...                                         IRelationshipAddedEvent
        >>> from schoolbell.relationship.interfaces import \
        ...                                         IRelationshipRemovedEvent
        >>> from schooltool.course.section import Section
        >>> from schoolbell.app.person.person import Person
        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

        >>> class AddEventStub(dict):
        ...     rel_type = URIMembership
        ...     implements(IRelationshipAddedEvent)

        >>> class RemoveEventStub(dict):
        ...     rel_type = URIMembership
        ...     implements(IRelationshipRemovedEvent)

        >>> class OtherEventStub(dict):
        ...     rel_type = URIMembership

        >>> person = Person()
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []
        >>> section = Section(title="SectionA")

    When the person is made a member of a section the sections calendar
    is added to the overlaid calendars:

        >>> add = AddEventStub()
        >>> add[URIMember] = person
        >>> add[URIGroup] = section
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionA']

    The calendar is removed when the person is no longer in the section:

        >>> remove = RemoveEventStub()
        >>> remove[URIMember] = person
        >>> remove[URIGroup] = section
        >>> updateStudentCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    If a person allready has that calendar nothing changes:

        >>> sectionb = Section(title="SectionB")
        >>> person.overlaid_calendars.add(sectionb.calendar)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

        >>> add = AddEventStub()
        >>> add[URIMember] = person
        >>> add[URIGroup] = sectionb
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        ['SectionB']

    If the person removes the calendar manually, that's ok for now, we may
    want to take away this ability later.

        >>> person.overlaid_calendars.remove(sectionb.calendar)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

        >>> remove = RemoveEventStub()
        >>> remove[URIMember] = person
        >>> remove[URIGroup] = sectionb
        >>> updateStudentCalendars(remove)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    Events that aren't RelationshipAdded/Removed are ignored:

        >>> other = OtherEventStub()
        >>> other[URIMember] = person
        >>> other[URIGroup] = sectionb
        >>> updateStudentCalendars(other)

        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    If you add a person to a Group that isn't a section, nothing happens, the
    user will have to overlay the calendar manually:

        >>> from schooltool.app import Group
        >>> person = Person()
        >>> group = Group()
        >>> add = AddEventStub()
        >>> add[URIMember] = person
        >>> add[URIGroup] = group
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []

    You can add a group to a section and it's members overlay list will be
    updated:

        >>> student = Person()
        >>> [cal.calendar.title for cal in person.overlaid_calendars]
        []
        >>> freshmen = Group()
        >>> freshmen.members.add(student)
        >>> section = Section("Freshmen Math")
        >>> add = AddEventStub()
        >>> add[URIMember] = freshmen
        >>> add[URIGroup] = section
        >>> updateStudentCalendars(add)
        >>> [cal.calendar.title for cal in student.overlaid_calendars]
        ['Freshmen Math']

        >>> remove = RemoveEventStub()
        >>> remove[URIMember] = freshmen
        >>> remove[URIGroup] = section
        >>> updateStudentCalendars(remove)
        >>> [cal.calendar.title for cal in student.overlaid_calendars]
        []

        >>> tearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.relationships',
                                     optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
