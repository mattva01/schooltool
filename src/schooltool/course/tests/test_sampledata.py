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
Unit tests for schooltool.course.sampledata

$Id$
"""

import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing import setup as stsetup
from schooltool.relationship.tests import setUpRelationships


def setUp(test):
    setup.placefulSetUp()
    setUpRelationships()
    stsetup.setupTimetabling()
    stsetup.setupCalendaring()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleCourse():
    """A sample data plugin that generates courses

        >>> from schooltool.course.sampledata import SampleCourses
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleCourses()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    As always, we'll need an application instance:

        >>> app = stsetup.setupSchoolToolSite()

    The plugin generates 24 courses:

        >>> plugin.generate(app, 42)

        >>> len(app['courses'])
        24

    The courses nave names like 'English A', 'History D', etc.

        >>> app['courses']['math_a'].title
        'Math A'

        >>> app['courses']['history_d'].title
        'History D'

    """


def doctest_SampleSections():
    """A sample data plugin that generates sections

        >>> from schooltool.course.sampledata import SampleSections
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleSections()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    As always, we'll need an application instance:

        >>> from schooltool.group.group import Group
        >>> app = stsetup.setupSchoolToolSite()
        >>> app['groups']['teachers'] = Group('Teachers')
        >>> app['groups']['students'] = Group('Students')

    This plugins depends on lots of stuff, so I'm afraid we'll have to
    run it all:

        >>> plugin.dependencies
        ('teachers', 'students', 'courses', 'resources')

        >>> from schooltool.person.sampledata import SampleStudents
        >>> from schooltool.person.sampledata import SampleTeachers
        >>> from schooltool.course.sampledata import SampleCourses
        >>> from schooltool.resource.sampledata import SampleResources
        >>> SampleTeachers().generate(app, 42)
        >>> SampleStudents().generate(app, 42)
        >>> SampleCourses().generate(app, 42)
        >>> SampleResources().generate(app, 42)

    Let's go:

        >>> plugin.generate(app, 42)

    5 sections for each of 48 teachers are created:

        >>> len(app['sections'])
        240

    This generates 5 sections for each teacher:

        >>> from schooltool.relationship import getRelatedObjects
        >>> from schooltool.app.relationships import URISection
        >>> for i in range(48):
        ...    teacher = app['persons']['teacher%03d' % i]
        ...    assert len(getRelatedObjects(teacher, URISection)) == 5

    Each course gets assigned 2 teachers, and 10 sections:

        >>> from schooltool.app.relationships import URISectionOfCourse
        >>> for course in app['courses'].values():
        ...    assert len(getRelatedObjects(course, URISectionOfCourse)) == 10

    All sections of a teacher gather in one room:

        >>> import zope.i18n
        >>> student = app['persons']['teacher042']
        >>> for section in getRelatedObjects(student, URISection):
        ...     print section.location.title
        Room 60
        Room 60
        Room 60
        Room 60
        Room 60

    """


def doctest_SampleTimetables():
    """A sample data plugin that creates timetables for students and teachers

        >>> from schooltool.course.sampledata import SampleTimetables
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleTimetables()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin needs the sections set up, and that requires a lot:

        >>> plugin.dependencies
        ('sections', 'ttschema', 'terms')

        >>> from schooltool.group.group import Group
        >>> app = stsetup.setupSchoolToolSite()
        >>> app['groups']['teachers'] = Group('Teachers')

        >>> from schooltool.person.sampledata import SampleStudents
        >>> from schooltool.person.sampledata import SampleTeachers
        >>> from schooltool.course.sampledata import SampleCourses
        >>> from schooltool.resource.sampledata import SampleResources
        >>> from schooltool.course.sampledata import SampleSections
        >>> from schooltool.timetable.sampledata import SampleTimetableSchema
        >>> from schooltool.timetable.sampledata import SampleTerms
        >>> SampleTeachers().generate(app, 42)
        >>> SampleStudents().generate(app, 42)
        >>> SampleCourses().generate(app, 42)
        >>> SampleResources().generate(app, 42)
        >>> SampleSections().generate(app, 42)
        >>> SampleTimetableSchema().generate(app, 42)
        >>> SampleTerms().generate(app, 42)

    Let's call the plugin:

        >>> plugin.generate(app, 42)

    It randomly assigns a period for each section, so that no sections
    of the same teacher happen on the same period:

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from schooltool.relationship import getRelatedObjects
        >>> from schooltool.app.relationships import URISection
        >>> teacher = app['persons']['teacher042']
        >>> for section in getRelatedObjects(teacher, URISection):
        ...     timetables = ITimetables(section)
        ...     timetable = timetables.timetables['2005-fall.simple']
        ...     for period, activities in timetable['Day 1'].items():
        ...         if activities:
        ...             print period, section.__name__
        F section215
        E section009
        B section117
        A section188
        C section212

    Also, on each day the same section gets the same slot:

        >>> section = getRelatedObjects(teacher, URISection)[0]
        >>> timetable = ITimetables(section).timetables['2005-fall.simple']
        >>> for day, period, activity in timetable.itercontent():
        ...     print day, period, activity.title
        Day 1 F Spanish C
        Day 2 F Spanish C
        Day 3 F Spanish C
        Day 4 F Spanish C
        Day 5 F Spanish C
        Day 6 F Spanish C

    The students get assigned to sections so that they get into one
    section of each subject, and they fall into different periods.

        >>> student = app['persons']['student042']
        >>> from schooltool.app.membership import URIGroup
        >>> for section in getRelatedObjects(student, URIGroup):
        ...     if section.title != 'Students':
        ...         timetable = ITimetables(section).\
timetables['2005-fall.simple']
        ...         for day, period, activity in list\
(timetable.itercontent())[:1]:
        ...             print period, activity.title
        D English B
        B Math A
        A History A
        E Science C
        C Spanish A
        F Art A

    """


def doctest_SampleTimetables_assignPeriodToSection():
    """Test for SampleTimetables.assignPeriodToSection method

        >>> from schooltool.course.sampledata import SampleTimetables
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleTimetables()

    We need a section and a course for this method:

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> from schooltool.app.relationships import CourseSections
        >>> app = stsetup.setupSchoolToolSite()
        >>> c = app['courses']['my_course'] = Course('My Course')
        >>> s = app['sections']['the_sect'] = Section('Sect')
        >>> CourseSections(course=c, section=s)

    Also, we need a timetable schema with terms:

        >>> from schooltool.timetable.sampledata import SampleTimetableSchema
        >>> from schooltool.timetable.sampledata import SampleTerms
        >>> SampleTimetableSchema().generate(app, 42)
        >>> SampleTerms().generate(app, 42)

    Let's call the method:

        >>> plugin.assignPeriodToSection(app, 'B', s)

    Now, let's inspect the timetables for this section:

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> timetable = ITimetables(s).timetables['2005-fall.simple']
        >>> for day, period, activity in timetable.itercontent():
        ...     print day, period, activity.title
        Day 1 B My Course
        Day 2 B My Course
        Day 3 B My Course
        Day 4 B My Course
        Day 5 B My Course
        Day 6 B My Course

        >>> timetable = ITimetables(s).timetables['2006-spring.simple']
        >>> for day, period, activity in timetable.itercontent():
        ...     print day, period, activity.title
        Day 1 B My Course
        Day 2 B My Course
        Day 3 B My Course
        Day 4 B My Course
        Day 5 B My Course
        Day 6 B My Course

    """


def doctest_SampleSectionAssignments():
    """A sample data plugin that creates events in section calendars

        >>> from schooltool.course.sampledata import SampleSectionAssignments
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleSectionAssignments()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin needs the timetables to be set up for sections, so we
    need lots of set up:

        >>> plugin.dependencies
        ('section_timetables', 'resources')

        >>> app = stsetup.setupSchoolToolSite()

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> s0 = app['sections']['section000'] = Section('section000')
        >>> s1 = app['sections']['section001'] = Section('section001')
        >>> s2 = app['sections']['section002'] = Section('section002')
        >>> s3 = app['sections']['section003'] = Section('section003')
        >>> s4 = app['sections']['section004'] = Section('section004')
        >>> s5 = app['sections']['section005'] = Section('section005')
        >>> s6 = app['sections']['section006'] = Section('section006')
        >>> s7 = app['sections']['section007'] = Section('section007')
        >>> s8 = app['sections']['section008'] = Section('section008')
        >>> c = app['courses']['somecourse'] = Course('Hard Science')

        >>> from schooltool.app.relationships import CourseSections
        >>> CourseSections(course=c, section=s0)
        >>> CourseSections(course=c, section=s1)
        >>> CourseSections(course=c, section=s2)
        >>> CourseSections(course=c, section=s3)
        >>> CourseSections(course=c, section=s4)
        >>> CourseSections(course=c, section=s5)
        >>> CourseSections(course=c, section=s6)
        >>> CourseSections(course=c, section=s7)
        >>> CourseSections(course=c, section=s8)

        >>> from schooltool.timetable.sampledata import SampleTimetableSchema
        >>> from schooltool.timetable.sampledata import SampleTerms
        >>> SampleTimetableSchema().generate(app, 42)
        >>> SampleTerms().generate(app, 42)

        >>> from schooltool.resource.sampledata import SampleResources
        >>> SampleResources().generate(app, 42)

    The sections will need to have some timetables.  We'll assign them
    to the same period

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from schooltool.timetable import TimetableActivity
        >>> Timetable = app['ttschemas'].getDefault().createTimetable
        >>> for sect in (s0, s1, s2, s3, s4, s5, s6, s7, s8):
        ...     timetables = ITimetables(sect).timetables
        ...     tt = timetables['2005-fall.simple'] = Timetable()
        ...     for day in range(1, 7):
        ...         activity = TimetableActivity('Stuff', owner=sect)
        ...         tt['Day %d' % day].add('A', activity)

    Now, let's run the plugin:

        >>> plugin.generate(app, 42)

    What we get is that the calendars of sections get events in them
    roughly once in 13 times the group meets.

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> len(ISchoolToolCalendar(s0))
        7
        >>> len(ISchoolToolCalendar(s1))
        8
        >>> len(ISchoolToolCalendar(s2))
        7

    These events have random titles and times coinciding with section
    timetable events:

        >>> for ev in sorted(ISchoolToolCalendar(s8)):
        ...     resources = [res.__name__ for res in ev.resources]
        ...     print ev.dtstart, ev.title, resources
        2005-08-31 13:30:00+00:00 Quiz [u'projector01']
        2005-09-07 08:00:00+00:00 Quiz [u'projector01']
        2005-09-22 09:00:00+00:00 Lab work [u'projector01']
        2005-11-10 10:00:00+00:00 Read the book [u'projector00']
        2005-11-11 09:00:00+00:00 Homework [u'projector00']
        2005-11-24 12:30:00+00:00 Read the book [u'projector00']
        2005-12-13 11:00:00+00:00 Homework [u'projector00']
        2005-12-14 10:00:00+00:00 Quiz [u'projector00']
        2005-12-15 09:00:00+00:00 Homework [u'projector00']

    Resources must have events in calendars.

        >>> projector = app['resources']['projector00']
        >>> calendar = ISchoolToolCalendar(projector)
        >>> for ev in sorted(calendar)[0:10]:
        ...     print ev.dtstart, ev.duration, ev.title
        2005-08-23 13:30:00+00:00 1:00:00 Quiz
        2005-08-24 12:30:00+00:00 0:55:00 Deadline for essay
        2005-08-26 10:00:00+00:00 0:55:00 Read the book
        2005-08-29 09:00:00+00:00 0:55:00 Quiz
        2005-08-31 13:30:00+00:00 1:00:00 Quiz
        2005-09-01 12:30:00+00:00 0:55:00 Homework
        2005-09-02 11:00:00+00:00 0:55:00 Homework
        2005-09-05 10:00:00+00:00 0:55:00 Homework
        2005-09-07 08:00:00+00:00 0:55:00 Assignment
        2005-09-12 11:00:00+00:00 0:55:00 Homework

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
