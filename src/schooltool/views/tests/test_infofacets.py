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
Unit tests for schooltool.views.infofacets

$Id$
"""

import unittest
from schooltool.views.tests import RequestStub
from schooltool.tests.utils import XMLCompareMixin

__metaclass__ = type


class TestPersonInfoFacetView(unittest.TestCase, XMLCompareMixin):

    def test(self):
        from schooltool.views.infofacets import PersonInfoFacetView
        from schooltool.infofacets import PersonInfoFacet

        context = PersonInfoFacet()
        view = PersonInfoFacetView(context)

        empty_xml = """
            <facet active="active" owned="unowned">
              <class>PersonInfoFacet</class>
              <name></name>
            </facet>
            """
        request = RequestStub('/person/000001/facets/person_info')
        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEqualsXML(result, empty_xml)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPersonInfoFacetView))
    return suite

if __name__ == '__main__':
    unittest.main()
