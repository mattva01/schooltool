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

$Id: test_sampledata.py 6531 2006-12-28 15:52:02Z ignas $
"""

import unittest

import zope.component
import z3c.optionstorage

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup
from zope.app.testing import ztapi
from zope.component import provideSubscriptionAdapter

import schooltool.requirement.testing

from schooltool.testing import setup as stsetup
from schooltool.relationship.tests import setUpRelationships
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.timetable.source import OwnedTimetableSource
from schooltool.timetable.interfaces import IOwnTimetables
from schooltool.timetable.interfaces import ITimetableSource
from schooltool.gradebook.activity import getSectionActivities
from schooltool.gradebook.gradebook import Gradebook, GradebookInit
from schooltool.gradebook.interfaces import IActivities, IGradebook
from schooltool.course.interfaces import ISection


def setUp(test):
    setup.placefulSetUp()
    setUpRelationships()
    app = stsetup.setUpSchoolToolSite()
    ztapi.provideAdapter(None, ISchoolToolApplication, lambda x: app)
    provideSubscriptionAdapter(OwnedTimetableSource,
                               (IOwnTimetables,),
                               ITimetableSource)
    stsetup.setUpTimetabling()
    stsetup.setUpCalendaring()
    stsetup.setUpApplicationPreferences()
    schooltool.requirement.testing.setUpEvaluation()
    zope.component.provideAdapter(
        z3c.optionstorage.OptionStorage,
        (zope.annotation.interfaces.IAnnotatable,),
        z3c.optionstorage.interfaces.IOptionStorage)
    zope.component.provideAdapter(
        getSectionActivities, 
        (ISection,), 
        IActivities)
    zope.component.provideAdapter(
        Gradebook, 
        (ISection,), 
        IGradebook)
    initializer = GradebookInit(app)
    initializer()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleGrades():
    """A sample data plugin that generates grades

        >>> from schooltool.gradebook.sampledata import SampleGrades
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleGrades()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

    As always, we'll need an application instance:

        >>> from schooltool.group.group import Group
        >>> app = ISchoolToolApplication(None)
        >>> app['groups']['teachers'] = Group('Teachers')
        >>> app['groups']['students'] = Group('Students')

    This plugins depends on section which, in turn, depend on lots of stuff, 
    so we'll have to run it all:

        >>> plugin.dependencies
        ('sections',)

        >>> from schooltool.demographics.sampledata import SampleStudents
        >>> from schooltool.demographics.sampledata import SampleTeachers
        >>> from schooltool.course.sampledata import SampleCourses
        >>> from schooltool.resource.sampledata import SampleResources
        >>> from schooltool.course.sampledata import SampleSections
        >>> from schooltool.timetable.sampledata import SampleTimetableSchema
        >>> from schooltool.term.sampledata import SampleTerms
        >>> from schooltool.course.sampledata import SampleTimetables
        >>> SampleTeachers().generate(app, 42)
        >>> SampleStudents().generate(app, 42)
        >>> SampleCourses().generate(app, 42)
        >>> SampleResources().generate(app, 42)
        >>> SampleSections().generate(app, 42)
        >>> SampleTimetableSchema().generate(app, 42)
        >>> SampleTerms().generate(app, 42)
        >>> SampleTimetables().generate(app, 42)

    Let's go:

        >>> plugin.generate(app, 42)

    Pick a teacher and see what sections are assigned to him/her:

        >>> from schooltool.relationship import getRelatedObjects
        >>> from schooltool.app.relationships import URISection
        >>> teacher = app['persons']['teacher042']
        >>> sections = list(getRelatedObjects(teacher, URISection))
        >>> for section in sections:
        ...     print section.title
        section215
        section009
        section117
        section188
        section212

    Pick a section and see that it has the expected activities:

        >>> section = sections[0]
        >>> activities = IActivities(section)
        >>> worksheets = list(activities.values())
        >>> worksheets
        [Worksheet('Semester 1'), Worksheet('Semester 2')]
        >>> list(worksheets[0].values())
        [<Activity 'First Semester Project'>, <Activity 'Midterm Exam'>]
        >>> list(worksheets[1].values())
        [<Activity 'Second Semester Project'>, <Activity 'Final Exam'>]

    Let's get the gradebook for the section:

        >>> gradebook = IGradebook(section)
        
   Pick a student and get his/her evaluations:
   
        >>> student = list(section.members)[0]
        >>> student.title
        'Cristina Garrett'
        >>> for ev in gradebook.getEvaluationsForStudent(student):
        ...     print ev[1]
        <Evaluation for <Activity 'First Semester Project'>, value=76>
        <Evaluation for <Activity 'Midterm Exam'>, value=52>
        <Evaluation for <Activity 'Second Semester Project'>, value=72>
        <Evaluation for <Activity 'Final Exam'>, value=57>

    """




def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
