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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Basic person sample data generation
"""
from schooltool.person.sampledata import SampleStudents
from schooltool.person.sampledata import SampleTeachers
from schooltool.basicperson.person import BasicPerson


class SampleBasicStudents(SampleStudents):

    def personFactory(self, namegen, prefixgen, gendergen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'student%03d' % count
        person = BasicPerson(person_id, first_name, last_name)
        person.setPassword(person_id)
        person.gender = gendergen.generate()
        return person


class SampleBasicTeachers(SampleTeachers):

    def personFactory(self, namegen, count):
        first_name, last_name, full_name = namegen.generate()
        person_id = 'teacher%03d' % count
        person = BasicPerson(person_id, first_name, last_name)
        person.setPassword(person_id)
        return person
