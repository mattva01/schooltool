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
from StringIO import StringIO

import zope
from zope.interface import Interface
from zope.interface.verify import verifyObject
from zope.app.traversing.interfaces import ITraversable
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.http import IHTTPRequest
from zope.testing import doctest

from zope.app.component.testing import PlacefulSetup
from zope.app.container.interfaces import INameChooser
from zope.app.testing import ztapi, setup

from schoolbell.app.app import SimpleNameChooser
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.rest.group import GroupFileFactory, GroupContainerView
from schooltool.person.person import Person
from schooltool.resource.interfaces import IResourceContainer
from schooltool.resource.rest.resource import ResourceFileFactory
from schoolbell.app.rest.tests.utils import XMLCompareMixin, QuietLibxml2Mixin
from schoolbell.app.rest.xmlparsing import XMLDocument, XMLParseError

from schooltool.testing import setup as sbsetup

class TestAppView(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        setup.placefulSetUp()
        self.app = sbsetup.setupSchoolBellSite()
        from schoolbell.app.rest.app import ApplicationView
        self.view = ApplicationView(self.app, TestRequest())

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
              <message>Welcome to the SchoolBell server</message>
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


class ContainerViewTestMixin(XMLCompareMixin, QuietLibxml2Mixin):
    """Common code for Container View tests"""

    def setUp(self):
        setup.placefulSetUp()
        self.setUpLibxml2()

        from zope.app.filerepresentation.interfaces import IFileFactory
        ztapi.provideView(Interface, Interface, ITraversable, 'view',
                          zope.app.traversing.namespace.view)
        ztapi.provideAdapter(IGroupContainer, INameChooser,
                             SimpleNameChooser)
        ztapi.provideAdapter(IGroupContainer, IFileFactory,
                             GroupFileFactory)
        ztapi.provideAdapter(IResourceContainer, IFileFactory,
                             ResourceFileFactory)


        self.app = sbsetup.setupSchoolBellSite()
        self.groupContainer = self.app['groups']
        self.group = self.app['groups']['root'] = Group("Root group")


    def tearDown(self):
        self.tearDownLibxml2()
        setup.placefulTearDown()

    def test_post(self, suffix="", view=None,
                  body="""<object xmlns="http://schooltool.org/ns/model/0.1"
                                  title="New Group"/>"""):
        view = GroupContainerView(self.groupContainer,
                                  TestRequest(StringIO(body)))
        result = view.POST()
        response = view.request.response

        self.assertEquals(response.getStatus(), 201)
        self.assertEquals(response._reason, "Created")

        location = response.getHeader('location')
        base = "http://127.0.0.1/groups/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['groups'].keys())
        self.assertEquals(response.getHeader('content-type'),
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        return name

    def test_post_with_a_description(self):
        name = self.test_post(body='''
            <object title="New Group"
                    description="A new group"
                    xmlns='http://schooltool.org/ns/model/0.1'/>''')
        self.assertEquals(self.app['groups'][name].title, 'New Group')
        self.assertEquals(self.app['groups'][name].description, 'A new group')
        self.assertEquals(name, 'new-group')

    def test_post_error(self):
        view = GroupContainerView(
            self.groupContainer,
            TestRequest(StringIO('<element title="New Group">')))
        self.assertRaises(XMLParseError, view.POST)


class FileFactoriesSetUp(PlacefulSetup):

    def setUp(self):
        from zope.app.filerepresentation.interfaces import IFileFactory
        PlacefulSetup.setUp(self)
        ztapi.provideAdapter(IGroupContainer,
                             IFileFactory,
                             GroupFileFactory)
        ztapi.provideAdapter(IResourceContainer,
                             IFileFactory,
                             ResourceFileFactory)


class ApplicationObjectViewTestMixin(ContainerViewTestMixin):

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
        self.personContainer = self.app['persons']
        self.groupContainer = self.app['groups']

    def get(self):
        """Perform a GET of the view being tested."""
        view = self.makeTestView(self.testObject, TestRequest())
        result = view.GET()

        return result, view.request.response


def doctest_CalendarView():
    r"""Tests for CalendarView.

        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

        >>> from schooltool.testing import setup as sbsetup
        >>> sbsetup.setupCalendaring()

    First lets create a view:

        >>> from schoolbell.app.rest.app import CalendarView
        >>> from schoolbell.app.interfaces import ISchoolBellCalendar
        >>> from schooltool.app.cal import WriteCalendar
        >>> from schoolbell.app.interfaces import IWriteCalendar
        >>> ztapi.provideAdapter(ISchoolBellCalendar, IWriteCalendar,
        ...                      WriteCalendar)

        >>> person = Person()
        >>> calendar = ISchoolBellCalendar(person)
        >>> view = CalendarView(calendar, TestRequest())

        >>> print view.GET()._outstream.getvalue().replace("\r\n", "\n")
        Status: 200 Ok
        Content-Length: ...
        Content-Type: text/calendar; charset=UTF-8
        X-Powered-By: Zope (www.zope.org), Python (www.python.org)
        <BLANKLINE>
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN
        BEGIN:VEVENT
        UID:empty-calendar-placeholder@schooltool.org
        SUMMARY:Empty calendar
        DTSTART:19700101T000000Z
        DURATION:P0D
        DTSTAMP:...
        END:VEVENT
        END:VCALENDAR
        <BLANKLINE>

        >>> calendar_text = '''\
        ... BEGIN:VCALENDAR
        ... VERSION:2.0
        ... PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN
        ... BEGIN:VEVENT
        ... UID:some-random-uid@example.com
        ... SUMMARY:LAN party %s
        ... DTSTART:20050226T160000Z
        ... DURATION:PT6H
        ... DTSTAMP:20050203T150000
        ... END:VEVENT
        ... END:VCALENDAR
        ... ''' %  chr(163)

        >>> view.request = TestRequest(StringIO(calendar_text),
        ...     environ={'CONTENT_TYPE': 'text/plain; charset=latin-1'})

        >>> view.PUT()
        ''
        >>> titles = [e.title for e in calendar]
        >>> titles[0]
        u'LAN party \xa3'

    Cleanup:

        >>> setup.placelessTearDown()

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.rest.app'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
