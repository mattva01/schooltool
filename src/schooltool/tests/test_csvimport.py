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
import datetime
from zope.testing.doctestunit import DocTestSuite
from schooltool.tests.utils import NiceDiffsMixin

__metaclass__ = type


class TestCSVImporterBase(NiceDiffsMixin, unittest.TestCase):

    def test_importGroupsCsv(self):
        from schooltool.csvimport import CSVImporterBase
        im = CSVImporterBase()

        groups = []
        def importGroupStub(name, title, parents, facets):
            groups.append((name, title, parents, facets))
        im.importGroup = importGroupStub

        im.importGroupsCsv(['"year1","Year 1","root",'])
        self.assertEquals(groups,
                          [(u'year1', u'Year 1', u'root', u'')])

    def test_importResourcesCsv(self):
        from schooltool.csvimport import CSVImporterBase
        im = CSVImporterBase()

        resources = []
        def importResourceStub(title, groups):
            resources.append((title, groups))
        im.importResource = importResourceStub

        im.importResourcesCsv(['"Hall","locations"'])
        self.assertEquals(resources, [(u'Hall', u'locations')])

    def test_importPersonsCsv(self):
        from schooltool.csvimport import CSVImporterBase
        im = CSVImporterBase()

        persons = []
        def importPersonStub(title, parent, groups, teaching=False):
            persons.append((title, parent, groups, teaching))
            return title
        im.importPerson = importPersonStub

        personinfo = []
        def importPersonInfoStub(name, title, dob, comment):
            personinfo.append((name, title, dob, comment))
        im.importPersonInfo = importPersonInfoStub

        im.importPersonsCsv(['"Jay Hacker","group1 group2","1998-01-01",'
                             '"yay"'],
                           'teachers', True)
        self.assertEquals(persons, [(u'Jay Hacker', 'teachers',
                                     u'group1 group2', True)])
        self.assertEquals(personinfo, [(u'Jay Hacker', u'Jay Hacker',
                                        u'1998-01-01', u'yay')])

    def test_import_badData(self):
        from schooltool.csvimport import CSVImporterBase
        from schooltool.csvimport import DataError
        im = CSVImporterBase()
        im.verbose = False

        class ResponseStub:
            def getheader(self, header):
                return 'foo://bar/baz/quux'

        im.process = lambda x, y, body=None: ResponseStub()

        im.importGroup = lambda name, title, parents, facets: None
        im.importPerson = lambda title, parent, groups, teaching: None
        im.importResource = lambda title, groups: None

        def raisesDataError(method, *args):
            im.fopen = lambda fn: StringIO('"invalid","csv')
            self.assertRaises(DataError, method, "fn")

        self.assertRaises(DataError, im.importGroupsCsv,
                          ['"year1","Year 1","root"'])
        self.assertRaises(DataError, im.importResourcesCsv,
                          ['"year1","Year 1","root"'])
        self.assertRaises(DataError, im.importPersonsCsv,
                          ['"Foo","bar","baz"'], 'pupils',
                          lambda group, member_path: None)

        self.assertRaises(DataError, im.importGroupsCsv, ['"invalid","csv'])
        self.assertRaises(DataError, im.importResourcesCsv, ['"b0rk","b0rk'])
        self.assertRaises(DataError, im.importPersonsCsv, ['"invalid","csv'],
                          'pupils', lambda group, member_path: None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCSVImporterBase))
    return suite

if __name__ == '__main__':
    unittest.main()
