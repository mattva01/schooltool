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
Unit tests for schooltool.app.browser.csvimport

$Id$
"""
import unittest
import datetime
from logging import INFO
from StringIO import StringIO

from zope.i18n import translate
from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import ztapi

from schooltool.app.browser.testing import setUp as testSetUp, tearDown
from schooltool.app.membership import URIMember
from schooltool.resource.resource import Resource
from schooltool.person.person import Person
from schooltool.group.group import Group
from schooltool.testing import setup

from schooltool.app.browser.csvimport import InvalidCSVError
from schooltool.common import dedent
from schooltool.course.course import Course
from schooltool.course.section import Section
from schooltool.app.relationships import URISection, URISectionOfCourse
from schooltool.timetable.interfaces import ITimetables

__metaclass__ = type


def setUp(test=None):
    testSetUp(test)

    from zope.app.annotation.interfaces import IAttributeAnnotatable
    from schooltool.timetable import TimetablesAdapter
    ztapi.provideAdapter(IAttributeAnnotatable, ITimetables,
                         TimetablesAdapter)


class TestTimetableCSVImportView(unittest.TestCase):

    def setUp(self):
        setUp()
        self.app = setup.setupSchoolToolSite()

        from schooltool.timetable import TimetableSchema, TimetableSchemaDay
        ttschema = TimetableSchema(["1","2","3"])
        for day in range(1, 4):
            ttschema[str(day)] = TimetableSchemaDay([str(day)])
        self.app['ttschemas']['three-day'] = ttschema

        from schooltool.timetable import Term
        self.app['terms']['fall'] = Term("Fall term",
                                         datetime.datetime(2004, 1, 1),
                                         datetime.datetime(2004, 5, 1))

    def tearDown(self):
        tearDown()

    def createView(self, form=None):
        from schooltool.app.browser.csvimport import TimetableCSVImportView
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

    def test_POST_csvfile(self):
        tt_csv_text = '"fall","three-day"\n""\n""'
        tt_csv = StringIO(tt_csv_text)
        view = self.createView(form={'csvfile': tt_csv,
                                     'csvtext': tt_csv_text,
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.success,
                          ["CSV file imported successfully.",
                           "CSV text imported successfully."],
                          view.errors)
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
        view = self.createView(form={'csvfile': tt_csv,
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.errors, ["Could not convert data to Unicode"
                                        " (incorrect charset?)."])

    def test_POST_utf8(self):
        ttschema = self.app["ttschemas"][u'three-day']
        self.app["ttschemas"][u'three-day \u263b'] = ttschema
        tt_csv = StringIO('"fall","three-day \xe2\x98\xbb"\n""\n""')
        view = self.createView(form={'csvfile': tt_csv,
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.success, ['CSV file imported successfully.'])


class TestTimetableCSVImporter(unittest.TestCase):

    days = ("Monday", "Tuesday", "Wednesday")
    periods = ("A", "B", "C")

    def setUp(self):
        setUp()

        # Set up a name chooser to pick names for new sections.
        from schooltool.course.interfaces import ISectionContainer
        from schooltool.app.app import SimpleNameChooser
        from zope.app.container.interfaces import INameChooser
        ztapi.provideAdapter(ISectionContainer, INameChooser,
                             SimpleNameChooser)

        self.app = app = setup.setupSchoolToolSite()

        self.course = app['courses']['philosophy'] = Course(title="Philosophy")
        self.section = app['sections']['section'] = Section(title="Something")
        self.location = app['resources']['location'] = Resource("Inside")
        self.location2 = app['resources']['location2'] = Resource("Outside")

        # set a timetable schema
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay
        ttschema = TimetableSchema(self.days)
        for day in self.days:
            ttschema[day] = TimetableSchemaDay(self.periods)
        self.app["ttschemas"]['three-day'] = ttschema

        from schooltool.timetable import Term
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
        tearDown()

    def createImporter(self, term=None, ttschema=None, charset=None):
        from schooltool.app.browser.csvimport import TimetableCSVImporter
        importer = TimetableCSVImporter(self.app['sections'], charset=charset)
        if term is not None:
            importer.term = self.app['terms'][term]
        if ttschema is not None:
            importer.ttschema = self.app['ttschemas'][ttschema]
        return importer

    def test_importSections(self):
        imp = self.createImporter()

        log = []
        imp.importHeader = lambda row: log.append(('header', row))
        imp.importChunks = lambda row, dry_run: \
                                    log.append(('chunks', row, dry_run))

        sections_csv = '"1"\n""\n"3"\n"4"\n'
        imp.importSections(sections_csv)
        self.assertEquals(log,
                          [('header', ['1']),
                           ('chunks', [['3'], ['4']], True),
                           ('chunks', [['3'], ['4']], False)])

    def test_importSections_errors(self):
        # empty CSV
        imp = self.createImporter()
        self.assertRaises(InvalidCSVError, imp.importSections, '')
        self.assertEquals(translate(imp.errors.generic[0]),
                          "No data provided")

        self.assertRaises(InvalidCSVError, imp.importSections, '"foo"')
        self.assertEquals(translate(imp.errors.generic[0]),
                          "No data provided")

        # invalid CSV
        imp = self.createImporter()
        self.assertRaises(InvalidCSVError, imp.importSections,
                          '\n'.join(['"invalid"', '"csv"', '"follows']))
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Error in timetable CSV data, line 3")

        # Data on second line
        imp = self.createImporter()
        self.assertRaises(InvalidCSVError, imp.importSections,
                          '\n'.join(['"ok"', '"not here!"', '"ok"']))
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Row 2 is not empty")

        def b0rker(*args, **kwarsg): imp.errors.anyErrors = lambda: True
        def k1ller(*args, **kwarsg): raise InvalidCSVError()
        def w1nner(*args, **kwarsg): return [1, 2, 3]

        imp.parseCSVRows = k1ller
        self.assertRaises(InvalidCSVError, imp.importSections, '\n')
        imp.errors.anyErrors = lambda: False

        imp.parseCSVRows = w1nner
        imp.importHeader = b0rker
        self.assertRaises(InvalidCSVError, imp.importSections, '\n')
        imp.errors.anyErrors = lambda: False

        imp.importHeader = w1nner
        imp.importChunks = b0rker
        self.assertRaises(InvalidCSVError, imp.importSections, '\n')

    def test_importSections_functional(self):
        imp = self.createImporter()
        data = dedent("""\
            "summer","three-day"
            "","",""
            "philosophy","lorch"
            "Monday","A","location"
            "Monday","B"
            "Tuesday","C","location2"
            "***"
            "guzman"
            "curtin"
            ""
            "philosophy","guzman",""
            "Wednesday","B",""
            "Wednesday","C","location2"
            "***"
            "curtin"
            "lorch"
        """)
        imp.importSections(data)

        # Let's do a little snooping around.  We don't have to be very
        # verbose as this test mostly checks integration; the components
        # are tested well individually.

        persons = self.app['persons']
        sections = self.app['sections']

        # Check out the created sections.
        philosophy_lorch = sections['philosophy--lorch']
        philosophy_guzman = sections['philosophy--guzman']

        self.assertEquals(list(philosophy_lorch.instructors),
                          [persons['lorch']])
        self.assert_(persons['guzman'] in philosophy_lorch.members)
        self.assert_(persons['curtin'] in philosophy_lorch.members)
        self.assert_(persons['lorch'] not in philosophy_lorch.members)

        self.assertEquals(list(philosophy_guzman.instructors),
                          [persons['guzman']])
        self.assert_(persons['guzman'] not in philosophy_guzman.members)
        self.assert_(persons['curtin'] in philosophy_guzman.members)
        self.assert_(persons['lorch'] in philosophy_guzman.members)

        # Look at the timetables of the sections
        lorch_tt = ITimetables(philosophy_lorch).timetables['summer.three-day']
        self.assertEquals(len(list(lorch_tt.itercontent())), 3)
        # Look at a couple of periods.
        self.assertEquals(len(lorch_tt['Monday']['B']), 1)
        self.assertEquals(len(lorch_tt['Monday']['C']), 0)

        # Look closer into an activity.
        activity = list(lorch_tt['Monday']['A'])[0]
        self.assert_(activity.owner is philosophy_lorch)
        self.assertEquals(list(activity.resources), [self.location])

        # Finally, let's make sure that we can import the same data
        # several times without crashing.
        imp.importSections(data)

    def test_importHeader(self):
        # too many fields on first row
        imp = self.createImporter()
        imp.importHeader(["too", "many", "fields"])
        self.assertEquals(translate(imp.errors.generic[0]),
                          "The first row of the CSV file must contain"
                          " the term id and the timetable schema id.")

        # nonexistent term
        imp = self.createImporter()
        imp.importHeader(["winter", "three-day"])
        self.assertEquals(translate(imp.errors.generic[0]),
                          "The term winter does not exist.")

        # nonexistent timetable schema
        imp = self.createImporter()
        imp.importHeader(["summer", "four-day"])
        self.assertEquals(translate(imp.errors.generic[0]),
                          "The timetable schema four-day does not exist.")

    def test_importChunks(self):
        lines = [[]]
        imp = self.createImporter()

        importchunk_calls = []
        def importChunkStub(rows, line, dry_run=True):
            importchunk_calls.append((rows, line, dry_run))
        imp.importChunk = importChunkStub

        # no input
        # TODO we might want to raise an error in this case
        lines = []
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls, [])
        importchunk_calls = []

        # trivial case: one single-line entry
        lines = [['hi']]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls, [([['hi']], 3, True)])
        importchunk_calls = []

        # another trivial case: one chunk
        lines = [['hi'], ['yadda'], ['yadda'], ['bye']]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls, [(lines, 3, True)])
        importchunk_calls = []

        # two one-line chunks separated by an empty line
        lines = [['hi'], [], ['bye']]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls,
                          [([['hi']], 3, True),
                           ([['bye']], 5, True)])
        importchunk_calls = []

        # two one-line chunks separated by several empty lines
        lines = [['hi'], [], [], [], ['bye']]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls,
                          [([['hi']], 3, True),
                           ([['bye']], 7, True)])
        importchunk_calls = []

        # two several-line chunks separated by several empty lines
        lines = [['hi'], ['foo'], [], [], [], ['bye'], ['really!']]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls,
                          [([['hi'], ['foo']], 3, True),
                           ([['bye'], ['really!']], 8, True)])
        importchunk_calls = []

        # leading empty lines
        lines = [[], [], [], ['hi']]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls, [([['hi']], 6, True)])
        importchunk_calls = []

        # trailing empty lines
        lines = [['hi'], [], [], []]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls, [([['hi']], 3, True)])
        importchunk_calls = []

        # several empty lines only
        # TODO we might want to raise an error in this case
        lines = [[], [], []]
        imp.importChunks(lines, dry_run=True)
        self.assertEquals(importchunk_calls, [])
        importchunk_calls = []

    def test_createSection(self):
        imp = self.createImporter(term='fall', ttschema='three-day')

        course = self.app['courses']['philosophy']
        instructor = self.app['persons']['lorch']
        periods = [('Monday', 'A', self.location),
                   ('Tuesday', 'C', None)]

        # dry run
        section = imp.createSection(course, instructor,
                                    periods=periods, dry_run=True)
        self.assert_(section is None)

        # real run
        section = imp.createSection(course, instructor,
                                    periods=periods, dry_run=False)

        # Check name
        self.assertEquals(section.__name__, 'philosophy--lorch')

        # Check links
        self.assert_(course in section.courses)
        self.assert_(instructor in section.instructors)

        # Check timetable
        tt = ITimetables(section).timetables['fall.three-day']
        self.assertEquals(len(list(tt.itercontent())), 2)

        # Check activities in timetable
        acts = tt['Monday']['A']
        self.assertEquals(len(acts), 1)
        act = list(acts)[0]
        self.assertEquals(act.title, course.title)
        self.assert_(act.owner is section)
        self.assertEquals(list(act.resources), [self.location])
        self.assert_(act.timetable is tt)

        acts = tt['Tuesday']['C']
        self.assertEquals(len(acts), 1)
        act = list(acts)[0]
        self.assertEquals(act.title, course.title)
        self.assert_(act.owner is section)
        self.assertEquals(list(act.resources), [])

        # If the same data is imported a second time, nothing should change.
        section2 = imp.createSection(course, instructor,
                                     periods=periods, dry_run=False)
        self.assert_(section2 is section)
        self.assert_(ITimetables(section).timetables['fall.three-day'] is tt)
        self.assertEquals(len(list(tt.itercontent())), 2)

    def test_createSection_existing(self):
        imp = self.createImporter(term='fall', ttschema='three-day')

        course = self.app['courses']['philosophy']
        instructor = self.app['persons']['lorch']
        periods = [('Monday', 'A', self.location),
                   ('Tuesday', 'C', None)]

        title = 'Philosophy - Lorch'
        section = self.app['sections']['oogabooga'] = Section(title=title)
        tt = imp.ttschema.createTimetable()
        ITimetables(section).timetables['fall.three-day'] = tt

        # real run
        section2 = imp.createSection(course, instructor,
                                     periods=periods, dry_run=False)

        self.assert_(section is section2)
        self.assert_(ITimetables(section).timetables['fall.three-day'] is tt)

    def test_importChunk(self):
        imp = self.createImporter(term='fall', ttschema='three-day')

        lines = [['philosophy', 'curtin'],
                 ['Monday', 'A', 'location'],
                 ['Wednesday', 'B'],
                 ['***'],
                 ['lorch'],
                 ['guzman']]

        imp.importChunk(lines, 5, dry_run=False)
        self.failIf(imp.errors.anyErrors(), imp.errors)

        philosophy_curtin = self.app['sections']['philosophy--curtin']
        tt = ITimetables(philosophy_curtin).timetables['fall.three-day']
        activities = list(tt.itercontent())
        self.assertEquals(len(activities), 2)

        # Let's stub out createSection and importPersons and make sure that the
        # right arguments are passed.
        imp = self.createImporter(term='fall', ttschema='three-day')
        section_log = []
        stub_section = self.section
        def createSectionStub(course, instructor, periods, dry_run=True):
            section_log.append((course, instructor, periods, dry_run))
            return stub_section
        imp.createSection = createSectionStub
        persons_log  = []
        def importPersonsStub(person_data, section, dry_run=True):
            persons_log.append((person_data, section, dry_run))
        imp.importPersons = importPersonsStub

        # invoke the method
        imp.importChunk(lines, 5, dry_run=False)
        self.failIf(imp.errors.anyErrors(), imp.errors)

        # check the logs
        philosophy = self.course
        curtin = self.app['persons']['curtin']
        expected_periods = [('Monday', 'A', self.location),
                            ('Wednesday', 'B', None)]
        self.assertEquals(section_log,
                          [(philosophy, curtin, expected_periods, False)])
        lines_expected = [['lorch'], ['guzman']]
        self.assertEquals(persons_log, [(lines_expected, stub_section, False)])

    def test_importChunk_errors_top(self):
        # only provide the top row
        lines = [['relativity_theory', 'einstein']]
        imp = self.createImporter()
        imp.importChunk(lines, line=5)
        self.assertEquals(imp.errors.courses, ['relativity_theory'])
        self.assertEquals(imp.errors.persons, ['einstein'])
        self.assertEquals(translate(imp.errors.generic[0]),
                          'Incomplete section description on line 5')

    def test_importChunk_errors_period(self):
        # provide a row for a period too
        lines = [['relativity_theory', 'einstein'],
                 ['day x', 'period y', 'location z']]
        imp = self.createImporter(term='fall', ttschema='three-day')
        imp.importChunk(lines, line=5)
        self.assertEquals(imp.errors.day_ids, ['day x'])
        self.assertEquals(imp.errors.periods, [])
        self.assertEquals(imp.errors.locations, ['location z'])
        self.assertEquals(translate(imp.errors.generic[0]),
                          'Incomplete section description on line 5')

    def test_importChunk_errors_wrong_period_descr(self):
        # miss out on the period id
        lines = [['relativity_theory', 'einstein'],
                 ['Monday'],
                 ['Saturday', 'is', 'my', 'favourite', 'day']]
        imp = self.createImporter(term='fall', ttschema='three-day')
        imp.importChunk(lines, line=5)
        self.assertEquals(translate(imp.errors.generic[0]),
                          'Malformed line 6 (it should contain a day id,'
                          ' a period id and optionally a location id)')
        self.assertEquals(translate(imp.errors.generic[1]),
                          'Malformed line 7 (it should contain a day id,'
                          ' a period id and optionally a location id)')

    def test_importChunk_errors_persons(self):
        # an extra row for a period and a terminator -- the section is still
        # malformed
        lines = [['relativity_theory', 'einstein'],
                 ['day x', 'ZZZ', 'Moon'],
                 ['Tuesday', 'ZZZ', 'Moon'],
                 ['***']]
        imp = self.createImporter(term='fall', ttschema='three-day')
        imported_person_data = []
        def importPersonsStub(person_data, section, dry_run):
            imported_person_data.append((person_data, section, dry_run))
        imp.importPersons = importPersonsStub

        imp.importChunk(lines, line=5)
        self.assertEquals(imp.errors.day_ids, ['day x'])
        self.assertEquals(imp.errors.periods, ['ZZZ'])
        self.assertEquals(imp.errors.locations, ['Moon'])
        self.assertEquals(translate(imp.errors.generic[0]),
                          'Incomplete section description on line 5')
        # importPersons did not get called
        self.assertEquals(imported_person_data, [])

        # add a bogus person, and importPersons will get called
        lines.append(['bogus_person', 'extra', 'stuff'])
        imp = self.createImporter(term='fall', ttschema='three-day')
        imp.importPersons = importPersonsStub
        imp.importChunk(lines, line=5)
        self.assertEquals(imported_person_data,
                          [([['bogus_person', 'extra', 'stuff']], None, True)])

    def test_importPersons(self):
        imp = self.createImporter(term='fall', ttschema='three-day')
        lines = [['curtin'], ['lorch']]
        imp.importPersons(lines, self.section, dry_run=False)
        self.failIf(imp.errors.anyErrors(), imp.errors)

        persons = self.app['persons']
        self.assert_(persons['curtin'] in self.section.members)
        self.assert_(persons['lorch'] in self.section.members)
        self.assert_(persons['guzman'] not in self.section.members)

        # Try the same import a second time.
        imp.importPersons(lines, self.section, dry_run=False)
        self.failIf(imp.errors.anyErrors(), imp.errors)

        self.assert_(persons['curtin'] in self.section.members)
        self.assert_(persons['lorch'] in self.section.members)
        self.assert_(persons['guzman'] not in self.section.members)

    def test_importPersons_errors(self):
        lines = [['007'], # nonexistent person
                 ['curtin'],
                 ['007'], # duplicate
                 ['008']]
        imp = self.createImporter(term='fall', ttschema='three-day')
        imp.importPersons(lines, None, dry_run=True)
        self.assertEquals(imp.errors.generic, [])
        self.assertEquals(imp.errors.persons, ['007', '008'])

    def test_parseCSVRows(self):
        # simple case
        imp = self.createImporter()
        result = imp.parseCSVRows(['"some "," stuff"', '"here"'])
        self.assertEquals(result, [["some", "stuff"], ["here"]])
        self.failIf(imp.errors.anyErrors(), imp.errors)

        # invalid CSV
        imp = self.createImporter()
        self.assertRaises(InvalidCSVError,
                          imp.parseCSVRows, ['"invalid"', '"csv"', '"follows'])
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Error in timetable CSV data, line 3")

        # test conversion to unicode
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['"Weird stuff: \xe2\x98\xbb"'])
        self.assertEquals(result, [[u"Weird stuff: \u263b"]])

        # test invalid charset
        imp = self.createImporter(charset='UTF-8')
        self.assertRaises(InvalidCSVError,
                          imp.parseCSVRows, ['"B0rken stuff: \xe2"'])
        self.assertEquals(translate(imp.errors.generic[0]),
                          "Conversion to unicode failed in line 1")

        # test string sanitization
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['', ',', '"",""', 'hi', '"some ","data"',
                                   '"two",""," \t ","elements"',
                                   '"cut","","the","tail",,,""'])
        self.failIf(imp.errors.anyErrors(), imp.errors)
        self.assertEquals(result, [[], [], [], ['hi'], ['some', 'data'],
                                   ['two', '', '', 'elements'],
                                   ['cut', '', 'the', 'tail']])


def doctest_PersonCSVImporter():
    r"""Tests for PersonCSVImporter.

    Create a person container and an importer

        >>> from schooltool.app.browser.csvimport import PersonCSVImporter
        >>> from schooltool.person.person import PersonContainer
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
