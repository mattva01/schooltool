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
Tests for level REST views.

$Id: test_app.py 4342 2005-07-25 16:02:24Z bskahan $
"""
import unittest

import zope.interface
from zope.app.traversing.interfaces import IPathAdapter
from zope.app.pagetemplate import talesapi
from zope.publisher.browser import TestRequest
from zope.app.component.testing import PlacefulSetup
from zope.app.filerepresentation.interfaces import IFileFactory
from zope.app.testing import ztapi

from schooltool.app.rest import testing
from schooltool.level import interfaces, level, rest
from schooltool.testing import setup

class TestLevelContainerView(testing.ContainerViewTestMixin, unittest.TestCase):
    """Test for LevelContainerView"""

    def setUp(self):
        testing.ContainerViewTestMixin.setUp(self)
        ztapi.provideAdapter(interfaces.ILevelContainer, IFileFactory,
                             rest.level.LevelFileFactory)

        self.level = self.app['levels']['level1'] = level.Level("1st Grade")
        self.levelContainer = self.app['levels']

    def test_render(self):
        view = rest.level.LevelContainerView(self.levelContainer, TestRequest())
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>levels</name>
              <items>
                <item xlink:href="http://127.0.0.1/levels/level1"
                      xlink:title="1st Grade"
                      xlink:type="simple"/>
              </items>
              <acl xlink:href="http://127.0.0.1/levels/acl" xlink:title="ACL"
                   xlink:type="simple"/>
            </container>
            """)

class TestLevelFileFactory(PlacefulSetup, unittest.TestCase):

    def setUp(self):
        super(TestLevelFileFactory, self).setUp()
        self.app = setup.setupSchoolToolSite()
        self.factory = rest.level.LevelFileFactory(self.app['levels'])

    def test_attributes(self):
        level2 = self.factory(
            "level2", None,
            '''<object xmlns="http://schooltool.org/ns/model/0.1"
                       title="Grade 2" isInitial="false"/>''')

        self.assertEquals(level2.title, "Grade 2")
        self.assertEquals(level2.isInitial, False)
        self.assertEquals(level2.nextLevel, None)

        self.app['levels']['level2'] = level2

        level1 = self.factory(
            "level1", None,
            '''<object xmlns="http://schooltool.org/ns/model/0.1"
                       title="Grade 1" isInitial="true"
                       nextLevel="level2"/>''')

        self.assertEquals(level1.title, "Grade 1")
        self.assertEquals(level1.isInitial, True)
        self.assertEquals(level1.nextLevel, level2)


class TestLevelFile(testing.FileFactoriesSetUp, PlacefulSetup,
                    unittest.TestCase):
    """A test for IPerson IWriteFile adapter"""

    def setUp(self):
        super(TestLevelFile, self).setUp()
        self.app = setup.setupSchoolToolSite()
        ztapi.provideAdapter(interfaces.ILevelContainer, IFileFactory,
                             rest.level.LevelFileFactory)


    def testWrite(self):
        levels = level.LevelContainer()
        level1 = level.Level("1st Grade")
        levels['level1'] = level1

        file = rest.level.LevelFile(level1)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="First Grade" isInitial="true"/>''')

        self.assertEquals(level1.title, "First Grade")


class TestLevelView(testing.ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of a group."""

    def setUp(self):
        testing.ApplicationObjectViewTestMixin.setUp(self)
        level2 = level.Level("2nd Grade")
        self.testObject = self.app['levels']['level2'] = level2
        level1 = level.Level("1st Grade", True, level2)
        self.app['levels']['level1'] = level1

        # Sigh, register the zope:name path adapter
        ztapi.provideAdapter(
            zope.interface.Interface, IPathAdapter, talesapi.ZopeTalesAPI,
            name="zope")

    def makeTestView(self, object, request):
        return rest.level.LevelView(object, request)

    def testGET(self):

        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, '''
            <level xmlns:xlink="http://www.w3.org/1999/xlink">
              <title>2nd Grade</title>
              <isInitial>
                false
              </isInitial>
              <nextLevel/>
              <relationships
                  xlink:href="http://127.0.0.1/levels/level2/relationships"
                  xlink:title="Relationships" xlink:type="simple"/>
              <acl xlink:href="http://127.0.0.1/levels/level2/acl"
                   xlink:title="ACL" xlink:type="simple"/>
            </level>''')

    def testGETNextLevel(self):

        self.testObject = self.app['levels']['level1']
        result, response = self.get()

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, '''
            <level xmlns:xlink="http://www.w3.org/1999/xlink">
              <title>1st Grade</title>
              <isInitial>
                true
              </isInitial>
              <nextLevel>
                level2
              </nextLevel>
              <relationships
                  xlink:href="http://127.0.0.1/levels/level1/relationships"
                  xlink:title="Relationships" xlink:type="simple"/>
              <acl xlink:href="http://127.0.0.1/levels/level1/acl"
                   xlink:title="ACL" xlink:type="simple"/>
            </level>''')




def test_suite():
    suite = unittest.TestSuite((
        unittest.makeSuite(TestLevelContainerView),
        unittest.makeSuite(TestLevelFileFactory),
        unittest.makeSuite(TestLevelFile),
        unittest.makeSuite(TestLevelView),
        ))

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
