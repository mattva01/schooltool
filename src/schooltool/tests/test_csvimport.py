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
Unit tests for schooltool.csvimport

$Id$
"""

import unittest
from schooltool.tests.utils import NiceDiffsMixin


__metaclass__ = type


class TestCSVImporterBase(NiceDiffsMixin, unittest.TestCase):

    def createImporter(self):
        from schooltool.csvimport import CSVImporterBase

        class Importer(CSVImporterBase):

            def __init__(self):
                self.groups = []
                self.resources = []
                self.persons = []
                self.personinfo = []

            def recode(self, value):
                return value.lower()

            def importGroup(self, name, title, parents, facets):
                self.groups.append((name, title, parents, facets))

            def importResource(self, title, groups):
                self.resources.append((title, groups))

            def importPerson(self, title, parent, groups, teaches=None):
                self.persons.append((title, parent, groups, teaches))
                return title

            def importPersonInfo(self, name, title, dob, comment):
                self.personinfo.append((name, title, dob, comment))

        return Importer()

    def test_importGroupsCsv(self):
        im = self.createImporter()
        im.importGroupsCsv(['"yeaR1","Year 1","rOot",'])
        self.assertEquals(im.groups, [(u'year1', u'year 1', u'root', u'')])

    def test_importResourcesCsv(self):
        im = self.createImporter()
        im.importResourcesCsv(['"Hall","locaTions"'])
        self.assertEquals(im.resources, [(u'hall', u'locations')])

    def test_importPersonsCsv(self):
        im = self.createImporter()
        im.importPersonsCsv(['"Jay Hacker","group1 group2","1998-01-01","yay","class1 class2"'], 'teachers')
        self.assertEquals(im.persons, [(u'jay hacker', u'teachers',
                                        u'group1 group2', 'class1 class2')])
        self.assertEquals(im.personinfo, [(u'jay hacker', u'jay hacker',
                                           u'1998-01-01', u'yay')])

    def test_import_badData(self):
        from schooltool.csvimport import DataError

        im = self.createImporter()
        im.verbose = False

        class ResponseStub:
            def getheader(self, header):
                return 'foo://bar/baz/quux'

        im.process = lambda x, y, body=None: ResponseStub()

        def raisesDataError(method, *args):
            im.fopen = lambda fn: StringIO('"invalid","csv')
            self.assertRaises(DataError, method, "fn")

        self.assertRaises(DataError, im.importGroupsCsv,
                          ['"year1","Year 1","root"'])
        self.assertRaises(DataError, im.importResourcesCsv,
                          ['"year1","Year 1","root"'])
        self.assertRaises(DataError, im.importPersonsCsv,
                          ['"Foo","bar","baz","fourth"'], 'pupils')

        self.assertRaises(DataError, im.importGroupsCsv, ['"invalid","csv'])
        self.assertRaises(DataError, im.importResourcesCsv, ['"b0rk","b0rk'])
        self.assertRaises(DataError, im.importPersonsCsv, ['"invalid","csv'],
                          'pupils')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCSVImporterBase))
    return suite

if __name__ == '__main__':
    unittest.main()
