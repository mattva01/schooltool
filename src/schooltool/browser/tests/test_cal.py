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
Unit tests for schooltool.browser.cal

$Id$
"""

import unittest
import datetime
from logging import INFO

from schooltool.browser.tests import RequestStub, setPath

__metaclass__ = type


class TestBookingView(unittest.TestCase):

    def setUp(self):
        from schooltool.model import Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer

        self.app = Application()
        self.app['persons'] = ApplicationObjectContainer(Person)
        resrc = self.app['resources'] = ApplicationObjectContainer(Resource)

        self.person = self.app['persons'].new("me", title="Me")
        self.resource = resrc.new("sink", title="Kitchen sink")

    def createView(self):
        from schooltool.model import Resource
        from schooltool.browser.cal import BookingView
        view = BookingView(self.resource)
        view.authorization = lambda ctx, rq: True
        return view

    def test(self):
        view = self.createView()
        request = RequestStub(args={'conflicts': 'ignore',
                                    'owner': '/persons/me',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:01',
                                    'duration': '61'})
        view.do_POST(request)
        self.assertEquals(view.error, "")
        self.assertEquals(request.applog,
                [(None, u'/resources/sink (Kitchen sink) booked by'
                  ' /persons/me (Me) at 2004-08-10 19:01:00 for 1:01:00',
                  INFO)])

        self.assertEquals(len(list(self.person.calendar)), 1)
        self.assertEquals(len(list(self.resource.calendar)), 1)
        ev1 = iter(self.person.calendar).next()
        ev2 = iter(self.resource.calendar).next()
        self.assertEquals(ev1, ev2)
        self.assert_(ev1.context is self.resource,
                     "%r is not %r" % (ev1.context, self.resource))
        self.assert_(ev1.owner is self.person,
                     "%r is not %r" % (ev1.owner, self.person))

    def test_conflict(self):
        from schooltool.cal import CalendarEvent
        from schooltool.common import parse_datetime
        ev = CalendarEvent(parse_datetime('2004-08-10 19:00:00'),
                           datetime.timedelta(hours=1), "Some event")
        self.resource.calendar.addEvent(ev)
        self.assertEquals(len(list(self.person.calendar)), 0)
        self.assertEquals(len(list(self.resource.calendar)), 1)

        view = self.createView()
        request = RequestStub(args={'owner': '/persons/me',
                                    'start_date': '2004-08-10',
                                    'start_time': '19:20',
                                    'duration': '61'})
        view.do_POST(request)
        self.assertEquals(request.applog, [])
        self.assertEquals(view.error, "The resource is busy at specified time")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingView))
    return suite


if __name__ == '__main__':
    unittest.main()
