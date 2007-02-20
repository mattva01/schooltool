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
Unit tests for lyceum csv import.

$Id$
"""
__docformat__ = 'reStructuredText'


import unittest

from zope.component import provideAdapter
from zope.app.testing import setup
from zope.testing import doctest


def doctest_CSVStudent():
    r"""Tests for CSVStudent.

        >>> from lyceum.csvimport import CSVStudent
        >>> student = CSVStudent(u"John", u"Johnson", "1a")
        >>> student.name
        u'John'
        >>> student.surname
        u'Johnson'

    Title has the surname first at the moment so that sort by title
    would work properly:

        >>> student.title
        u'Johnson John'

        >>> student.user_name
        u'john-johnson'
        >>> student.group_id
        '1a'

    Lithuanian characters are transliterated to ascii when username is
    being formed:

        >>> student = CSVStudent(u"\u0020\u0105\u010d\u0117\u0119",
        ...                      u"\u012f\u0161\u016b\u0173\u017e", "1a")
        >>> student.user_name
        u'-acee-isuuz'

    Let's add the person to a schooltoolApplication:

        >>> class GroupStub(list):
        ...     def __init__(self, title):
        ...         self.title = title
        ...     @property
        ...     def members(self):
        ...         return self
        ...     def add(self, item):
        ...         self.append(item)
        >>> appStub = {'persons': {},
        ...            'groups': {'1a': GroupStub('1a')}}

        >>> from zope.annotation.interfaces import IAnnotations
        >>> def stubAnnotations(context):
        ...     if not hasattr(context, '_annotations'):
        ...         context._annotations = {}
        ...     return context._annotations
        >>> provideAdapter(stubAnnotations, adapts=(None,), provides=IAnnotations)

        >>> class StubNameChooser(object):
        ...     def __init__(self, context):
        ...         pass
        ...     def checkName(self, name, ignore):
        ...         print "Checking for name %s in container" % name
        >>> from zope.app.container.interfaces import INameChooser
        >>> provideAdapter(StubNameChooser, adapts=(None,), provides=INameChooser)
        >>> student.addToApp(appStub)
        Checking for name -acee-isuuz in container

    A person object has been created and added to the container:

        >>> appStub
        {'persons': {u'-acee-isuuz': <lyceum.person.LyceumPerson object at ...>},
         'groups': {'1a': [<lyceum.person.LyceumPerson object at ...>]}}

        >>> person = appStub['persons'][u'-acee-isuuz']
        >>> person.title
        u'\u012e\u0161\u016b\u0173\u017e  \u0105\u010d\u0117\u0119'
        >>> person.username
        u'-acee-isuuz'

        >>> person.first_name
        u' \u0105\u010d\u0117\u0119'
        >>> person.last_name
        u'\u012e\u0161\u016b\u0173\u017e'

        >>> person.gradeclass is appStub["groups"]["1a"]
        True

    Timetables are not show by default:

        >>> IAnnotations(person)
        {'schooltool.app.browser.cal.show_my_timetable': False}

    """


def doctest_LyceumGroupsAndStudents():
    """Tests for LyceumGroupsAndStudents.

        >>> from lyceum.csvimport import LyceumGroupsAndStudents
        >>> plugin = LyceumGroupsAndStudents()
        >>> app = {}
        >>> app['groups'] = {}
        >>> app['persons'] = {}
        >>> class StudentStub(object):
        ...     def __init__(self, *args):
        ...         self.data = args
        ...     def addToApp(self, app):
        ...         app['persons'][self.data] = 'A Student'
        >>> plugin.group_factory = lambda title: '<Group %s>' % title
        >>> plugin.student_factory = StudentStub
        >>> plugin.generate(app)

    We got all the groups created:

        >>> sorted(app['groups'].items())
        [(u'1a', u'<Group 1a>'),
         (u'1b', u'<Group 1b>'),
         (u'1c', u'<Group 1c>'),
         (u'1d', u'<Group 1d>'),
         (u'2a', u'<Group 2a>'),
         (u'2b', u'<Group 2b>'),
         (u'2c', u'<Group 2c>'),
         (u'2d', u'<Group 2d>')]

    As well as persons:

        >>> app['persons']
        {(u'Zobie', u'Brai', u'1a'): 'A Student',
         (u'Zmbie', u'Bran', u'1c'): 'A Student',
         (u'Zombe', u'Bain', u'1b'): 'A Student',
         (u'Zomie', u'Brin', u'2a'): 'A Student',
         (u'Zobie', u'Bain', u'1d'): 'A Student',
         (u'Zombe', u'Bran', u'2d'): 'A Student',
         (u'Zombi', u'Bran', u'2b'): 'A Student',
         (u'Zombie', u'Brain', u'2c'): 'A Student'}

    """


def doctest_CSVTeacher():
    """Tests for CSVTeacher.

    Parse a string that denotes a teacher:

        >>> from lyceum.csvimport import CSVTeacher
        >>> teacher = CSVTeacher(u"B. Johnson")
        >>> teacher.user_name
        u'bjohnson'
        >>> teacher.group_id
        'teachers'
        >>> teacher.surname
        u'Johnson'
        >>> teacher.name
        u'B.'
        >>> teacher.title
        u'B. Johnson'

    """


def doctest_LyceumTeachers():
    """Tests for LyceumTeachers.

        >>> from lyceum.csvimport import LyceumTeachers
        >>> lt = LyceumTeachers()
        >>> app = {}
        >>> app['persons'] = {}
        >>> class TeacherStub(object):
        ...     def __init__(self, name):
        ...         self.name = name
        ...         self.user_name = name
        ...     def addToApp(self, app):
        ...         print "Adding %s to Application" % self.name
        >>> lt.teacher_factory = TeacherStub
        >>> lt.generate(app)
        Adding T. Surname to Application
        Adding B. Duh to Application
        Adding R. Mah to Application
        Adding T. Surname to Application
        Adding B. Duh to Application
        Adding R. Mah to Application
        Adding T. Surname to Application
        Adding B. Duh to Application
        Adding R. Mah to Application
        Adding T. Surname to Application
        Adding B. Duh to Application
        Adding R. Mah to Application
        Adding T. Surname to Application
        Adding B. Duh to Application
        Adding R. Mah to Application

    """


def doctest_make_course_level():
    """Tests for make_course_level.

    Create a course title from the name of the base course and the
    level extracted from a list of groups:

        >>> from lyceum.csvimport import make_course_level
        >>> make_course_level('tb1 en', 'History')
        'History tb1 en'
        >>> make_course_level('2abd', 'English')
        'English 2'
        >>> make_course_level('3d A', 'English')
        'English 3A'
        >>> make_course_level('tb2', 'English')
        'English tb2'

    """


def CSVCourse():
    """Tests for CSVCourse.

    Parse a string that describes a course into an intermediate course
    object:

        >>> from lyceum.csvimport import CSVCourse
        >>> course = CSVCourse(u'English lang. 1')
        >>> course.title
        u'English lang. 1'
        >>> course.id
        u'english-1'
        >>> course = CSVCourse(u'History TB1')
        >>> course.title
        u'History TB1'
        >>> course.id
        u'history-tb1'

    Add it to the application:

        >>> app = {'courses': {}}
        >>> course.addToApp(app)
        >>> course_ob = app['courses']['history-tb1']
        >>> course_ob.title
        u'History TB1'

    """


def doctest_LyceumCourses():
    """Tests for LyceumCourses.

        >>> from lyceum.csvimport import LyceumCourses
        >>> class CourseStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def addToApp(self, app):
        ...         print "Adding %s to app." % self.title
        >>> lc = LyceumCourses()
        >>> lc.course_factory = CourseStub
        >>> lc.generate({})
        Adding History 1 to app.
        Adding Science 2 to app.

    """


def doctest_parse_groups():
    """Tests for parse_groups.

    Parse a string that describes multiple groups into a list of group ids:

        >>> from lyceum.csvimport import parse_groups
        >>> parse_groups("1a,b,c")
        ['1a', '1b', '1c']
        >>> parse_groups("2abc")
        ['2a', '2b', '2c']
        >>> parse_groups("1a,b A")
        ['1a', '1b']
        >>> parse_groups("1abB")
        ['1a', '1b']
        >>> parse_groups("Tb1")
        ['TB1']

    """


def doctest_LyceumScheduling_create_sections():
    """Tests for LyceumScheduling.create_sections.

    Create sections creates a dict with section descriptors as keys
    and associated meetings as values:

        >>> from lyceum.csvimport import LyceumScheduling
        >>> plugin = LyceumScheduling()
        >>> sorted(plugin.create_sections().items())
        [((u'history-1', u'B. Duh', u'1a'),
         [(1, 1, <CSVRoom 311, 311>), (1, 2, <CSVRoom 311, 311>),
          (2, 1, <CSVRoom 311, 311>), (2, 2, <CSVRoom 311, 311>),
          (3, 1, <CSVRoom 311, 311>), (3, 2, <CSVRoom 311, 311>),
          (4, 1, <CSVRoom 311, 311>), (4, 2, <CSVRoom 311, 311>),
          (5, 1, <CSVRoom 311, 311>), (5, 2, <CSVRoom 311, 311>)]),
         ((u'history-1', u'B. Duh', u'1b'),
         [(1, 3, <CSVRoom 311, 311>),
          (2, 3, <CSVRoom 311, 311>),
          (3, 3, <CSVRoom 311, 311>),
          (4, 3, <CSVRoom 311, 311>),
          (5, 3, <CSVRoom 311, 311>)]),
         ((u'history-1', u'B. Duh', u'1c'),
         [(1, 4, <CSVRoom 311, 311>), (1, 7, <CSVRoom 311, 311>),
          (2, 4, <CSVRoom 311, 311>), (2, 7, <CSVRoom 311, 311>),
          (3, 4, <CSVRoom 311, 311>), (3, 7, <CSVRoom 311, 311>),
          (4, 4, <CSVRoom 311, 311>), (4, 7, <CSVRoom 311, 311>),
          (5, 4, <CSVRoom 311, 311>), (5, 7, <CSVRoom 311, 311>)]),
         ((u'history-1', u'B. Duh', u'1d'),
         [(1, 5, <CSVRoom 311, 311>), (1, 6, <CSVRoom 311, 311>),
          (2, 5, <CSVRoom 311, 311>), (2, 6, <CSVRoom 311, 311>),
          (3, 5, <CSVRoom 311, 311>), (3, 6, <CSVRoom 311, 311>),
          (4, 5, <CSVRoom 311, 311>), (4, 6, <CSVRoom 311, 311>),
          (5, 5, <CSVRoom 311, 311>), (5, 6, <CSVRoom 311, 311>)]),
         ((u'science-2', u'R. Mah', u'2a'),
         [(1, 5, <CSVRoom 212, 212>), (1, 6, <CSVRoom 212, 212>),
          (2, 5, <CSVRoom 212, 212>), (2, 6, <CSVRoom 212, 212>),
          (3, 5, <CSVRoom 212, 212>), (3, 6, <CSVRoom 212, 212>),
          (4, 5, <CSVRoom 212, 212>), (4, 6, <CSVRoom 212, 212>),
          (5, 5, <CSVRoom 212, 212>), (5, 6, <CSVRoom 212, 212>)]),
         ((u'science-2', u'R. Mah', u'2b'),
         [(1, 1, <CSVRoom 212, 212>), (1, 2, <CSVRoom 212, 212>),
          (2, 1, <CSVRoom 212, 212>), (2, 2, <CSVRoom 212, 212>),
          (3, 1, <CSVRoom 212, 212>), (3, 2, <CSVRoom 212, 212>),
          (4, 1, <CSVRoom 212, 212>), (4, 2, <CSVRoom 212, 212>),
          (5, 1, <CSVRoom 212, 212>), (5, 2, <CSVRoom 212, 212>)]),
         ((u'science-2', u'R. Mah', u'2c'),
         [(1, 3, <CSVRoom 212, 212>), (1, 4, <CSVRoom 212, 212>),
          (2, 3, <CSVRoom 212, 212>), (2, 4, <CSVRoom 212, 212>),
          (3, 3, <CSVRoom 212, 212>), (3, 4, <CSVRoom 212, 212>),
          (4, 3, <CSVRoom 212, 212>), (4, 4, <CSVRoom 212, 212>),
          (5, 3, <CSVRoom 212, 212>), (5, 4, <CSVRoom 212, 212>)]),
         ((u'science-2', u'R. Mah', u'2d'),
         [(1, 7, <CSVRoom 212, 212>),
          (2, 7, <CSVRoom 212, 212>),
          (3, 7, <CSVRoom 212, 212>),
          (4, 7, <CSVRoom 212, 212>),
          (5, 7, <CSVRoom 212, 212>)])]

    """


def doctest_LyceumScheduling_schedule_section():
    """Tests for LyceumScheduling.schedule_section.

        >>> from lyceum.csvimport import days
        >>> from lyceum.csvimport import LyceumScheduling
        >>> plugin = LyceumScheduling()
        >>> from lyceum.csvimport import CSVRoom
        >>> ttschema_id = 'ttschema1'
        >>> app = {}
        >>> app['sections'] = {}
        >>> sid = 'history-1 1a john'
        >>> class TitleStub(object):
        ...     def __init__(self, title):
        ...         self.title = title

        >>> class GroupStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.members = []

        >>> from schooltool.timetable.interfaces import ITimetables
        >>> from zope.interface import implements
        >>> class TimetablesStub(object):
        ...     implements(ITimetables)
        ...     timetables = {}

        >>> class MemberList(list):
        ...     def __init__(self, members):
        ...         for member in members:
        ...             self.append(member)
        ...     def add(self, member):
        ...         self.append(member)

        >>> class SectionStub(object):
        ...     courses = [TitleStub('History 1')]
        ...     a1 = GroupStub('1a')
        ...     a1.members.append(TitleStub('John'))
        ...     a1.members.append(TitleStub('Peter'))
        ...     b1 = GroupStub('1b')
        ...     b1.members.append(TitleStub('Ann'))
        ...     members = MemberList([a1, b1])
        ...     def __conform__(self, iface):
        ...         if iface == ITimetables:
        ...             return TimetablesStub()
        ...     def __repr__(self):
        ...         return '<Section title=%s>' % self.title

        >>> class DayStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def add(self, period_id, activity, send_events=True):
        ...         assert send_events == False
        ...         print 'Adding %s on %s - %s' % (activity, self.title, period_id)
        >>> class TimetableStub(dict):
        ...     def __init__(self):
        ...         for day in days:
        ...             self[day] = DayStub(day)

        >>> app['sections'][sid] = SectionStub()
        >>> class TTSchemaStub(object):
        ...     def createTimetable(self):
        ...         return TimetableStub()
        >>> app['ttschemas'] = {ttschema_id: TTSchemaStub()}

        >>> app['resources'] = {"201": "Room 201"}

        >>> class TermStub(object):
        ...     __name__ = 'term1'
        >>> app['terms'] = {'term1': TermStub()}
        >>> meet1 = (1, 1, ttschema_id, "201")
        >>> meet2 = (2, 2, ttschema_id, "201")
        >>> meet3 = (4, 2, ttschema_id, "")
        >>> plugin.schedule_section(app, sid, [meet1, meet2, meet3])
        Adding TimetableActivity('History (1a, 1b)', <Section title=History (1a, 1b)>, None, ('Room 201',)) on Monday - 1 pamoka
        Adding TimetableActivity('History (1a, 1b)', <Section title=History (1a, 1b)>, None, ('Room 201',)) on Tuesday - 2 pamoka
        Adding TimetableActivity('History (1a, 1b)', <Section title=History (1a, 1b)>, None, ()) on Thursday - 2 pamoka

    Group members were added to sections, groups themselves were
    removed from there:

        >>> [m.title for m in app['sections'][sid].members]
        ['John', 'Peter', 'Ann']

    """


def doctest_LyceumScheduling_generate():
    """Tests for LyceumScheduling.generate.

    Generate should creates all sections, add members and schedules all of them:

        >>> from lyceum.csvimport import LyceumScheduling
        >>> plugin = LyceumScheduling()
        >>> def schedule_section(app, sid, meetings):
        ...     section = app['sections'][sid]
        ...     section.title = sid
        ...     section.scheduled = True
        >>> plugin.schedule_section = schedule_section
        >>> class RelationshipsStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.items = []
        ...     def add(self, item):
        ...         self.items.append(item)
        ...     def __repr__(self):
        ...         return '%s=[%s]' % (self.title, ', '.join(self.items))
        ...     __str__ = __repr__
        >>> class SectionStub(object):
        ...     def __init__(self):
        ...         self.courses = RelationshipsStub('Courses')
        ...         self.resources = RelationshipsStub('Resources')
        ...         self.members = RelationshipsStub('Members')
        ...         self.instructors = RelationshipsStub('Instructors')
        ...         self.scheduled = False
        ...     def __repr__(self):
        ...         return '<Section %s %s %s %s %s scheduled=%s>' % (
        ...                    self.title, self.courses, self.resources, self.members, self.instructors, self.scheduled)
        >>> plugin.section_factory = SectionStub
        >>> app = {}
        >>> app['sections'] = {}
        >>> app['groups'] = dict([(id, id) for id in ['1a', '1b', '1c', '1d',
        ...                                           '2a', '2b', '2c', '2d']])
        >>> app['persons'] = {'rmah': 'Teacher Rmah', 'bduh': 'Teacher Bduh'}
        >>> app['resources'] = {'212': 'Room 212', '311': 'Room 311'}
        >>> app['courses'] = {}
        >>> app['courses']['science-2'] = 'Science 2'
        >>> app['courses']['history-1'] = 'History 1'
        >>> plugin.generate(app)
        >>> print sorted(app['sections'].items())
        [(u'history-1 1a bduh', <Section history-1 1a bduh
              Courses=[History 1]
              Resources=[]
              Members=[1a]
              Instructors=[Teacher Bduh]
              scheduled=True>),
         (u'history-1 1b bduh', <Section history-1 1b bduh
              Courses=[History 1]
              Resources=[]
              Members=[1b]
              Instructors=[Teacher Bduh]
              scheduled=True>),
         (u'history-1 1c bduh', <Section history-1 1c bduh Courses=[History 1]
             Resources=[]
             Members=[1c]
             Instructors=[Teacher Bduh]
             scheduled=True>),
        (u'history-1 1d bduh', <Section history-1 1d bduh
             Courses=[History 1]
             Resources=[]
             Members=[1d]
             Instructors=[Teacher Bduh]
             scheduled=True>),
         (u'science-2 2a rmah', <Section science-2 2a rmah
             Courses=[Science 2]
             Resources=[]
             Members=[2a]
             Instructors=[Teacher Rmah]
             scheduled=True>),
         (u'science-2 2b rmah', <Section science-2 2b rmah
             Courses=[Science 2]
             Resources=[]
             Members=[2b]
             Instructors=[Teacher Rmah]
             scheduled=True>),
         (u'science-2 2c rmah', <Section science-2 2c rmah
             Courses=[Science 2]
             Resources=[]
             Members=[2c]
             Instructors=[Teacher Rmah]
             scheduled=True>),
         (u'science-2 2d rmah', <Section science-2 2d rmah
             Courses=[Science 2]
             Resources=[]
             Members=[2d]
             Instructors=[Teacher Rmah]
             scheduled=True>)]

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
