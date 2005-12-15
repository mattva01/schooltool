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
from schooltool.course.course import Course
from schooltool.course.section import Section
from schooltool.app.relationships import Instruction, CourseSections
from schooltool.app.relationships import URICourse, URISection
from schooltool.app.membership import Membership
from schooltool.relationship import getRelatedObjects
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable import TimetableActivity
from schooltool.app.cal import CalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar


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


class SampleTimetables(object):
    """Set up a random schedule for teachers and students"""

    implements(ISampleDataPlugin)

    name = "section_timetables"

    dependencies = ("sections", "ttschema", "terms")

    def assignPeriodToSection(self, app, period, section):
        course = getRelatedObjects(section, URICourse)[0]
        for ttname in '2005-fall.simple', '2006-spring.simple':
            timetable = app['ttschemas'].getDefault().createTimetable()
            ITimetables(section).timetables[ttname] = timetable
            for day_id in timetable.keys():
                activity = TimetableActivity(course.title, owner=section,
                                             resources=(section.location, ))
                timetable[day_id].add(period, activity)

    def generate(self, app, seed=None):
        # Let's assign a period for each teacher's sections
        self.random = random.Random()
        self.random.seed(str(seed) + self.name)
        app = removeSecurityProxy(app)
        sections = {}
        for person in app['persons'].values():
            if person.__name__.startswith('teacher'):
                periods = ['A', 'B', 'C', 'D', 'E', 'F']
                for section in getRelatedObjects(person, URISection):
                    course = getRelatedObjects(section, URICourse)[0]
                    subject = course.title.split()[0]
                    period = self.random.choice(periods)
                    periods.remove(period)
                    self.assignPeriodToSection(app, period, section)
                    if (subject, period) not in sections:
                        sections[(subject, period)] = []
                    sections[(subject, period)].append(section)

        assert len(sections) == 36, "Try a different random seed please"

        # Now, let's choose timetables for each student:
        for person in app['persons'].values():
            if person.__name__.startswith('student'):
                periods = ['A', 'B', 'C', 'D', 'E', 'F']
                for subject in SampleCourses.subjects:
                    period = self.random.choice(periods)
                    periods.remove(period)
                    section = self.random.choice(sections[(subject, period)])
                    Membership(group=section, member=person)


class SampleSectionAssignments(object):
    """A plugin that generates assignments and other events for sections"""

    implements(ISampleDataPlugin)

    name = "section_events"

    dependencies = ('section_timetables', 'resources')

    excuses = ('Assignment', 'Quiz', 'Quiz', 'Quiz', 'Homework',
               'Homework', 'Homework','Homework', 'Test',
               'Presentation', 'Deadline for essay',
               'Deadline for project', 'Read the book', 'Lab work', )

    def _findProjector(self, ev, projectors):
        for projector in projectors:
            if (projector, ev.dtstart) not in self.taken_projectors:
                return projector
        return None

    def generate(self, app, seed=None):
        app = removeSecurityProxy(app)
        self.random = random.Random()
        self.random.seed(str(seed) + self.name)

        projectors = [resource
                      for resource in app['resources'].values()
                          if resource.__name__.startswith('projector')]

        # tuples of (projector, datetime)
        self.taken_projectors = set()

        for section in app['sections'].values():
            ttcal = ITimetables(section).makeTimetableCalendar()
            calendar = ISchoolToolCalendar(section)
            for event in ttcal:
                if self.random.randrange(13) == 7: # is today lucky?
                    title = self.random.choice(self.excuses)
                    ev = CalendarEvent(event.dtstart, event.duration, title)
                    projector = self._findProjector(ev, projectors)
                    if projector is not None:
                        ev.bookResource(projector)
                        self.taken_projectors.add((projector, ev.dtstart))
                    calendar.addEvent(ev)

