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
Unit tests for schooltool.xmlparsing

$Id$
"""

import unittest
from zope.testing.doctest import DocTestSuite
from schooltool.common.xmlparsing import XMLParseError


def test_validate_ill_formed_document():
    """Test for LxmlDocument.

        >>> from schooltool.common.xmlparsing import LxmlDocument
        >>> schema = '''
        ...   <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        ...     <start>
        ...       <element name="sample">
        ...         <text/>
        ...       </element>
        ...     </start>
        ...   </grammar>
        ... '''
        >>> LxmlDocument("<ill></formed>", schema)
        Traceback (most recent call last):
          ...
        XMLParseError: Ill-formed document.

    Double-check that invalid schemas are caught.

        >>> LxmlDocument("<sample>Foo!</sample>", '<ill></formed>')
        Traceback (most recent call last):
          ...
        XMLSchemaError: Invalid RelaxNG schema.

    """


class TestRelaxNGValidation(unittest.TestCase):

    def test_validate_against_schema(self):
        from schooltool.common.xmlparsing import validate_against_schema
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
        self.assertRaises(XMLParseError,
                          validate_against_schema, schema, notxml)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRelaxNGValidation))
    suite.addTest(DocTestSuite('schooltool.common.xmlparsing'))
    suite.addTest(DocTestSuite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
