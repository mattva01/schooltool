#!/usr/bin/env python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Random sample data generation script.

Accepts a random seed as an optional argument.

Generates three CSV files: groups.csv, pupils.csv and teacher.csv

$Id$
"""
import random
import sys

names = ('David', 'Deb', 'Sue', 'Martin', 'Denise', 'Vicki', 'Lorne',
         'Jeff', 'Michael', 'Norma', 'Nicola', 'Wendy', 'Lesley',
         'Carey', 'Debbie', 'Alden', 'Carol', 'Jay', 'Heather',
         'Barbara', 'John', 'Peter', 'Andrea', 'Courtney', 'Kathleen',
         'Lisa', 'Sharon', 'James', 'Patricia', 'Mary', 'Mary',
         'John', 'John', 'John', 'James', 'James', 'James',
         'Geoffrey', 'Tom')

surnames = ('Moore', 'McCullogh', 'Buckingham', 'Butler', 'Davies',
            'Clark', 'Cooper', 'Thrift', 'Cox', 'Ford', 'Horsman',
            'Price', 'Siggs', 'Bisset', 'Ball', 'Barrett', 'Oakley',
            'Hall', 'Turner', 'Hester', 'Batchelor', 'Broughton',
            'Jones', 'Smith', 'Smith', 'Smith', 'Smith', 'Smith',
            'Smith', 'Smith', 'Greenspun', 'Eastwood', 'Baggins')

def random_name():
    return "%s %s" % (random.choice(names), random.choice(surnames))

def createGroups():
    f = open("groups.csv", "w")

    # name, title, parents, facet
    print >> f, '"year1","Year 1","/",'
    print >> f, '"year2","Year 2","/",'
    print >> f, '"year3","Year 3","/",'
    print >> f, '"ling","Department of Linguistics","/",'
    print >> f, '"phys","Department of Physics","/",'
    print >> f, '"math","Department of Maths","/",'
    print >> f, '"biol","Department of Biology","/",'

    print >> f, '"ling1","Linguistics 1","/ ling year1","Subject Group"'
    print >> f, '"ling2","Linguistics 2","/ ling year2","Subject Group"'
    print >> f, '"ling3","Linguistics 3","/ ling year3","Subject Group"'

    print >> f, '"phys1","Physics 1","/ phys year1","Subject Group"'
    print >> f, '"phys2","Physics 2","/ phys year2","Subject Group"'
    print >> f, '"phys3","Physics 3","/ phys year3","Subject Group"'

    print >> f, '"math1","Mathematics 1","/ math year1","Subject Group"'
    print >> f, '"math2","Mathematics 2","/ math year2","Subject Group"'
    print >> f, '"math3","Mathematics 3","/ math year3","Subject Group"'

    print >> f, '"biol1","Biology 1","/ biol year1","Subject Group"'
    print >> f, '"biol2","Biology 2","/ biol year2","Subject Group"'
    print >> f, '"biol3","Biology 3","/ biol year3","Subject Group"'

    f.close()

def createPupils(nr=60):

    f = open("pupils.csv", "w")

    for i in range(nr):
        year = i / (nr/3) + 1
        subjects = [format % year
                    for format in ("ling%d", "phys%d", "math%d", "biol%d")]
        subject1 = random.choice(subjects)
        subjects.remove(subject1)
        subject2 = random.choice(subjects)

        print >> f, '"%s","%s"' % (random_name(),
                                   " ".join(("year%d" % year,
                                            subject1, subject2)))
    f.close()


def createTeachers():

    f = open("teachers.csv", "w")

    teachers = []
    for i in range(10):
        teachers.append([])

    for dept in ("ling", "phys", "math", "biol"):
        for year in range(1,4):
            teacher = random.choice(teachers)
            teacher.append("%s%d" % (dept, year))

    for groups in teachers:
        print >> f, '"%s","%s"' % (random_name(),  " ".join(groups))
    f.close()

def main():
    if len(sys.argv) > 1:
        random.seed(sys.argv[1])
    createGroups()
    createPupils()
    createTeachers()

if __name__ == '__main__':
    main()
