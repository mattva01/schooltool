#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for schooltool.views.csvexport

$Id$
"""

import unittest
import datetime
import zipfile
import csv
from cStringIO import StringIO
from pprint import pformat
from schooltool.tests.utils import RegistriesSetupMixin, NiceDiffsMixin
from schooltool.tests.helpers import sorted, diff
from schooltool.views.tests import RequestStub

__metaclass__ = type


groups_csv = """\
"math","Mathematics Department","root",""
"year1","Year 1","root",""
"math1","Mathematics 1","math year1","subject_group"
"year3","Year 3","root",""
"biol3","Biology 3","year3","subject_group"
"ling3","Linguistics 3","year3","subject_group"
"""

pupils_csv = """\
"James Cox","year1 math1","1994-03-10","No relation to Jeff Cox"
"Tom Hall","year3 ling3 biol3","1992-07-20",""
"""

teachers_csv = """\
"Nicola Smith","ling3","1952-12-06","A comment"
"Jeff Cox","biol3 math1","1967-06-13",""
"""

resources_csv = """\
"Hall"
"Room 1"
"Room 2"
"Projector 1"
"""


class TestCSVExporter(RegistriesSetupMixin, NiceDiffsMixin, unittest.TestCase):

    def setUp(self):
        from schooltool import relationship, membership, teaching
        self.setUpRegistries()
        relationship.setUp()
        membership.setUp()
        teaching.setUp()

    def createEmptyApp(self):
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.model import Group, Person, Resource
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        app['groups'].new("root", title="Root Group")
        app['groups'].new("teachers", title="Teachers")
        app['groups'].new("pupils", title="Pupils")
        return app

    def createApp(self):
        from schooltool.component import FacetManager
        from schooltool.membership import Membership
        from schooltool.teaching import Teaching, SubjectGroupFacet

        app = self.createEmptyApp()
        groups = app['groups']
        persons = app['persons']
        resources = app['resources']

        # Groups
        root = groups['root']

        year1 = groups.new("year1", title="Year 1")
        Membership(member=year1, group=root)

        year3 = groups.new("year3", title="Year 3")
        Membership(member=year3, group=root)

        math = groups.new("math", title="Mathematics Department")
        Membership(member=math, group=root)

        math1 = groups.new("math1", title="Mathematics 1")
        FacetManager(math1).setFacet(SubjectGroupFacet())
        Membership(member=math1, group=year1)
        Membership(member=math1, group=math)

        ling3 = groups.new("ling3", title="Linguistics 3")
        FacetManager(ling3).setFacet(SubjectGroupFacet())
        Membership(member=ling3, group=year3)

        biol3 = groups.new("biol3", title="Biology 3")
        FacetManager(biol3).setFacet(SubjectGroupFacet())
        Membership(member=biol3, group=year3)

        # Pupils
        pupils = groups['pupils']

        p = persons.new(title="James Cox")
        person_info = FacetManager(p).facetByName('person_info')
        person_info.date_of_birth = datetime.date(1994, 3, 10)
        person_info.comment = "No relation to Jeff Cox"
        Membership(member=p, group=pupils)
        Membership(member=p, group=year1)
        Membership(member=p, group=math1)

        p = persons.new(title="Tom Hall")
        person_info = FacetManager(p).facetByName('person_info')
        person_info.date_of_birth = datetime.date(1992, 7, 20)
        Membership(member=p, group=pupils)
        Membership(member=p, group=year3)
        Membership(member=p, group=biol3)
        Membership(member=p, group=ling3)

        # Teachers
        teachers = groups['teachers']

        p = persons.new(title="Nicola Smith")
        person_info = FacetManager(p).facetByName('person_info')
        person_info.date_of_birth = datetime.date(1952, 12, 6)
        person_info.comment = "A comment"
        Membership(member=p, group=teachers)
        Teaching(teacher=p, taught=ling3)

        p = persons.new(title="Jeff Cox")
        person_info = FacetManager(p).facetByName('person_info')
        person_info.date_of_birth = datetime.date(1967, 6, 13)
        Membership(member=p, group=teachers)
        Teaching(teacher=p, taught=biol3)
        Teaching(teacher=p, taught=math1)

        # Resources

        resources.new(title="Hall")
        resources.new(title="Room 1")
        resources.new(title="Room 2")
        resources.new(title="Projector 1")

        return app

    def test(self):
        from schooltool.views.csvexport import CSVExporter
        app = self.createApp()
        view = CSVExporter(app)
        request = RequestStub()
        result = view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'], "application/x-zip")

        stm = StringIO(result)
        zf = zipfile.ZipFile(stm)
        files = zf.namelist()
        required = ['groups.csv', 'pupils.csv', 'teachers.csv',
                    'resources.csv']
        self.assertEquals(sorted(files), sorted(required))

        self.check(zf, 'groups.csv', groups_csv, reorder_words_in_col=3)
        self.check(zf, 'pupils.csv', pupils_csv, reorder_words_in_col=2)
        self.check(zf, 'teachers.csv', teachers_csv, reorder_words_in_col=2)
        self.check(zf, 'resources.csv', resources_csv)

    def check(self, zf, filename, expected, reorder_words_in_col=None):
        result = zf.read(filename)
        result = list(csv.reader(StringIO(result)))
        result.sort()
        expected = list(csv.reader(StringIO(expected)))
        expected.sort()
        if reorder_words_in_col is not None:
            for row in result + expected:
                values = row[reorder_words_in_col - 1].split()
                values.sort()
                row[reorder_words_in_col - 1] = " ".join(values)
        msg = filename + ":\n" + diff(pformat(expected), pformat(result))
        self.assertEquals(result, expected, msg)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCSVExporter))
    return suite

if __name__ == '__main__':
    unittest.main()

