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
Unit tests for schooltool.rest.xmlparsing

$Id$
"""

import unittest
from zope.testing.doctest import DocTestSuite
from schooltool.tests.utils import QuietLibxml2Mixin


def test_xpath_context_sharing():
    """XMLDocument and XMLNode instances share the same XPath context.

    We want to make sure that this sharing does not break XPath queries.

        >>> from schooltool.rest.xmlparsing import XMLDocument
        >>> doc = XMLDocument('''
        ...    <sample>
        ...      <child>
        ...        <grandchild/>
        ...      </child>
        ...    </sample>
        ... ''')

    Queries performed from the document are relative to the document node
    (which is a parent of the document element).

        >>> len(doc.query('sample'))
        1
        >>> len(doc.query('child'))
        0

    Queries performed from a child node are relative to that node.

        >>> child = doc.query('//child')[0]
        >>> len(child.query('grandchild'))
        1
        >>> len(child.query('sample'))
        0

    XMLDocument.query resets the context node of the shared XPath context.

        >>> len(doc.query('sample'))
        1
        >>> len(doc.query('child'))
        0

    """


def test_xpath_namespace_sharing():
    """XMLDocument and XMLNode instances share the same set of namespaces.

        >>> from schooltool.rest.xmlparsing import XMLDocument
        >>> doc = XMLDocument('''
        ...   <sample xmlns="http://example.com/ns/samplens"
        ...           xmlns:xlink="http://www.w3.org/1999/xlink">
        ...      <a xlink:type="simple" xlink:href="http://example.com" />
        ...   </sample>
        ... '''.lstrip())
        >>> doc.registerNs('sample', 'http://example.com/ns/samplens')
        >>> doc.registerNs('xlnk', 'http://www.w3.org/1999/xlink')

        >>> node = doc.query('/sample:sample')[0]
        >>> len(node.query('a'))
        0
        >>> len(node.query('sample:a'))
        1

        >>> node = doc.query('//sample:a')[0]
        >>> node['xlnk:type']
        u'simple'

    """


def test_multilevel_query():
    """Regression test for a bug in XMLNode.query.

    XMLNode.query would pass self instead of self._doc to XMLNodes
    that it created.

        >>> from schooltool.rest.xmlparsing import XMLDocument
        >>> doc = XMLDocument('<a><b><c>d</c></b></a>')
        >>> a = doc.query('a')[0]
        >>> b = a.query('b')[0]
        >>> c = b.query('c')[0]
        >>> c.content
        u'd'

    """


def test_validate_ill_formed_document():
    """Regression test for a bug in XMLDocument.__init__.

    validate_against_schema may raise a libxml2.parseError that was not
    caught in XMLDocument.__init__.

        >>> from schooltool.rest.xmlparsing import XMLDocument
        >>> schema = '''
        ...   <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        ...     <start>
        ...       <element name="sample">
        ...         <text/>
        ...       </element>
        ...     </start>
        ...   </grammar>
        ... '''
        >>> XMLDocument("<ill></formed>", schema)
        Traceback (most recent call last):
          ...
        XMLParseError: Ill-formed document.

    Double-check that invalid schemas are caught.

        >>> XMLDocument("<sample>Foo!</sample>", '<ill></formed>')
        Traceback (most recent call last):
          ...
        XMLSchemaError: Invalid RelaxNG schema.

    """


def test_suite():
    suite = unittest.TestSuite()
    mixin = QuietLibxml2Mixin()
    suite.addTest(DocTestSuite('schooltool.rest.xmlparsing',
                               setUp=mixin.setUpLibxml2,
                               tearDown=mixin.tearDownLibxml2))
    suite.addTest(DocTestSuite('schooltool.rest.tests.test_xmlparsing',
                               setUp=mixin.setUpLibxml2,
                               tearDown=mixin.tearDownLibxml2))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
