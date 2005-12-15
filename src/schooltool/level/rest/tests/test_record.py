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
import datetime
import unittest
import cStringIO

import zope.interface
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.component.testing import PlacefulSetup
from zope.app.location.interfaces import ILocation

from schooltool.app.rest.testing import ApplicationObjectViewTestMixin
from schooltool.app.rest.errors import RestError
from schooltool.group.group import Group
from schooltool.person.person import Person
from schooltool.testing import setup

import schooltool.level.rest.record
from schooltool.level import record, rest, testing, level


def testAcademicStatus():
    """Test academic status adapter.

    First we have to create a record stub:

      >>> class AcademicRecord(object):
      ...     status = None

    Now we can create the adapter that will access the status:

      >>> record = AcademicRecord()
      >>> status = rest.record.AcademicStatus(record)

    Initially there is no status:

      >>> status.getStatus()

    Once, we set the status, it will be available:

      >>> status.setStatus(u'some value')
      >>> status.getStatus()
      u'some value'
      >>> record.status
      u'some value'
    """

def testAcademicHistory():
    """Test for academic history adapter.

    First we have to create a record stub:

      >>> class AcademicRecord(object):
      ...     pass

    Now we can create the adapter:

      >>> record = AcademicRecord()
      >>> history = rest.record.AcademicHistory(record)

    That's it.
    """

def testAcademicProcessCreator():
    """Test for academic process creator adapter.

    First we have to create a record stub:

      >>> class AcademicRecord(object):
      ...     context = None
      ...     levelProcess = None

    Next let's ensure we have a full-blown setup:

      >>> from zope.app.testing.setup import placefulSetUp
      >>> placefulSetUp()
      >>> app = setup.setupSchoolToolSite()
      >>> app['groups']['manager'] = Group('manager', 'School Manager')

    Then we need to make sure that persons can be annotated:

      >>> zope.interface.classImplements(Person, IAttributeAnnotatable)

    Now we can create the adapter:

      >>> record = AcademicRecord()
      >>> record.context = Person('srichter', 'Stephan Richter')
      >>> creator = rest.record.AcademicProcessCreator(record)

    Once we setup the promotion workflow code, then we can attach a new
    process instance:

      >>> testing.setUpPromotionWorkflow()
      >>> creator.create()

      >>> record.levelProcess
      Process('schooltool.promotion')

    Cleanup:

      >>> from zope.app.testing.setup import placefulTearDown
      >>> placefulTearDown()
    """


class TestAcademicStatusView(ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of teh academic status."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        class AcademicRecord(object):
            status = 'Initial Status'

        self.testObject = rest.record.AcademicStatus(AcademicRecord())

    def makeTestView(self, object, request):
        return rest.record.AcademicStatusView(object, request)

    def testGET(self):
        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'), "text/plain")
        self.assertEquals(result, 'Initial Status')

    def testPOST(self):
        request = TestRequest(cStringIO.StringIO('new status'))
        view = self.makeTestView(self.testObject, request)
        view.POST()
        self.assertEqual(self.testObject.getStatus(), 'new status')

        request = TestRequest(cStringIO.StringIO('new status'),
                              environ={'HTTP_CONTENT_SOMETHING': True})
        view = self.makeTestView(self.testObject, request)
        view.POST()
        self.assertEqual(request.response.getStatus(), 501)


class TestAcademicHistoryView(ApplicationObjectViewTestMixin,
                              unittest.TestCase):
    """A test for the RESTive view of the academic history."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        entry1 = record.HistoricalRecord('Entry 1', 'This is entry 1.')
        entry1.timestamp = datetime.datetime(2005, 01, 25, 3, 0, 0)
        entry2 = record.HistoricalRecord('Entry 2', 'This is entry 2.')
        entry2.timestamp = datetime.datetime(2005, 01, 25, 4, 0, 0)

        class AcademicRecord(object):
            history = [entry1, entry2]

        self.testObject = rest.record.AcademicHistory(AcademicRecord())

    def makeTestView(self, object, request):
        return rest.record.AcademicHistoryView(object, request)

    def testHistory(self):
        request = TestRequest()
        view = self.makeTestView(self.testObject, request)
        self.assertEqual(
            list(view.history()),
            [{'timestamp': u'2005 1 25  03:00:00 ',
              'description': 'This is entry 1.',
              'title': 'Entry 1'},
             {'timestamp': u'2005 1 25  04:00:00 ',
              'description': 'This is entry 2.',
              'title': 'Entry 2'}])

    def testGET(self):
        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(
            result, '''
            <history>
              <entry>
                <title>Entry 1</title>
                <description>This is entry 1.</description>
                <timestamp>2005 1 25  03:00:00</timestamp>
              </entry>
              <entry>
                <title>Entry 2</title>
                <description>This is entry 2.</description>
                <timestamp>2005 1 25  04:00:00</timestamp>
              </entry>
            </history>''')


class TestAcademicProcessCreatorView(ApplicationObjectViewTestMixin,
                                     PlacefulSetup, unittest.TestCase):
    """A test for the RESTive view of the academic process creation."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)
        testing.setUpPromotionWorkflow()

        zope.interface.classImplements(Person, IAttributeAnnotatable)

        app = setup.setupSchoolToolSite()
        app['groups']['manager'] = Group('manager', 'School Manager')


        class AcademicRecord(object):
            context = Person('srichter', 'Stephan Richter')
            levelProcess = None

        self.testObject = rest.record.AcademicProcessCreator(AcademicRecord())

    def makeTestView(self, object, request):
        return rest.record.AcademicProcessCreatorView(object, request)

    def testGET(self):
        result, response = self.get()
        self.assertEqual(response.getHeader('content-type'), "text/plain")
        self.assertEqual(response.getStatus(), 200)

    def testPUT(self):
        request = TestRequest()
        view = self.makeTestView(self.testObject, request)
        view.PUT()
        self.assertEqual(request.response.getStatus(), 200)
        self.assert_(self.testObject.record.levelProcess is not None)


class TestSelectInitialLevelView(ApplicationObjectViewTestMixin, PlacefulSetup,
                                 unittest.TestCase):

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        app = setup.setupSchoolToolSite()
        app['levels']['level1'] = level.Level('level1', '1st Grade')
        self.level1 = app['levels']['level1']

        class WorkItem(object):
            level = None
            def finish(self, level):
                self.level = level

        self.testObject = WorkItem()

    def makeTestView(self, object, request):
        return rest.record.SelectInitialLevelView(object, request)

    def testPOST(self):
        request = TestRequest(
            cStringIO.StringIO('''
                <object xmlns="http://schooltool.org/ns/model/0.1"
                        initialLevel="level1" />'''))
        view = self.makeTestView(self.testObject, request)
        view.POST()
        self.assertEqual(self.testObject.level, self.level1)

        request = TestRequest(
            cStringIO.StringIO('''
                <object xmlns="http://schooltool.org/ns/model/0.1"
                        initialLevel="level2" />'''))
        view = self.makeTestView(self.testObject, request)
        self.assertRaises(RestError, view.POST)


class TestSetLevelOutcomeView(ApplicationObjectViewTestMixin, PlacefulSetup,
                              unittest.TestCase):

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        app = setup.setupSchoolToolSite()
        app['levels']['level1'] = level.Level('level1', '1st Grade')
        self.level1 = app['levels']['level1']

        class WorkItem(object):
            zope.interface.implements(ILocation)
            __name__ = 'level1'
            outcome = None
            def __getattr__(self, name):
                return self
            def finish(self, outcome):
                self.outcome = outcome

        self.testObject = WorkItem()

    def makeTestView(self, object, request):
        return rest.record.SetLevelOutcomeView(object, request)

    def testLevel(self):
        request = TestRequest()
        view = self.makeTestView(self.testObject, request)
        self.assertEqual(view.level(), 'level1')

    def testPOST(self):
        request = TestRequest(
            cStringIO.StringIO('''
                <object xmlns="http://schooltool.org/ns/model/0.1"
                        outcome="pass" />'''))
        view = self.makeTestView(self.testObject, request)
        self.assertEqual(view.POST(), "Outcome submitted.")
        self.assertEqual(self.testObject.outcome, 'pass')


def test_suite():
    suite = unittest.TestSuite((
        unittest.makeSuite(TestAcademicStatusView),
        unittest.makeSuite(TestAcademicHistoryView),
        unittest.makeSuite(TestAcademicProcessCreatorView),
        unittest.makeSuite(TestSelectInitialLevelView),
        unittest.makeSuite(TestSetLevelOutcomeView),
        ))
    suite.addTest(doctest.DocTestSuite(
        optionflags=doctest.ELLIPSIS|
                    doctest.REPORT_NDIFF|
                    doctest.REPORT_ONLY_FIRST_FAILURE)
        )

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
