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
from schooltool.browser.tests import RequestStub, AppSetupMixin
from schooltool.tests.utils import RegistriesSetupMixin

__metaclass__ = type


class TestCSVImportView(AppSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpSampleApp()

    def test_render(self):
        from schooltool.browser.csv import CSVImportView
        view = CSVImportView(self.app)
        view.authorization = lambda x, y: True

        request = RequestStub()
        content = view.render(request)

        self.assert_('Upload CSV' in content)


class TestCSVImporterZODB(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.browser.csv import CSVImporterZODB
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()

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
        self.im.importGroup('gr0wl', 'A tiny group', 'group1 group2', '')
        group = self.groups['gr0wl']
        self.assertEquals(group.title, 'A tiny group')
        self.assertEquals(len(group.listLinks()), 2) # TODO examine links
        # TODO: facets

    def test_importPerson(self):
        name = self.im.importPerson('Smith', 'group1', 'group2', '')
        person = self.persons[name]
        self.assertEquals(person.title, 'Smith')
        # TODO: other arguments

    def test_importResource(self):
        name = self.im.importResource('Stool', 'group1 group2')
        resource = self.resources[name]
        self.assertEquals(resource.title, 'Stool')
        self.assertEquals(len(resource.listLinks()), 2) # TODO examine links

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
