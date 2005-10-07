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
from pprint import pprint

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing.setup import setupLocalGrants
from schooltool.testing import setup as stsetup
from schooltool.relationship.tests import setUpRelationships


def setUp(test):
    setup.placefulSetUp()
    setUpRelationships()
    stsetup.setupTimetabling()

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

        >>> app = stsetup.setupSchoolToolSite()

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

    All students get assigned to 6 sections, one of each subject:

        >>> from schooltool.app.membership import URIGroup
        >>> import zope.i18n
        >>> student = app['persons']['student042']
        >>> for section in getRelatedObjects(student, URIGroup):
        ...     print zope.i18n.translate(section.label)
        Daniel Reid -- English C
        Callum Mendoza -- Math D
        Francisco Hunt -- History D
        Sanne Parks -- Science A
        Dorothy Mendoza -- Spanish C
        Hank Nielsen -- Art C

    Each section has a room attached:

        >>> from schooltool.app.membership import URIGroup
        >>> import zope.i18n
        >>> student = app['persons']['student042']
        >>> for section in getRelatedObjects(student, URIGroup):
        ...     print section.location.title
        Room 12
        Room 41
        Room 20
        Room 40
        Room 52
        Room 08

    All sections of a teacher gather in one room:

        >>> import zope.i18n
        >>> student = app['persons']['teacher042']
        >>> for section in getRelatedObjects(student, URISection):
        ...     print section.location.title
        Room 22
        Room 22
        Room 22
        Room 22
        Room 22

    """


def doctest_PopulateSectionTimetables():
    """A sample data plugin that populates section timetables with events

        >>> from schooltool.course.sampledata import PopulateSectionTimetables
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = PopulateSectionTimetables()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    This plugin depends on some stuff:

        >>> plugin.dependencies
        ('sections', 'ttschema', 'terms')

    As always, we'll need an application instance:

        >>> app = stsetup.setupSchoolToolSite()

    In the application we'll need several sections and a course:

        >>> from schooltool.course.course import Course
        >>> from schooltool.course.section import Section
        >>> s1 = app['sections']['section000'] = Section('section000')
        >>> s2 = app['sections']['section001'] = Section('section001')
        >>> s3 = app['sections']['section002'] = Section('section002')
        >>> c = app['courses']['somecourse'] = Course('Hard Science')

        >>> from schooltool.app.relationships import CourseSections
        >>> CourseSections(course=c, section=s1)
        >>> CourseSections(course=c, section=s2)
        >>> CourseSections(course=c, section=s3)

    As for the ttschema and terms, it's easier just to invoke the plugins:

        >>> from schooltool.timetable.sampledata import SampleTimetableSchema
        >>> from schooltool.timetable.sampledata import SampleTerms
        >>> SampleTimetableSchema().generate(app, 42)
        >>> SampleTerms().generate(app, 42)

    Let's run the plugin:

        >>> plugin.generate(app, 42)

    All sections get timetables attached to them:

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> for schema in s1, s2, s3:
        ...  ITimetables(schema).timetables.keys()
        ['2005-fall.simple', '2006-spring.simple']
        ['2005-fall.simple', '2006-spring.simple']
        ['2005-fall.simple', '2006-spring.simple']

    These timetables have events randomly scattered in them, 6 events
    in each:

        >>> timetable = ITimetables(schema).timetables['2005-fall.simple']
        >>> for day, period, activity in timetable.itercontent():
        ...     print day, period, activity.title
        Day 1 B Hard Science
        Day 1 E Hard Science
        Day 1 F Hard Science
        Day 4 B Hard Science
        Day 5 E Hard Science
        Day 6 D Hard Science

    """

def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
