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
from zope.component import provideAdapter
from zope.testing import doctest
from zope.app import zapi
from zope.interface.verify import verifyObject
from zope.app.testing import setup, ztapi, placelesssetup
from schoolbell.app.tests.test_security import setUpLocalGrants
from zope.app.container.contained import ObjectAddedEvent


def doctest_SchoolToolApplication():
    """SchoolToolApplication

    Let's check that the interface is satisfied:

        >>> from schooltool.app import SchoolToolApplication
        >>> from schooltool.interfaces import ISchoolToolApplication

    We need to register an adapter to make the title attribute available:

        >>> placelesssetup.setUp()
        >>> from schoolbell.app.app import ApplicationPreferences
        >>> from schoolbell.app.interfaces import IApplicationPreferences
        >>> provideAdapter(ApplicationPreferences,
        ...                provides=IApplicationPreferences)

        >>> app = SchoolToolApplication()
        >>> verifyObject(ISchoolToolApplication, app)
        True

        # Usually automatically called subscribers
        # XXX: Should be done with test setup framework
        >>> from schooltool.interfaces import ApplicationInitializationEvent

        >>> from schoolbell.app.person import person
        >>> person.addPersonContainerToApplication(
        ...     ApplicationInitializationEvent(app))
        >>> from schoolbell.app.group import group
        >>> group.addGroupContainerToApplication(
        ...     ApplicationInitializationEvent(app))
        >>> from schoolbell.app.resource import resource
        >>> resource.addResourceContainerToApplication(
        ...     ApplicationInitializationEvent(app))

        >>> import schooltool.app
        >>> schooltool.app.addCourseContainerToApplication(
        ...     ApplicationInitializationEvent(app))
        >>> schooltool.app.addSectionContainerToApplication(
        ...     ApplicationInitializationEvent(app))


    Also, the app is a schoolbell application:

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> verifyObject(ISchoolBellApplication, app)
        True

        >>> placelesssetup.tearDown()

    The person, group, and resource containers should be from
    SchoolTool, not SchoolBell:

        >>> from schoolbell.app.person.interfaces import IPersonContainer
        >>> from schoolbell.app.group.interfaces import IGroupContainer
        >>> from schoolbell.app.resource.interfaces import IResourceContainer
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

    Our ApplicationPreferences title should be 'SchoolTool' by default:

      >>> setup.setUpAnnotations()
      >>> from schooltool.app import getApplicationPreferences
      >>> getApplicationPreferences(app).title
      'SchoolBell'

      XXX: Acceptable for now to see SchoolBell here.
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
        >>> from schoolbell.app.person.interfaces import IPerson
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

        >>> from schoolbell.app.group.group import Group
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

        >>> from schoolbell.app.resource.resource import Resource
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
      ValueError: can't get a SchoolBellApplication

    If current site is a SchoolToolApplication, we get it:

      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolToolApplication() is app
      True

      >>> setup.placelessTearDown()
    """


def doctest_CourseContainer():
    r"""Schooltool toplevel container for Courses.

        >>> from schooltool.interfaces import ICourseContainer
        >>> from schooltool.app import CourseContainer
        >>> courses = CourseContainer()
        >>> verifyObject(ICourseContainer, courses)
        True

    It should only be able to contain courses

        >>> from schooltool.app import Course, Section
        >>> from zope.app.container.constraints import checkObject
        >>> checkObject(courses, 'name', Course())

        >>> checkObject(courses, 'name', Section())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...
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
      ValueError: can't get a SchoolBellApplication

    If current site is a SchoolToolApplication, we get it:

      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

      >>> getSchoolToolApplication() is app
      True

    """


def doctest_applicationCalendarPermissionsSubscriber():
    r"""
    Set up:

        >>> from schooltool import app
        >>> root = setup.placefulSetUp(True)
        >>> setUpLocalGrants()
        >>> st = app.SchoolToolApplication()

        # Usually automatically called subscribers
        # XXX: Should be done with test setup framework.
        >>> from schooltool.interfaces import ApplicationInitializationEvent

        >>> from schoolbell.app.person import person
        >>> person.addPersonContainerToApplication(
        ...     ApplicationInitializationEvent(st))
        >>> from schoolbell.app.group import group
        >>> group.addGroupContainerToApplication(
        ...     ApplicationInitializationEvent(st))
        >>> from schoolbell.app.resource import resource
        >>> resource.addResourceContainerToApplication(
        ...     ApplicationInitializationEvent(st))

        >>> import schooltool.app
        >>> app.addCourseContainerToApplication(
        ...     ApplicationInitializationEvent(st))
        >>> app.addSectionContainerToApplication(
        ...     ApplicationInitializationEvent(st))
        >>> from schooltool import timetable
        >>> timetable.addToApplication(ApplicationInitializationEvent(st))

        >>> root['sb'] = st

        >>> from zope.app.security.interfaces import IUnauthenticatedGroup
        >>> from zope.app.security.principalregistry import UnauthenticatedGroup
        >>> ztapi.provideUtility(IUnauthenticatedGroup,
        ...                      UnauthenticatedGroup('zope.unauthenticated',
        ...                                         'Unauthenticated users',
        ...                                         ''))
        >>> from zope.app.annotation.interfaces import IAnnotatable
        >>> from zope.app.securitypolicy.interfaces import \
        ...      IPrincipalPermissionManager
        >>> from zope.app.securitypolicy.principalpermission import \
        ...      AnnotationPrincipalPermissionManager
        >>> setup.setUpAnnotations()
        >>> ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
        ...                      AnnotationPrincipalPermissionManager)

    Call our subscriber:

        >>> app.applicationCalendarPermissionsSubscriber(ObjectAddedEvent(st))

    Check that unauthenticated has calendarView permission on st.calendar:

        >>> from zope.app.securitypolicy.interfaces import \
        ...         IPrincipalPermissionManager
        >>> unauthenticated = zapi.queryUtility(IUnauthenticatedGroup)
        >>> map = IPrincipalPermissionManager(st)
        >>> x = map.getPermissionsForPrincipal(unauthenticated.id)
        >>> x.sort()
        >>> print x
        [('schoolbell.view', PermissionSetting: Allow), ('schoolbell.viewCalendar', PermissionSetting: Allow)]

    We don't want to open up everything:

        >>> for container in ['persons', 'groups', 'resources', 'sections',
        ...                   'courses']:
        ...     map = IPrincipalPermissionManager(st[container])
        ...     x = map.getPermissionsForPrincipal(unauthenticated.id)
        ...     x.sort()
        ...     print x
        [('schoolbell.view', PermissionSetting: Deny), ('schoolbell.viewCalendar', PermissionSetting: Deny)]
        [('schoolbell.view', PermissionSetting: Deny), ('schoolbell.viewCalendar', PermissionSetting: Deny)]
        [('schoolbell.view', PermissionSetting: Deny), ('schoolbell.viewCalendar', PermissionSetting: Deny)]
        [('schoolbell.view', PermissionSetting: Deny), ('schoolbell.viewCalendar', PermissionSetting: Deny)]
        [('schoolbell.view', PermissionSetting: Deny), ('schoolbell.viewCalendar', PermissionSetting: Deny)]

        >>> for container in ['terms', 'ttschemas']:
        ...     map = IPrincipalPermissionManager(st[container])
        ...     x = map.getPermissionsForPrincipal(unauthenticated.id)
        ...     x.sort()
        ...     print x
        []
        []

    Check that no permissions are set if the object added is not an app.

        >>> person = app.Person('james')
        >>> root['sb']['persons']['james'] = person
        >>> app.applicationCalendarPermissionsSubscriber(
        ...     ObjectAddedEvent(person))
        >>> map = IPrincipalPermissionManager(person.calendar)
        >>> map.getPermissionsForPrincipal(unauthenticated.id)
        []

    Nothing happens if the event isn't ObjectAdded:

        >>> from zope.app.container.contained import ObjectRemovedEvent
        >>> st2 = app.SchoolToolApplication()
        >>> app.applicationCalendarPermissionsSubscriber(
        ...     ObjectRemovedEvent(st2))
        >>> map2 = IPrincipalPermissionManager(st2)
        >>> x2 = map.getPermissionsForPrincipal(unauthenticated.id)
        >>> x2.sort()
        >>> print x2
        []



    Clean up:

        >>> setup.placefulTearDown()
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
