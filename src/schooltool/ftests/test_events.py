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
from zope.interface import implements, Attribute
from schooltool.interfaces import IEvent, IEventTarget
from schooltool.event import EventMixin
from schooltool.model import GroupMember
from transaction import get_transaction

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


class EventCatcher(GroupMember):
    implements(IEventTarget)

    def __init__(self):
        GroupMember.__init__(self)
        self.received = []

    def notify(self, event):
        self.received.append(event)


class TestEventSystem(unittest.TestCase):

    def test(self):
        from zodb.db import DB
        from zodb.storage.mapping import MappingStorage
        db = DB(MappingStorage())
        datamgr = db.open()

        # Create some groups and persons and set up event routing tables:
        #
        #   root group (routes IStudentEvents to its members)
        #   `-- students group (routes all events to its parent)
        #   | `-- Fred person (routes all events to its parent)
        #   `-- another_listener (stores all received events)
        #
        from schooltool.model import RootGroup, Group, Person
        from schooltool.event import RouteToGroupsAction, RouteToMembersAction
        root = RootGroup("root")
        datamgr.root()['root'] = root
        datamgr.add(root)
        root.eventTable.append(RouteToMembersAction(IStudentEvent))

        students = Group("students")
        students.eventTable.append(RouteToGroupsAction(IEvent))
        root.add(students)

        student1 = Person("Fred")
        student1.eventTable.append(RouteToGroupsAction(IEvent))
        students.add(student1)

        another_listener = EventCatcher()
        root.add(another_listener)

        # Create another event listener, not attached to the containment
        # hierarchy, and subscribe it to the global event service
        from schooltool.component import getEventService
        event_log = EventCatcher()
        getEventService(root).subscribe(event_log, IEvent)

        get_transaction().commit()

        # Dispatch two events on student1 and watch their progress
        event1 = StudentEvent(student1)
        event1.dispatch(event1.context)
        event2 = ArbitraryEvent(student1)
        event2.dispatch(event2.context)

        # event log should receive all events
        self.assertEquals(event_log.received, [event1, event2])

        # another_listener only receives IStudentEvents routed through the
        # root group
        self.assertEquals(another_listener.received, [event1])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventSystem))
    return suite

if __name__ == '__main__':
    unittest.main()
