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
import sets

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

years = 3
nr_teachers = 10
nr_pupils = 60
subjects = {
    'ling': 'Linguistics',
    'phys': 'Physics',
    'math': 'Mathematics',
    'biol': 'Biology'
    }


def random_name():
    return "%s %s" % (random.choice(names), random.choice(surnames))


def createGroups():
    f = open("groups.csv", "w")

    # name, title, parents, facet

    for subj, subject in subjects.items():
        print >> f, '"%s","Department of %s","root",' % (subj, subject)

    for year in range(1, years + 1):
        print >> f, '"year%d","Year %d","root",' % (year, year)
        for subj, subject in subjects.items():
            print >> f, ('"%s%d","%s %d","%s year%d","Subject Group"' %
                         (subj, year, subject, year, subj, year))
    f.close()



def createPupils(nr=nr_pupils):

    f = open("pupils.csv", "w")

    # title, groups
    names = sets.Set()
    for i in range(nr):
        year = i / (nr/years) + 1
        groups = ["%s%d" % (subj, year) for subj in subjects.keys()]
        subject1 = random.choice(groups)
        groups.remove(subject1)
        subject2 = random.choice(groups)

        for counter in range(20):
            name = random_name()
            if name not in names:
                break

        names.add(name)
        print >> f, '"%s","%s"' % (name, " ".join(("year%d" % year,
                                                   subject1, subject2)))
    f.close()


def createTeachers():

    f = open("teachers.csv", "w")

    # title, taught

    teachers = []
    for i in range(nr_teachers):
        teachers.append([])

    for dept in subjects.keys():
        for year in range(1,years + 1):
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
