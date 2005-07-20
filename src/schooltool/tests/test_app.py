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

        >>> app = SchoolToolApplication()
        >>> verifyObject(ISchoolToolApplication, app)
        True

    Also, the app is a schoolbell application:

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> verifyObject(ISchoolBellApplication, app)
        True

    The person, group, and resource containers should be from
    SchoolTool, not SchoolBell:

        >>> from schooltool.interfaces import IPersonContainer, IGroupContainer
        >>> from schooltool.interfaces import IResourceContainer
        >>> verifyObject(IPersonContainer, app['persons'])
        True
        >>> verifyObject(IGroupContainer, app['groups'])
        True
        >>> verifyObject(IResourceContainer, app['resources'])
        True

    We should have a CourseContainer and a SectionContainer

        >>> from schooltool.interfaces import ICourseContainer
        >>> verifyObject(ICourseContainer, app['courses'])
        True

        >>> from schooltool.interfaces import ISectionContainer
        >>> verifyObject(ISectionContainer, app['sections'])
        True

    We should also have a calendar:

        >>> app.calendar
        <schoolbell.app.cal.Calendar object at ...

    """


def doctest_Course():
    r"""Tests for Courses

    Courses are similar to SchoolBell groups but have sections instead of
    members.

        >>> from schooltool.app import Course
        >>> algebraI = Course("Algebra I", "First year math.")
        >>> from schooltool.interfaces import ICourse
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

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schooltool.relationships import enforceCourseSectionConstraint
        >>> setUp()
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(enforceCourseSectionConstraint)

    We need some sections and a person to test:

        >>> from schooltool.app import Course, Section, Person
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

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> from schoolbell.relationship import getRelatedObjects
        >>> setUp()

        >>> from schooltool.app import Section
        >>> section = Section(title="section 1", description="advanced")
        >>> from schooltool.interfaces import ISection
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

        >>> from schooltool.app import Person
        >>> from schooltool.interfaces import IPerson
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

        >>> from schooltool.app import Group
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

        >>> from schooltool.app import Course
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

        >>> from schooltool.app import Resource
        >>> section.location is None
        True

        >>> room123 = Resource("Room123", isLocation=True)
        >>> section.location = room123
        >>> section.location.title
        'Room123'

    Locations have to be marked with isLocation, so printers can'r be
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

def doctest_Person():
    """
        >>> from schooltool.app import Person
        >>> p = Person("jonn")

        >>> from schooltool.interfaces import IPerson, ITimetabled
        >>> verifyObject(IPerson, p)
        True
        >>> verifyObject(ITimetabled, p)
        True
    """

def doctest_Group():
    """
        >>> from schooltool.app import Group
        >>> g = Group("The Beatles")

        >>> from schooltool.interfaces import IGroup, ITimetabled
        >>> verifyObject(IGroup, g)
        True
        >>> verifyObject(ITimetabled, g)
        True
    """

def doctest_Resource():
    """
        >>> from schooltool.app import Resource
        >>> r = Resource("Printer")

        >>> from schooltool.interfaces import IResource, ITimetabled
        >>> verifyObject(IResource, r)
        True
        >>> verifyObject(ITimetabled, r)
        True
    """


def doctest_PersonContainer():
    """
    First, make sure that PersonContainer implements the advertised
    interface:

        >>> from schooltool.app import PersonContainer
        >>> from schooltool.interfaces import IPersonContainer
        >>> pc = PersonContainer()
        >>> verifyObject(IPersonContainer, pc)
        True

    It should be able to contain persons:

        >>> from schooltool.app import Group, Section, Course, Person, Resource
        >>> from zope.app.container.constraints import checkObject
        >>> checkObject(pc, 'name', Person())

    But not groups and resources:

        >>> checkObject(pc, 'name', Group())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(pc, 'name', Section())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(pc, 'name', Course())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(pc, 'name', Resource())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

    """


def doctest_GroupContainer():
    """
    First, make sure that GroupContainer implements the
    IGroupContainer interface:

        >>> from schooltool.app import GroupContainer
        >>> from schooltool.interfaces import IGroupContainer
        >>> gc = GroupContainer()
        >>> verifyObject(IGroupContainer, gc)
        True

    Now, let's check that it can contain groups

        >>> from schooltool.app import Group, Section, Course, Person
        >>> from zope.app.container.constraints import checkObject
        >>> checkObject(gc, 'name', Group())

    It cannot contain persons, sections, or courses though:

        >>> checkObject(gc, 'name', Person())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(gc, 'name', Course())
        Traceback (most recent call last):
          ...
        InvalidContainerType: ...

        >>> checkObject(gc, 'name', Section())
        Traceback (most recent call last):
          ...
        InvalidContainerType: ...

    """


def doctest_ResourceContainer():
    """
    First, make sure that ResourceContainer implements the advertised
    interface:

        >>> from schooltool.app import ResourceContainer
        >>> from schooltool.interfaces import IResourceContainer
        >>> rc = ResourceContainer()
        >>> verifyObject(IResourceContainer, rc)
        True

    It should be able to contain resources:

        >>> from schooltool.app import Group, Section, Course, Person, Resource
        >>> from zope.app.container.constraints import checkObject
        >>> checkObject(rc, 'name', Resource())

    But not groups and persons:

        >>> checkObject(rc, 'name', Group())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(rc, 'name', Section())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(rc, 'name', Course())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(rc, 'name', Person())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

    """

def doctest_CourseContainer():
    r"""Schooltool toplevel container for Courses.

        >>> from schooltool.interfaces import ICourseContainer
        >>> from schooltool.app import CourseContainer
        >>> courses = CourseContainer()
        >>> verifyObject(ICourseContainer, courses)
        True

    It should only be able to contain courses

        >>> from schooltool.app import Group, Section, Course, Person, Resource
        >>> from zope.app.container.constraints import checkObject
        >>> checkObject(courses, 'name', Course())

        >>> checkObject(courses, 'name', Group())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(courses, 'name', Person())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(courses, 'name', Section())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

        >>> checkObject(courses, 'name', Resource())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

    """

def doctest_PersonPreferences():
    """Tests for SchoolTool PersonPreferences.

    Simple check against the interface:

        >>> from schooltool.app import PersonPreferences
        >>> prefs = PersonPreferences()
        >>> from schooltool.interfaces import IPersonPreferences
        >>> verifyObject(IPersonPreferences, prefs)
        True

    Check the getPersonPreferences function too:

        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

        >>> from schooltool.app import Person, getPersonPreferences
        >>> person = Person('person')
        >>> prefs = getPersonPreferences(person)

    `prefs` is the SchoolTool preferences object, not SchoolBell:

        >>> prefs
        <schooltool.app.PersonPreferences object at 0x...>

        >>> prefs.cal_periods
        True

        >>> prefs.__parent__ is person
        True

    Called another time, getPersonPreferences() returns the same object:

        >>> getPersonPreferences(person) is prefs
        True

    By the way, getPersonPreferences should preserve settings found in a
    SchoolBell preferences object.

        >>> from schoolbell.app import app as sb
        >>> person = Person('person')
        >>> old_prefs = sb.getPersonPreferences(person)
        >>> old_prefs
        <schoolbell.app.app.PersonPreferences object at 0x...>
        >>> old_prefs.timezone = 'Europe/Vilnius'

        >>> new_prefs = getPersonPreferences(person)
        >>> new_prefs
        <schooltool.app.PersonPreferences object at 0x...>
        >>> new_prefs.timezone
        'Europe/Vilnius'

    Afterwards even the SchoolBell getPersonPreferences function returns the ST
    preferences object.

        >>> sb.getPersonPreferences(person) is new_prefs
        True

    We're done.

        >>> setup.placelessTearDown()

    """


def doctest_getSchoolToolApplication():
    """Tests for getSchoolToolApplication.

    Let's say we have a SchoolTool app.

      >>> from schooltool.app import SchoolToolApplication, Person
      >>> from zope.app.component.site import LocalSiteManager
      >>> app = SchoolToolApplication()
      >>> app.setSiteManager(LocalSiteManager(app))

    If site is not a SchoolToolApplication, we get an error

      >>> from schooltool.app import getSchoolToolApplication
      >>> getSchoolToolApplication()
      Traceback (most recent call last):
      ...
      ValueError: can't get a SchoolToolApplication

    If current site is a SchoolToolApplication, we get it:

      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolToolApplication() is app
      True

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.app',
                                     optionflags=doctest.ELLIPSIS),
                doctest.DocFileSuite('../README.txt',
                                     optionflags=doctest.ELLIPSIS)
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
