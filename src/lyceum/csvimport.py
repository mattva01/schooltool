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
Lyceum person csv import functionality.

$Id$
"""
import csv
import os
from datetime import time, timedelta, date

from zope.security.proxy import removeSecurityProxy
from zope.exceptions.interfaces import UserError
from zope.app.container.interfaces import INameChooser
from zope.annotation.interfaces import IAnnotations

from schooltool.common import DateRange
from schooltool.course.course import Course
from schooltool.course.section import Section
from schooltool.group.group import Group
from schooltool.resource.resource import Location
from schooltool.term.term import Term
from schooltool.timetable import SchooldaySlot
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable import TimetableActivity
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.model import WeeklyTimetableModel
from schooltool.timetable.schema import TimetableSchema
from schooltool.timetable.schema import TimetableSchemaDay
from schooltool.app.browser.cal import CalendarSTOverlayView

from lyceum.person import LyceumPerson


def encode_row(row):
    return [unicode(cell, 'UTF-8') for cell in row]


def load_csv(file_name):
    return map(encode_row, csv.reader(open(file_name)))


lit_map = {0x0020: u'-',
           0x0105: u'a',
           0x010d: u'c',
           0x0117: u'e',
           0x0119: u'e',
           0x012f: u'i',
           0x0161: u's',
           0x016b: u'u',
           0x0173: u'u',
           0x017e: u'z'}

tvarkarastis_template = os.path.join(os.path.dirname(__file__), "csv",
                                     "tvarkarastis%s.csv")
tvarkarastis_csvs = map(load_csv, [tvarkarastis_template % n for n in range(1,6)])
klases_csv = load_csv(os.path.join(os.path.dirname(__file__), "csv",
                                   "klases.csv"))[2:]

merged_tvarkarastis_csvs = []
for lst in tvarkarastis_csvs:
    merged_tvarkarastis_csvs.extend(lst[1:])


class CSVStudent(object):
    """An intermediate object that stores persons information."""

    def __init__(self, name, surname, group):
        self.name = name.capitalize()
        self.surname = surname.capitalize()
        self.title = u"%s %s" % (self.surname, self.name)
        user_name = u"%s-%s" % (name.lower(), surname.lower())
        self.user_name = user_name.translate(lit_map)
        self.group_id = group

    def addToApp(self, app):
        """Add a person to a container"""
        try:
            INameChooser(app['persons']).checkName(self.user_name, None)
            user_name = self.user_name
        except UserError:
            user_name = INameChooser(app['persons']).chooseName(self.user_name, None)

        person = LyceumPerson(user_name, self.name, self.surname)
        app['persons'][user_name] = person
        group = removeSecurityProxy(app['groups'][self.group_id])
        group.members.add(person)
        person.gradeclass = self.group_id

        annotations = IAnnotations(person)
        annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = False


class LyceumGroupsAndStudents(object):
    """Plugin that creates all persons and groups.

    Add person to groups they belong to.
    """

    dependencies = ()
    name = "lyceum_groups_students"

    group_factory = Group
    student_factory = CSVStudent

    def generate(self, app):
        """Create a person object for every student.

        Adds the person to the appropriate group.
        """

        group_ids = set([row[0] for row in klases_csv])
        for id in group_ids:
            app['groups'][id] = self.group_factory(title=id)

        for group_id, name, surname in reversed(klases_csv):
            self.student_factory(name, surname, group_id).addToApp(app)


class CSVTeacher(CSVStudent):
    """Extract teacher information from a string"""

    def __init__(self, str):
        self.title = str.strip()
        self.name, self.surname = self.title.split(' ')
        user_name = self.name[0].lower() + self.surname.strip().lower()
        self.user_name = user_name.translate(lit_map)
        self.group_id = "teachers"


class LyceumTeachers(object):
    """Plugin that creates a person for each teacher.

    And adds them to the teacher group.
    """

    dependencies = ()
    name = "lyceum_teachers"
    teacher_factory = CSVTeacher

    def generate(self, app):
        """Create a person for each teacher.

        Add persons to the teacher group.
        """
        for table in tvarkarastis_csvs:
            for row in table[2:]:
                if row[0].strip() != '' and row[1].strip() != '':
                    teacher = self.teacher_factory(row[1])
                    if teacher.user_name not in app['persons']:
                        teacher.addToApp(app)


def make_course(cell, course):
    if cell[0] in '1234':
        level = cell[0]
    else:
        level = cell[:3]
        if len(cell) > 3:
             level += ' ' + cell[-2:]
    return "%s %s" % (course, level)


class CSVCourse(object):

    def __init__(self, str):
        self.id = ('.' in str and (str.split(' ')[0] + ' ' + str.split(' ')[-1]) or str).lower().translate(lit_map)
        self.title = str

    def addToApp(self, app):
        app['courses'][self.id] = Course(title=self.title)


class LyceumCourses(object):
    """Creates course objects and add them to the course container."""

    dependencies = ()
    name = "lyceum_courses"
    course_factory = CSVCourse

    def generate(self, app):
        """Parse strings into course objects.

        Add course objects to the application.
        """
        courses = []
        current_course = None
        for row in merged_tvarkarastis_csvs:
            if row[0].strip() == '' and row[1].strip() != '':
                current_course = row[1].strip()
                continue
            if current_course:
                for n, cell in enumerate(row[2:]):
                    if n % 2 == 0 and cell.strip() != '':
                        courses.append(make_course(cell, current_course))
        courses = set(courses)

        for course in courses:
            self.course_factory(course).addToApp(app)


def parse_groups(groups):
    if groups[0] in '1234':
        level = groups[0]
        if groups[-1] in 'AB':
            segments = groups[1:-1].strip()
        else:
            segments = groups[1:].strip()
        segments = segments.replace(',', '')
        return [level + segment for segment in segments]
    else:
        return [groups[0:3].upper()]


def normalize_groups(groups):
    if groups[0] in '1234':
        level = groups[0]
        if groups[-1] in 'AB':
            segments = groups[1:-1].strip()
        else:
            segments = groups[1:].strip()
        segments = segments.replace(',', '')
        segments = segments.replace(' ', '')
        return level + segments
    else:
        return groups[0:3].upper()


def parse_level(groups):
    if groups[-1] in 'AB':
        return groups[-1]


class CSVRoom(object):

    def __init__(self, str):
        self.id = str.lower().translate(lit_map)
        self.title = str
        if self.id == 'sk.':
            self.id = 'skaitykla'
            self.title = 'Skaitykla'

    def __repr__(self):
        return '<CSVRoom %s, %s>' % (self.id, self.title)


class LyceumResources(object):

    dependencies = ()
    name = "lyceum_resources"

    def generate(self, app):
        rooms = []
        for row in merged_tvarkarastis_csvs:
            for n, cell in enumerate(row[2:]):
                if n % 2 == 1 and cell.strip() != '':
                    rooms.append(cell.strip())

        rooms = set(rooms)
        for room in rooms:
            room = CSVRoom(room)
            app['resources'][room.id] = Location(title=room.title)


days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


class LyceumScheduling(object):

    dependencies = ("lyceum_groups_students", "lyceum_teachers",
                    "lyceum_courses", "lyceum_resources")
    name = "lyceum_scheduling"

    def create_sections(self):
        """Generates a dict that contains all sections and their meetings.

        Returns a dict with a key (course_id, teacher, groups) and a
        list of meetings as the value.
        """
        sections = {}
        for day, csv_data in enumerate(tvarkarastis_csvs):
            for row in csv_data[1:]:
                if row[0].strip() == '' and row[1].strip() != '':
                    current_course = row[1].strip()
                    continue
                if row[0].strip() != '' and row[1].strip() != '':
                    current_teacher = row[1].strip()
                for n, cell in enumerate(row[2:]):
                    if n % 2 == 0 and cell.strip() != '':
                        course = CSVCourse(make_course(cell, current_course))
                        teacher, group = current_teacher, cell
                        meeting = (day + 1, n / 2 + 1, CSVRoom(row[2:][n+1]))
                        level = parse_level(group) or ""
                        group = normalize_groups(group)
                        if (course.id, teacher, group, level) in sections:
                            sections[(course.id, teacher, group, level)].append(meeting)
                        else:
                            sections[(course.id, teacher, group, level)] = [meeting]
        return sections

    def _create_activity_title(self, section, level):
        course_title = ' '.join(list(section.courses)[0].title.split(' ')[:-1])
        group_titles = ', '.join([group.title
                                  for group in section.members])
        if not level:
            return "%s (%s)" % (course_title, group_titles)
        else:
            return "%s (%s) %s lygis" % (course_title, group_titles, level)

    def schedule_section(self, app, sid, level, meetings):
        sob = removeSecurityProxy(app['sections'][sid])
        activity_title = self._create_activity_title(sob, level)
        sob.title = activity_title
        ttschema_id = meetings[0][2]
        ttschema = removeSecurityProxy(app['ttschemas'][ttschema_id])
        for term in removeSecurityProxy(app['terms']).values():
            key = '%s.%s' % (term.__name__, ttschema_id)
            timetable = ttschema.createTimetable()
            for id, period, _, room in  meetings:
                day_id = days[id-1]
                resources = []
                if room != '':
                    resources = [removeSecurityProxy(app['resources'][room])]
                act = TimetableActivity(title=activity_title, owner=sob,
                                        resources=resources)
                timetable[day_id].add('%d pamoka' % period, act,
                                      send_events=False)
            ITimetables(sob).timetables[key] = timetable
        for group in list(sob.members):
            for person in group.members:
                sob.members.add(person)
            sob.members.remove(group)

    section_factory = Section

    def generate(self, app):
        sections = self.create_sections()
        # schedule the section
        unscheduled_sections = {}
        for section, meetings in sections.items():
            course_id, teacher, groups, level = section
            teacher = CSVTeacher(teacher)
            current_room = None
            grp = parse_groups(groups)[0]
            if grp[0] in '12':
                ttschema = 'i-ii-kursui'
            else:
                ttschema = 'iii-iv-kursui'

            if level:
                sid = (course_id + ' ' + groups + ' ' + level + ' ' + teacher.user_name).strip()
            else:
                sid = (course_id + ' ' + groups + ' ' + teacher.user_name).strip()

            for day, period, room in sorted(meetings, key=lambda meeting: meeting[2].id):
                meeting = (day, period, ttschema, room.id)
                if (sid, level) not in unscheduled_sections:
                    unscheduled_sections[sid, level] = [meeting]
                else:
                    unscheduled_sections[sid, level].append(meeting)
                if sid not in app['sections']:
                    sob = self.section_factory()
                    app['sections'][sid] = sob
                    course = removeSecurityProxy(app['courses'][course_id])
                    sob.courses.add(course)
                    for group_id in parse_groups(groups):
                        sob.members.add(removeSecurityProxy(app['groups'][group_id]))
                    sob.instructors.add(removeSecurityProxy(app['persons'][teacher.user_name]))

        for (sid, level), meetings in unscheduled_sections.items():
            self.schedule_section(app, sid, level, meetings)


class LyceumSchoolTimetables(object):

    def generateSchoolDayTemplate(self, lesson_starts, period_length=45):
        template = SchooldayTemplate()
        for lesson_time in lesson_starts:
            template.add(SchooldaySlot(time(*lesson_time),
                                       timedelta(minutes=period_length)))
        return template

    def generateSchoolTimetable(self, app, title, id, lesson_starts):
        periods = ['%d pamoka' % n for n in range(1, 11)]
        template = self.generateSchoolDayTemplate(lesson_starts)
        model = WeeklyTimetableModel(day_templates={None: template})
        ttschema = TimetableSchema(days, title=title, model=model)
        for day in days:
            ttschema[day] = TimetableSchemaDay(tuple(periods))
        app['ttschemas'][id] = ttschema

    def generate(self, app):

        lesson_starts = [(8, 0), (8, 55), (9, 50),
                         (11, 5), (12, 0), (13, 5),
                         (14, 0), (14, 55), (15, 50), (16, 40)]

        self.generateSchoolTimetable(app, "I-II kursui", 'i-ii-kursui',
                                     lesson_starts)

        lesson_starts[3] = (10, 45)
        self.generateSchoolTimetable(app, "III-IV kursui", 'iii-iv-kursui',
                                     lesson_starts)


class LyceumTerms(object):

    def __init__(self):
        self.holidays = []
        self.holidays.append(DateRange(date(2006, 10, 30), date(2006, 11, 5)))
        self.holidays.append(DateRange(date(2006, 12, 24), date(2007, 1, 6)))
        self.holidays.append(DateRange(date(2007, 4, 2), date(2007, 4, 9)))

    def addTerm(self, app, title, id, first, last):
        term = Term(title, first, last)
        for date in term:
            term.add(date)

        for holiday in self.holidays:
            for day in holiday:
                if day in term:
                    term.remove(day)

        term.removeWeekdays(5)
        term.removeWeekdays(6)
        app['terms'][id] = term

    def generate(self, app):
        first = date(2006, 9, 1)
        last = date(2007, 1, 26)
        self.addTerm(app, "2006 Ruduo", "2006-ruduo", first, last)

        first = date(2007, 1, 29)
        last = date(2007, 6, 15)
        self.addTerm(app, "2007 Pavasaris", "2007-pavasaris", first, last)
