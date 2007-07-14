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
Unit tests for course and section views.

$Id$
"""
import unittest

from zope.i18n import translate
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.container.browser.adding import Adding
from zope.traversing.interfaces import IContainmentRoot
from zope.app.testing import ztapi
from zope.component import adapts
from zope.interface import implements
from zope.component import provideAdapter

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.testing import setup

class AddingStub(Adding):
    pass

def doctest_CourseContainerView():
    r"""View for the courses container.

        >>> from schooltool.course.browser.course import CourseContainerView
        >>> from schooltool.course.course import CourseContainer
        >>> cc = CourseContainer()
        >>> request = TestRequest()
        >>> view = CourseContainerView(cc, request)

    """


def doctest_CourseView():
    r"""View for courses.

    Lets create a simple view for a course:

        >>> from schooltool.course.browser.course import CourseView
        >>> from schooltool.course.course import Course
        >>> course = Course(title="Algebra 1")
        >>> request = TestRequest()
        >>> view = CourseView(course, request)

    """


def doctest_CourseAddView():
    r"""

        >>> from schooltool.course.browser.course import CourseAddView
        >>> from schooltool.course.course import Course
        >>> from schooltool.course.interfaces import ICourse

        >>> class CourseAddViewForTesting(CourseAddView):
        ...     schema = ICourse
        ...     fieldNames = ('title', 'description')
        ...     _factory = Course


        >>> app = setup.setUpSchoolToolSite()
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


def doctest_CourseCSVImporter():
    r"""Tests for CourseCSVImporter.

    Create a course container and an importer

        >>> from schooltool.course.browser.csvimport import CourseCSVImporter
        >>> from schooltool.course.course import CourseContainer
        >>> container = CourseContainer()
        >>> importer = CourseCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Course 1, Course 1 Description
        ... Course2
        ... Course3, Course 3 Description, Some extra data'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the courses exist

        >>> [course for course in container]
        [u'course-1', u'course2', u'course3']

    Check that descriptions were imported properly

        >>> [course.description for course in container.values()]
        ['Course 1 Description', '', 'Course 3 Description']

    """


def doctest_CourseCSVImportView():
    r"""
    We'll create a course csv import view

        >>> from schooltool.course.browser.csvimport import CourseCSVImportView
        >>> from schooltool.course.course import CourseContainer
        >>> from zope.publisher.browser import TestRequest
        >>> container = CourseContainer()
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : "A Course, The best Course\nAnother Course",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> [course for course in container]
        [u'a-course', u'another-course']

    If no data is provided, we naturally get an error

        >>> request.form = {'charset' : 'UTF-8', 'UPDATE_SUBMIT': 1}
        >>> view.update()
        >>> view.errors
        [u'No data provided']

    We also get an error if a line starts with a comma (no title)

        >>> request.form = {'csvtext' : ", No title provided here",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> view.errors
        [u'Failed to import CSV text', u'Titles may not be empty']

    """


def doctest_SectionContainerView():
    r"""View for the sections container.

        >>> from schooltool.course.browser.section import SectionContainerView
        >>> from schooltool.course.section import SectionContainer
        >>> sc = SectionContainer()
        >>> request = TestRequest()
        >>> view = SectionContainerView(sc, request)

    """


def doctest_SectionView():
    r"""View for sections

    Lets create a simple view for a section:

        >>> from schooltool.course.browser.section import SectionView
        >>> from schooltool.course.section import Section
        >>> section = Section()
        >>> request = TestRequest()
        >>> view = SectionView(section, request)
        >>> view.getPersons()
        []
        >>> view.getGroups()
        []

    Let's create some students and a group:

        >>> from schooltool.group.group import Group
        >>> from schooltool.person.person import Person
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

        >>> from schooltool.course.browser.section import SectionAddView
        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from schooltool.course.interfaces import ISection

    We need some setup to make traversal work in a unit test.

        >>> setUp()

        >>> class FakeURL:
        ...     def __init__(self, context, request): pass
        ...     def __call__(self): return "http://localhost/frogpond/groups"
        ...
        >>> from schooltool.group.interfaces import IGroupContainer
        >>> from zope.traversing.browser.interfaces import IAbsoluteURL
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

        >>> from schooltool.app.app import SchoolToolApplication
        >>> app = setup.setUpSchoolToolSite()
        >>> directlyProvides(app, IContainmentRoot)
        >>> sections = app['sections']
        >>> courses = app['courses']
        >>> course = Course(title="Algebra I")
        >>> courses['algebraI'] = course

    On to the actual work...

    Sections are special types of groups meant to represent one meeting time
    of a course.  If they don't have a course, they can't be created "stand
    alone".

        >>> request = TestRequest()
        >>> request.form = {'field.course_id' : 'algebraI'}
        >>> context = AddingStub(sections, request)
        >>> view = SectionAddViewForTesting(context, request)
        >>> view()

    Our section is now a member of the Course, we use a generic title for
    sections

        >>> for section in course.sections:
        ...     print section.title
        1

        >>> tearDown()

    """


def doctest_SectionEditView():
    r"""Test for SectionEditView

    Let's create a view for editing a section:

        >>> from schooltool.course.browser.section import SectionEditView
        >>> from schooltool.course.section import Section
        >>> from schooltool.course.interfaces import ISection

    We need some setup:

        >>> from schooltool.app.app import SchoolToolApplication
        >>> app = setup.setUpSchoolToolSite()
        >>> from schooltool.resource.resource import Location
        >>> app['resources']['room1'] = room1 = Location("Room 1")

        >>> section = Section()
        >>> directlyProvides(section, IContainmentRoot)
        >>> request = TestRequest()

        >>> class TestSectionEditView(SectionEditView):
        ...     schema = ISection
        ...     fieldNames = ('title', 'description')
        ...     _factory = Section

        >>> view = TestSectionEditView(section, request)

    We should not get redirected if we did not click on apply button:

        >>> request = TestRequest()
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        ''
        >>> request.response.getStatus()
        599

    After changing name of the section you should get redirected to the
    container:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u'new_title'}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        u'Updated on ${date_time}'
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

        >>> section.title
        u'new_title'

    Even if the title has not changed you should get redirected to the section
    list:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u'new_title'}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        ''
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

        >>> section.title
        u'new_title'

    We should not get redirected if there were errors:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u''}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        u'An error occurred.'
        >>> request.response.getStatus()
        599

        >>> section.title
        u'new_title'

    We can cancel an action if we want to:

        >>> request = TestRequest()
        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = TestSectionEditView(section, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    """


def doctest_ConflictDisplayMixin():
    r"""Tests for ConflictDisplayMixin.

        >>> app = setup.setUpSchoolToolSite()

        >>> class ItemStub(object):
        ...     def __init__(self, name):
        ...         self.__name__ = name
        ...         self.title = name.title()
        >>> class RelationshipPropertyStub(object):
        ...     items = [ItemStub('john'),
        ...              ItemStub('pete')]
        ...     def __iter__(self):
        ...         return iter(self.items)
        ...     def add(self, item):
        ...         print "Adding: %s" % item.title
        ...     def remove(self, item):
        ...         print "Removing: %s" % item.title

    Inheriting views must implement getCollection() and
    getAvailableItems():

        >>> from schooltool.course.browser.section import ConflictDisplayMixin
        >>> class SchemaStub(ItemStub):
        ...     def items(self):
        ...         return []
        >>> class RelationshipView(ConflictDisplayMixin):
        ...     def getCollection(self):
        ...         return RelationshipPropertyStub()
        ...     def getAvailableItems(self):
        ...         return [ItemStub('ann'), ItemStub('frog')]
        ...     def getTerm(self): return ItemStub('does not matter')
        ...     def getSchema(self): return SchemaStub('does not matter')

    Let's add Ann to the list:

        >>> request = TestRequest()
        >>> request.form = {'add_item.ann': 'on',
        ...                 'ADD_ITEMS': 'Apply'}
        >>> view = RelationshipView(None, request)
        >>> view.update()
        Adding: Ann

    Someone might want to cancel a change.

        >>> request = TestRequest()
        >>> request.form = {'add_item.ann': 'on', 'CANCEL': 'Cancel'}
        >>> view = RelationshipView(None, request)
        >>> view.update()

    No one was added, but we got redirected:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    We can remove items too:

        >>> request.form = {'remove_item.john': 'on',
        ...                 'remove_item.pete': 'on',
        ...                 'REMOVE_ITEMS': 'Remove'}
        >>> view = RelationshipView(None, request)
        >>> view.update()
        Removing: John
        Removing: Pete

    We also use a batch for available items in this view

        >>> [i.title for i in view.batch]
        ['Ann', 'Frog']

    Which is searchable

        >>> request.form = {'SEARCH': 'ann'}
        >>> view = RelationshipView(None, request)
        >>> view.update()
        >>> [i.title for i in view.batch]
        ['Ann']

    The search can be cleared, ignoring any search value passed:

        >>> request.form = {'SEARCH': 'ann', 'CLEAR_SEARCH': 'on'}
        >>> view = RelationshipView(None, request)
        >>> view.update()
        >>> [i.title for i in view.batch]
        ['Ann', 'Frog']

    """


def doctest_ConflictDisplayMixin_no_timetables_terms():
    r"""Tests for ConflictDisplayMixin.

    ConflictDisplayMixin should work even if there are no timetables
    defined.

        >>> from schooltool.course.browser.section import ConflictDisplayMixin
        >>> app = setup.setUpSchoolToolSite()
        >>> view = ConflictDisplayMixin(app)
        >>> view.getSchema = lambda: None
        >>> view.getAvailableItems = lambda: []

        >>> view.update()
        >>> view.busy_periods
        []

    If there are no terms, but there are timetables - it still works:

        >>> view.getSchema = lambda: "I am a schema"
        >>> view.getTerm = lambda: None
        >>> view.update()
        >>> view.busy_periods
        []

    """


def doctest_ConflictDisplayMixin_getConflictingSections():
    r"""Tests for ConflictDisplayMixin.getConflictingSections

        >>> class SectionStub(object):
        ...     def __init__(self, label):
        ...         self.label = label
        ...     def __repr__(self):
        ...         return 'Section ' + self.label

        >>> context = SectionStub('x')
        >>> section1 = SectionStub('1')
        >>> section2 = SectionStub('2')

        >>> def getSectionsStub(item):
        ...     print "Called getSections on", item
        ...     return [context, section2]

        >>> from schooltool.course.browser.section import ConflictDisplayMixin
        >>> view = ConflictDisplayMixin(context)
        >>> view.getSections = getSectionsStub
        >>> view.busy_periods = [(('d1', 'a'), [section1]),
        ...                      (('d2', 'b'), [section1, context]),
        ...                      (('d4', 'd'), [section2]),
        ...                      (('d3', 'c'), [section2])]

        >>> for d in view.getConflictingSections('iTeM'):
        ...     print sorted(d.items())
        Called getSections on iTeM
        [('day_id', 'd3'), ('period_id', 'c'), ('section', Section 2)]
        [('day_id', 'd4'), ('period_id', 'd'), ('section', Section 2)]

    Note that the results are sorted by (day_id, period, section.label).

    """


def doctest_ConflictDisplayMixin():
    """Tests for ConflictDisplayMixin._findConflists

        >>> from schooltool.course.browser.section import ConflictDisplayMixin
        >>> view = ConflictDisplayMixin(None)
        >>> view._findConflicts([], [])
        []

        >>> class EventStub(object):
        ...     def __init__(self, start, duration, name):
        ...         self.dtstart = start
        ...         self.duration = duration
        ...         self.name = name
        ...     def __cmp__(self, other):
        ...         return cmp(self.dtstart, other.dtstart)
        ...     def __repr__(self):
        ...         return self.name

        >>> def e(s):
        ...     events = []
        ...     cur = None
        ...     for time, char in enumerate(s):
        ...         if cur and char == cur.name:
        ...             cur.duration += 1
        ...         elif char != '-':
        ...             cur = EventStub(time, 1, char)
        ...             events.append(cur)
        ...     return events

        >>> tte = e('---aaaaa----bbbbb----ccccc----ddddddd--')
        >>> cal = e('---------xxx-----yy-----zzzz----q-w----')
        >>> view._findConflicts(tte, cal)
        [z, q, w]

        >>> tte = e('--abcd-----eee------')
        >>> cal = e('-xxxxxx--yyy-----zz-')
        >>> view._findConflicts(tte, cal)
        [x, y]

    """


def doctest_ConflictDisplayMixin_groupConflicts():
    """Tests for ConflictDisplayMixin._groupConflicts

    Given an empty list the function should return an empty list:

        >>> from schooltool.course.browser.section import ConflictDisplayMixin
        >>> view = ConflictDisplayMixin(None)
        >>> view._groupConflicts([])
        []

    Events are considered unique if their unique_id's are different:

        >>> class EventStub(object):
        ...     def __init__(self, id):
        ...         self.unique_id = id

        >>> events = [EventStub(id) for id in "abcda"]

        >>> sorted(e.unique_id for e in view._groupConflicts(events))
        ['a', 'b', 'c', 'd']

    """

def doctest_ConflictDisplayMixin_getConflictingEvents():
    """Tests for ConflictDisplayMixin.getConflictingEvents

        >>> from schooltool.timetable.interfaces import ICompositeTimetables
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> class TimetabledStub(object):
        ...     def __init__(self, events):
        ...         self.events = events
        >>> class CompositeTimetablesStub(object):
        ...     adapts(TimetabledStub)
        ...     implements(ICompositeTimetables)
        ...     def __init__(self, section):
        ...         self.section = section
        ...     def makeTimetableCalendar(self):
        ...         return self.section.events
        >>> provideAdapter(CompositeTimetablesStub)

        >>> class CalendarStub(object):
        ...     adapts(TimetabledStub)
        ...     implements(ISchoolToolCalendar)
        ...     def __init__(self, item):
        ...         self.item = item
        ...     def expand(self, start, end):
        ...         print "Expanding from %s to %s" % (start, end)
        ...         return self.item.events
        >>> provideAdapter(CalendarStub)

    First let's try it out with a section without events in its
    timetable:

        >>> from schooltool.course.browser.section import ConflictDisplayMixin
        >>> view = ConflictDisplayMixin(TimetabledStub([]))
        >>> view.getConflictingEvents(TimetabledStub([]))
        []

        >>> class EventStub(object):
        ...     def __init__(self, start):
        ...         self.dtstart = start
        ...         self.duration = 3
        ...     def __cmp__(self, other):
        ...         return cmp(self.dtstart, other.dtstart)
        ...     def __repr__(self):
        ...         return "e%s" % self.dtstart

    Any events in the item calendar are ignored and an empty list is
    returned:

        >>> events = [EventStub(start) for start in [30, 10, 20]]
        >>> view.getConflictingEvents(TimetabledStub(events))
        []

    If there are no events in the item calendar, an empty list is
    returned:

        >>> view = ConflictDisplayMixin(TimetabledStub(events))
        >>> view.getConflictingEvents(TimetabledStub([]))
        Expanding from 10 to 33
        []

    The calendar was expanded from the dtstart of the first event till
    the dtend of the last one. This works with only one event too:

        >>> view = ConflictDisplayMixin(TimetabledStub(events[-1:]))
        >>> view.getConflictingEvents(TimetabledStub([]))
        Expanding from 20 to 23
        []

    If there are events in both calendars all unique conflicting
    events are returned:

        >>> more_events = [EventStub(start) for start in [25, 15]]
        >>> view._findConflicts = lambda tte, cae: "conflicts between %s and %s" % (tte, cae)
        >>> view._groupConflicts = lambda conflicts: "Grouped %s" % conflicts

        >>> print view.getConflictingEvents(TimetabledStub(more_events))
        Expanding from 20 to 23
        Grouped conflicts between [e20] and [e25, e15]

    """


def doctest_SectionInstructorView():
    """Tests for SectionInstructorView.

    First we need to set up some persons:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.person.person import Person
        >>> school = setup.setUpSchoolToolSite()
        >>> provideAdapter(lambda context: school, (None,), ISchoolToolApplication)
        >>> persons = school['persons']
        >>> directlyProvides(school, IContainmentRoot)
        >>> persons['smith'] = Person('smith', 'John Smith')
        >>> persons['jones'] = Person('jones', 'Sally Jones')
        >>> persons['stevens'] = Person('stevens', 'Bob Stevens')

    getCollection plainly returns instructors attribute of a section:

        >>> from schooltool.course.browser.section import SectionInstructorView
        >>> class SectionStub(object):
        ...     instructors = [persons['smith']]
        >>> view = SectionInstructorView(SectionStub(), None)
        >>> [item.title for item in view.getCollection()]
        ['John Smith']

    All persons that are not in the current instructor list are
    considered available:

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'Bob Stevens']

        >>> view.context.instructors = []

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'John Smith', 'Bob Stevens']

    """


def doctest_SectionLearnerView():
    """Tests for SectionLearnerView.

    First we need to set up some persons:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.person.person import Person
        >>> school = setup.setUpSchoolToolSite()
        >>> provideAdapter(lambda context: school, (None,), ISchoolToolApplication)
        >>> persons = school['persons']
        >>> directlyProvides(school, IContainmentRoot)
        >>> smith = persons['smith'] = Person('smith', 'John Smith')
        >>> jones = persons['jones'] = Person('jones', 'Sally Jones')
        >>> stevens = persons['stevens'] = Person('stevens', 'Bob Stevens')

    getCollection plainly returns members attribute of a section:

        >>> from schooltool.course.browser.section import SectionLearnerView
        >>> class SectionStub(object):
        ...     members = [smith]
        >>> view = SectionLearnerView(SectionStub(), None)
        >>> [item.title for item in view.getCollection()]
        ['John Smith']

    All persons that are not in the selected learner list are
    considered available:

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'Bob Stevens']

        >>> view.context.members = []

        >>> [item.title for item in view.getAvailableItems()]
        ['Sally Jones', 'John Smith', 'Bob Stevens']

    Any non-person members should be skipped when displaying selected
    items:

        >>> from schooltool.group.group import Group
        >>> frogs = Group('frogs')
        >>> view.context.members = [smith, frogs]
        >>> [item.title for item in view.getSelectedItems()]
        ['John Smith']

    """


def doctest_SectionLearnerGroupView():
    """Tests for SectionLearnerGroupView.

    First we need to set up some groups:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.group.group import Group
        >>> school = setup.setUpSchoolToolSite()
        >>> provideAdapter(lambda context: school, (None,), ISchoolToolApplication)
        >>> groups = school['groups']
        >>> directlyProvides(school, IContainmentRoot)
        >>> frogs = groups['frogs'] = Group('frogs', 'Bunch of frogs')
        >>> lilies = groups['lilies'] = Group('lilies', 'Lillie pond')
        >>> bugs = groups['bugs'] = Group('bugs', "Lot's o Bugs")

    getCollection plainly returns members attribute of a section:

        >>> from schooltool.course.browser.section import SectionLearnerGroupView
        >>> class SectionStub(object):
        ...     members = [frogs]
        >>> view = SectionLearnerGroupView(SectionStub(), None)
        >>> [item.title for item in view.getCollection()]
        ['frogs']

    All groups that are not in the selected learner list are
    considered available:

        >>> [item.title for item in view.getAvailableItems()]
        ['bugs', 'lilies']

        >>> view.context.members = []

        >>> [item.title for item in view.getAvailableItems()]
        ['bugs', 'frogs', 'lilies']

    Any non-person members should be skipped when displaying selected
    items:

        >>> from schooltool.person.person import Person
        >>> smith = Person('smith', 'John Smith')
        >>> view.context.members = [smith, frogs]
        >>> [item.title for item in view.getSelectedItems()]
        ['frogs']

    """


def doctest_SectionResourceView():
    """Tests for SectionResourceView.

    First we need to set up some persons:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.resource.resource import Resource
        >>> school = setup.setUpSchoolToolSite()
        >>> provideAdapter(lambda context: school, (None,), ISchoolToolApplication)
        >>> resources = school['resources']
        >>> directlyProvides(school, IContainmentRoot)
        >>> rock = resources['rock'] = Resource('rock')
        >>> stone = resources['stone'] = Resource('stone')
        >>> boulder = resources['boulder'] = Resource('boulder')

    getCollection plainly returns resources attribute of a section:

        >>> from schooltool.course.browser.section import SectionResourceView
        >>> class SectionStub(object):
        ...     resources = [rock]
        >>> view = SectionResourceView(SectionStub(), None)
        >>> [item.title for item in view.getCollection()]
        ['rock']

    All resources that are not currently booked are considered
    available:

        >>> [item.title for item in view.getAvailableItems()]
        ['boulder', 'stone']

        >>> view.context.resources = []

        >>> [item.title for item in view.getAvailableItems()]
        ['boulder', 'rock', 'stone']

    """


def doctest_CoursesViewlet():
    r"""Test for CoursesViewlet

    Let's create a viewlet for a person's courses:

        >>> from schooltool.course.browser.course import CoursesViewlet
        >>> from schooltool.person.person import Person

        >>> school = setup.setUpSchoolToolSite()
        >>> persons = school['persons']
        >>> sections = school['sections']

        >>> persons['teacher'] = teacher = Person("Teacher")
        >>> teacher_view = CoursesViewlet(teacher, TestRequest())

    Not a teacher yet:

        >>> teacher_view.isTeacher()
        False

    We'll need something to teach:

        >>> from schooltool.course.section import Section
        >>> sections['section'] = section1 = Section(title="History")
        >>> sections['section2'] = section2 = Section(title="Algebra")
        >>> section1.instructors.add(teacher)

    Now we're teaching:

        >>> teacher_view.isTeacher()
        True
        >>> teacher_view.isLearner()
        False

    We'll teach 2 courses this semester, and we'll need an easy way to get a
    list of all the courses we're teaching.

        >>> section2.instructors.add(teacher)
        >>> teacher_view = CoursesViewlet(teacher, TestRequest())
        >>> [item['section'].title for item in teacher_view.instructorOf()]
        ['History', 'Algebra']
        >>> [item['title'] for item in teacher_view.instructorOf()]
        ['History', 'Algebra']

    Let's create a student

        >>> persons['student'] = student = Person("Student")
        >>> student_view = CoursesViewlet(student, TestRequest())

        >>> student_view.isTeacher()
        False
        >>> student_view.isLearner()
        False

    Membership in a Section implies being a learner:

        >>> section2.members.add(student)
        >>> student_view.isTeacher()
        False

        >>> student_view.isLearner()
        True

        >>> sections['section3'] = section3 = Section(title="English")
        >>> sections['section4'] = section4 = Section(title="Gym")

    Our student is taking several classes

        >>> section3.members.add(student)
        >>> student_view = CoursesViewlet(student, TestRequest())

        >>> [item['section'].title for item in student_view.learnerOf()]
        ['Algebra', 'English']

    Students can also participate in sections as part of a group, say all 10th
    grade students must take gym:

        >>> from schooltool.group.group import Group
        >>> tenth_grade = Group(title="Tenth Grade")
        >>> tenth_grade.members.add(student)
        >>> section4.members.add(tenth_grade)

        >>> student_view = CoursesViewlet(student, TestRequest())
        >>> [section['section'].title for section in student_view.learnerOf()]
        ['Algebra', 'English', 'Gym']

    One thing that might confuse is that learnerOf may be similar to but not
    the same as view.context.groups

        >>> [group.title for group in student_view.context.groups]
        ['Algebra', 'English', 'Tenth Grade']

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
