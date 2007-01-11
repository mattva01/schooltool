import csv
import os

from zope.security.proxy import removeSecurityProxy
from zope.exceptions.interfaces import UserError
from zope.app.container.interfaces import INameChooser

from schooltool.timetable.interfaces import ITimetables
from schooltool.demographics.person import Person
from schooltool.group.group import Group
from schooltool.course.section import Section
from schooltool.course.course import Course
from schooltool.resource.resource import Resource
from schooltool.timetable import TimetableActivity


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

tvarkarastis_template = os.path.join(os.path.dirname(__file__), "tvarkarastis%s.csv")
tvarkarastis_csvs = map(load_csv, [tvarkarastis_template % n for n in range(1,6)])
klases_csv = load_csv(os.path.join(os.path.dirname(__file__), "klases.csv"))[2:]

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

        person = Person(user_name, self.title)
        person.nameinfo.first_name = self.name
        person.nameinfo.last_name = self.surname
        app['persons'][user_name] = person
        group = removeSecurityProxy(app['groups'][self.group_id])
        person.schooldata.grade_section = group

        from zope.annotation.interfaces import IAnnotations
        annotations = IAnnotations(person)
        from schooltool.app.browser.cal import CalendarSTOverlayView
        annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = False

        group.members.add(person)


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


def make_course_level(cell, course):
    if cell[0] in '1234':
        level = cell[0]
        if cell[-1] in 'AB':
            level += cell[-1]
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
                        courses.append(make_course_level(cell, current_course))
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
            app['resources'][room.id] = Resource(title=room.title, isLocation=True)


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
                        course = CSVCourse(make_course_level(cell, current_course))
                        teacher, group = current_teacher, cell
                        meeting = (day + 1, n / 2 + 1, CSVRoom(row[2:][n+1]))
                        if (course.id, teacher, group) in sections:
                            sections[(course.id, teacher, group)].append(meeting)
                        else:
                            sections[(course.id, teacher, group)] = [meeting]
        return sections

    def _create_activity_title(self, section):
        course_title = ' '.join(list(section.courses)[0].title.split(' ')[:-1])
        group_titles = ', '.join([group.title
                                  for group in section.members])
        return "%s (%s)" % (course_title, group_titles)

    def schedule_section(self, app, sid, meetings):
        sob = removeSecurityProxy(app['sections'][sid])
        activity_title = self._create_activity_title(sob)
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
            course_id, teacher, groups = section
            teacher = CSVTeacher(teacher)
            current_room = None
            grp = parse_groups(groups)[0]
            if grp[0] in '12':
                ttschema = 'iii-kursui'
            else:
                ttschema = 'iiiiv-kursui'
            for day, period, room in sorted(meetings, key=lambda meeting: meeting[2].id):
                sid = (course_id + ' ' + groups + ' ' + teacher.user_name).strip()
                meeting = (day, period, ttschema, room.id)
                if sid not in unscheduled_sections:
                    unscheduled_sections[sid] = [meeting]
                else:
                    unscheduled_sections[sid].append(meeting)
                if sid not in app['sections']:
                    sob = self.section_factory()
                    app['sections'][sid] = sob
                    course = removeSecurityProxy(app['courses'][course_id])
                    sob.courses.add(course)
                    for group_id in parse_groups(groups):
                        sob.members.add(removeSecurityProxy(app['groups'][group_id]))
                    sob.instructors.add(removeSecurityProxy(app['persons'][teacher.user_name]))

        for sid, meetings in unscheduled_sections.items():
            self.schedule_section(app, sid, meetings)
