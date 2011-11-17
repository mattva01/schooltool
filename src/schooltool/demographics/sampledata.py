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
"""
from schooltool.person.sampledata import SampleStudents
from schooltool.person.sampledata import SampleTeachers

from schooltool.demographics.person import Person


class SampleStudents(SampleStudents):

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


class SampleTeachers(SampleTeachers):

    def personFactory(self, namegen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'teacher%03d' % count
        person = Person(person_id, title=full_name)
        person.nameinfo.first_name = first_name
        person.nameinfo.last_name = last_name
        person.setPassword(person_id)
        return person
