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
Unit tests for schooltool.browser.app

$Id$
"""

import unittest
import datetime
from logging import INFO
from schooltool.browser.tests import RequestStub
from schooltool.tests.utils import RegistriesSetupMixin, AppSetupMixin
from schooltool.common import dedent
from schooltool import uris

__metaclass__ = type


class TestCharsetMixin(unittest.TestCase):

    def createMixin(self):
        from schooltool.browser.csvimport import CharsetMixin
        return CharsetMixin(None)

    def test_getCharset(self):
        mixin = self.createMixin()

        request = RequestStub(args={'charset': 'UTF-8',
                                    'other_charset': ''})
        self.assertEquals(mixin.getCharset(request), 'UTF-8')

        request = RequestStub(args={'charset': '',
                                    'other_charset': 'ISO-8859-1'})
        self.assertEquals(mixin.getCharset(request), 'ISO-8859-1')

        self.assertRaises(ValueError, mixin.getCharset,
                          RequestStub(args={'charset': 'bogus-charset',
                                            'other_charset': 'UTF-8'}))
        self.assertRaises(ValueError, mixin.getCharset,
                          RequestStub(args={'charset': '',
                                            'other_charset': 'bogus-charset'}))


class TestCSVImportView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.browser.csvimport import CSVImportView
        from schooltool import teaching
        self.setUpSampleApp()
        teaching.setUp()

        self.view = CSVImportView(self.app)
        self.view.authorization = lambda x, y: True

    def test_render(self):
        request = RequestStub()
        content = self.view.render(request)

        self.assert_('Upload CSV' in content)

    def test_POST_empty(self):
        request = RequestStub(args={'groups.csv': '',
                                    'resources.csv': '',
                                    'persons.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('No data provided' in content)
        self.assert_('Data imported successfully' not in content)

        self.assertEquals(request.applog, [])

    def test_POST_groups(self):
        from schooltool.component import FacetManager
        from schooltool.teaching import TeacherGroupFacet
        request = RequestStub(args={'groups.csv':'"year1","Year 1","root",""',
                                    'resources.csv': '',
                                    'persons.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        self.assert_('year1' in self.app['groups'].keys())
        self.assertEquals(request.applog,
                      [(None, u'CSV data import started', INFO),
                       (None, u'Imported group: year1', INFO),
                       (None, u'CSV data import finished successfully', INFO)])

    def test_POST_groups_errors(self):
        request = RequestStub(args={'groups.csv': '"year1","b0rk',
                                    'resources.csv': '',
                                    'persons.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' not in content)
        self.assert_('Error in group data' in content)
        self.assertEquals(request.applog, [])

    def test_POST_groups_nonascii(self):
        from schooltool.component import FacetManager
        from schooltool.teaching import TeacherGroupFacet
        request = RequestStub(args={'groups.csv':
                                        '"year1","\xe2\x98\xbb","root",""',
                                    'resources.csv': '',
                                    'persons.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        self.assert_('year1' in self.app['groups'].keys())
        self.assertEquals(self.app['groups']['year1'].title, u'\u263B')
        self.assertEquals(request.applog,
                      [(None, u'CSV data import started', INFO),
                       (None, u'Imported group: year1', INFO),
                       (None, u'CSV data import finished successfully', INFO)])

    def test_POST_groups_invalid_charset(self):
        request = RequestStub(args={'groups.csv':'"year1","\xff","root",""',
                                    'resources.csv': '',
                                    'persons.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('incorrect charset' in content)
        self.assert_('Data imported successfully' not in content)
        self.assertEquals(request.applog, [])

    def test_POST_resources(self):
        request = RequestStub(args={'resources.csv':'"Stool",""',
                                    'groups.csv': '',
                                    'persons.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        titles = [resource.title
                  for resource in self.app['resources'].itervalues()]
        self.assert_('Stool' in titles)

        self.assertEquals(request.applog,
                      [(None, u'CSV data import started', INFO),
                       (None, u'Imported resource: Stool', INFO),
                       (None, u'CSV data import finished successfully', INFO)])

    def test_POST_persons(self):
        request = RequestStub(args={'persons.csv':
                                        '"ab","B","A","","1929-1-1",""',
                                    'groups.csv': '',
                                    'resources.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        titles = [resource.title
                  for resource in self.app['persons'].itervalues()]
        self.assert_('A B' in titles)
        self.assertEquals(request.applog,
           [(None, u'CSV data import started', INFO),
            (None, u'Imported person: A B', INFO),
            (None, u'Imported person info for ab (A B, 1929-01-01)', INFO),
            (None, u'CSV data import finished successfully', INFO)])


class TestCSVImporterZODB(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.browser.csvimport import CSVImporterZODB
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool import membership, teaching, relationship

        self.setUpRegistries()
        membership.setUp()
        relationship.setUp()
        teaching.setUp()

        self.groups = ApplicationObjectContainer(Group)
        self.group1 = self.groups.new(__name__='group1')
        self.group2 = self.groups.new(__name__='group2')
        self.group3 = self.groups.new(__name__='group3')
        self.root = self.groups.new(__name__='root')

        self.persons = ApplicationObjectContainer(Person)
        self.person1 = self.persons.new(__name__='person1')

        self.resources = ApplicationObjectContainer(Resource)

        self.app = Application()
        self.app['groups'] = self.groups
        self.app['persons'] = self.persons
        self.app['resources'] = self.resources

        self.im = CSVImporterZODB(self.app, 'us-ascii')

    def test_init(self):
        self.assert_(self.im.groups is self.groups)
        self.assert_(self.im.persons is self.persons)
        self.assert_(self.im.resources is self.resources)

    def test_importGroup(self):
        from schooltool.component import FacetManager
        from schooltool.teaching import TeacherGroupFacet, SubjectGroupFacet
        self.im.importGroup('gr0wl', 'A tiny group', 'group1 group2',
                            'teacher_group subject_group')
        self.assertEquals(self.im.logs, ["Imported group: gr0wl"])

        group = self.groups['gr0wl']
        self.assertEquals(group.title, 'A tiny group')

        objs = [link.target for link in group.listLinks()]
        self.assertEquals(len(objs), 2)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)

        facets = list(FacetManager(group).iterFacets())
        self.assertEquals(len(facets), 2)
        classes = [facet.__class__ for facet in facets]
        self.assert_(TeacherGroupFacet in classes)
        self.assert_(SubjectGroupFacet in classes)

    def test_importGroup_errors(self):
        from schooltool.browser.csvimport import DataError
        self.assertRaises(DataError, self.im.importGroup,
                          'gr1', 'A tiny group', 'group1 group2', 'b0rk')
        self.assertEquals(self.im.logs, [])

    def test_importPerson(self):
        name = self.im.importPerson('','Smith', 'Joe', 'group1 group2')
        self.assertEquals(self.im.logs, ["Imported person: Joe Smith"])
        person = self.persons[name]
        self.assertEquals(person.title, 'Joe Smith')

        objs = [link.target for link in person.listLinks()]
        self.assertEquals(len(objs), 3)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)
        self.assert_(self.root in objs)

    def test_importPerson_errors(self):
        from schooltool.browser.csvimport import DataError
        self.assertRaises(DataError, self.im.importPerson,
                          '', 'Smith', 'Jim', 'invalid_group')
        self.assertRaises(DataError, self.im.importPerson,
                          '', 'Smith', 'Jim', 'group1 invalid_group')

        self.assertEquals(self.im.logs, [])

    def test_importResource(self):
        name = self.im.importResource('Stool', 'group1 group2')
        self.assertEquals(self.im.logs, ["Imported resource: Stool"])
        resource = self.resources[name]
        self.assertEquals(resource.title, 'Stool')

        objs = [link.target for link in resource.listLinks()]
        self.assertEquals(len(objs), 2)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)

    def test_importResource_errors(self):
        from schooltool.browser.csvimport import DataError
        self.assertRaises(DataError, self.im.importResource,
                          'Resource', 'group1 invalid_group group2')
        self.assertEquals(self.im.logs, [])

    def test_importPersonInfo(self):
        from schooltool.component import FacetManager
        self.im.importPersonInfo('person1', 'Bayer', 'Foo',
                                 '1922-12-12', 'Wazzup?')
        self.assertEquals(self.im.logs, ["Imported person info for person1"
                                         " (Foo Bayer, 1922-12-12)"])
        info = FacetManager(self.person1).facetByName('person_info')

        self.assertEquals(info.first_name, 'Foo')
        self.assertEquals(info.last_name, 'Bayer')
        self.assertEquals(info.date_of_birth, datetime.date(1922, 12, 12))
        self.assertEquals(info.comment, 'Wazzup?')

    def test_importPersonInfo2(self):
        from schooltool.component import FacetManager
        self.im.importPersonInfo('person1','Anonymous','','1922-1-1','Wazzup?')
        self.assertEquals(self.im.logs, ["Imported person info for person1"
                                         " ( Anonymous, 1922-01-01)"])
        info = FacetManager(self.person1).facetByName('person_info')
        self.assertEquals(info.first_name, '')
        self.assertEquals(info.last_name, 'Anonymous')


class TestTimetableCSVImportView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.timetable import Timetable, TimetableDay
        self.setUpSampleApp()

        ttschema = Timetable(["1","2","3"])
        for day in range(1, 4):
            ttschema[str(day)] = TimetableDay([str(day)])
        self.app.timetableSchemaService['three-day'] = ttschema

    def createView(self):
        from schooltool.browser.csvimport import TimetableCSVImportView
        return TimetableCSVImportView(self.app)

    def test_render(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        result = view.render(request)
        self.assertEquals(request.code, 200, result)

    def test_access(self):
        view = self.createView()
        view.isManager = lambda: False
        request = RequestStub(authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 302, result)
        self.assert_('forbidden' in result)

    def test_POST(self):
        view = self.createView()

        request = RequestStub(authenticated_user=self.manager,
                              method='POST',
                              args={'timetable.csv': '"fall","three-day"',
                                    'roster.txt': 'Locations\nJohn Doe',
                                    'charset': 'UTF-8'})
        result = view.render(request)
        self.assertEquals(request.code, 200, result)
        self.assert_('timetable.csv imported successfully' in result, result)

        self.assertEquals(request.applog,
                  [(self.manager, u'School timetable imported', INFO),
                   (self.manager, u'School timetable roster imported', INFO)])

    def test_POST_empty(self):
        view = self.createView()
        view.request = RequestStub(args={'timetable.csv': '',
                                         'roster.txt': '',
                                         'charset': 'UTF-8'})
        content = view.do_POST(view.request)
        self.assert_('No data provided' in content)

        self.assertEquals(view.request.applog, [])

    def test_POST_invalid_charset(self):
        view = self.createView()
        view.request = RequestStub(args={'timetable.csv':'"A","\xff","C","D"',
                                         'roster.txt': '',
                                         'charset': 'UTF-8'})
        content = view.do_POST(view.request)
        self.assert_('incorrect charset' in content)
        self.assertEquals(view.request.applog, [])

    def test_POST_utf8(self):
        view = self.createView()
        ttschema = self.app.timetableSchemaService[u'three-day']
        self.app.timetableSchemaService[u'three-day \u263b'] = ttschema
        view.request = RequestStub(
                args={'timetable.csv': '"whatever","three-day \xe2\x98\xbb"',
                      'roster.txt': '', 'charset': 'UTF-8'})
        result = view.do_POST(view.request)
        self.assert_('timetable.csv imported successfully' in result, result)
        self.assertEquals(view.request.applog,
                          [(None, u'School timetable imported', INFO)])


class TestTimetableCSVImporter(AppSetupMixin, unittest.TestCase):

    days = ("Monday", "Tuesday", "Wednesday")
    periods = ("A", "B", "C")

    def setUp(self):
        from schooltool.timetable import Timetable, TimetableDay
        from schooltool import relationship

        self.setUpSampleApp()
        relationship.setUp()

        # set a timetable schema
        ttschema = Timetable(self.days)
        for day in self.days:
            ttschema[day] = TimetableDay(self.periods)
        self.app.timetableSchemaService['three-day'] = ttschema

        # add some people and groups
        for title in ['Curtin', 'Lorch', 'Guzman']:
            self.app['persons'].new(title.lower(), title=title)
        for title in ['Math1', 'Math2', 'Math3',
                      'English1', 'English2', 'English3']:
            self.app['groups'].new(title.lower(), title=title)

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

        new_person = self.app['persons'].new(title='New guy')
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

        math101 = self.app['groups'].new('math101', title='Math 101')

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
        self.assertRaises(KeyError, imp.findByTitle,
                          'groups', 'Math 101 - Prof. Bar')

        imp.scheduleClass('A', 'Math 101', 'Prof. Bar',
                          day_ids=['day1', 'day2'], location='Inside')

        group = imp.findByTitle('groups', 'Math 101 - Prof. Bar')
        self.assertIsRelated(group, math101)
        self.assertIsRelated(group, self.teacher, rel=uris.URITaught)

        tt = group.timetables['period1', 'two_day']
        activities = list(tt.itercontent())
        self.assertEquals(len(activities), 2)
        for day_id, period_id, activity in activities:
            self.assertEquals(activity.title, 'Math 101')
            self.assert_(activity.owner is group)
            self.assertEquals(list(activity.resources), [self.location])
            self.assert_(activity.timetable is tt)

        new_group = self.app['groups'].new(title='Math 101 - Lorch')
        imp.scheduleClass('A', 'Math 101', 'Lorch',
                          day_ids=['day1', 'day2'], location='Inside')
        self.assertIsRelated(new_group, self.app['persons']['lorch'],
                             rel=uris.URITaught)

    def test_scheduleClass_errors(self):
        from schooltool.timetable import Timetable, TimetableDay

        math101 = self.app['groups'].new('math101', title='Math 101')

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

    def assertIsRelated(self, obj, group, expected=True, rel=uris.URIMember):
        from schooltool.component import getRelatedObjects
        related = getRelatedObjects(group, rel)
        self.assertEquals(obj in related, expected,
                          "%r %sin %r (%r)" % (obj, expected and "not " or "",
                                               related, rel))

    def test_importRoster(self):
        g1 = self.app['groups'].new(title="Math1 - Lorch")
        g2 = self.app['groups'].new(title="Math2 - Guzman")
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
        g2 = self.app['groups'].new(title="Math2 - Guzman")
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

    def test_importRoster_check_parent(self):
        from schooltool.membership import Membership
        master = self.app['groups'].new(title="Master")
        slave = self.app['groups'].new(title="Slave")
        Membership(group=self.app['groups']['pupils'], member=master)
        Membership(group=master, member=slave)

        self.app.restrict_membership = True
        imp = self.createImporter()
        self.failIf(imp.importRoster("Slave\nLorch\nNonexistent"))
        self.assertEquals(imp.errors.generic,
                          ['Lorch does not belong to a parent group of Slave'])
        self.assertEquals(imp.errors.persons, ['Nonexistent'])

        slave = self.app['persons'].new(title="Existent")
        self.app.restrict_membership = False
        imp = self.createImporter()
        ok = imp.importRoster("Slave\nLorch\nExistent")
        self.assert_(ok)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCharsetMixin))
    suite.addTest(unittest.makeSuite(TestCSVImportView))
    suite.addTest(unittest.makeSuite(TestCSVImporterZODB))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImportView))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImporter))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
