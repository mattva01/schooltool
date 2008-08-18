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
Person sample data generation

$Id$
"""

import datetime
import os

from pytz import utc
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.term.interfaces import ITermContainer
from schooltool.sampledata import PortableRandom
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.sampledata.name import NameGenerator
from schooltool.demographics.person import Person
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.cal import CalendarEvent
from schooltool.common import DateRange

class ChoiceGenerator(object):
    def __init__(self, seed, choices):
        self.random = PortableRandom(seed)
        self.choices = choices

    def generate(self):
        return self.random.choice(self.choices)


class SampleStudents(object):

    implements(ISampleDataPlugin)

    name = 'students'
    dependencies = ()

    # Number of persons to generate
    power = 1000

    def personFactory(self, namegen, prefixgen, gendergen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'student%03d' % count
        person = Person(person_id, title=full_name)
        person.nameinfo.prefix = prefixgen.generate()
        person.nameinfo.first_name = first_name
        person.nameinfo.last_name = last_name
        person.setPassword(person_id)
        person.demographics.gender = gendergen.generate()
        person.schooldata.id = person.__name__
        person.parent1.name = namegen.generate()[2]
        person.parent2.name = namegen.generate()[2]
        return person

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        prefixgen = ChoiceGenerator(str(seed), ['Mr', 'Mrs', 'Miss', ''])
        gendergen = ChoiceGenerator(str(seed), ['male', 'female'])

        # some of the tests (e.g., for groups) are set up on the assumption that
        # we won't populate the student group as we create students.  This
        # is annoying, since we end up with an empty student group.  I'm not
        # sure how to get around this except with a try/except here.
        try:
            students = app['groups']['students']
            stud_group = True
        except KeyError:
            stud_group = False
        for count in range(self.power):
            person = self.personFactory(namegen, prefixgen, gendergen, count)
            # Without removeSecurityProxy we can't add members a
            # group.
            if stud_group:
                removeSecurityProxy(students.members).add(person)
            app['persons'][person.__name__] = person


class SampleTeachers(object):
    implements(ISampleDataPlugin)

    name = 'teachers'
    dependencies = ()

    # Number of teachers to generate
    power = 48

    def personFactory(self, namegen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'teacher%03d' % count
        person = Person(person_id, title=full_name)
        person.nameinfo.first_name = first_name
        person.nameinfo.last_name = last_name
        person.setPassword(person_id)
        return person

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        teachers = app['groups']['teachers']
        for count in range(self.power):
            person = self.personFactory(namegen, count)
            # Without removeSecurityProxy we can't add members a
            # group.
            removeSecurityProxy(teachers.members).add(person)
            app['persons'][person.__name__] = person


class SamplePersonalEvents(object):
    """Sample data plugin class that generates personal random events."""

    implements(ISampleDataPlugin)

    name = 'personal_events'
    dependencies = ('students', 'teachers', 'terms')

    probability = 10 # probability of having an event on any day

    def _readLines(self, filename):
        """Read in lines from file

        Filename is relative to the module.
        Returned lines are stripped.
        """
        fullpath = os.path.join(os.path.dirname(__file__), filename)
        lines = file(fullpath).readlines()
        return [line.strip() for line in lines]

    def generate(self, app, seed=None):
        self.random = PortableRandom(seed)
        event_titles = self._readLines('event_titles.txt')
        person_ids = [person for person in app['persons'].keys()
                      if person.startswith('student') or
                         person.startswith('teacher')]
        dates = []
        for term in ITermContainer(app).values():
            dates.append(term.first)
            dates.append(term.last)
        first = min(dates)
        last = max(dates)
        days = DateRange(first, last)
        for person_id in person_ids:
            person = app['persons'][person_id]
            calendar = ISchoolToolCalendar(person)
            for day in days:
                if self.random.randrange(0, 100) < self.probability:
                    event_title = self.random.choice(event_titles)
                    time_hour = self.random.randint(6, 23)
                    time_min = self.random.choice((0, 30))
                    event_time = datetime.datetime(day.year,
                                                   day.month,
                                                   day.day,
                                                   time_hour,
                                                   time_min,
                                                   tzinfo=utc)
                    event_duration = datetime.timedelta(
                                       minutes=self.random.randint(1, 12)*30)
                    event = CalendarEvent(event_time,
                                          event_duration,
                                          event_title)
                    calendar.addEvent(event)

