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
Unit tests for schooltool.rest.timetable.

$Id$
"""

import unittest
import datetime

from zope.interface import Interface
from zope.app.traversing import namespace
from zope.app.testing import ztapi, setup
from zope.interface import implements, directlyProvides
from zope.app.filerepresentation.interfaces import IFileFactory, IWriteFile
from zope.interface.verify import verifyObject
from zope.app.location.interfaces import ILocation
from zope.app.traversing.interfaces import ITraversable
from zope.app.component.testing import PlacefulSetup
from zope.testing.doctest import DocTestSuite
from zope.publisher.browser import TestRequest
from zope.app.traversing.interfaces import IContainmentRoot

from schoolbell.app.rest.tests.utils import QuietLibxml2Mixin
from schoolbell.app.rest.tests.utils import XMLCompareMixin
from schoolbell.app.rest.errors import RestError


class TestTimetableReadView(PlacefulSetup, XMLCompareMixin, unittest.TestCase):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    full_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
          <day id="Day 1">
            <period id="A">
              <activity title="Maths">
                <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/room1"
                          xlink:title="Room1"/>
              </activity>
            </period>
            <period id="B">
              <activity title="English" />
              <activity title="French">
              </activity>
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
              <activity title="CompSci">
                <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/lab1"
                          xlink:title="Lab1"/>
                <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/lab2"
                          xlink:title="Lab2"/>
              </activity>
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    full_xml_with_exceptions = full_xml.replace('</timetable>', '') + """
        <exception date="2004-10-24" period="C">
          <activity title="CompSci">
            <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/lab1"
                      xlink:title="Lab1"/>
            <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/lab2"
                      xlink:title="Lab2"/>
          </activity>
        </exception>
        <exception date="2004-11-04" period="A">
          <activity title="Maths">
            <resource xlink:type="simple" xlink:href="http://127.0.0.1/resources/room1"
                      xlink:title="Room1"/>
          </activity>
          <replacement time="08:30" duration="45" uid="rpl-ev-uid1">
            Geometry
          </replacement>
        </exception>
        <exception date="2004-11-25" period="B">
          <activity title="English" />
          <replacement date="2004-11-26" time="12:45" duration="30"
                       uid="rpl-ev-uid2">
            English (short)
          </replacement>
        </exception>
        """ + "</timetable>"

    def setUp(self):
        from schooltool.app import SchoolToolApplication
        from schooltool.app import Person
        from schooltool.app import Resource
        PlacefulSetup.setUp(self)
        self.app = SchoolToolApplication()
        directlyProvides(self.app, IContainmentRoot)
        self.app["persons"]["john"] = self.person = Person("john", "John Smith")
        self.app["resources"]['room1'] = Resource("Room1")
        self.app["resources"]['lab1'] = Resource("Lab1")
        self.app["resources"]['lab2'] = Resource("Lab2")

    def createEmpty(self):
        from schooltool.timetable import Timetable, TimetableDay
        tt = Timetable(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableDay(['A', 'B'])
        tt['Day 2'] = TimetableDay(['C', 'D'])
        self.person.timetables['random.something'] = tt
        return tt

    def createFull(self, owner=None):
        from schooltool.timetable import TimetableActivity
        tt = self.createEmpty()
        room1 = self.app["resources"]['room1']
        lab1 = self.app["resources"]['lab1']
        lab2 = self.app["resources"]['lab2']
        tt['Day 1'].add('A', TimetableActivity('Maths', owner, [room1]))
        tt['Day 1'].add('B', TimetableActivity('English', owner))
        tt['Day 1'].add('B', TimetableActivity('French', owner))
        tt['Day 2'].add('C', TimetableActivity('CompSci', owner, [lab1, lab2]))
        return tt

    def createFullWithExceptions(self, owner=None):
        from schooltool.timetable import TimetableException
        from schooltool.timetable import ExceptionalTTCalendarEvent
        tt = self.createFull(owner)
        maths = list(tt['Day 1']['A'])[0]
        english = list(tt['Day 1']['B'])[0]
        compsci = list(tt['Day 2']['C'])[0]
        tt.exceptions.append(TimetableException(datetime.date(2004, 10, 24),
                                                'C', compsci))
        exc = TimetableException(datetime.date(2004, 11, 4), 'A', maths)
        exc.replacement = ExceptionalTTCalendarEvent(
                                       datetime.datetime(2004, 11, 4, 8, 30),
                                       datetime.timedelta(minutes=45),
                                       "Geometry",
                                       unique_id="rpl-ev-uid1",
                                       exception=exc)
        tt.exceptions.append(exc)
        exc = TimetableException(datetime.date(2004, 11, 25), 'B', english)
        exc.replacement = ExceptionalTTCalendarEvent(
                                       datetime.datetime(2004, 11, 26, 12, 45),
                                       datetime.timedelta(minutes=30),
                                       "English (short)",
                                       unique_id="rpl-ev-uid2",
                                       exception=exc)
        tt.exceptions.append(exc)
        return tt

    def createView(self, context, request):
        from schooltool.rest.timetable import TimetableReadView
        return TimetableReadView(context, request)

    def do_test_get(self, context, expected, ctype="text/xml"):
        request = TestRequest()
        view = self.createView(context, request)
        result = view.GET()
        self.assertEquals(request.response.getHeader('content-type'),
                          "%s; charset=UTF-8" % ctype)
        self.assertEqualsXML(result, expected, recursively_sort=['timetable'])

    def test_get(self):
        self.do_test_get(self.createEmpty(), self.empty_xml)
        self.do_test_get(self.createFull(), self.full_xml)
        self.do_test_get(self.createFullWithExceptions(),
                         self.full_xml_with_exceptions)


class TimetableSchemaMixin(QuietLibxml2Mixin):

    schema_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate>
              <used when="default" />
              <period id="A" tstart="9:00" duration="60" />
              <period id="C" tstart="9:00" duration="60" />
              <period id="B" tstart="10:00" duration="60" />
              <period id="D" tstart="10:00" duration="60" />
            </daytemplate>
            <daytemplate>
              <used when="Friday Thursday" />
              <period id="A" tstart="8:00" duration="60" />
              <period id="C" tstart="8:00" duration="60" />
              <period id="B" tstart="11:00" duration="60" />
              <period id="D" tstart="11:00" duration="60" />
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    def setUp(self):
        from schooltool.app import SchoolToolApplication
        from schooltool.interfaces import ITimetableSchemaContainer
        from schooltool.rest.timetable import TimetableSchemaFileFactory
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.interfaces import ITimetableModelFactory

        self.app = SchoolToolApplication()
        self.schemaContainer = self.app["ttschemas"]

        setup.placelessSetUp()
        setup.setUpTraversal()

        ztapi.provideAdapter(ITimetableSchemaContainer, IFileFactory,
                             TimetableSchemaFileFactory)

        ztapi.provideUtility(ITimetableModelFactory,
                             SequentialDaysTimetableModel,
                             "SequentialDaysTimetableModel")

        ztapi.provideView(Interface, Interface, ITraversable, 'view',
                          namespace.view)

        directlyProvides(self.schemaContainer, IContainmentRoot)

        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownLibxml2()
        setup.placelessTearDown()

    def createEmptySchema(self):
        from schooltool.timetable import TimetableSchema, TimetableSchemaDay

        timetable = TimetableSchema(['Day 1', 'Day 2'])
        timetable['Day 1'] = TimetableSchemaDay(['A', 'B'])
        timetable['Day 2'] = TimetableSchemaDay(['C', 'D'])
        return timetable

    def createExtendedSchema(self):
        from schooltool.timetable import SequentialDaysTimetableModel
        from schooltool.timetable import SchooldayPeriod, SchooldayTemplate
        from datetime import time, timedelta

        tt = self.createEmptySchema()

        day_template1 = SchooldayTemplate()
        hour = timedelta(minutes=60)
        day_template1.add(SchooldayPeriod('A', time(9, 0), hour))
        day_template1.add(SchooldayPeriod('B', time(10, 0), hour))
        day_template1.add(SchooldayPeriod('C', time(9, 0), hour))
        day_template1.add(SchooldayPeriod('D', time(10, 0), hour))

        day_template2 = SchooldayTemplate()
        hour = timedelta(minutes=60)
        day_template2.add(SchooldayPeriod('A', time(8, 0), hour))
        day_template2.add(SchooldayPeriod('B', time(11, 0), hour))
        day_template2.add(SchooldayPeriod('C', time(8, 0), hour))
        day_template2.add(SchooldayPeriod('D', time(11, 0), hour))
        tm = SequentialDaysTimetableModel(['Day 1', 'Day 2'],
                                          {None: day_template1,
                                           3: day_template2,
                                           4: day_template2})
        tt.model = tm
        return tt


class TestTimetableSchemaView(TimetableSchemaMixin, XMLCompareMixin,
                              unittest.TestCase):

    empty_xml = """
        <timetable xmlns="http://schooltool.org/ns/timetable/0.1">
          <model factory="SequentialDaysTimetableModel">
            <daytemplate>
              <used when="Friday Thursday"/>
              <period duration="60" id="A" tstart="08:00"/>
              <period duration="60" id="B" tstart="11:00"/>
              <period duration="60" id="C" tstart="08:00"/>
              <period duration="60" id="D" tstart="11:00"/>
            </daytemplate>
            <daytemplate>
              <used when="default"/>
              <period duration="60" id="A" tstart="09:00"/>
              <period duration="60" id="B" tstart="10:00"/>
              <period duration="60" id="C" tstart="09:00"/>
              <period duration="60" id="D" tstart="10:00"/>
            </daytemplate>
          </model>
          <day id="Day 1">
            <period id="A">
            </period>
            <period id="B">
            </period>
          </day>
          <day id="Day 2">
            <period id="C">
            </period>
            <period id="D">
            </period>
          </day>
        </timetable>
        """

    def test_get(self):
        from schooltool.rest.timetable import TimetableSchemaView
        request = TestRequest()
        view = TimetableSchemaView(self.createExtendedSchema(), request)

        result = view.GET()
        self.assertEquals(request.response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, self.empty_xml, recursively_sort=['timetable'])


class TestTimetableSchemaFileFactory(TimetableSchemaMixin, unittest.TestCase):

    def test(self):
        from schooltool.rest.timetable import TimetableSchemaFileFactory
        verifyObject(IFileFactory, TimetableSchemaFileFactory(self.schemaContainer))

    def test_call(self):
        factory = IFileFactory(self.schemaContainer)
        self.assertRaises(RestError, factory, "two_day", "text/plain", self.schema_xml)

    def test_parseXML(self):
        factory = IFileFactory(self.schemaContainer)
        schema = factory("two_day", "text/xml", self.schema_xml)
        self.assertEquals(schema, self.createExtendedSchema())


class TestTimetableSchemaFile(TimetableSchemaMixin, unittest.TestCase):

    def setUp(self):
        TimetableSchemaMixin.setUp(self)
        self.schemaContainer["two_day"] = self.createEmptySchema()

    def test(self):
        from schooltool.rest.timetable import TimetableSchemaFile
        verifyObject(IWriteFile,
                     TimetableSchemaFile(self.schemaContainer["two_day"]))

    def test_write(self):
        from schooltool.rest.timetable import TimetableSchemaFile
        schemaFile = TimetableSchemaFile(self.schemaContainer["two_day"])
        schemaFile.write(self.schema_xml)
        self.assertEquals(self.schemaContainer["two_day"],
                          self.createExtendedSchema())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('schooltool.rest.timetable'))
    suite.addTest(unittest.makeSuite(TestTimetableReadView))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaFileFactory))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaFile))
    suite.addTest(unittest.makeSuite(TestTimetableSchemaView))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
