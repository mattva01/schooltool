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
Unit tests for schooltool.rest.app

$Id$
"""

import unittest
from schooltool.common import dedent
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import XMLCompareMixin, EqualsSortedMixin
from schooltool.tests.utils import QuietLibxml2Mixin, NiceDiffsMixin
from schooltool.rest.tests import RequestStub, UtilityStub
from schooltool.rest.tests import XPathTestContext


__metaclass__ = type


class TestAppView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.rest.app import ApplicationView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool import membership, rest
        self.setUpRegistries()
        membership.setUp()
        rest.setUp()
        self.app = Application()
        self.app['groups'] = ApplicationObjectContainer(Group)
        self.app['persons'] = ApplicationObjectContainer(Person)
        self.group = self.app['groups'].new("root", title="Root group")
        self.app.addRoot(self.group)

        self.app.utilityService["foo"] = UtilityStub("Foo utility")

        self.view = ApplicationView(self.app)
        self.view.authorization = lambda ctx, rq: True

    def tearDown(self):
        from schooltool.component import resetViewRegistry
        resetViewRegistry()
        RegistriesSetupMixin.tearDown(self)

    def test_render_Usingxpath(self):
        request = RequestStub("http://localhost/")
        result = self.view.render(request)

        context = XPathTestContext(self, result)
        try:
            containers = context.oneNode('/schooltool/containers')
            context.assertNumNodes(2, '/schooltool/containers/container')
            persons = context.oneNode(
                '/schooltool/containers/container[@xlink:href="/persons"]')
            groups = context.oneNode(
                '/schooltool/containers/container[@xlink:href="/groups"]')

            context.assertAttrEquals(persons, 'xlink:type', 'simple')
            context.assertAttrEquals(persons, 'xlink:title', 'persons')

            context.assertAttrEquals(groups, 'xlink:type', 'simple')
            context.assertAttrEquals(groups, 'xlink:title', 'groups')
        finally:
            context.free()
        context.assertNoErrors()

    def test_render(self):
        request = RequestStub("http://localhost/")
        result = self.view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
              <message>Welcome to the SchoolTool server</message>
              <roots>
                <root xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="Root group"/>
              </roots>
              <containers>
                <container xlink:type="simple" xlink:href="/persons"
                           xlink:title="persons"/>
                <container xlink:type="simple" xlink:href="/groups"
                           xlink:title="groups"/>
              </containers>
              <utilities>
                <utility xlink:type="simple" xlink:href="/utils/foo"
                         xlink:title="Foo utility"/>
              </utilities>
              <schooltt xlink:href="/schooltt"
                        xlink:title="Whole school timetables"
                        xlink:type="simple"/>
              <time-periods xlink:href="/time-periods"
                            xlink:title="Time periods"
                            xlink:type="simple"/>
              <ttschemas xlink:href="/ttschemas"
                         xlink:title="Timetable schemas"
                         xlink:type="simple"/>
       </schooltool>
            """, recursively_sort=["schooltool"])

    def test__traverse(self):
        from schooltool.rest.app import ApplicationObjectContainerView
        from schooltool.rest.app import AvailabilityQueryView
        from schooltool.rest.app import UriObjectListView
        from schooltool.rest.utility import UtilityServiceView
        from schooltool.rest.timetable import SchoolTimetableTraverseView
        from schooltool.rest.cal import AllCalendarsView
        from schooltool.rest.csvexport import CSVExporter
        request = RequestStub("http://localhost/groups")
        view = self.view._traverse('groups', request)
        self.assert_(view.__class__ is ApplicationObjectContainerView)
        self.assertRaises(KeyError, self.view._traverse, 'froups', request)

        view = self.view._traverse('utils', request)
        self.assert_(view.__class__ is UtilityServiceView)

        view = self.view._traverse('schooltt', request)
        self.assert_(view.__class__ is SchoolTimetableTraverseView)
        self.assert_(view.context is self.view.context)

        view = self.view._traverse('calendars.html', request)
        self.assert_(view.__class__ is AllCalendarsView)
        self.assert_(view.context is self.view.context)

        view = self.view._traverse('busysearch', request)
        self.assert_(view.__class__ is AvailabilityQueryView)
        self.assert_(view.context is self.view.context)

        view = self.view._traverse('csvexport.zip', request)
        self.assert_(view.__class__ is CSVExporter)
        self.assert_(view.context is self.view.context)

        view = self.view._traverse('uris', request)
        self.assert_(view.__class__ is UriObjectListView)
        self.assert_(view.context is self.view.context)


class TestAppObjContainerView(XMLCompareMixin, RegistriesSetupMixin,
                              QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        from schooltool.rest.app import ApplicationObjectContainerView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool import membership, rest
        self.setUpLibxml2()
        self.setUpRegistries()
        membership.setUp()
        rest.setUp()
        self.app = Application()
        self.app['groups'] = ApplicationObjectContainer(Group)
        self.app['persons'] = ApplicationObjectContainer(Person)
        self.group = self.app['groups'].new("root", title="Root group")
        self.app.addRoot(self.group)

        self.view = ApplicationObjectContainerView(self.app['groups'])
        self.view.authorization = lambda ctx, rq: True

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def test_render(self):
        request = RequestStub("http://localhost/groups")
        result = self.view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>groups</name>
              <items>
                <item xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="Root group"/>
              </items>
            </container>
            """)

    def test_post(self, suffix="", method="POST", view=None,
                  body="<object xmlns='http://schooltool.org/ns/model/0.1'/>"):
        if view is None:
            view = self.view

        request = RequestStub("http://localhost:7001/groups" + suffix,
                              method=method, body=body)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        location = request.headers['location']
        base = "http://localhost:7001/groups/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['groups'].keys())
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        return name

    def test_post_with_a_title(self):
        name = self.test_post(body='''
            <object title="New Group"
                    xmlns='http://schooltool.org/ns/model/0.1'/>''')
        self.assert_(self.app['groups'][name].title == 'New Group')

    def test_post_error(self):
        request = RequestStub("http://localhost:7001/groups", method="POST",
                              body='<element title="New Group">')
        self.view.authorization = lambda ctx, rq: True
        result = self.view.render(request)
        self.assertEquals(request.code, 400)

    def test_get_child(self, method="GET"):
        from schooltool.rest.app import ApplicationObjectCreatorView
        view = ApplicationObjectCreatorView(self.app['groups'], 'foo')
        request = RequestStub("http://localhost/groups/foo", method=method)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.code, 404)
        self.assertEquals(request.reason, "Not Found")

    def test_delete_child(self):
        self.test_get_child(method="DELETE")

    def test_put_child(self):
        from schooltool.rest.app import ApplicationObjectCreatorView
        view = ApplicationObjectCreatorView(self.app['groups'], 'foo')
        name = self.test_post(method="PUT", suffix="/foo", view=view)
        self.assertEquals(name, 'foo')

        view = ApplicationObjectCreatorView(self.app['groups'], 'bar')
        xml = '''<object title="Bar Bar \xe2\x98\xbb"
                         xmlns='http://schooltool.org/ns/model/0.1'/>'''
        name = self.test_post(method="PUT", suffix="/bar", view=view,
                              body=xml)
        self.assertEquals(name, 'bar')
        self.assert_(self.app['groups'][name].title == u'Bar Bar \u263B')

    def test__traverse(self):
        from schooltool.rest.model import GroupView
        from schooltool.rest.app import ApplicationObjectCreatorView
        request = RequestStub("http://localhost/groups/root")
        view = self.view._traverse('root', request)
        self.assert_(view.__class__ is GroupView)
        view = self.view._traverse('newchild', request)
        self.assert_(view.__class__ is ApplicationObjectCreatorView)
        self.assertEquals(view.context, self.view.context)
        self.assertEquals(view.name, 'newchild')


class TestAvailabilityQueryView(unittest.TestCase, XMLCompareMixin,
                                EqualsSortedMixin):

    def setUp(self):
        from schooltool.rest.app import AvailabilityQueryView
        from schooltool.model import Resource, Person
        from schooltool.app import Application, ApplicationObjectContainer
        self.app = Application()
        self.app['resources'] = ApplicationObjectContainer(Resource)
        self.room1 = self.app['resources'].new('room1', title='Room 1')
        self.room2 = self.app['resources'].new('room2', title='Room 2')
        self.room3 = self.app['resources'].new('room3', title='Room 3')

        self.app['persons'] = ApplicationObjectContainer(Person)
        self.person = self.app['persons'].new('albert', title='Albert')

        self.view = AvailabilityQueryView(self.app)
        self.view.authorization = lambda ctx, rq: True

        def addEvent(cal, day, hr, dur, title):
            """A helper to avoid verbiage involved in adding events to
            a calendar.
            """
            from schooltool.cal import CalendarEvent
            from datetime import datetime, timedelta
            ev = CalendarEvent(datetime(2004, 1, day, hr, 0),
                               timedelta(minutes=dur), title)
            cal.addEvent(ev)

        addEvent(self.room1.calendar, 2, 11, 45, "English")
        addEvent(self.room2.calendar, 3, 12, 240, "Conference")

    def test_parseHours(self):
        from datetime import time, timedelta
        cases = [
            (range(24), [(time(0,0), timedelta(hours=24))]),

            (['11', '12'], [(time(11,0), timedelta(hours=2))]),

            (['0', '1', '6', '22', '23'], [(time(0,0), timedelta(hours=2)),
                                           (time(6,0), timedelta(hours=1)),
                                           (time(22,0), timedelta(hours=2))]),
            ]
        for hours, expected in cases:
            periods = self.view.parseHours(hours)
            self.assertEquals(periods, expected)

    def test_args(self):
        from datetime import date, time, timedelta
        expected = """
            <availability xmlns:xlink="http://www.w3.org/1999/xlink">
              <resource xlink:href="/resources/room1" xlink:title="Room 1"
                        xlink:type="simple">
                <slot duration="135" start="2004-01-02 11:45:00"/>
                <slot duration="180" start="2004-01-03 11:00:00"/>
              </resource>
              <resource xlink:href="/resources/room2" xlink:title="Room 2"
                        xlink:type="simple">
                <slot duration="180" start="2004-01-02 11:00:00"/>
                <slot duration="60" start="2004-01-03 11:00:00"/>
              </resource>
            </availability>
            """
        request = RequestStub('/availability', method="GET")
        request.args.update({'first': ['2004-01-02'],
                             'last': ['2004-01-03'],
                             'duration': ['22'],
                             'hours': ['12', '11', '13'],
                             'resources': ['/resources/room1',
                                           '/resources/room2',]})
        result = self.view.render(request)
        self.assertEquals(request.code, 200)
        self.assertEquals(self.view.first, date(2004, 1, 2))
        self.assertEquals(self.view.last, date(2004, 1, 3))
        self.assertEquals(self.view.duration, timedelta(minutes=22))
        self.assertEquals(self.view.hours, [(time(11, 0), timedelta(hours=3))])
        self.assertEquals(self.view.resources,
                          [self.room1, self.room2])
        self.assertEqualsXML(result, expected)

    def test_no_hours(self):
        from datetime import time, timedelta
        request = RequestStub('/availability', method="GET")
        request.args.update({'first': ['2004-01-02'],
                             'last': ['2004-01-03'],
                             'duration': ['22'],
                             'resources': ['/resources/room1',
                                           '/resources/room2',]})
        result = self.view.render(request)
        self.assertEquals(self.view.hours, [(time(0, 0), timedelta(hours=24))])

    def testResourceArg(self):
        request = RequestStub('/availability', method="GET")
        request.args.update({'first': ['2004-01-02'],
                             'last': ['2004-01-03'],
                             'duration': ['22'],
                             'hours': ['12', '11', '13']})
        result = self.view.render(request)
        self.assertEqualsSorted(self.view.resources,
                                [self.room1, self.room2, self.room3])

    def testErrors(self):
        request = RequestStub('/availability', method="GET")
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(result, "'first' argument must be provided")

        request.args['first'] = ['2004-01-01']
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(result, "'last' argument must be provided")

        request.args['last'] = ['2004-01-01']
        result = self.view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(result, "'duration' argument must be provided")

        for arg, badvalue in [('first', ['2004-01-aa']),
                              ('last', ['2004-01-aa']),
                              ('duration', ['aa']),
                              ('hours', [ 'hm']),]:
            request.args['duration'] = ['90']
            request.args['first'] = ['2004-01-01']
            request.args['last'] = ['2004-01-01']

            request.args[arg] = badvalue
            result = self.view.render(request)
            self.assertEquals(request.code, 400)
            self.assertEquals(result, "'%s' argument is invalid" % arg)

        del request.args['hours']
        for value, error in [(['/persons/albert'],
                              "'/persons/albert' is not a resource"),
                             (['/resources/foo'],
                              "Invalid resource: '/resources/foo'"),
                             (['foo'], "Invalid resource: 'foo'")]:
            request.args['duration'] = ['90']
            request.args['first'] = ['2004-01-01']
            request.args['last'] = ['2004-01-01']

            request.args['resources'] = value
            result = self.view.render(request)
            self.assertEquals(request.code, 400)
            self.assertEquals(result, error)


class TestUriObjectListView(NiceDiffsMixin, XMLCompareMixin,
                            RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.rest.app import UriObjectListView
        from schooltool.app import Application
        from schooltool.uris import URIObject, registerURI, resetURIRegistry
        self.setUpRegistries()
        URI1 = URIObject("http://example.com/foobar",
                         name="da name",
                         description="A long\ndescription")
        URI2 = URIObject("http://example.com/foo",
                         name="da name",
                         description="Another long\ndescription")
        resetURIRegistry()
        registerURI(URI1)
        registerURI(URI2)
        self.app = Application()
        self.view = UriObjectListView(self.app)

    def tearDown(self):
        self.tearDownRegistries()

    def test_render(self):
        request = RequestStub("http://localhost/uris")
        result = self.view.render(request)
        self.assertEqualsXML(result, dedent("""
                <uriobjects>
                  <uriobject uri="http://example.com/foobar">
                    <name>da name</name>
                    <description>A long
                description</description>
                  </uriobject>
                  <uriobject uri="http://example.com/foo">
                    <name>da name</name>
                    <description>Another long
                description</description>
                  </uriobject>
                </uriobjects>
                """))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    suite.addTest(unittest.makeSuite(TestAppObjContainerView))
    suite.addTest(unittest.makeSuite(TestAvailabilityQueryView))
    suite.addTest(unittest.makeSuite(TestUriObjectListView))
    return suite

if __name__ == '__main__':
    unittest.main()
