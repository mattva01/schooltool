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
Sample courses generation

$Id$
"""

import random

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.person.person import Person
from schooltool.course.course import Course
from schooltool.course.section import Section
from schooltool.sampledata.name import NameGenerator
from schooltool.app.relationships import Instruction, CourseSections
from schooltool.app.relationships import URICourse, URISection
from schooltool.app.membership import Membership
from schooltool.relationship import getRelatedObjects
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable import TimetableActivity


class SampleCourses(object):

    implements(ISampleDataPlugin)

    name = 'courses'
    dependencies = ()

    subjects = ("English", "Math", "History", "Science", "Spanish", "Art")

    def generate(self, app, seed=None):
        courses = app['courses']

        for name in self.subjects:
            for subname in ('A', 'B', 'C', 'D'):
                obname = ("%s_%s" % (name, subname)).lower()
                title = "%s %s" % (name, subname)
                courses[obname] = Course(title)


class SampleSections(object):
    """Sample data plugin for sections

    This plugin creates sections and associates them with courses,
    teachers, rooms and students.
    """

    implements(ISampleDataPlugin)

    name = 'sections'
    dependencies = ('teachers', 'students', 'courses', 'resources')

    def generate(self, app, seed=None):
        app = removeSecurityProxy(app)
        self.random = random.Random()
        self.random.seed(str(seed) + self.name)

        # Create 5 sections for each teacher.
        sections = []
        for i in range(48 * 5):
            sectionname = 'section%03d' % i
            section = Section(sectionname)
            app['sections'][sectionname] = section
            sections.append(section)

        # For each teacher, assign a course and 5 sections.
        courses = list(app['courses'].values()) * 2
        assert len(courses) >= 48, len(courses)
        for personid in app['persons']:
            if personid.startswith('teacher'):
                teacher = app['persons'][personid]
                course = self.random.choice(courses)
                courses.remove(course)

                for i in range(5):
                    section = self.random.choice(sections)
                    sections.remove(section)
                    Instruction(instructor=teacher, section=section)
                    CourseSections(course=course, section=section)
        assert len(courses) == 0
        assert len(sections) == 0

        # Now we want to assign students to sections.
        # Each student must be in a section for each subject.
        # There are 6 subjects, 4 courses for each.

        # Let's sort the sections by subject.
        sections = dict([(subject, [])
                         for subject in SampleCourses.subjects])
        for section in app['sections'].values():
            course = getRelatedObjects(section, URICourse)[0]
            course_subject = course.title.split()[0]
            sections[course_subject].append(section)

        # Now let's assign student to one section of each subject.
        for person in app['persons'].values():
            if person.__name__.startswith('student'):
                for subject in SampleCourses.subjects:
                    section = self.random.choice(sections[subject])
                    Membership(group=section, member=person)

        # Now let's assign rooms to sections.  In order to avoid
        # collisions we'll in fact assign rooms to teachers.

        rooms = [resource
                 for resource in app['resources'].values()
                 if resource.__name__.startswith('room')]

        for person in app['persons'].values():
            if person.__name__.startswith('teacher'):
                room = self.random.choice(rooms)
                rooms.remove(room)
                for section in getRelatedObjects(person, URISection):
                    section.location = room



class PopulateSectionTimetables(object):
    """A sample data plugin that populates section timetables with events"""

    implements(ISampleDataPlugin)

    name = 'section_timetables'

    dependencies = ('sections', 'ttschema', 'terms')

    def generate(self, app, seed=None):
        app = removeSecurityProxy(app)
        self.random = random.Random()
        self.random.seed(str(seed) + self.name)

        for section in app['sections'].values():
            course = getRelatedObjects(section, URICourse)[0]
            for ttname in '2005-fall.simple', '2006-spring.simple':
                timetable = app['ttschemas'].getDefault().createTimetable()
                ITimetables(section).timetables[ttname] = timetable
                for i in range(6):
                    day_id = self.random.choice(timetable.keys())
                    period_id = self.random.choice(timetable[day_id].keys())
                    activity = TimetableActivity(course.title, owner=section)
                    timetable[day_id].add(period_id, activity)
