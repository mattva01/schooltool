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
from schooltool.browser.tests import RequestStub, AppSetupMixin
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestCSVImportView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.browser.csv import CSVImportView
        self.setUpSampleApp()

        # XXX CSV import tries to create basic groups and will b0rk
        #     if the groups already exist.
        del self.app['groups']['teachers']

        # Register the teacher_group facet.
        import schooltool.teaching
        schooltool.teaching.setUp()

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
                                    'pupils.csv': ''})
        content = self.view.do_POST(request)
        self.assert_('No data provided' in content)
        self.assert_('Data imported successfully' not in content)

        self.assert_('teachers' not in self.app['groups'].keys())
        self.assertEquals(request.applog, [])

    def test_POST_groups(self):
        from schooltool.component import FacetManager
        from schooltool.teaching import TeacherGroupFacet
        request = RequestStub(args={'groups.csv':'"year1","Year 1","root",""',
                                    'resources.csv': '',
                                    'teachers.csv': '',
                                    'pupils.csv': ''})
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        # The import should have created basic groups.
        self.assert_('teachers' in self.app['groups'].keys())
        teachers = self.app['groups']['teachers']
        facets = list(FacetManager(teachers).iterFacets())
        self.assertEquals(len(facets), 1)
        self.assert_(isinstance(facets[0], TeacherGroupFacet))

        self.assert_('year1' in self.app['groups'].keys())
        self.assertEquals(request.applog, [(None, u'CSV data imported', INFO)])

    def test_POST_groups_errors(self):
        request = RequestStub(args={'groups.csv': '"year1","b0rk',
                                    'resources.csv': '',
                                    'teachers.csv': '',
                                    'pupils.csv': ''})
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' not in content)
        self.assert_('Error in group data' in content)
        self.assertEquals(request.applog, [])

    def test_POST_resources(self):
        request = RequestStub(args={'resources.csv':'"Stool",""',
                                    'groups.csv': '',
                                    'teachers.csv': '',
                                    'pupils.csv': ''})
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        titles = [resource.title
                  for resource in self.app['resources'].itervalues()]
        self.assert_('Stool' in titles)

        self.assertEquals(request.applog, [(None, u'CSV data imported', INFO)])

    def test_POST_pupils(self):
        request = RequestStub(args={'pupils.csv':'"Me !","","1922-11-22",""',
                                    'groups.csv': '',
                                    'teachers.csv': '',
                                    'resources.csv': ''})
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        titles = [resource.title
                  for resource in self.app['persons'].itervalues()]
        self.assert_('Me !' in titles)

    def test_POST_teachers(self):
        request = RequestStub(args={'teachers.csv':'"Me !","","1922-11-22",""',
                                    'groups.csv': '',
                                    'pupils.csv': '',
                                    'resources.csv': ''})
        content = self.view.do_POST(request)
        self.assert_('Data imported successfully' in content)

        titles = [resource.title
                  for resource in self.app['persons'].itervalues()]
        self.assert_('Me !' in titles)


class TestCSVImporterZODB(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.browser.csv import CSVImporterZODB
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()

        # Register the teacher_group facet.
        import schooltool.teaching
        schooltool.teaching.setUp()

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

        self.im = CSVImporterZODB(self.app)

    def test_init(self):
        self.assert_(self.im.groups is self.groups)
        self.assert_(self.im.persons is self.persons)
        self.assert_(self.im.resources is self.resources)

    def test_importGroup(self):
        from schooltool.component import FacetManager
        from schooltool.teaching import TeacherGroupFacet, SubjectGroupFacet
        self.im.importGroup('gr0wl', 'A tiny group', 'group1 group2',
                            'teacher_group subject_group')
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

    def test_importPerson(self):
        name = self.im.importPerson('Smith', 'group1', 'group2')
        person = self.persons[name]
        self.assertEquals(person.title, 'Smith')

        objs = [link.traverse() for link in person.listLinks()]
        self.assertEquals(len(objs), 2)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)

#    def test_importPerson_teacher(self):
#        name = self.im.importPerson('Wesson', 'group1', 'group2',
#                                    teaching=True)
#        person = self.persons[name]
#        self.assertEquals(person.title, 'Wesson')
#
#        objs = [link.traverse() for link in person.listLinks()]
#        self.assertEquals(len(objs), 2)
#        self.assert_(self.group1 in objs)
#        self.assert_(self.group2 in objs)

    def test_importResource(self):
        name = self.im.importResource('Stool', 'group1 group2')
        resource = self.resources[name]
        self.assertEquals(resource.title, 'Stool')

        objs = [link.traverse() for link in resource.listLinks()]
        self.assertEquals(len(objs), 2)
        self.assert_(self.group1 in objs)
        self.assert_(self.group2 in objs)

    def test_importPersonInfo(self):
        from schooltool.component import FacetManager
        self.im.importPersonInfo('person1', 'Foo Bayer',
                                 '1922-12-12', 'Wazzup?')
        info = FacetManager(self.person1).facetByName('person_info')

        self.assertEquals(info.first_name, 'Foo')
        self.assertEquals(info.last_name, 'Bayer')
        self.assertEquals(info.dob, datetime.date(1922, 12, 12))
        self.assertEquals(info.comment, 'Wazzup?')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCSVImportView))
    suite.addTest(unittest.makeSuite(TestCSVImporterZODB))
    return suite


if __name__ == '__main__':
    unittest.main()
