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
import random
import os

from pytz import utc
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.sampledata.name import NameGenerator
from schooltool.person.person import Person
from schooltool.timetable.term import DateRange
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.cal import CalendarEvent


class SampleStudents(object):

    implements(ISampleDataPlugin)

    name = 'students'
    dependencies = ()

    # Number of persons to generate
    power = 1000

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        for i in range(self.power):
            name = namegen.generate()
            person_id = 'student%03d' % i
            app['persons'][person_id] = Person(person_id, title=name)
            app['persons'][person_id].setPassword(person_id)


class SampleTeachers(object):
    implements(ISampleDataPlugin)

    name = 'teachers'
    dependencies = ()

    # Number of teachers to generate
    power = 48

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        teachers = app['groups']['teachers']
        for i in range(self.power):
            name = namegen.generate()
            person_id = 'teacher%03d' % i
            person = Person(person_id, title=name)
            person.setPassword(person_id)
            # Without removeSecurityProxy we can't add members a
            # group.
            removeSecurityProxy(teachers.members).add(person)
            app['persons'][person_id] = person


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
        self.random = random.Random(seed)
        event_titles = self._readLines('event_titles.txt')
        person_ids = [person for person in app['persons'].keys()
                      if person.startswith('student') or
                         person.startswith('teacher')]
        dates = []
        for term in app['terms'].values():
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

