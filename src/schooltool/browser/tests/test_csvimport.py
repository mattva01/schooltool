#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.browser.csvimport

$Id$
"""

import unittest
import datetime
from StringIO import StringIO
from logging import INFO
from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.i18n import translate
from zope.interface.verify import verifyObject
from schooltool.common import dedent
from schooltool.app import Person, Course, Section, Resource
from schooltool.relationships import URISection, URISectionOfCourse
from schoolbell.app.membership import URIMember
from schoolbell.relationship.tests import setUp as setUpRelationshipStuff
from schoolbell.relationship.tests import tearDown as tearDownRelationshipStuff
from schoolbell.app.browser.tests.setup import setUp, tearDown

__metaclass__ = type


class TestTimetableCSVImportView(unittest.TestCase):

    def setUp(self):
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay
        from schooltool.app import SchoolToolApplication
        from schooltool.timetable import Term
        setUpRelationshipStuff()
        self.app = SchoolToolApplication()

        ttschema = TimetableSchema(["1","2","3"])
        for day in range(1, 4):
            ttschema[str(day)] = TimetableSchemaDay([str(day)])
        self.app['ttschemas']['three-day'] = ttschema

        self.app['terms']['fall'] = Term("Fall term",
                                         datetime.datetime(2004, 1, 1),
                                         datetime.datetime(2004, 5, 1))

    def tearDown(self):
        tearDownRelationshipStuff()

    def createView(self, form=None):
        from schooltool.browser.csvimport import TimetableCSVImportView
        if form is None:
            form = {}
        request = TestRequest(form=form)
        return TimetableCSVImportView(self.app, request)

    def test_getCharset(self):
        view = self.createView(form={'charset': 'UTF-8',
                                     'other_charset': ''})
        self.assertEquals(view.getCharset(), 'UTF-8')
        self.failIf(view.errors)

        view = self.createView(form={'charset': 'other',
                                     'other_charset': 'ISO-8859-1'})
        self.assertEquals(view.getCharset(), 'ISO-8859-1')
        self.failIf(view.errors)

        view = self.createView(form={'charset': 'bogus-charset',
                                     'other_charset': ''})
        self.assertEquals(view.getCharset(), None)
        self.assertEquals(view.errors, ['Unknown charset'])

        view = self.createView(form={'charset': 'other',
                                     'other_charset': 'bogus-charset'})
        self.assertEquals(view.getCharset(), None)
        self.assertEquals(view.errors, ['Unknown charset'])

    def test_dummy_update(self):
        view = self.createView()
        view.update()
        self.failIf(view.errors)
        self.failIf(view.success)

    def test_POST(self):
        from schooltool.app import Person, Section
        self.app['persons']['person'] = Person('person', 'Some person')
        self.app['sections']['s'] = Section('staff')
        tt_csv = StringIO('"fall","three-day"')
        roster = StringIO('staff\nSome person')
        view = self.createView(form={'timetable.csv': tt_csv,
                                     'roster.txt': roster,
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.success,
                          ['timetable.csv imported successfully.',
                           'roster.txt imported successfully.'], view.errors)
        self.assertEquals(view.errors, [])

    def test_POST_empty(self):
        view = self.createView(form={'timetable.csv': '',
                                     'roster.txt': '',
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.errors, ['No data provided'])

    def test_POST_invalid_charset(self):
        tt_csv = StringIO('"A","\xff","C","D"')
        view = self.createView(form={'timetable.csv': tt_csv,
                                     'roster.txt': '',
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.errors, ["Could not convert data to Unicode"
                                        " (incorrect charset?)."])

    def test_POST_utf8(self):
        ttschema = self.app["ttschemas"][u'three-day']
        self.app["ttschemas"][u'three-day \u263b'] = ttschema
        tt_csv = StringIO('"fall","three-day \xe2\x98\xbb"')
        view = self.createView(form={'timetable.csv': tt_csv,
                                     'roster.txt': '',
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.success,
                          ['timetable.csv imported successfully.'])


class TestTimetableCSVImporter(unittest.TestCase):

    days = ("Monday", "Tuesday", "Wednesday")
    periods = ("A", "B", "C")

    def setUp(self):
        setUpRelationshipStuff()
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay
        from schooltool.timetable import Term
        from schooltool.app import SchoolToolApplication
        self.app = app = SchoolToolApplication()

        self.course = app['courses']['philosophy'] = Course(title="Philosophy")
        self.section = app['sections']['section'] = Section(title="Something")
        self.location = app['resources']['location'] = Resource("Inside")
        self.location2 = app['resources']['location2'] = Resource("Outside")

        # set a timetable schema
        ttschema = TimetableSchema(self.days)
        for day in self.days:
            ttschema[day] = TimetableSchemaDay(self.periods)
        self.app["ttschemas"]['three-day'] = ttschema

        term = Term("Summer term",
                    datetime.datetime(2004, 1, 1),
                    datetime.datetime(2004, 5, 1))
        self.app["terms"]["summer"] = term

        term2 = Term("Fall term",
                    datetime.datetime(2004, 1, 1),
                    datetime.datetime(2004, 5, 1))
        self.app["terms"]["fall"] = term2

        # add some people and groups
        for title in ['Curtin', 'Lorch', 'Guzman']:
            name = title.lower()
            self.app['persons'][name] = Person(name, title)
        for title in ['Math1', 'Math2', 'Math3',
                      'English1', 'English2', 'English3']:
            name = title.lower()
            self.app['courses'][name] = Course(title)

    def tearDown(self):
        tearDownRelationshipStuff()

    def createImporter(self, charset=None):
        from schooltool.browser.csvimport import TimetableCSVImporter
        return TimetableCSVImporter(self.app, charset=charset)

    def test_timetable_vacancies(self):
        from schooltool.timetable import Timetable, TimetableDay
        imp = self.createImporter()

        csv = dedent("""
                "summer","three-day"
                ""
                "Monday","Tuesday"
                "","A","B","C"
                "Inside","Math1|Curtin","","Math1|Curtin"
                "Outside","Math2|Lorch"
                """)
        ok = imp.importTimetable(csv)
        self.assert_(ok, imp.errors)
        section = imp.findByTitle('sections', 'Math1 - Curtin')
        tt = section.timetables['summer.three-day']
        self.assert_(list(tt['Monday']['A']))
        self.assert_(not list(tt['Monday']['B']))
        self.assert_(list(tt['Monday']['C']))

        section2 = imp.findByTitle('sections', 'Math2 - Lorch')
        tt2 = section2.timetables['summer.three-day']
        self.assert_(list(tt2['Monday']['A']))
        self.assert_(not list(tt2['Monday']['B']))
        self.assert_(not list(tt2['Monday']['C']))

    def test_timetable_functional(self):
        from schooltool.timetable import Timetable, TimetableDay
        imp = self.createImporter()

        csv = dedent("""
                "summer","three-day",,
                ,
                "Monday","Tuesday",,
                "","A","B","C",,,
                "Inside","Math1|Curtin","Math2|Guzman","Math3|Curtin",
                "Outside","English1|Lorch","English2|Lorch","English3|Lorch",,

                "Wednesday"
                "","A","B","C"
                "Outside","Math1|Curtin","Math3|Guzman",""
                "Inside","English3|Lorch","","English1|Lorch"
                """)
        success = imp.importTimetable(csv)
        self.assert_(success, imp.errors)

        # A little poking around.  We could be more comprehensive...
        section = imp.findByTitle('sections', 'English1 - Lorch')
        tt = section.timetables['summer.three-day']
        self.assert_(list(tt['Monday']['A']))
        self.assert_(not list(tt['Monday']['B']))
        self.assert_(not list(tt['Monday']['C']))
        self.assert_(not list(tt['Wednesday']['A']))
        self.assert_(not list(tt['Wednesday']['B']))
        self.assert_(list(tt['Wednesday']['C']))

    def test_parseCSVRows(self):
        # simple case
        imp = self.createImporter()
        result = imp.parseCSVRows(['"some "," stuff"', '"here"'])
        self.assertEquals(result, [["some", "stuff"], ["here"]])
        self.failIf(imp.errors.anyErrors(), imp.errors)

        # invalid CSV
        imp = self.createImporter()
        result = imp.parseCSVRows(['"invalid"', '"csv"', '"follows'])
        self.assertEquals(result, None)
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Error in timetable CSV data, line 3")

        # test conversion to unicode
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['"Weird stuff: \xe2\x98\xbb"'])
        self.failIf(imp.errors.anyErrors(), imp.errors)
        self.assertEquals(result, [[u"Weird stuff: \u263b"]])

        # test invalid charset
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['"B0rken stuff: \xe2"'])
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Conversion to unicode failed in line 1")
        self.assertEquals(result, None)

        # test string sanitization
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['', ',', '"",""', 'hi', '"some ","data"',
                                   '"two",""," \t ","elements"',
                                   '"cut","","the","tail",,,""'])
        self.failIf(imp.errors.anyErrors(), imp.errors)
        self.assertEquals(result, [[], [], [], ['hi'], ['some', 'data'],
                                   ['two', '', '', 'elements'],
                                   ['cut', '', 'the', 'tail']])

    def test_timetable_invalid(self):
        imp = self.createImporter()
        ok = imp.importTimetable('"Some"\n"invalid"\n"csv"\n"follows')
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Error in timetable CSV data, line 4")
        self.failIf(ok)

        imp = self.createImporter()
        ok = imp.importTimetable('"too","many","fields"')
        self.failIf(ok)
        self.assert_(imp.errors.generic[0].startswith("The first row of"),
                     imp.errors.generic)

        imp = self.createImporter()
        ok = imp.importTimetable('"summer","four-day"')
        self.failIf(ok)
        self.assertEquals(translate(imp.errors.generic[0]),
                          "The timetable schema four-day does not exist.")

        imp = self.createImporter()
        ok = imp.importTimetable('"winter","three-day"')
        self.failIf(ok)
        self.assertEquals(translate(imp.errors.generic[0]),
                          "The term winter does not exist.")

        csv = dedent("""
                "summer","three-day"
                ""
                "Monday","Bogus","Tuesday","Bogus","Junk"
                "","A","B","C"
                """)
        imp = self.createImporter()
        ok = imp.importTimetable(csv)
        self.failIf(ok)
        self.assertEquals(imp.errors.day_ids, ["Bogus", "Junk"])

        csv = dedent("""
                "summer","three-day"
                ""
                "Monday","Tuesday"
                "","No","A","such","B","period","No","No"
                "Inside",%s
                """ % ','.join(['"English1|Lorch"'] * 7))
        imp = self.createImporter()
        self.failIf(imp.importTimetable(csv))
        self.assertEquals(imp.errors.periods, ["No", "such", "period"])

        csv = dedent("""
                "summer","three-day"
                ""
                "Monday","Tuesday"
                "","No","A","such","B","period","No","No"
                "Inside",%s
                """ % ','.join(['"English1|Lorch"'] * 7))
        imp = self.createImporter()
        self.failIf(imp.importTimetable(csv))
        self.assertEquals(imp.errors.periods, ["No", "such", "period"])

        csv = dedent("""
                "summer","three-day"
                ""
                "Monday","Tuesday"
                "","A","B"
                "too","many","","values"
                """)
        imp = self.createImporter()
        self.failIf(imp.importTimetable(csv))
        self.assertEquals(translate(imp.errors.generic[0]),
                          "There are more records [many, , values] (line 5)"
                          " than periods [A, B].")

        csv = dedent("""
                "summer","three-day"
                ""
                "Monday","Tuesday"
                "this should be empty!","A","B","Invalid"
                """)
        imp = self.createImporter()
        self.failIf(imp.importTimetable(csv))
        self.assertEquals(translate(imp.errors.generic[0]),
                          "The first cell on the period list row"
                          " (this should be empty!) should be empty.")
        self.assertEquals(imp.errors.periods, ["Invalid"])

    def test_findByTitle(self):
        imp = self.createImporter()
        errs = []
        self.assert_(imp.findByTitle('persons', 'Lorch')
                     is self.app['persons']['lorch'])
        self.assert_(imp.findByTitle('persons', 'Missing', errs) is None)
        self.assert_(imp.findByTitle('sections', 'Foo', errs) is None)
        self.assertEquals(errs, ['Missing', 'Foo'])
        self.assertRaises(KeyError, imp.findByTitle, 'persons', 'Missing')

        new_person = self.app['persons']['new'] = Person('new', 'New guy')
        self.assert_(imp.findByTitle('persons', 'New guy') is new_person)

    def test_clearTimetables(self):
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.timetable import TimetableActivity
        tt = Timetable(['day1'])
        ttday = tt['day1'] = TimetableDay(['A', 'B'])
        ttday.add('A', TimetableActivity(title="Sleeping"))
        ttday.add('B', TimetableActivity(title="Snoring"))
        self.section.timetables['term1.some_schema'] = tt

        tt2 = Timetable(['day2'])
        tt2day = tt2['day2'] = TimetableDay(['A', 'B'])
        tt2day.add('A', TimetableActivity(title="Working"))
        self.section.timetables['term2.some_schema'] = tt2

        imp = self.createImporter()
        imp.term_id = 'term1'
        imp.ttschema = 'some_schema'
        imp.clearTimetables()

        tt_notblank = self.section.timetables['term2.some_schema']
        self.assert_(('term1.some_schema')
                     not in self.section.timetables.keys())
        self.assertEquals(len(list(tt_notblank.itercontent())), 1)

    def test_scheduleClass(self):
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay

        math101 = self.app['courses']['math101'] = Course(title='Math 101')
        teacher = Person('teacher', 'Prof. Bar')
        self.app['persons']['teacher'] = teacher

        imp = self.createImporter()
        imp.ttname = 'tt'
        imp.ttschema = 'two_day'
        imp.term_id = 'term1'
        ttschema = TimetableSchema(("day1", "day2"))
        ttschema["day1"] = TimetableSchemaDay(("A", "B"))
        ttschema["day2"] = TimetableSchemaDay(("A", "B"))
        self.app["ttschemas"]['two_day'] = ttschema

        imp.scheduleClass('A', 'Math 101', 'Prof. Bar',
                          day_ids=['day1', 'day2'], location='Inside',
                          dry_run=True)
        self.failIf(imp.errors.anyErrors(), imp.errors)
        self.assertRaises(KeyError, imp.findByTitle,
                          'sections', 'Math 101 - Prof. Bar')

        imp.scheduleClass('A', 'Math 101', 'Prof. Bar',
                          day_ids=['day1', 'day2'], location='Inside')

        section = imp.findByTitle('sections', 'Math 101 - Prof. Bar')
        self.assertIsRelated(section, math101, rel=URISectionOfCourse)
        self.assertIsRelated(section, teacher, rel=URISection)

        tt = section.timetables['term1.two_day']
        activities = list(tt.itercontent())
        self.assertEquals(len(activities), 2)
        for day_id, term_id, activity in activities:
            self.assertEquals(activity.title, 'Math 101')
            self.assert_(activity.owner is section)
            self.assertEquals(list(activity.resources), [self.location])
            self.assert_(activity.timetable is tt)

        new_section = Section(title='Math 101 - Lorch')
        self.app['sections']['g1'] = new_section
        imp.scheduleClass('A', 'Math 101', 'Lorch',
                          day_ids=['day1', 'day2'], location='Inside')
        self.assertIsRelated(new_section, self.app['persons']['lorch'],
                             rel=URISection)

    def test_scheduleClass_errors(self):
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay

        math101 = self.app['courses']['math101'] = Course(title='Math 101')

        imp = self.createImporter()
        imp.ttname = 'tt'
        imp.ttschema = 'two_day'
        imp.term_id = 'term1'
        imp.ttschema = TimetableSchema(("day1", "day2"))
        imp.ttschema["day1"] = TimetableSchemaDay(("A", "B"))
        imp.ttschema["day2"] = TimetableSchemaDay(("A", "B"))

        imp.scheduleClass('A', 'Invalid course', 'Dumb professor',
                          day_ids=['day1', 'day2'], location='Nowhere')
        self.assertEquals(list(imp.errors.persons), ['Dumb professor'])
        self.assertEquals(list(imp.errors.courses), ['Invalid course'])
        self.assertEquals(list(imp.errors.locations), ['Nowhere'])

    def test_parseRecordRow(self):
        imp = self.createImporter()

        for row, expected in [
                 ([], []),
                 (["Math|Whiz", "Comp|Geek"],
                  [("Math", "Whiz"), ("Comp", "Geek")]),
                 (["Math |  Long  Name  ", " Comp|Geek "],
                  [("Math", "Long  Name"), ("Comp", "Geek")]),
                 (["Biology|Nut", None, "Chemistry|Nerd"],
                  [("Biology", "Nut"), None, ("Chemistry", "Nerd")])]:
            self.assertEquals(imp.parseRecordRow(row), expected)
            self.failIf(imp.errors.anyErrors(), imp.errors)

        self.assertEquals(imp.parseRecordRow(
                ["B0rk", "Good | guy", "Wank", "B0rk"]),
                [None, ("Good", "guy"), None, None])
        self.assertEquals(imp.errors.records, ["B0rk", "Wank"])

    def assertIsRelated(self, obj, group, expected=True, rel=URIMember):
        from schoolbell.relationship import getRelatedObjects
        related = getRelatedObjects(group, rel)
        self.assertEquals(obj in related, expected,
                          "%r %sin %r (%r)" % (obj, expected and "not " or "",
                                               related, rel))

    def test_importRoster(self):
        from schooltool.app import Course, Section
        course = self.app['courses']['math'] = Course()
        g1 = self.app['sections']['g1'] = Section(title="Math1 - Lorch")
        g2 = self.app['sections']['g2'] = Section(title="Math2 - Guzman")
        course.sections.add(g1)
        course.sections.add(g2)

        roster = dedent("""
            Math1 - Lorch
            Guzman
            Curtin

            Math2 - Guzman
            Lorch
            Curtin
            """)
        imp = self.createImporter()
        ok = imp.importRoster(roster)
        self.assert_(ok, imp.errors)

        for name, group, expected in [('lorch', g1, False),
                                      ('guzman', g1, True),
                                      ('curtin', g1, True),
                                      ('lorch', g2, True),
                                      ('guzman', g2, False),
                                      ('curtin', g2, True)]:
            self.assertIsRelated(self.app['persons'][name], group, expected)

    def test_importRoster_errors(self):
        g2 = self.app['sections']['s'] = Section(title="Math2 - Guzman")
        self.assertIsRelated(self.app['persons']['curtin'], g2, False)
        roster = dedent("""
            Nonexistent section
            Guzman
            Curtin

            Math2 - Guzman
            Bogus person
            Curtin
            Lorch
            """)
        imp = self.createImporter()
        self.failIf(imp.importRoster(roster))
        self.assertIsRelated(self.app['persons']['curtin'], g2, False)
        self.assertEquals(imp.errors.sections, ['Nonexistent section'])
        self.assertEquals(imp.errors.persons, ['Bogus person'])
        self.assertEquals(imp.errors.generic, [])


def doctest_CourseCSVImporter():
    r"""Tests for CourseCSVImporter.

    Create a course container and an importer

        >>> from schooltool.browser.csvimport import CourseCSVImporter
        >>> from schooltool.app import CourseContainer
        >>> container = CourseContainer()
        >>> importer = CourseCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Course 1, Course 1 Description
        ... Course2
        ... Course3, Course 3 Description, Some extra data'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the courses exist

        >>> [course for course in container]
        [u'course-1', u'course2', u'course3']

    Check that descriptions were imported properly

        >>> [course.description for course in container.values()]
        ['Course 1 Description', '', 'Course 3 Description']

    """


def doctest_CourseCSVImportView():
    r"""
    We'll create a course csv import view

        >>> from schooltool.browser.csvimport import CourseCSVImportView
        >>> from schooltool.app import CourseContainer
        >>> from zope.publisher.browser import TestRequest
        >>> container = CourseContainer()
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : "A Course, The best Course\nAnother Course",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> [course for course in container]
        [u'a-course', u'another-course']

    If no data is provided, we naturally get an error

        >>> request.form = {'charset' : 'UTF-8', 'UPDATE_SUBMIT': 1}
        >>> view.update()
        >>> view.errors
        [u'No data provided']

    We also get an error if a line starts with a comma (no title)

        >>> request.form = {'csvtext' : ", No title provided here",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = CourseCSVImportView(container, request)
        >>> view.update()
        >>> view.errors
        [u'Failed to import CSV text', u'Titles may not be empty']

    """


def doctest_GroupCSVImporter():
    r"""Tests GroupCSVImporter to make sure we're generating Schooltool objects

    Create a group container and an importer

        >>> from schooltool.browser.csvimport import GroupCSVImporter
        >>> from schooltool.app import GroupContainer
        >>> from schooltool.interfaces import IGroup
        >>> container = GroupContainer()
        >>> importer = GroupCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Group 1, Group 1 Description
        ... Group2
        ... Group3, Group 3 Description, Some extra data'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the groups are schooltool groups

        >>> for group in container.values():
        ...     verifyObject(IGroup, group)
        True
        True
        True

    """


def doctest_GroupCSVImportView():
    r"""Tests for GroupCSVImportView

    We'll create a group csv import view

        >>> from schooltool.browser.csvimport import GroupCSVImportView
        >>> from schooltool.app import GroupContainer
        >>> from schooltool.interfaces import IGroup
        >>> from zope.publisher.browser import TestRequest
        >>> container = GroupContainer()
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : "A Group, The best Group\nAnother Group",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = GroupCSVImportView(container, request)
        >>> view.update()
        >>> [verifyObject(IGroup, group) for group in container.values()]
        [True, True]

    """


def doctest_ResourceCSVImporter():
    r"""Tests ResourceCSVImporter for generating Schooltool objects

    Create a resource container and an importer

        >>> from schooltool.browser.csvimport import ResourceCSVImporter
        >>> from schooltool.app import ResourceContainer
        >>> from schooltool.interfaces import IResource
        >>> container = ResourceContainer()
        >>> importer = ResourceCSVImporter(container, None)

    Import some sample data

        >>> csvdata='''Resource 1, Resource 1 Description
        ... Resource2
        ... Resource3, Resource 3 Description, Some extra data'''
        >>> importer.importFromCSV(csvdata)
        True

    Check that the resources are schooltool resources

        >>> for resource in container.values():
        ...     verifyObject(IResource, resource)
        True
        True
        True

    """


def doctest_ResourceCSVImportView():
    r"""Tests for ResourceCSVImportView

    We'll create a resource csv import view

        >>> from schooltool.browser.csvimport import ResourceCSVImportView
        >>> from schooltool.app import ResourceContainer
        >>> from schooltool.interfaces import IResource
        >>> from zope.publisher.browser import TestRequest
        >>> container = ResourceContainer()
        >>> request = TestRequest()

    Now we'll try a text import.  Note that the description is not required

        >>> request.form = {'csvtext' : "A Resource, The best Resource\nAnother Resource",
        ...                 'charset' : 'UTF-8',
        ...                 'UPDATE_SUBMIT': 1}
        >>> view = ResourceCSVImportView(container, request)
        >>> view.update()
        >>> for resource in container.values():
        ...     verifyObject(IResource, resource)
        True
        True

    """

def doctest_PersonCSVImporter():
    r"""Tests for PersonCSVImporter.

    Create a person container and an importer

        >>> from schooltool.browser.csvimport import PersonCSVImporter
        >>> from schooltool.app import PersonContainer
        >>> container = PersonContainer()
        >>> importer = PersonCSVImporter(container, None)

    Import a user and verify that it worked

        >>> importer.createAndAdd([u'joe', u'Joe Smith'], False)
        >>> [p for p in container]
        [u'joe']

    Import a user with a password and verify it

        >>> importer.createAndAdd([u'jdoe', u'John Doe', u'monkey'], False)
        >>> container['jdoe'].checkPassword('monkey')
        True

    Some basic data validation exists.  Note that the errors are cumulative
    between calls on an instance.

        >>> importer.createAndAdd([], False)
        >>> importer.errors.fields
        [u'Insufficient data provided.']
        >>> importer.createAndAdd([u'', u'Jim Smith'], False)
        >>> importer.errors.fields
        [u'Insufficient data provided.', u'username may not be empty']
        >>> importer.createAndAdd([u'user', u''], False)
        >>> importer.errors.fields
        [u'Insufficient data provided.', u'username may not be empty', u'fullname may not be empty']

    Let's clear the errors and review the contents of the container

        >>> importer.errors.fields = []
        >>> [p for p in container]
        [u'jdoe', u'joe']

    Now we'll try to add another 'jdoe' username.  In this case the error
    message contains a translated variable, so we need zope.i18n.translate to
    properly demonstrate it.

        >>> from zope.i18n import translate
        >>> importer.createAndAdd([u'jdoe', u'Jim Doe'], False)
        >>> [translate(error) for error in importer.errors.fields]
        [u'Duplicate username: jdoe, Jim Doe']

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableCSVImportView))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImporter))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
