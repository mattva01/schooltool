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
Unit tests for schooltool.rest.utility

$Id$
"""

import unittest
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.rest.tests import RequestStub, UtilityStub

__metaclass__ = type


class TestUtilityServiceView(XMLCompareMixin, RegistriesSetupMixin,
                             unittest.TestCase):

    def setUp(self):
        from schooltool.rest.utility import UtilityServiceView
        from schooltool.app import Application
        import schooltool.rest
        self.setUpRegistries()
        schooltool.rest.setUp()
        self.app = Application()
        self.app.utilityService["foo"] = UtilityStub("Foo utility")
        self.view = UtilityServiceView(self.app.utilityService)
        self.view.authorization = lambda ctx, rq: True

    def test_render(self):
        request = RequestStub("http://localhost/groups")
        result = self.view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>utils</name>
              <items>
                <item xlink:type="simple" xlink:href="/utils/foo"
                      xlink:title="Foo utility"/>
              </items>
            </container>
            """)

    def test__traverse(self):
        from schooltool.rest.utility import UtilityView
        request = RequestStub("http://localhost/utils/foo")
        view = self.view._traverse('foo', request)
        self.assert_(view.__class__ is UtilityView)
        self.assertRaises(KeyError, view._traverse, 'moot', request)


class TestUtilityView(XMLCompareMixin, RegistriesSetupMixin,
                      unittest.TestCase):

    def setUp(self):
        from schooltool.rest.utility import UtilityView
        from schooltool.app import Application
        import schooltool.rest
        self.setUpRegistries()
        schooltool.rest.setUp()
        self.app = Application()
        self.app.utilityService["foo"] = UtilityStub("Foo utility")
        self.view = UtilityView(self.app.utilityService['foo'])
        self.view.authorization = lambda ctx, rq: True

    def test_render(self):
        request = RequestStub("http://localhost/groups")
        result = self.view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <utility>
              <name>foo</name>
            </utility>
            """)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUtilityServiceView))
    suite.addTest(unittest.makeSuite(TestUtilityView))
    return suite

if __name__ == '__main__':
    unittest.main()
