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
Unit tests for schooltool.views.model

$Id$
"""

import unittest
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.views.tests import RequestStub, viewClass

__metaclass__ = type


class AbsenceTrackerStub:

    def __init__(self):
        self.absences = []


class TestApplicationObjectTraverserView(RegistriesSetupMixin,
                                         unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import ApplicationObjectTraverserView
        from schooltool.model import Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['persons'] = ApplicationObjectContainer(Person)
        self.per = app['persons'].new("p", title="Pete")
        self.view = ApplicationObjectTraverserView(self.per)
        self.view.authorization = lambda ctx, rq: True

    def test_traverse(self):
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.views.cal import CalendarView, CalendarReadView
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.timetable import CompositeTimetableTraverseView
        from schooltool.interfaces import IFacetManager

        request = RequestStub("http://localhost/people/p")
        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.providedBy(result.context))

        result = self.view._traverse('calendar', request)
        self.assert_(isinstance(result, CalendarView))
        self.assert_(result.context is self.view.context.calendar)

        result = self.view._traverse('timetable-calendar', request)
        self.assert_(isinstance(result, CalendarReadView))

        result = self.view._traverse('timetables', request)
        self.assert_(isinstance(result, TimetableTraverseView))
        self.assert_(result.context is self.view.context)

        result = self.view._traverse('composite-timetables', request)
        self.assert_(isinstance(result, CompositeTimetableTraverseView))
        self.assert_(result.context is self.view.context)

        self.assertRaises(KeyError, self.view._traverse, 'anything', request)


class TestGroupView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import GroupView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.per = app['persons'].new("p", title="p")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)

        self.view = GroupView(self.group)
        self.view.authorization = lambda ctx, rq: True

    def tearDown(self):
        self.tearDownRegistries()

    def test_render(self):
        from schooltool.component import getPath
        request = RequestStub("http://localhost/group/")
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <group xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>group</name>
              <item xlink:type="simple" xlink:title="p"
                    xlink:href="%s"/>
              <item xlink:type="simple" xlink:title="subgroup"
                    xlink:href="%s"/>
              <facets xlink:type="simple" xlink:title="Facets"
                      xlink:href="/groups/root/facets"/>
              <relationships xlink:type="simple" xlink:title="Relationships"
                             xlink:href="/groups/root/relationships"/>
              <timetables xlink:href="/groups/root/timetables"
                          xlink:title="Own timetables"
                          xlink:type="simple"/>
              <timetables
                    xlink:href="/groups/root/composite-timetables"
                    xlink:title="Composite timetables"
                    xlink:type="simple"/>
              <calendar xlink:type="simple" xlink:title="Private calendar"
                        xlink:href="/groups/root/calendar"/>
              <calendar xlink:type="simple"
                        xlink:title="Calendar derived from timetables"
                        xlink:href="/groups/root/timetable-calendar"/>
            </group>
            """ % (getPath(self.per), getPath(self.sub)),
            recursively_sort=['group'])

    def test_traverse(self):
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.views.model import TreeView
        from schooltool.views.absence import RollCallView
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/group")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.group)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.providedBy(result.context))

        result = self.view._traverse("rollcall", request)
        self.assert_(isinstance(result, RollCallView))
        self.assert_(result.context is self.group)

        result = self.view._traverse("tree", request)
        self.assert_(isinstance(result, TreeView))
        self.assert_(result.context is self.group)

        result = self.view._traverse('timetables', request)
        self.assert_(isinstance(result, TimetableTraverseView))
        self.assert_(result.context is self.view.context)
        self.assert_(not result.readonly)

        self.assertRaises(KeyError, self.view._traverse, "otherthings",
                          request)


class TestTreeView(XMLCompareMixin, RegistriesSetupMixin, QuietLibxml2Mixin,
                   unittest.TestCase):

    def setUp(self):
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="root group")
        self.group1 = app['groups'].new("group1", title="group1")
        self.group2 = app['groups'].new("group2", title="group2")
        self.group1a = app['groups'].new("group1a", title="group1a")
        self.group1b = app['groups'].new("group1b", title="group1b")
        self.persona = app['persons'].new("a", title="a")

        Membership(group=self.group, member=self.group1)
        Membership(group=self.group, member=self.group2)
        Membership(group=self.group1, member=self.group1a)
        Membership(group=self.group1, member=self.group1b)
        Membership(group=self.group2, member=self.persona)

        self.setUpLibxml2()

    def test(self):
        from schooltool.views.model import TreeView
        view = TreeView(self.group)
        view.authorization = lambda ctx, rq: True
        request = RequestStub("http://localhost/groups/root/tree")
        result = view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <tree xmlns:xlink="http://www.w3.org/1999/xlink">
              <group xlink:type="simple" xlink:href="/groups/root"
                     xlink:title="root group">
                <group xlink:type="simple" xlink:href="/groups/group2"
                       xlink:title="group2">
                </group>
                <group xlink:type="simple" xlink:href="/groups/group1"
                       xlink:title="group1">
                  <group xlink:type="simple" xlink:href="/groups/group1a"
                         xlink:title="group1a">
                  </group>
                  <group xlink:type="simple" xlink:href="/groups/group1b"
                         xlink:title="group1b">
                  </group>
                </group>
              </group>
            </tree>
            """, recursively_sort=['tree'])


class TestPersonView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import PersonView
        from schooltool.model import Group, Person
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        self.group = app['groups'].new("root", title="group")
        self.sub = app['groups'].new("subgroup", title="subgroup")
        self.per = app['persons'].new("p", title="Pete")

        Membership(group=self.group, member=self.sub)
        Membership(group=self.group, member=self.per)
        Membership(group=self.sub, member=self.per)

        self.view = PersonView(self.per)
        self.view.authorization = lambda ctx, rq: True

    def test_traverse(self):
        from schooltool.views.model import PersonPasswordView
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.views.absence import AbsenceManagementView
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/person")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.providedBy(result.context))

        result = self.view._traverse('absences', request)
        self.assert_(isinstance(result, AbsenceManagementView))
        self.assert_(result.context is self.per)

        result = self.view._traverse('timetables', request)
        self.assert_(isinstance(result, TimetableTraverseView))
        self.assert_(result.context is self.view.context)
        self.assert_(not result.readonly)

        result = self.view._traverse('password', request)
        self.assert_(isinstance(result, PersonPasswordView))
        self.assert_(result.context is self.view.context)

    def test_render(self):
        request = RequestStub("http://localhost/person")
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <person xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>Pete</name>
              <groups>
                <item xlink:type="simple" xlink:href="/groups/root"
                      xlink:title="group"/>
                <item xlink:type="simple" xlink:href="/groups/subgroup"
                      xlink:title="subgroup"/>
              </groups>
              <relationships xlink:type="simple"
                             xlink:title="Relationships"
                             xlink:href="/persons/p/relationships"/>
              <facets xlink:type="simple" xlink:title="Facets"
                      xlink:href="/persons/p/facets"/>
              <timetables xlink:href="/persons/p/timetables"
                          xlink:title="Own timetables"
                          xlink:type="simple"/>
              <timetables xlink:href="/persons/p/composite-timetables"
                          xlink:title="Composite timetables"
                          xlink:type="simple"/>
              <calendar xlink:type="simple" xlink:title="Private calendar"
                        xlink:href="/persons/p/calendar"/>
              <calendar xlink:type="simple"
                        xlink:title="Calendar derived from timetables"
                        xlink:href="/persons/p/timetable-calendar"/>
            </person>
            """, recursively_sort=['groups'])


class TestPersonPasswordView(unittest.TestCase):

    def test_do_PUT(self):
        from schooltool.model import Person
        from schooltool.views.model import PersonPasswordView
        p = Person("John")
        v = PersonPasswordView(p)
        v.authorization = lambda ctx, rq: True

        passwd = """
        Foo bar
        """

        request = RequestStub(method="PUT", body=passwd)
        result = v.render(request)
        self.assertEqual(request.code, 200)
        self.assertEqual(result, "Password changed")
        self.assert_(p.checkPassword("Foo bar"))

    def test_do_DELETE(self):
        from schooltool.model import Person
        from schooltool.views.model import PersonPasswordView
        p = Person("John")
        p.setPassword("foo")
        v = PersonPasswordView(p)
        v.authorization = lambda ctx, rq: True
        request = RequestStub(method="DELETE")
        result = v.render(request)
        self.assertEqual(request.code, 200)
        self.assertEqual(result, "Account disabled")
        self.assert_(not p.checkPassword("foo"))


class TestResourceView(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        from schooltool.views.model import ResourceView
        from schooltool.model import Resource
        from schooltool.app import Application, ApplicationObjectContainer
        app = Application()
        app['resources'] = ApplicationObjectContainer(Resource)
        self.resource = app['resources'].new('room3', title='Room 3')

        self.view = ResourceView(self.resource)
        self.view.authorization = lambda ctx, rq: True

    def test_traverse(self):
        from schooltool.views.facet import FacetManagementView
        from schooltool.views.relationship import RelationshipsView
        from schooltool.views.timetable import TimetableTraverseView
        from schooltool.views.cal import BookingView
        from schooltool.interfaces import IFacetManager
        request = RequestStub("http://localhost/resources/room3")

        result = self.view._traverse('relationships', request)
        self.assert_(isinstance(result, RelationshipsView))
        self.assert_(result.context is self.resource)

        result = self.view._traverse('facets', request)
        self.assert_(isinstance(result, FacetManagementView))
        self.assert_(IFacetManager.providedBy(result.context))

        result = self.view._traverse('timetables', request)
        self.assert_(isinstance(result, TimetableTraverseView))
        self.assert_(result.context is self.view.context)
        self.assert_(result.readonly)

        result = self.view._traverse('booking', request)
        self.assert_(isinstance(result, BookingView))
        self.assert_(result.context is self.view.context)

    def test_render(self):
        request = RequestStub("http://localhost/resources/room3")
        result = self.view.render(request)
        self.assertEquals(request.headers['Content-Type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <resource xmlns:xlink="http://www.w3.org/1999/xlink">
              <title>Room 3</title>
              <relationships xlink:href="/resources/room3/relationships"
                             xlink:title="Relationships" xlink:type="simple"/>
              <facets xlink:href="/resources/room3/facets" xlink:title="Facets"
                      xlink:type="simple"/>
              <timetables xlink:href="/resources/room3/timetables"
                          xlink:title="Own timetables" xlink:type="simple"/>
              <timetables xlink:href="/resources/room3/composite-timetables"
                          xlink:title="Composite timetables"
                          xlink:type="simple"/>
              <calendar xlink:href="/resources/room3/calendar"
                        xlink:title="Private calendar" xlink:type="simple"/>
              <calendar xlink:href="/resources/room3/timetable-calendar"
                        xlink:title="Calendar derived from timetables"
                        xlink:type="simple"/>
            </resource>
            """)


class TestModuleSetup(RegistriesSetupMixin, unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup, IPerson, IResource
        from schooltool.views.model import GroupView, PersonView, ResourceView
        import schooltool.views.model
        schooltool.views.model.setUp()

        self.assert_(viewClass(IGroup) is GroupView)
        self.assert_(viewClass(IPerson) is PersonView)
        self.assert_(viewClass(IResource) is ResourceView)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplicationObjectTraverserView))
    suite.addTest(unittest.makeSuite(TestGroupView))
    suite.addTest(unittest.makeSuite(TestTreeView))
    suite.addTest(unittest.makeSuite(TestPersonView))
    suite.addTest(unittest.makeSuite(TestPersonPasswordView))
    suite.addTest(unittest.makeSuite(TestResourceView))
    suite.addTest(unittest.makeSuite(TestModuleSetup))
    return suite

if __name__ == '__main__':
    unittest.main()
