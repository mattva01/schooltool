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
Unit tests for schooltool.views.eventlog

$Id$
"""

import datetime
import unittest
from schooltool.tests.helpers import diff
from schooltool.tests.utils import XMLCompareMixin
from schooltool.views.tests import RequestStub

__metaclass__ = type


class EventLogStub:

    received = []

    def getReceived(self):
        return self.received

    def clear(self):
        self.received = []


class EventStub:

    def __str__(self):
        return "Fake event"

    def __repr__(self):
        return "EventStub()"


class TestEventLogView(XMLCompareMixin, unittest.TestCase):

    def test_empty(self):
        from schooltool.views.eventlog import EventLogView
        context = EventLogStub()
        view = EventLogView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub("http://localhost/foo/eventlog")
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <eventLog>
            </eventLog>
            """)

    def test_nonempty(self):
        from schooltool.views.eventlog import EventLogView
        context = EventLogStub()
        context.received = [(datetime.datetime(2003, 10, 01, 11, 12, 13),
                             EventStub())]
        view = EventLogView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub("http://localhost/foo/eventlog")
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <eventLog>
              <event ts="2003-10-01 11:12:13">Fake event</event>
            </eventLog>
            """)

    def test_clear(self):
        from schooltool.views.eventlog import EventLogView
        context = EventLogStub()
        context.received = [(datetime.datetime(2003, 10, 01, 11, 12, 13),
                             EventStub())]
        view = EventLogView(context)
        view.authorization = lambda ctx, rq: True
        request = RequestStub("http://localhost/foo/eventlog", "PUT")
        result = view.render(request)
        expected = "1 event cleared"
        self.assertEquals(result, expected, "\n" + diff(expected, result))

        result = view.render(request)
        expected = "0 events cleared"
        self.assertEquals(result, expected, "\n" + diff(expected, result))

        request = RequestStub("http://localhost/foo/eventlog", "PUT")
        request.content.write("something")
        request.content.seek(0)
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(result,
                "Only PUT with an empty body is defined for event logs")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventLogView))
    return suite

if __name__ == '__main__':
    unittest.main()
