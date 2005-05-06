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
from zope.publisher.browser import TestRequest
from schooltool.common import dedent
from schooltool.app import Person, Group, Resource
from schooltool.relationships import URISection
from schoolbell.app.membership import URIMember
from schoolbell.relationship.tests import setUp as setUpRelationshipStuff
from schoolbell.relationship.tests import tearDown as tearDownRelationshipStuff

__metaclass__ = type


#class TestCharsetMixin(unittest.TestCase):
#
#    def createMixin(self):
#        from schooltool.browser.csvimport import CharsetMixin
#        return CharsetMixin(None)
#
#    def test_getCharset(self):
#        mixin = self.createMixin()
#
#        request = TestRequest(args={'charset': 'UTF-8',
#                                    'other_charset': ''})
#        self.assertEquals(mixin.getCharset(request), 'UTF-8')
#
#        request = TestRequest(args={'charset': '',
#                                    'other_charset': 'ISO-8859-1'})
#        self.assertEquals(mixin.getCharset(request), 'ISO-8859-1')
#
#        self.assertRaises(ValueError, mixin.getCharset,
#                          RequestStub(args={'charset': 'bogus-charset',
#                                            'other_charset': 'UTF-8'}))
#        self.assertRaises(ValueError, mixin.getCharset,
#                          RequestStub(args={'charset': '',
#                                            'other_charset': 'bogus-charset'}))


class TestTimetableCSVImportView(unittest.TestCase):

    def setUp(self):
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.app import SchoolToolApplication
        setUpRelationshipStuff()
        self.app = SchoolToolApplication()

        ttschema = Timetable(["1","2","3"])
        for day in range(1, 4):
            ttschema[str(day)] = TimetableDay([str(day)])
        self.app.timetableSchemaService['three-day'] = ttschema

    def tearDown(self):
        tearDownRelationshipStuff()

    def createView(self, form=None):
        from schooltool.browser.csvimport import TimetableCSVImportView
        if form is None:
            form = {}
        request = TestRequest(form=form)
        return TimetableCSVImportView(self.app, request)

    def test_dummy_update(self):
        view = self.createView()
        view.update()
        self.failIf(view.errors)
        self.failIf(view.success)

    def test_POST(self):
        from schooltool.app import Person
        self.app['persons']['person'] = Person('person', 'Some person')
        tt_csv = StringIO('"fall","three-day"')
        roster = StringIO('staff\nSome person')
        view = self.createView(form={'timetable.csv': tt_csv,
                                     'roster.txt': roster,
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.success,
                          ['timetable.csv imported successfully.',
                           'roster.txt imported successfully.'])
        self.assertEquals(view.errors, [])

#        self.assertEquals(request.applog,
#                  [(self.manager, u'School timetable imported', INFO),
#                   (self.manager, u'School timetable roster imported', INFO)])

    def test_POST_empty(self):
        view = self.createView(form={'timetable.csv': '',
                                     'roster.txt': '',
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.errors, ['No data provided'])

#        self.assertEquals(view.request.applog, [])

#    def test_POST_invalid_charset(self):
#        view = self.createView()
#        view.request = RequestStub(args={'timetable.csv':'"A","\xff","C","D"',
#                                         'roster.txt': '',
#                                         'charset': 'UTF-8'})
#        content = view.do_POST(view.request)
#        self.assert_('incorrect charset' in content)
#        self.assertEquals(view.request.applog, [])

    def test_POST_utf8(self):
        ttschema = self.app.timetableSchemaService[u'three-day']
        self.app.timetableSchemaService[u'three-day \u263b'] = ttschema
        tt_csv = StringIO('"whatever","three-day \xe2\x98\xbb"')
        view = self.createView(form={'timetable.csv': tt_csv,
                                     'roster.txt': '',
                                     'charset': 'UTF-8',
                                     'UPDATE_SUBMIT': 'Submit'})
        view.update()
        self.assertEquals(view.success,
                          ['timetable.csv imported successfully.'])
#        self.assertEquals(view.request.applog,
#                          [(None, u'School timetable imported', INFO)])


class TestTimetableCSVImporter(unittest.TestCase):

    days = ("Monday", "Tuesday", "Wednesday")
    periods = ("A", "B", "C")

    def setUp(self):
        setUpRelationshipStuff()
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool.app import SchoolToolApplication
        self.app = app = SchoolToolApplication()

        self.pupils = app['groups']['pupils'] = Group(title="Pupils")
        self.location = app['resources']['location'] = Resource("Inside")
        self.location2 = app['resources']['location2'] = Resource("Outside")

        # set a timetable schema
        ttschema = Timetable(self.days)
        for day in self.days:
            ttschema[day] = TimetableDay(self.periods)
        self.app.timetableSchemaService['three-day'] = ttschema

        # add some people and groups
        for title in ['Curtin', 'Lorch', 'Guzman']:
            name = title.lower()
            self.app['persons'][name] = Person(name, title)
        for title in ['Math1', 'Math2', 'Math3',
                      'English1', 'English2', 'English3']:
            name = title.lower()
            self.app['groups'][name] = Group(title)

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
        group = imp.findByTitle('groups', 'Math1 - Curtin')
        tt = group.timetables['summer', 'three-day']
        self.assert_(list(tt['Monday']['A']))
        self.assert_(not list(tt['Monday']['B']))
        self.assert_(list(tt['Monday']['C']))

        group2 = imp.findByTitle('groups', 'Math2 - Lorch')
        tt2 = group2.timetables['summer', 'three-day']
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
        group = imp.findByTitle('groups', 'English1 - Lorch')
        tt = group.timetables['summer', 'three-day']
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
        self.assertEquals(imp.errors.generic[0],
                          "Error in timetable CSV data, line 3")

        # test conversion to unicode
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['"Weird stuff: \xe2\x98\xbb"'])
        self.failIf(imp.errors.anyErrors(), imp.errors)
        self.assertEquals(result, [[u"Weird stuff: \u263b"]])

        # test invalid charset
        imp = self.createImporter(charset='UTF-8')
        result = imp.parseCSVRows(['"B0rken stuff: \xe2"'])
        self.assertEquals(imp.errors.generic[0],
                          "Conversion to unicode failed in line 1")
        self.assertEquals(result, None)

        # test sanitization
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
        self.assertEquals(imp.errors.generic[0],
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
        self.assert_(imp.errors.generic[0].startswith(
                                "The timetable schema four-day "),
                     imp.errors.generic)

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
                "","A","B"
                "too","many","","values"
                """)
        imp = self.createImporter()
        self.failIf(imp.importTimetable(csv))
        self.assertEquals(imp.errors.generic[0],
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
        self.assertEquals(imp.errors.generic[0],
                "The first cell on the period list row"
                " (this should be empty!) should be empty.")
        self.assertEquals(imp.errors.periods, ["Invalid"])

    def test_findByTitle(self):
        imp = self.createImporter()
        errs = []
        self.assert_(imp.findByTitle('persons', 'Lorch')
                     is self.app['persons']['lorch'])
        self.assert_(imp.findByTitle('persons', 'Missing', errs) is None)
        self.assert_(imp.findByTitle('groups', 'Foo', errs) is None)
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
        self.pupils.timetables['period1', 'some_schema'] = tt

        tt2 = Timetable(['day2'])
        tt2day = tt2['day2'] = TimetableDay(['A', 'B'])
        tt2day.add('A', TimetableActivity(title="Working"))
        self.pupils.timetables['period2', 'some_schema'] = tt2

        imp = self.createImporter()
        imp.period_id = 'period1'
        imp.ttschema = 'some_schema'
        imp.clearTimetables()

        tt_notblank = self.pupils.timetables['period2', 'some_schema']
        self.assert_(('period1', 'some_schema')
                     not in self.pupils.timetables.keys())
        self.assertEquals(len(list(tt_notblank.itercontent())), 1)

    def test_scheduleClass(self):
        from schooltool.timetable import Timetable, TimetableDay

        math101 = self.app['groups']['math101'] = Group(title='Math 101')
        teacher = Person('teacher', 'Prof. Bar')
        self.app['persons']['teacher'] = teacher

        imp = self.createImporter()
        imp.ttname = 'tt'
        imp.ttschema = 'two_day'
        imp.period_id = 'period1'
        ttschema = Timetable(("day1", "day2"))
        ttschema["day1"] = TimetableDay(("A", "B"))
        ttschema["day2"] = TimetableDay(("A", "B"))
        self.app.timetableSchemaService['two_day'] = ttschema

        imp.scheduleClass('A', 'Math 101', 'Prof. Bar',
                          day_ids=['day1', 'day2'], location='Inside',
                          dry_run=True)
        self.failIf(imp.errors.anyErrors(), imp.errors)
        self.assertRaises(KeyError, imp.findByTitle,
                          'groups', 'Math 101 - Prof. Bar')

        imp.scheduleClass('A', 'Math 101', 'Prof. Bar',
                          day_ids=['day1', 'day2'], location='Inside')

        group = imp.findByTitle('groups', 'Math 101 - Prof. Bar')
        self.assertIsRelated(group, math101)
        self.assertIsRelated(group, teacher, rel=URISection)

        tt = group.timetables['period1', 'two_day']
        activities = list(tt.itercontent())
        self.assertEquals(len(activities), 2)
        for day_id, period_id, activity in activities:
            self.assertEquals(activity.title, 'Math 101')
            self.assert_(activity.owner is group)
            self.assertEquals(list(activity.resources), [self.location])
            self.assert_(activity.timetable is tt)

        new_group = self.app['groups']['g1'] = Group(title='Math 101 - Lorch')
        imp.scheduleClass('A', 'Math 101', 'Lorch',
                          day_ids=['day1', 'day2'], location='Inside')
        self.assertIsRelated(new_group, self.app['persons']['lorch'],
                             rel=URISection)

    def test_scheduleClass_errors(self):
        from schooltool.timetable import Timetable, TimetableDay

        math101 = self.app['groups']['math101'] = Group(title='Math 101')

        imp = self.createImporter()
        imp.ttname = 'tt'
        imp.ttschema = 'two_day'
        imp.period_id = 'period1'
        imp.ttschema = Timetable(("day1", "day2"))
        imp.ttschema["day1"] = TimetableDay(("A", "B"))
        imp.ttschema["day2"] = TimetableDay(("A", "B"))

        imp.scheduleClass('A', 'Invalid subject', 'Dumb professor',
                          day_ids=['day1', 'day2'], location='Nowhere')
        self.assertEquals(list(imp.errors.persons), ['Dumb professor'])
        self.assertEquals(list(imp.errors.groups), ['Invalid subject'])
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
        g1 = self.app['groups']['g1'] = Group(title="Math1 - Lorch")
        g2 = self.app['groups']['g2'] = Group(title="Math2 - Guzman")
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
        self.assert_(ok)

        for name, group, expected in [('lorch', g1, False),
                                      ('guzman', g1, True),
                                      ('curtin', g1, True),
                                      ('lorch', g2, True),
                                      ('guzman', g2, False),
                                      ('curtin', g2, True)]:
            self.assertIsRelated(self.app['persons'][name], group, expected)

    def test_importRoster_errors(self):
        g2 = self.app['groups']['g2'] = Group(title="Math2 - Guzman")
        self.assertIsRelated(self.app['persons']['curtin'], g2, False)
        roster = dedent("""
            Nonexistent group
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
        self.assertEquals(imp.errors.groups, ['Nonexistent group'])
        self.assertEquals(imp.errors.persons, ['Bogus person'])
        self.assertEquals(imp.errors.generic, [])


def test_suite():
    suite = unittest.TestSuite()
#    suite.addTest(unittest.makeSuite(TestCharsetMixin))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImportView))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImporter))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
