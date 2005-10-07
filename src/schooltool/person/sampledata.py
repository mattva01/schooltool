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

import random

from zope.interface import implements

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.person.person import Person
from schooltool.group.group import Group
from schooltool.sampledata.name import NameGenerator


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
        teachers = app['groups']['teachers'] = Group(title='Teachers')
        for i in range(self.power):
            name = namegen.generate()
            person_id = 'teacher%03d' % i
            person = Person(person_id, title=name)
            person.setPassword(person_id)
            teachers.members.add(person)
            app['persons'][person_id] = person
