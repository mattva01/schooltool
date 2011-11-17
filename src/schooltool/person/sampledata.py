#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
"""
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.person.person import Person
from schooltool.sampledata import PortableRandom
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.sampledata.name import NameGenerator
from schooltool.group.interfaces import IGroupContainer


class ChoiceGenerator(object):
    def __init__(self, seed, choices):
        self.random = PortableRandom(seed)
        self.choices = choices

    def generate(self):
        return self.random.choice(self.choices)


class SampleStudents(object):

    implements(ISampleDataPlugin)

    name = 'students'
    dependencies = ('terms', )

    # Number of persons to generate
    power = 1000

    def personFactory(self, namegen, prefixgen, gendergen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'student%03d' % count
        person = Person(person_id, full_name)
        person.setPassword(person_id)
        return person

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        prefixgen = ChoiceGenerator(str(seed), ['Mr', 'Mrs', 'Miss', ''])
        gendergen = ChoiceGenerator(str(seed), ['male', 'female'])

        students = IGroupContainer(app)['students']
        for count in range(self.power):
            person = self.personFactory(namegen, prefixgen, gendergen, count)
            # Without removeSecurityProxy we can't add members a
            # group.
            removeSecurityProxy(students.members).add(person)
            app['persons'][person.__name__] = person


class SampleTeachers(object):
    implements(ISampleDataPlugin)

    name = 'teachers'
    dependencies = ('terms', )

    # Number of teachers to generate
    power = 48

    def personFactory(self, namegen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'teacher%03d' % count
        person = Person(person_id, full_name)
        person.setPassword(person_id)
        return person

    def generate(self, app, seed=None):
        namegen = NameGenerator(str(seed) + self.name)
        teachers = IGroupContainer(app)['teachers']
        for count in range(self.power):
            person = self.personFactory(namegen, count)
            # Without removeSecurityProxy we can't add members a
            # group.
            removeSecurityProxy(teachers.members).add(person)
            app['persons'][person.__name__] = person
