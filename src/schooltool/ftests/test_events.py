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
Functional tests for SchoolTool event system
"""

import unittest
from sets import Set

import transaction
from persistent import Persistent
from zope.interface import implements, Attribute
from schooltool.interfaces import IEvent, IEventTarget, IRelatable, ILocation
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.event import EventMixin


__metaclass__ = type


class IStudentEvent(IEvent):
    context = Attribute("Student")


class IArbitraryEvent(IEvent):
    context = Attribute("Context")


class ContextEvent(EventMixin):
    implements(IEvent)

    def __init__(self, context):
        EventMixin.__init__(self)
        self.context = context

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.context)


class StudentEvent(ContextEvent):
    implements(IStudentEvent)


class ArbitraryEvent(ContextEvent):
    implements(IArbitraryEvent)


class EventCatcher(Persistent):
    implements(IEventTarget, IRelatable, ILocation)

    def __init__(self):
        self.received = []
        self.__links__ = Set()

    def notify(self, event):
        self.received.append(event)


class TestEventSystem(RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpRegistries()

    def tearDown(self):
        transaction.abort()
        self.tearDownRegistries()

    def test(self):
        from ZODB.DB import DB
        from ZODB.MappingStorage import MappingStorage
        db = DB(MappingStorage())
        datamgr = db.open()
        transaction.begin()

        # Create some groups and persons and set up event routing tables:
        #
        #   root group (routes IStudentEvents to its members)
        #   `-- students group (routes all events to its parent)
        #   | `-- student1 "Fred" (routes all events to its parent)
        #   `-- another_listener (stores all received events)
        #
        from schooltool import model
        from schooltool.event import RouteToGroupsAction, RouteToMembersAction
        from schooltool.event import RouteToRelationshipsAction
        from schooltool.uris import URIGroup, URIMember
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.eventlog import EventLogFacet
        from schooltool.component import FacetManager
        from schooltool.membership import Membership
        import schooltool.membership

        schooltool.membership.setUp()

        app = Application()

        app['groups'] = ApplicationObjectContainer(model.Group)
        app['persons'] = ApplicationObjectContainer(model.Person)
        app['stubs'] = ApplicationObjectContainer(EventCatcher)
        Person = app['persons'].new
        Group = app['groups'].new
        EventCatcherFactory = app['stubs'].new

        root = Group(title="root")
        datamgr.root()['root'] = app
        root.eventTable.append(RouteToMembersAction(IStudentEvent))

        students = Group(title="students")
        students.eventTable.append(RouteToRelationshipsAction(URIGroup))
        Membership(group=root, member=students)

        student1 = Person(title="Fred")
        student1.eventTable.append(RouteToGroupsAction(IEvent))
        Membership(group=students, member=student1)
        event_log_facet = EventLogFacet()
        FacetManager(student1).setFacet(event_log_facet)

        misc_group = Group(title="misc")
        misc_group.eventTable.append(RouteToRelationshipsAction(URIMember))
        Membership(group=root, member=misc_group)

        another_listener = EventCatcherFactory()
        Membership(group=misc_group, member=another_listener)

        # We want to forget the event of our addition
        another_listener.received = []

        # Create another event listener, not attached to the containment
        # hierarchy, and subscribe it to the global event service
        from schooltool.component import getEventService
        event_log = EventCatcherFactory()
        getEventService(app).subscribe(event_log, IEvent)

        transaction.commit()

        # Dispatch two events on student1 and watch their progress
        event1 = StudentEvent(student1)
        event1.dispatch(event1.context)
        event_log_facet.active = False
        event2 = ArbitraryEvent(student1)
        event2.dispatch(event2.context)

        # event log should receive all events
        self.assertEquals(event_log.received, [event1, event2])

        # another_listener only receives IStudentEvents routed through the
        # root group
        self.assertEquals(another_listener.received, [event1])

        # facets should receive events too (when they're active)
        self.assertEquals(
            [event for ts, event in event_log_facet.getReceived()],
            [event1])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventSystem))
    return suite

if __name__ == '__main__':
    unittest.main()
