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
                                    'teachers.csv': '',
                                    'pupils.csv': '',
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
                                    'teachers.csv': '',
                                    'pupils.csv': '',
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
                                    'teachers.csv': '',
                                    'pupils.csv': '',
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
                                    'teachers.csv': '',
                                    'pupils.csv': '',
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

    def test_POST_groups_wrong_charset(self):
        request = RequestStub(args={'groups.csv':'"year1","\xff","root",""',
                                    'resources.csv': '',
                                    'teachers.csv': '',
                                    'pupils.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('incorrect charset' in content)
        self.assert_('Data imported successfully' not in content)
        self.assertEquals(request.applog, [])

    def test_POST_resources(self):
        request = RequestStub(args={'resources.csv':'"Stool",""',
                                    'groups.csv': '',
                                    'teachers.csv': '',
                                    'pupils.csv': '',
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

    def test_POST_pupils(self):
        request = RequestStub(args={'pupils.csv':'"A B","","1922-11-22",""',
                                    'groups.csv': '',
                                    'teachers.csv': '',
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
            (None, u'Imported person info for 000001 (A B, 1922-11-22)', INFO),
            (None, u'CSV data import finished successfully', INFO)])

    def test_POST_teachers(self):
        request = RequestStub(args={'teachers.csv':'"C D","","1922-11-22",""',
                                    'groups.csv': '',
                                    'pupils.csv': '',
                                    'resources.csv': '',
                                    'charset': 'UTF-8'})
        self.view.request = request
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        titles = [resource.title
                  for resource in self.app['persons'].itervalues()]
        self.assert_('C D' in titles)
        self.assertEquals(request.applog,
           [(None, u'CSV data import started', INFO),
            (None, u'Imported person (teacher): C D', INFO),
            (None, u'Imported person info for 000001 (C D, 1922-11-22)', INFO),
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

        objs = [link.traverse() for link in group.listLinks()]
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
        name = self.im.importPerson('Smith', 'group1', 'group2')
        self.assertEquals(self.im.logs, ["Imported person: Smith"])
        person = self.persons[name]
        self.assertEquals(person.title, 'Smith')

        objs = [link.traverse() for link in person.listLinks()]
        self.assertEquals(len(objs), 2)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)

    def test_importPerson_teacher(self):
        name = self.im.importPerson('Wesson', 'group1', 'group2',
                                    teaching=True)
        self.assertEquals(self.im.logs, ["Imported person (teacher): Wesson"])
        person = self.persons[name]
        self.assertEquals(person.title, 'Wesson')

        objs = [link.traverse() for link in person.listLinks()]
        self.assertEquals(len(objs), 2)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)

    def test_importPerson_errors(self):
        from schooltool.browser.csvimport import DataError
        self.assertRaises(DataError, self.im.importPerson,
                          'Smith', 'invalid_group', 'group2')
        self.assertRaises(DataError, self.im.importPerson,
                          'Smith', 'group1', 'invalid_group')
        self.assertRaises(DataError, self.im.importPerson,
                          'Smith', 'invalid_group', 'group2', True)
        self.assertRaises(DataError, self.im.importPerson,
                          'Smith', 'group1', 'invalid_group', True)
        self.assertEquals(self.im.logs, [])

    def test_importResource(self):
        name = self.im.importResource('Stool', 'group1 group2')
        self.assertEquals(self.im.logs, ["Imported resource: Stool"])
        resource = self.resources[name]
        self.assertEquals(resource.title, 'Stool')

        objs = [link.traverse() for link in resource.listLinks()]
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
        self.im.importPersonInfo('person1', 'Foo Bayer',
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
        self.im.importPersonInfo('person1', 'Anonymous',
                                 '', 'Wazzup?')
        self.assertEquals(self.im.logs, ["Imported person info for person1"
                                         " ( Anonymous, None)"])
        info = FacetManager(self.person1).facetByName('person_info')
        self.assertEquals(info.first_name, '')
        self.assertEquals(info.last_name, 'Anonymous')


class TestTimetableCSVImportView(AppSetupMixin, unittest.TestCase):

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
        request = RequestStub(authenticated_user=self.person)
        result = view.render(request)
        self.assertEquals(request.code, 302, result)
        self.assert_('forbidden' in result)

    def test_post(self):
        view = self.createView()
        request = RequestStub(authenticated_user=self.manager)
        # TODO
        result = view.render(request)
        self.assertEquals(request.code, 200, result)

    def test_POST_empty(self):
        view = self.createView()
        view.request = RequestStub(args={'timetable.csv': '',
                                         'roster.txt': '',
                                         'charset': 'UTF-8'})
        content = view.do_POST(view.request)
        self.assert_('No data provided' in content)

        self.assertEquals(view.request.applog, [])

    def test_POST_wrong_charset(self):
        view = self.createView()
        view.request = RequestStub(args={'timetable.csv':'"A","\xff","C","D"',
                                         'roster.txt': '',
                                         'charset': 'UTF-8'})
        content = view.do_POST(view.request)
        self.assert_('incorrect charset' in content)
        self.assertEquals(view.request.applog, [])


class TestTimetableCSVImporter(AppSetupMixin, unittest.TestCase):

    def createImporter(self):
        from schooltool.browser.csvimport import TimetableCSVImporter
        return TimetableCSVImporter(self.app)

    def test_timetable_headers(self):
        imp = self.createImporter()
        csv = ('"ttschema name","period_id"\n'
               '"Monday","Friday"\n')
        imp.importTimetable(csv)
        self.assertEquals(imp.ttschema_name, 'ttschema name')
        self.assertEquals(imp.period_id, 'period_id')
        self.assertEquals(imp.day_ids, ['Monday', 'Friday'])

#    def test_timetable_empty(self):
#        imp = self.createImporter()
#        imp.importTimetable('')
#        # TODO
#
#    def test_timetable_invalid(self):
#        imp = self.createImporter()
#        imp.importTimetable('"Some","invalid","csv')
#        # TODO
#
#    def test_timetable(self):
#        imp = self.createImporter()
#        imp.importTimetable(
#                '"","A","B","C"\n'
#                '"105","Math1 Curtin","Math2 Guzman","Math3 Curtin"\n'
#                '"129","English1 Lorch","English2 Lorch","English3 Lorch"\n')
#        # TODO
#
#        class TimetableSchemaServiceStub:
#            def getSchema(self, schema_id):
#                if schema_id == 'weekly':
#                    tt = Timetable(("day1", "day2"))
#                    tt["day1"] = TimetableDay(("A", "B"))
#                    tt["day2"] = TimetableDay(("A", "B"))
#                    return tt

    def test__clearTimetables(self):
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
        imp.ttschema_name = 'some_schema'
        imp._clearTimetables()

        tt_notblank = self.pupils.timetables['period2', 'some_schema']
        self.assert_(('period1', 'some_schema')
                     not in self.pupils.timetables.keys())
        self.assertEquals(len(list(tt_notblank.itercontent())), 1)

    def test__scheduleClass(self):
        from schooltool.timetable import Timetable, TimetableDay

        math101 = self.app['groups'].new('math101', title='Math 101')

        imp = self.createImporter()
        imp.ttname = 'tt'
        imp.ttschema_name = 'two_day'
        imp.period_id = 'period1'
        ttschema = Timetable(("day1", "day2"))
        ttschema["day1"] = TimetableDay(("A", "B"))
        ttschema["day2"] = TimetableDay(("A", "B"))
        self.app.timetableSchemaService['two_day'] = ttschema
        imp.day_ids = ['day1', 'day2']

        imp._scheduleClass('A', 'Math 101', 'Prof. Bar')

        tt = math101.timetables['period1', 'two_day']
        activities = list(tt.itercontent())
        self.assertEquals(len(activities), 2)
        for day_id, period_id, activity in activities:
            self.assertEquals(activity.title, 'Math 101')
            self.assert_(activity.owner is self.teacher)
            # self.assert_(activity.resources, ...) TODO
            self.assert_(activity.timetable is tt)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCharsetMixin))
    suite.addTest(unittest.makeSuite(TestCSVImportView))
    suite.addTest(unittest.makeSuite(TestCSVImporterZODB))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImportView))
    suite.addTest(unittest.makeSuite(TestTimetableCSVImporter))
    return suite


if __name__ == '__main__':
    unittest.main()
