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

from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import ztapi, setup

from schooltool.person.person import Person
from schooltool.xmlparsing import XMLDocument
from schooltool.testing import setup as sbsetup
from schooltool.testing.util import XMLCompareMixin


class TestAppView(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        setup.placefulSetUp()
        self.app = sbsetup.setupSchoolToolSite()
        from schooltool.app.rest.app import ApplicationView
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
            self.assert_(len(nodes) >= 3)

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
        # XXX: Very fragile test that depends on setup.
        #self.assertEqualsXML(result, """
        #    <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
        #      <message>Welcome to the SchoolTool server</message>
        #      <containers>
        #        <container xlink:type="simple"
        #                   xlink:href="http://127.0.0.1/persons"
        #                   xlink:title="persons"/>
        #        <container xlink:href="http://127.0.0.1/resources"
        #                   xlink:title="resources"
        #                   xlink:type="simple"/>
        #        <container xlink:type="simple"
        #                   xlink:href="http://127.0.0.1/groups"
        #                   xlink:title="groups"/>
        #      </containers>
        #    </schooltool>
        #    """, recursively_sort=["schooltool"])


def doctest_CalendarView():
    r"""Tests for CalendarView.

        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

        >>> from schooltool.testing import setup as sbsetup
        >>> sbsetup.setupCalendaring()

    First lets create a view:

        >>> from schooltool.app.rest.app import CalendarView
        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> from schooltool.app.cal import WriteCalendar
        >>> from schooltool.app.interfaces import IWriteCalendar
        >>> ztapi.provideAdapter(ISchoolToolCalendar, IWriteCalendar,
        ...                      WriteCalendar)

        >>> person = Person()
        >>> calendar = ISchoolToolCalendar(person)
        >>> view = CalendarView(calendar, TestRequest())

        >>> print view.GET().replace("\r\n", "\n")
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
    suite.addTest(doctest.DocTestSuite('schooltool.app.rest.app'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
