#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Tests for schollbell.rest.app

$Id$
"""

import unittest

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.app.testing import setup
from zope.app.traversing.interfaces import IContainmentRoot

from schoolbell.app.rest.tests.utils import XMLCompareMixin
from schoolbell.app.rest.xmlparsing import XMLDocument


class TestAppView(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        from schoolbell.app.rest.app import ApplicationView
        from schoolbell.app.app import SchoolBellApplication
        setup.placefulSetUp()
        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)
        self.view = ApplicationView(self.app, TestRequest("/"))

    def tearDown(self):
        setup.placefulTearDown()

    def test_render_Usingxpath(self):
        result = self.view.GET()

        doc = XMLDocument(result)
        doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

        def oneNode(expr):
            nodes = doc.query(expr)
            self.assertEquals(len(nodes), 1,
                              "%s matched %d nodes" % (expr, len(nodes)))
            return nodes[0]

        try:
            nodes = doc.query('/schooltool/containers')
            self.assertEquals(len(nodes), 1)
            nodes = doc.query('/schooltool/containers/container')
            self.assertEquals(len(nodes), 3)

            persons = oneNode('/schooltool/containers/container'
                              '[@xlink:href="http://127.0.0.1/persons"]')
            self.assertEquals(persons['xlink:type'], 'simple')
            self.assertEquals(persons['xlink:title'], 'persons')

            groups = oneNode('/schooltool/containers/container'
                             '[@xlink:href="http://127.0.0.1/groups"]')
            self.assertEquals(groups['xlink:type'], 'simple')
            self.assertEquals(groups['xlink:title'], 'groups')

            notes = oneNode('/schooltool/containers/container'
                            '[@xlink:href="http://127.0.0.1/resources"]')
            self.assertEquals(notes['xlink:type'], 'simple')
            self.assertEquals(notes['xlink:title'], 'resources')
        finally:
            doc.free()

    def test_render(self):
        result = self.view.GET()
        response = self.view.request.response
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
              <message>Welcome to the SchoolTool server</message>
              <containers>
                <container xlink:type="simple"
                           xlink:href="http://127.0.0.1/persons"
                           xlink:title="persons"/>
                <container xlink:href="http://127.0.0.1/resources"
                           xlink:title="resources"
                           xlink:type="simple"/>
                <container xlink:type="simple"
                           xlink:href="http://127.0.0.1/groups"
                           xlink:title="groups"/>
              </containers>
            </schooltool>
            """, recursively_sort=["schooltool"])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
