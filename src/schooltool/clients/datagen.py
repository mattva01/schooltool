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

Generates four CSV files (groups.csv, persons.csv, resources.csv and
timetable.csv) and roster.txt.

$Id$
"""
import random
import sys
import sets
import datetime
from schooltool.translation import gettext as _

names = _('David Deb Sue Martin Denise Vicki Lorne Jeff Michael '
          'Norma Nicola Wendy Lesley Carey Debbie Alden Carol Jay '
          'Heather Barbara John Peter Andrea Courtney Kathleen '
          'Lisa Sharon James Patricia Mary Mary John John John James '
          'James James Geoffrey Tom').split()

surnames = _('Moore McCullogh Buckingham Butler Davies Clark Cooper '
             'Thrift Cox Ford Horsman Price Siggs Bisset Ball Barrett '
             'Oakley Hall Turner Hester Batchelor Broughton Jones '
             'Smith Smith Smith Smith Smith Smith Smith Greenspun '
             'Eastwood Baggins').split()

# The number of years, teachers and subjects are wired in at this point.

years = 2
nr_pupils = 60
nr_teachers = 8
subjects = {'ling': _('Linguistics'),
            'math': _('Mathematics'),
            'biol': _('Biology'),
            'hist': _('History')}
pupil_age_end = 1994        # Which year the youngest pupils will be
teacher_age_start = 1950    # Oldest teachers
teacher_age_end = 1980      # Youngest teachers

timetable = [[''] * 4 for line in range(8)]
rosters = [''] * 8


def random_name():
    return (random.choice(surnames), random.choice(names))


def random_date(start, end):
    """Generate a random date in the given date range (inclusive)."""
    len = end - start
    days = len.days
    return start + datetime.timedelta(days=random.randint(0, days))


def createGroups():
    """Create a randomly generated groups.csv in the current directory.

    Format of the file:
      group_name, group_title, parents, facets
    where
      parents is a space separated list of parent group names
      facets is a space separated list of facet factory names
    """
    f = open("groups.csv", "w")

    for subj, subject in subjects.items():
        print >> f, '"%s","%s","root",' % (subj, _("%s Department") % subject)

    for year in range(1, years + 1):
        print >> f, '"year%d","%s","root",' % (year, _("Year %d") % year)
        for subj, subject in subjects.items():
            print >> f, ('"%s%d","%s %d","%s year%d","subject_group"' %
                         (subj, year, subject, year, subj, year))
    f.close()


def createPersons():
    """Generate persons.csv and roster.txt in the current directory."""
    persons = open("persons.csv", "w")
    roster = open("roster.txt", "w")
    names = sets.Set()
    subNames = subjects.keys()
    subNames.extend(subjects.keys())
    team = 1
    kids = []

    for i in range(nr_pupils):
        year = i / (nr_pupils/years) + 1
        groups = ["%s%d" % (subj, year) for subj in subjects.keys()]
        birthday = random_date(datetime.date(pupil_age_end - year + 1, 1, 1),
                               datetime.date(pupil_age_end - year + 2, 1, 1))

        for counter in range(20):
            surname, name = random_name()
            full = "%s %s" % (name, surname)
            if full not in names:
                break

        names.add(full)
        kids.append(full)

        groups_str = 'year%s %s' % (year, 'pupils')
        print >> persons, '"","%s","%s","%s","%s",""' % (surname, name,
                                                         groups_str, birthday)

    for count in range(0, nr_teachers):
        period = count
        if count > 3:
            team = 2
            period = period - 4
            students = kids[31:]
        else:
            students = kids[:30]
        for counter in range(20):
            surname, name = random_name()
            full = "%s %s" % (name, surname)
            if full not in names:
                break

        names.add(full)
        birthday = random_date(datetime.date(teacher_age_start, 1, 1),
                               datetime.date(teacher_age_end, 1, 1))
        print >> persons, ('"","%s","%s","%s teachers","%s",""'
                           % (surname, name, subNames[count], birthday))
        timetable[count][period] = ('%s %s | %s %s' %
                                    (subjects[subNames[count]],
                                     team, name, surname))
        print >> roster, '%s %s' % (subjects[subNames[count]], team)
        for kid in students:
            print >> roster, kid
        print >> roster, ""

    roster.close()
    persons.close()


def createResources():
    """Create a generated resources.csv in the current directory.

    Format of the file:
      title, groups
    """
    f = open("resources.csv", "w")
    print >> f, '"%s","locations"' % _('Hall')
    for i in range(1, 10):
        print >> f, '"%s","locations"' % (_('Room %d') % i)
    for i in range(1, 4):
        print >> f, '"%s",""' % (_('Projector %d') % i)
    f.close()


def createTimetable():
    """Create timetable.csv in the current directory."""
    f = open("timetable.csv", "w")
    print >> f, '"2004-fall","default"'
    print >> f, '""'
    print >> f, '"Day 1"'
    print >> f, '"","A","B"'
    for count in range(1, 9):
        print >> f, '"Room %i","%s","%s"' % (count, timetable[count-1][0],
                                             timetable[count-1][1])
    print >> f, '""'
    print >> f, '"Day 2"'
    print >> f, '"","C","D"'
    for count in range(1, 9):
        print >> f, '"Room %i","%s","%s"' % (count, timetable[count-1][2],
                                             timetable[count-1][3])
    f.close()


def main(argv):
    if len(argv) > 1:
        random.seed(argv[1])
    createGroups()
    createPersons()
    createResources()
    createTimetable()

if __name__ == '__main__':
    main(sys.argv)
