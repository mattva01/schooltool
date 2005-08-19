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
Unit tests for the schooltool.schema.rng module.

$Id: test_cal.py 415 2003-11-28 15:21:45Z alga $
"""

import unittest
import libxml2
from schooltool.app.rest.testing import QuietLibxml2Mixin


class TestRelaxNGValidation(QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()

    def test_validate_against_schema(self):
        from schooltool.app.rest.rng import validate_against_schema
        schema = '''<?xml version="1.0" encoding="UTF-8"?>
            <grammar xmlns="http://relaxng.org/ns/structure/1.0"
                ns="http://schooltool.org/ns/test"
                datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
              <start>
                <element name="foo">
                    <attribute name="bar">
                      <text/>
                    </attribute>
                </element>
              </start>
            </grammar>
            '''

        xml = '<foo xmlns="http://schooltool.org/ns/test" bar="baz"/>'
        self.assert_(validate_against_schema(schema, xml))

        badxml = '<foo xmlns="http://schooltool.org/ns/test" baz="baz"/>'
        self.assert_(not validate_against_schema(schema, badxml))

        notxml = 'who am I?'
        self.assertRaises(libxml2.parserError,
                          validate_against_schema, schema, notxml)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelaxNGValidation))
    return suite
