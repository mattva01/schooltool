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
Unit tests for schooltool.event

$Id$
"""

import unittest
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IEvent

__metaclass__ = type


class TargetStub:
    events = ()

    def notify(self, event):
        self.events += (event, )

class TestEventMixin(unittest.TestCase):

    def test(self):
        from schooltool.event import EventMixin
        from schooltool.interfaces import IEvent
        e = EventMixin()
        verifyObject(IEvent, e)

    def test_dispatch(self):
        from schooltool.event import EventMixin
        target = TargetStub()
        e = EventMixin()
        e.dispatch(target)
        self.assertEquals(target.events, (e, ))

    def test_dispatch_repeatedly(self):
        from schooltool.event import EventMixin
        target = TargetStub()
        e = EventMixin()
        e.dispatch(target)
        e.dispatch(target)
        e.dispatch(target)
        self.assertEquals(target.events, (e, ))


class IEventA(IEvent):
    pass

class IEventB(IEvent):
    pass

class EventAStub:
    implements(IEventA)

    def __init__(self):
        self.dispatched_to = []

    def dispatch(self, target):
        self.dispatched_to.append(target)

class EventActionStub:
    def __init__(self, evtype):
        self.eventType = evtype
        self.calls = []

    def handle(self, event, target):
        self.calls.append((event, target))

class TestEventTargetMixin(unittest.TestCase):

    def test(self):
        from schooltool.event import EventTargetMixin
        from schooltool.interfaces import IEventTarget, IEventConfigurable
        et = EventTargetMixin()
        verifyObject(IEventTarget, et)
        verifyObject(IEventConfigurable, et)
        self.assertEquals(list(et.eventTable), [])

    def test_handle(self):
        from schooltool.event import EventTargetMixin
        et = EventTargetMixin()
        handler_a = EventActionStub(IEventA)
        handler_b = EventActionStub(IEventB)
        et.eventTable.extend([handler_a, handler_b])
        event = EventAStub()
        et.notify(event)
        self.assertEqual(handler_a.calls, [(event, et)])
        self.assertEqual(handler_b.calls, [])


class TestEventActionMixins(unittest.TestCase):

    def test(self):
        from schooltool.event import EventActionMixin
        from schooltool.interfaces import IEventAction
        marker = object()
        ea = EventActionMixin(marker)
        verifyObject(IEventAction, ea)
        self.assertEquals(ea.eventType, marker)
        self.assertRaises(NotImplementedError, ea.handle, None, None)

    def testLookupAction(self):
        from schooltool.event import LookupAction
        from schooltool.interfaces import ILookupAction
        la = LookupAction()
        verifyObject(ILookupAction, la)
        self.assertEquals(list(la.eventTable), [])
        self.assertEquals(la.eventType, IEvent)

        handler_a = EventActionStub(IEventA)
        handler_b = EventActionStub(IEventB)
        la = LookupAction(eventType=IEventA, eventTable=[handler_a, handler_b])
        self.assertEquals(la.eventType, IEventA)
        event = EventAStub()
        target = object()
        la.handle(event, target)
        self.assertEqual(handler_a.calls, [(event, target)])
        self.assertEqual(handler_b.calls, [])

    def testRouteToMembersAction(self):
        from schooltool.event import RouteToMembersAction
        from schooltool.interfaces import IRouteToMembersAction
        action = RouteToMembersAction(IEventA)
        verifyObject(IRouteToMembersAction, action)
        self.assertEquals(action.eventType, IEventA)

        event = EventAStub()
        child1, child2 = object(), object()
        target = {1: child1, 2: child2}
        action.handle(event, target)
        dispatched_to = event.dispatched_to
        members = [child1, child2]
        members.sort()
        dispatched_to.sort()
        self.assertEquals(dispatched_to, members)

    def testRouteToGroupsAction(self):
        from schooltool.event import RouteToGroupsAction
        from schooltool.interfaces import IRouteToGroupsAction
        action = RouteToGroupsAction(IEventA)
        verifyObject(IRouteToGroupsAction, action)
        self.assertEquals(action.eventType, IEventA)

        class MemberStub:
            def __init__(self, groups):
                self._groups = groups
            def groups(self):
                return self._groups

        event = EventAStub()
        group1, group2 = object(), object()
        target = MemberStub(groups=[group1, group2])
        action.handle(event, target)
        dispatched_to = event.dispatched_to
        groups = [group1, group2]
        groups.sort()
        dispatched_to.sort()
        self.assertEquals(dispatched_to, groups)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventMixin))
    suite.addTest(unittest.makeSuite(TestEventTargetMixin))
    suite.addTest(unittest.makeSuite(TestEventActionMixins))
    return suite

if __name__ == '__main__':
    unittest.main()
